"""Eşleştirici: ERP okuyucunun kayıtlarını veritabanına işler.

Her yüklemede ERP'deki satırlar uygulamadaki kayıtlarla karşılaştırılır: yeni
sipariş ve kalemler eklenir, değişen ERP alanları güncellenir. ERP verisi
yalnızca ERP'den gelen alanları değiştirir; ekibin girdiği bilgilere (aşama,
ileride notlar ve kontrol listesi) dokunmaz.

Kart ve servis satırlarının her adedi için bir ürün kartı açılır. Satır
uygulamaya ilk kez kapanmış (sevk edilmiş) olarak geliyorsa kartı doğrudan
"Sevk edildi" aşamasında açılır; açıkken bilinen bir satırın kapanması ise
kartı değiştirmez (kullanıcıya sorulması planın 5. adımında).
"""

from collections import Counter, defaultdict

from .urun_kurallari import KARTLI_TURLER, satir_turu, seri_nolar, siparis_tipi

IPTAL = "İptal"
KAPALI = "Kapalı"
BEKLEMEDE = "Beklemede"  # onay bekleyen sipariş satırı
KALEM_ALANLARI = (
    "urun_kodu", "urun_adi", "miktar", "sevk_miktari", "birim", "aciklama", "planlama_bilgisi",
    "bagli_is_emri_no", "erp_durum", "erp_genel_durum", "erp_urun_durumu", "detay_turu",
    "teslim_tarihi", "ilk_sevk_tarihi", "son_sevk_tarihi", "tur", "aile", "siparis_aciklama",
)


def kapali_mi(kalem):
    return kalem["erp_genel_durum"] == KAPALI or kalem["erp_durum"] == KAPALI


def siparis_bilgileri(kayitlar):
    """Sipariş başına üst bilgiler. İptal edilmemiş satırlardan alınır: yanlış girilip iptal edilen
    satırların notu ("Yanlış") ve tarihleri siparişin kendisini anlatmaz."""
    gruplar = defaultdict(list)
    for kayit in kayitlar:
        gruplar[kayit["siparis_no"]].append(kayit)
    bilgiler = {}
    for siparis_no, satirlar in gruplar.items():
        gecerli = [k for k in satirlar if k["erp_durum"] != IPTAL] or satirlar

        def ilk(alan):
            return next((k[alan] for k in gecerli if k[alan]), None)

        servis = any(satir_turu(k["urun_kodu"], k["detay_turu"])[0] == "servis" for k in gecerli)
        bilgiler[siparis_no] = {
            "musteri": ilk("musteri"),
            "tip": siparis_tipi(ilk("detay_turu")) or ("servis" if servis else None),
            "talep_tarihi": ilk("talep_tarihi"),
            "notu": ilk("siparis_aciklama"),
        }
    return bilgiler


def _siparis_id(vt, siparis_no, bilgi, yukleme_id, sayac):
    satir = vt.execute("SELECT id FROM siparisler WHERE siparis_no = ?", (siparis_no,)).fetchone()
    if satir is None:
        sayac["yeni_siparis"] += 1
        return vt.execute(
            "INSERT INTO siparisler (siparis_no, musteri, tip, talep_tarihi, notu, ilk_yukleme_id, son_yukleme_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (siparis_no, bilgi["musteri"], bilgi["tip"], bilgi["talep_tarihi"], bilgi["notu"], yukleme_id, yukleme_id),
        ).lastrowid
    # Not her yüklemede listedeki hâline getirilir; ERP'de silinen not uygulamada da kalkar.
    vt.execute(
        "UPDATE siparisler SET musteri = COALESCE(?, musteri), tip = COALESCE(?, tip),"
        " talep_tarihi = COALESCE(?, talep_tarihi), notu = ?, son_yukleme_id = ? WHERE id = ?",
        (bilgi["musteri"], bilgi["tip"], bilgi["talep_tarihi"], bilgi["notu"], yukleme_id, satir["id"]),
    )
    return satir["id"]


def _urunleri_ac(vt, kalem_id, alanlar, ilk_kez, sayac):
    adet = max(1, round(alanlar["miktar"] or 1))
    seriler = seri_nolar(alanlar["planlama_bilgisi"])
    mevcut = {
        u["adet_sira"]: u
        for u in vt.execute("SELECT id, adet_sira, seri_no FROM urunler WHERE kalem_id = ?", (kalem_id,))
    }
    for sira in range(1, adet + 1):
        seri = seriler[sira - 1] if sira <= len(seriler) else None
        urun = mevcut.get(sira)
        if urun is None:
            asama = "sevk_edildi" if ilk_kez and kapali_mi(alanlar) else "siparis"
            vt.execute(
                "INSERT INTO urunler (kalem_id, adet_sira, seri_no, asama) VALUES (?, ?, ?, ?)",
                (kalem_id, sira, seri, asama),
            )
            sayac["yeni_urun"] += 1
        elif seri and urun["seri_no"] != seri:
            vt.execute("UPDATE urunler SET seri_no = ? WHERE id = ?", (seri, urun["id"]))
            sayac["seri_guncellenen"] += 1


def eksik_siralar(siralar):
    """Bir siparişin satır numaralarında atlananlar: {1, 2, 4, 7} → [3, 5, 6]."""
    siralar = set(siralar)
    return sorted(set(range(1, max(siralar, default=0) + 1)) - siralar)


def tekillestir(kayitlar):
    """Aynı sipariş satırı listede iki kez geçebiliyor (iptal edilip aynı sıra numarasıyla yeniden
    girilmiş): iptal edilmemiş kayıt geçerlidir; ikisi de aynı durumdaysa sonraki."""
    secilen = {}
    for kayit in kayitlar:
        anahtar = (kayit["siparis_no"], kayit["sira_no"])
        onceki = secilen.get(anahtar)
        if onceki is None or not (kayit["erp_durum"] == IPTAL and onceki["erp_durum"] != IPTAL):
            secilen[anahtar] = kayit
    return list(secilen.values())


