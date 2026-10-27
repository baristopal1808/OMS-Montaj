"""Uyarılar: ERP verisinden çıkan, ürün kartlarında ve Yapılacaklar'da görünen uyarılar.

Eksik malzeme: "Çıkış yapılamayan malzeme" raporu açık iş emirlerinin bütün malzeme satırlarını verir;
planlanan takip miktarı gerçekleşen çıkıştan büyükse malzeme eksiktir (eksik = plan - çıkış). Rapor her
yüklemede baştan yazılır (ERP'nin bugünkü hâli); iş emri kapanınca eksikleri de listeden düşer. Malzeme
depoda varsa (yalnızca çıkışı yapılmamışsa) sarı, depoda yoksa kırmızı görünür. Ekibe iş emri başına bir
kez sorulur ("12 malzemenin çıkışı yapılmamış, bilginiz var mı?"); cevaptan sonra yeni bir malzeme eksik
görünür ya da eksik miktarı artarsa yeniden sorulur. "Takip etme" denen iş emirleri sorulmaz.

İmalattan beklenen yarı mamuller: envanter türü "Yarı Mamul" olan eksikler imalat fabrikasından geliyor; ERP'de
çıkışları yapılmadığı için hep "depoda yok" görünürler (kullanıcı, 26/10/2026). Bunlar eksik malzemeden ayrı
gösterilir ve sorulmaz; ekip geldiklerinde parça parça ya da kırılımın tamamı için "Geldi" işaretler (kim, ne
zaman saklanır). İşaretler rapor yeniden yüklense de kalır; ERP'de çıkışı yapılan yarı mamul listeden kendiliğinden düşer.

"İmalatta" uyarısı: ürünün iş emri stoğa girmeye başlamış (kısmen ya da tamamen) ama planlama biriminin
ERP'deki ürün durumu hâlâ "İmalatta" ise (imalat fabrikası başka yerleşkede; ERP geç güncellenebiliyor)
ürünün kartında uyarı görünür; aynı üründen birden çok olsa da her ürün ve iş emri için ayrı sorulur. ERP'deki
durum değişince uyarı kendiliğinden kalkar.

Uygunsuzluk ve DÖF uyarıları ileride buraya eklenir.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime

from .erp_aktarim import IPTAL, KAPALI

EKSIK_CEVAPLARI = {
    "bekleniyor": "Biliyorum, bekleniyor",
    "etkilemiyor": "Montajı etkilemiyor",
    "bildirildi": "Depoya / satın almaya bildirdim",
    "erp_hatasi": "ERP'de hata var",
}
IMALATTA = "İmalatta"
IMALATTA_CEVAPLARI = {
    "montajda": "Ürün montajda ya da tamamlandı; ERP güncel değil",
    "imalatta": "ERP doğru, ürün imalatta",
}
DEPOLAR = {
    "montaj_depo": "Montaj depo",
    "montaj_uretim_depo": "Montaj üretim depo",
    "sevk_depo": "Sevk depo",
    "uretim_depo": "Üretim depo",
    "ana_urun_depo": "Ana ürün depo",
}
DEPO_DURUMLARI = {"var": "Depoda var, çıkışı yapılmamış", "kismen": "Bir kısmı depoda", "yok": "Depoda yok"}
YARI_MAMUL = "Yarı Mamul"  # imalat fabrikasından gelir; ERP'de çıkışı yapılmıyor


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Eksik malzeme

def yari_mamul_mu(malzeme):
    return malzeme["envanter_turu"] == YARI_MAMUL


def eksik_miktari(malzeme):
    return (malzeme["plan_miktar"] or 0) - (malzeme["cikis_miktar"] or 0)


def depo_durumu(malzeme):
    """'var' (eksiğin tamamı depoda), 'kismen' ya da 'yok'."""
    eldeki = malzeme["eldeki"] or 0
    return "var" if eldeki >= eksik_miktari(malzeme) else "kismen" if eldeki > 0 else "yok"


def depolar(malzeme):
    """Malzemenin bulunduğu depolar: [(depo adı, miktar)]."""
    return [(ad, malzeme[alan]) for alan, ad in DEPOLAR.items() if (malzeme[alan] or 0) > 0]


def eksikleri_isle(vt, kayitlar, yukleme_id):
    """Raporu baştan yazar (yalnızca eksik satırlar saklanır); ne bulunduğunu sayan bir Counter döndürür."""
    sayac = Counter(satir=len(kayitlar))
    vt.execute("DELETE FROM eksik_malzemeler")
    bilinen = {r[0] for r in vt.execute("SELECT is_emri_no FROM is_emirleri")}
    ieler, bilinmeyen = set(), set()
    for kayit in kayitlar:
        if eksik_miktari(kayit) <= 0:
            continue
        if yari_mamul_mu(kayit):
            sayac["yari_mamul"] += 1
        else:
            sayac["eksik"] += 1
            sayac["depoda"] += (kayit["eldeki"] or 0) >= eksik_miktari(kayit)
        ieler.add(kayit["is_emri_no"])
        if kayit["is_emri_no"] not in bilinen:
            bilinmeyen.add(kayit["is_emri_no"])
        vt.execute(
            "INSERT INTO eksik_malzemeler (is_emri_no, sira_no, malzeme_kodu, malzeme_adi, envanter_turu, birim,"
            " plan_miktar, cikis_miktar, eldeki, ana_urun_depo, uretim_depo, montaj_depo, montaj_uretim_depo, sevk_depo,"
            " yukleme_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kayit["is_emri_no"], kayit["sira_no"], kayit["malzeme_kodu"], kayit["malzeme_adi"], kayit["envanter_turu"],
             kayit["birim"], kayit["plan_miktar"], kayit["cikis_miktar"], kayit["eldeki"], kayit["ana_urun_depo"],
             kayit["uretim_depo"], kayit["montaj_depo"], kayit["montaj_uretim_depo"], kayit["sevk_depo"], yukleme_id),
        )
    sayac["is_emri"], sayac["bilinmeyen"] = len(ieler), len(bilinmeyen)
    return sayac


def eksik_ozeti(sayac):
    parcalar = [f"{sayac['satir']} satır okundu"]
    if sayac["eksik"] or sayac["yari_mamul"]:
        parcalar.append(f"{sayac['is_emri']} iş emrinde {sayac['eksik']} malzemenin çıkışı yapılmamış"
                        f" ({sayac['depoda']} tanesi depoda var)")
        if sayac["yari_mamul"]:
            parcalar.append(f"ayrıca {sayac['yari_mamul']} yarı mamul imalattan bekleniyor")
    else:
        parcalar.append("çıkışı yapılmamış malzeme yok")
    ozet = "; ".join(parcalar) + "."
    if sayac["bilinmeyen"]:
        ozet += (f" {sayac['bilinmeyen']} iş emri iş emirleri listesinde yok; listeyi de yüklerseniz hangi ürüne ait"
                 " olduğu görünür.")
    return ozet


def _imza(malzemeler):
    """Eksiklerin (yarı mamuller hariç) karşılaştırılabilir hâli: {"sıra|malzeme": eksik miktarı}."""
    imza = Counter()
    for m in malzemeler:
        if not yari_mamul_mu(m):
            imza[f"{m['sira_no']}|{m['malzeme_kodu']}"] += eksik_miktari(m)
    return dict(imza)


def _gelenler(vt, is_emri_nolari):
    """"Geldi" işaretlenen yarı mamuller: {(iş emri no, sıra no, malzeme kodu): işaret}."""
    nolar = list(is_emri_nolari)
    if not nolar:
        return {}
    return {(g["is_emri_no"], g["sira_no"], g["malzeme_kodu"]): g for g in vt.execute(
        "SELECT y.*, k.ad_soyad FROM gelen_yari_mamuller y LEFT JOIN kullanicilar k ON k.id = y.kullanici_id"
        f" WHERE y.is_emri_no IN ({', '.join('?' * len(nolar))})",
        nolar,
    )}


def eksik_ozetleri(vt, is_emri_nolari=None):
    """İş emri no → {"toplam", "var", "kismen", "yok" (satın alınan eksik malzemeler), "yari_mamul" (imalattan
    beklenen, "geldi" işaretlenmemiş yarı mamuller), "gelen", "cevap" (son cevap ya da None), "bekliyor"}.
    Soru yalnızca satın alınan malzemeler için sorulur; cevaptan sonra yeni bir malzeme eksik görünürse ya da
    eksik miktarı artarsa yeniden "bekliyor" olur."""
    malzemeler = defaultdict(list)
    sorgu, degerler = "SELECT * FROM eksik_malzemeler", ()
    if is_emri_nolari is not None:
        nolar = list(is_emri_nolari)
        sorgu += f" WHERE is_emri_no IN ({', '.join('?' * len(nolar))})"
        degerler = nolar
    for m in vt.execute(sorgu, degerler):
        malzemeler[m["is_emri_no"]].append(m)
    if not malzemeler:
        return {}
    yer = ", ".join("?" * len(malzemeler))
    cevaplar = {c["is_emri_no"]: c for c in vt.execute(
        "SELECT c.*, k.ad_soyad FROM eksik_cevaplari c LEFT JOIN kullanicilar k ON k.id = c.kullanici_id"
        f" WHERE c.id IN (SELECT MAX(id) FROM eksik_cevaplari WHERE is_emri_no IN ({yer}) GROUP BY is_emri_no)",
        list(malzemeler),
    )}
    gelenler = _gelenler(vt, malzemeler)
    sonuc = {}
    for no, liste in malzemeler.items():
        satin_alinan = [m for m in liste if not yari_mamul_mu(m)]
        yari = [m for m in liste if yari_mamul_mu(m)]
        gelen = sum(1 for m in yari if (no, m["sira_no"], m["malzeme_kodu"]) in gelenler)
        cevap = cevaplar.get(no)
        onceki = json.loads(cevap["eksikler"]) if cevap else None
        bekliyor = bool(satin_alinan) and (onceki is None or any(
            miktar > onceki.get(anahtar, 0) + 1e-9 for anahtar, miktar in _imza(satin_alinan).items()
        ))
        durumlar = Counter(depo_durumu(m) for m in satin_alinan)
        sonuc[no] = {"toplam": len(satin_alinan), "var": durumlar["var"], "kismen": durumlar["kismen"],
                     "yok": durumlar["yok"], "yari_mamul": len(yari) - gelen, "gelen": gelen,
                     "cevap": cevap, "bekliyor": bekliyor}
    return sonuc


def is_emri_eksikleri(vt, is_emri_no):
    """İş emrinin eksikleri, kırılım kırılım: [{"sira", "ad", "malzemeler" (satın alınan), "depoda_olmayan",
    "yari_mamuller" (imalattan; her birinde "geldi": işaret ya da None), "bekleyen" (gelmemiş yarı mamul sayısı)}]."""
    ie = vt.execute("SELECT id, urun_adi FROM is_emirleri WHERE is_emri_no = ?", (is_emri_no,)).fetchone()
    adlar = {}
    if ie:
        adlar[0] = ie["urun_adi"]
        for r in vt.execute("SELECT sira_no, urun_adi FROM is_emri_satirlari WHERE is_emri_id = ?", (ie["id"],)):
            adlar[r["sira_no"]] = r["urun_adi"]
    gelenler = _gelenler(vt, [is_emri_no])
    gruplar = {}
    for m in vt.execute("SELECT * FROM eksik_malzemeler WHERE is_emri_no = ? ORDER BY sira_no, malzeme_kodu", (is_emri_no,)):
        grup = gruplar.setdefault(m["sira_no"], {"sira": m["sira_no"], "ad": adlar.get(m["sira_no"]),
                                                 "malzemeler": [], "yari_mamuller": [], "bekleyen": 0})
        if yari_mamul_mu(m):
            geldi = gelenler.get((is_emri_no, m["sira_no"], m["malzeme_kodu"]))
            grup["yari_mamuller"].append({**dict(m), "geldi": geldi})
            grup["bekleyen"] += not geldi
        else:
            grup["malzemeler"].append(m)
    for grup in gruplar.values():
        grup["depoda_olmayan"] = sum(1 for m in grup["malzemeler"] if depo_durumu(m) != "var")
    return [gruplar[sira] for sira in sorted(gruplar)]


def yari_mamul_isaretle(vt, is_emri_no, anahtarlar, kullanici_id):
    """Yarı mamulleri "geldi" işaretler; anahtarlar: [(sıra no, malzeme kodu)]."""
    zaman = _simdi()
    vt.executemany(
        "INSERT OR IGNORE INTO gelen_yari_mamuller (is_emri_no, sira_no, malzeme_kodu, kullanici_id, zaman)"
        " VALUES (?, ?, ?, ?, ?)",
        [(is_emri_no, sira, kod, kullanici_id, zaman) for sira, kod in anahtarlar],
    )


def yari_mamul_geri_al(vt, is_emri_no, sira, kod):
    vt.execute("DELETE FROM gelen_yari_mamuller WHERE is_emri_no = ? AND sira_no = ? AND malzeme_kodu = ?",
               (is_emri_no, sira, kod))


def bekleyen_eksikler(vt):
    """Sorulacak iş emirleri (eksik malzemesi olan, cevaplanmamış ya da yeni eksik gelmiş): [(iş emri, özet)].
    Siparişe bağlı olanlar önce. "Takip etme" denen iş emirleri sorulmaz."""
    ozetler = {no: o for no, o in eksik_ozetleri(vt).items() if o["bekliyor"]}
    if not ozetler:
        return []
    ieler = vt.execute(
        "SELECT i.*, s.siparis_no, k.sira_no AS kalem_sira FROM is_emirleri i"
        " LEFT JOIN siparisler s ON s.id = i.siparis_id LEFT JOIN siparis_kalemleri k ON k.id = i.kalem_id"
        f" WHERE i.is_emri_no IN ({', '.join('?' * len(ozetler))}) AND COALESCE(i.baglanti, '') != 'yok_sayildi'"
        " ORDER BY i.siparis_id IS NULL, s.siparis_no, i.acilis_tarihi, i.is_emri_no",
        list(ozetler),
    ).fetchall()
    return [(ie, ozetler[ie["is_emri_no"]]) for ie in ieler]


def eksik_cevapla(vt, is_emri_no, cevap, kullanici_id):
    """Cevabı, o anki eksiklerle (yarı mamuller hariç) birlikte saklar (sonra yeni eksik gelirse yeniden sorulsun diye)."""
    liste = vt.execute("SELECT * FROM eksik_malzemeler WHERE is_emri_no = ?", (is_emri_no,)).fetchall()
    vt.execute(
        "INSERT INTO eksik_cevaplari (is_emri_no, cevap, eksikler, kullanici_id, zaman) VALUES (?, ?, ?, ?, ?)",
        (is_emri_no, cevap, json.dumps(_imza(liste)), kullanici_id, _simdi()),
    )


# "İmalatta" uyarısı

def imalatta_uyarilari(vt, siparis_id=None, urun_id=None):
    """İş emri stoğa girmeye başlamış ama ERP ürün durumu "İmalatta" olan açık ürünler, ekibin cevabıyla."""
    kosullar, degerler = [], [IMALATTA, IPTAL, KAPALI, KAPALI]
    if siparis_id is not None:
        kosullar.append(" AND k.siparis_id = ?")
        degerler.append(siparis_id)
    if urun_id is not None:
        kosullar.append(" AND u.id = ?")
        degerler.append(urun_id)
    return vt.execute(
        "SELECT u.id AS urun_id, u.adet_sira, u.seri_no, i.id AS is_emri_id, i.is_emri_no, i.durum AS ie_durum,"
        " i.gercek_miktar, i.plan_miktar, i.ilk_stok_giris, k.urun_kodu, k.urun_adi, k.aile, k.miktar, k.sira_no,"
        " k.siparis_id, s.siparis_no, s.musteri, c.cevap, c.zaman AS cevap_zamani, kk.ad_soyad AS cevaplayan"
        " FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id"
        " JOIN is_emirleri i ON i.id = u.is_emri_id"
        " LEFT JOIN imalatta_cevaplari c ON c.urun_id = u.id AND c.is_emri_id = i.id"
        " LEFT JOIN kullanicilar kk ON kk.id = c.kullanici_id"
        " WHERE COALESCE(i.gercek_miktar, 0) > 0 AND k.erp_urun_durumu = ? AND u.asama != 'sevk_edildi'"
        " AND COALESCE(k.erp_durum, '') NOT IN (?, ?) AND COALESCE(k.erp_genel_durum, '') != ? AND s.erp_listede = 1"
        + "".join(kosullar) + " ORDER BY s.siparis_no, k.sira_no, u.adet_sira",
        degerler,
    ).fetchall()


def bekleyen_imalatta(vt):
    return [u for u in imalatta_uyarilari(vt) if not u["cevap"]]


def imalatta_cevapla(vt, urun_id, is_emri_id, cevap, kullanici_id):
    vt.execute(
        "INSERT INTO imalatta_cevaplari (urun_id, is_emri_id, cevap, kullanici_id, zaman) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT (urun_id, is_emri_id) DO UPDATE SET cevap = excluded.cevap, kullanici_id = excluded.kullanici_id,"
        " zaman = excluded.zaman",
        (urun_id, is_emri_id, cevap, kullanici_id, _simdi()),
    )