def listede_olmayanlari_isaretle(vt, gorulen_siparisler):
    """En son yüklenen listeler gerçeği gösterir: açık olup listede bulunmayan siparişler gizlenir,
    listede yeniden görünenler geri gelir. (gizlenen, geri gelen) sayılarını döndürür."""
    gizlenen = geri_gelen = 0
    for siparis in vt.execute("SELECT id, siparis_no, erp_listede FROM siparisler").fetchall():
        listede = siparis["siparis_no"] in gorulen_siparisler
        if listede and not siparis["erp_listede"]:
            geri_gelen += 1
        elif not listede and siparis["erp_listede"]:
            acik = vt.execute(
                "SELECT 1 FROM siparis_kalemleri WHERE siparis_id = ? AND COALESCE(erp_durum, '') NOT IN (?, ?)"
                " AND COALESCE(erp_genel_durum, '') != ?",
                (siparis["id"], IPTAL, KAPALI, KAPALI),
            ).fetchone()
            if not acik:
                continue
            gizlenen += 1
        else:
            continue
        vt.execute("UPDATE siparisler SET erp_listede = ? WHERE id = ?", (int(listede), siparis["id"]))
    return gizlenen, geri_gelen


def siparisleri_isle(vt, kayitlar, yukleme_id):
    """Sipariş talepleri kayıtlarını işler; ne yapıldığını sayan bir Counter döndürür."""
    sayac = Counter(satir=len(kayitlar))
    kayitlar = tekillestir(kayitlar)
    # Satır numarası atlanan siparişler: ERP'den liste alınırken bir süzgeç uygulanmış olabilir.
    siralar = {}
    for kayit in kayitlar:
        siralar.setdefault(kayit["siparis_no"], []).append(kayit["sira_no"])
    for liste in siralar.values():
        if eksik := eksik_siralar(liste):
            sayac["eksik_sirali_siparis"] += 1
            sayac["eksik_sira"] += len(eksik)
    siparis_idleri = {
        siparis_no: _siparis_id(vt, siparis_no, bilgi, yukleme_id, sayac)
        for siparis_no, bilgi in siparis_bilgileri(kayitlar).items()
    }
    for kayit in kayitlar:
        tur, aile = satir_turu(kayit["urun_kodu"], kayit["detay_turu"])
        siparis_id = siparis_idleri[kayit["siparis_no"]]
        alanlar = {alan: kayit.get(alan) for alan in KALEM_ALANLARI}
        alanlar.update(tur=tur, aile=aile, miktar=kayit["miktar"] or 0)

        eski = vt.execute(
            "SELECT * FROM siparis_kalemleri WHERE siparis_id = ? AND sira_no = ?", (siparis_id, kayit["sira_no"])
        ).fetchone()
        if eski is None:
            kalem_id = vt.execute(
                f"INSERT INTO siparis_kalemleri (siparis_id, sira_no, son_yukleme_id, {', '.join(KALEM_ALANLARI)})"
                f" VALUES (?, ?, ?, {', '.join('?' * len(KALEM_ALANLARI))})",
                (siparis_id, kayit["sira_no"], yukleme_id, *alanlar.values()),
            ).lastrowid
            sayac["yeni_kalem"] += 1
        else:
            kalem_id = eski["id"]
            if any(eski[alan] != alanlar[alan] for alan in KALEM_ALANLARI):
                sayac["guncellenen_kalem"] += 1
                if eski["erp_durum"] != IPTAL and alanlar["erp_durum"] == IPTAL:
                    sayac["iptal_edilen"] += 1
                if not kapali_mi(eski) and kapali_mi(alanlar):
                    sayac["kapanan"] += 1
            vt.execute(
                f"UPDATE siparis_kalemleri SET {', '.join(f'{alan} = ?' for alan in KALEM_ALANLARI)},"
                " son_yukleme_id = ? WHERE id = ?",
                (*alanlar.values(), yukleme_id, kalem_id),
            )

        if tur in KARTLI_TURLER and alanlar["erp_durum"] != IPTAL:
            _urunleri_ac(vt, kalem_id, alanlar, eski is None, sayac)
    return sayac


def siparis_ozeti(sayac):
    """Yükleme sonucunun bir cümlelik özeti."""
    parcalar = [f"{sayac['satir']} satır okundu"]
    yeniler = [
        f"{sayac[anahtar]} {ad}"
        for anahtar, ad in (("yeni_siparis", "sipariş"), ("yeni_kalem", "kalem"), ("yeni_urun", "ürün kartı"))
        if sayac[anahtar]
    ]
    if yeniler:
        parcalar.append("yeni: " + ", ".join(yeniler))
    for anahtar, ad in (
        ("guncellenen_kalem", "kalem güncellendi"),
        ("kapanan", "kalem ERP'de kapandı"),
        ("iptal_edilen", "kalem iptal edildi"),
        ("seri_guncellenen", "seri no güncellendi"),
    ):
        if sayac[anahtar]:
            parcalar.append(f"{sayac[anahtar]} {ad}")
    if len(parcalar) == 1:
        parcalar.append("değişiklik yok")
    ozet = "; ".join(parcalar) + "."
    if sayac["eksik_sira"]:
        ozet += (
            f" Uyarı: {sayac['eksik_sirali_siparis']} siparişte toplam {sayac['eksik_sira']} satır listede yok"
            " (satır numaraları atlanıyor). ERP'den liste alınırken bir süzgeç uygulanmış olabilir."
        )
    return ozet
