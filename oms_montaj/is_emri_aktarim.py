"""İş emirleri: açık ve kapalı iş emirleri listelerinin işlenmesi ve sipariş satırlarına bağlanması.

Her iş emrinin 0. satırı ana üründür, diğer satırları kırılımlarıdır (alt montajlar,
işlemler). ERP alanları her yüklemede güncellenir; kullanıcının elle kurduğu
bağlantıya dokunulmaz. Açık bir iş emrinin bitmiş kırılımları kapalı listede, kendisi
ve bitmemiş kırılımları açık listede olabilir: ana satırı listede olmayan iş emrinin
yalnızca kırılımları güncellenir ve kırılımlar iki listeden birleştirilir (biri öbürünü
silmez).

Bağlantı her yüklemeden sonra (sipariş ya da iş emri listesi) baştan kurulur, sırayla:
  erp       sipariş satırının "Bağlı İşemri No"su ya da iş emrinin "Sip. No"su
            (…-<proje>-<sıra>-) bu iş emrini gösteriyor
  aciklama  iş emrinin açıklamasında ya da ürün kodunda (OZ-<proje>-PR-01 gibi projeye özel ürünler)
            proje kodu geçiyor ve o siparişte aynı ürün var
  proje     proje kodu geçiyor ama ürün siparişte yok: alt montaj ya da yarı mamul
  stok      açıklamada "stok" geçiyor: stok için açılmış
  (boş)     bağlanamadı; Yapılacaklar'da kullanıcıya sorulur
Kullanıcının Yapılacaklar'da yaptığı seçim (kullanici, kullanici_stok, yok_sayildi) korunur.

Siparişe bağlı iş emirleri, sipariş satırının ürün kartlarına adet sırasıyla dağıtılır ve
ürün ERP'nin gösterdiği aşamaya ilerler (docs/ihtiyaclar.md 3.1): iş emri açıldı → "Malzeme
hazırlık", kırılımlarından biri stoğa girdi → "Montaj", iş emri tamamlandı (ürün stoğa girdi)
→ "Montaj tamamlandı". Aşama yalnızca ileri gider; ekibin ileri aldığı ürün geri gelmez.
Üretim girişi olmadan kapatılan iş emri ürüne dağıtılmaz.
"""

import re
from collections import Counter, defaultdict

from .asamalar import ASAMALAR, erp_asamasi, ileri
from .erp_aktarim import IPTAL
from .urun_kurallari import sade

ACIK = "Açık"
KAPALI = "Kapalı"
ALANLAR = (
    "urun_kodu", "urun_adi", "durum", "kaynak_tipi", "envanter_tipi", "plan_miktar", "gercek_miktar",
    "kalan_miktar", "acilis_tarihi", "baslama_tarihi", "tahmini_bitis", "kapatma_tarihi", "ilk_stok_giris",
    "son_stok_giris", "aciklama", "erp_siparis",
)
SATIR_ALANLARI = (
    "urun_kodu", "urun_adi", "durum", "envanter_tipi", "plan_miktar", "gercek_miktar", "kalan_miktar", "aciklama",
)
PROJE_KODU = re.compile(r"OZ-[A-Z]{2}\d{4}(?!\d)")
ERP_SIPARIS = re.compile(r"(OZ-[A-Z]{2}\d{4})-(\d+)-")
BAGLANTILAR = {
    "erp": "ERP'de bağlı",
    "aciklama": "açıklamadaki proje kodundan",
    "proje": "projenin alt montajı / yarı mamulü",
    "stok": "stok için",
    "kullanici": "elle siparişe bağlandı",
    "kullanici_stok": "elle stok olarak işaretlendi",
    "yok_sayildi": "takip edilmiyor",
}
# Kullanıcının seçtiği bağlantılar: ERP yüklemesinden sonra yeniden kurulmaz.
KULLANICI_BAGLANTILARI = ("kullanici", "kullanici_stok", "yok_sayildi")


def uretimsiz_kapandi(ie):
    return ie["durum"] == KAPALI and not ie["gercek_miktar"]


def is_emri_durumu(ie):
    """Ekranda gösterilen durum: (metin, sınıf)."""
    if ie["durum"] == KAPALI:
        if not ie["gercek_miktar"]:
            return "Üretim girişi olmadan kapatıldı", "iptal"
        return "ERP'de iş emri tamamlandı", "kapali"
    if ie["gercek_miktar"]:
        return "Kısmen tamamlandı", "kismen"
    return "Açık", "acik"


def kirilim_durumu(satir):
    """Kırılımın (alt montaj, işlem) durumu: (metin, sınıf)."""
    plan, gercek = satir["plan_miktar"] or 0, satir["gercek_miktar"] or 0
    if satir["durum"] == KAPALI or (plan and gercek >= plan):
        return "Tamamlandı", "kapali"
    if gercek:
        return "Kısmen", "kismen"
    return "Bekliyor", "acik"


def is_emirlerini_isle(vt, kayitlar, yukleme_id):
    """İş emri kayıtlarını (ana satır ve kırılımlar) işler; ne yapıldığını sayan bir Counter döndürür."""
    gruplar = defaultdict(list)
    for kayit in kayitlar:
        gruplar[kayit["is_emri_no"]].append(kayit)
    sayac = Counter(satir=len(kayitlar))
    for no, satirlar in gruplar.items():
        ana = next((k for k in satirlar if k["sira_no"] == 0), None)
        eski = vt.execute("SELECT id, durum FROM is_emirleri WHERE is_emri_no = ?", (no,)).fetchone()
        if ana is None:
            # Ana satırı öbür listede: yalnızca kırılımları işlenir; iş emri ana satırı gelince dolar.
            sayac["yalniz_kirilim"] += 1
            ie_id = eski["id"] if eski else vt.execute(
                "INSERT INTO is_emirleri (is_emri_no, ilk_yukleme_id, son_yukleme_id) VALUES (?, ?, ?)",
                (no, yukleme_id, yukleme_id),
            ).lastrowid
        else:
            alanlar = {alan: ana.get(alan) for alan in ALANLAR}
            alanlar["erp_siparis"] = alanlar["erp_siparis"] or next((k["erp_siparis"] for k in satirlar if k["erp_siparis"]), None)
            sayac["is_emri"] += 1
            sayac["acik" if alanlar["durum"] == ACIK else "kapali"] += 1
            if eski is None:
                ie_id = vt.execute(
                    f"INSERT INTO is_emirleri (is_emri_no, ilk_yukleme_id, son_yukleme_id, {', '.join(ALANLAR)})"
                    f" VALUES (?, ?, ?, {', '.join('?' * len(ALANLAR))})",
                    (no, yukleme_id, yukleme_id, *alanlar.values()),
                ).lastrowid
                sayac["yeni"] += 1
            else:
                ie_id = eski["id"]
                if eski["durum"] != KAPALI and alanlar["durum"] == KAPALI:
                    sayac["kapanan"] += 1
                vt.execute(
                    f"UPDATE is_emirleri SET {', '.join(f'{alan} = ?' for alan in ALANLAR)}, son_yukleme_id = ? WHERE id = ?",
                    (*alanlar.values(), yukleme_id, ie_id),
                )
        # Kırılımlar sıra numarasıyla güncellenir; listede olmayan kırılım (öbür listededir) silinmez.
        vt.executemany(
            f"INSERT INTO is_emri_satirlari (is_emri_id, sira_no, {', '.join(SATIR_ALANLARI)})"
            f" VALUES (?, ?, {', '.join('?' * len(SATIR_ALANLARI))})"
            f" ON CONFLICT (is_emri_id, sira_no) DO UPDATE SET {', '.join(f'{a} = excluded.{a}' for a in SATIR_ALANLARI)}",
            [(ie_id, k["sira_no"], *(k.get(alan) for alan in SATIR_ALANLARI)) for k in satirlar if k["sira_no"] != 0],
        )
    return sayac


def is_emri_ozeti(sayac):
    """İş emri yüklemesinin bir cümlelik özeti."""
    parcalar = [f"{sayac['is_emri']} iş emri okundu ({sayac['acik']} açık, {sayac['kapali']} kapalı)"]
    if sayac["yeni"]:
        parcalar.append(f"{sayac['yeni']} yeni")
    if sayac["kapanan"]:
        parcalar.append(f"{sayac['kapanan']} iş emri ERP'de kapandı")
    if sayac["yalniz_kirilim"]:
        parcalar.append(f"{sayac['yalniz_kirilim']} iş emrinin yalnızca kırılımları var (ana satırı öbür listede)")
    return "; ".join(parcalar) + "."


def _baglanti_bul(ie, siparisler, kalemler, erp_bagli, doluluk):
    """(sipariş id, kalem id, bağlantı türü)."""
    kalem = erp_bagli.get(ie["is_emri_no"])
    if kalem is None and (eslesme := ERP_SIPARIS.search((ie["erp_siparis"] or "").upper())):
        siparis = siparisler.get(eslesme.group(1))
        aday = kalemler.get(siparis["id"], {}).get(int(eslesme.group(2))) if siparis else None
        if aday is not None and aday["urun_kodu"] == ie["urun_kodu"]:
            kalem = aday
    if kalem is not None:
        return kalem["siparis_id"], kalem["id"], "erp"

    metin = f'{ie["aciklama"] or ""} {ie["urun_kodu"] or ""}'.upper()
    projeler = [siparisler[kod] for kod in dict.fromkeys(PROJE_KODU.findall(metin)) if kod in siparisler]
    for siparis in projeler:
        adaylar = [k for k in kalemler.get(siparis["id"], {}).values()
                   if k["urun_kodu"] == ie["urun_kodu"] and k["erp_durum"] != IPTAL]
        if adaylar:
            # Aynı ürün birden çok satırdaysa iş emri, dolmamış ilk satıra bağlanır.
            kalem = next((k for k in adaylar if doluluk[k["id"]] < (k["miktar"] or 1)), adaylar[0])
            return siparis["id"], kalem["id"], "aciklama"
    if projeler:
        return projeler[0]["id"], None, "proje"
    if "stok" in sade(ie["aciklama"] or ""):
        return None, None, "stok"
    return None, None, None


def is_emirlerini_bagla(vt):
    """Bütün iş emirlerini siparişlere bağlar ve ürün kartlarına dağıtır; bağlantı türlerini sayar."""
    siparisler = {s["siparis_no"]: s for s in vt.execute("SELECT id, siparis_no FROM siparisler")}
    kalemler = defaultdict(dict)
    erp_bagli = {}
    for k in vt.execute(
        "SELECT id, siparis_id, sira_no, urun_kodu, miktar, erp_durum, bagli_is_emri_no FROM siparis_kalemleri"
        " ORDER BY erp_durum = ?, sira_no",  # iptal edilmemiş satırın bağlantısı önce gelir
        (IPTAL,),
    ):
        kalemler[k["siparis_id"]][k["sira_no"]] = k
        if k["bagli_is_emri_no"]:
            erp_bagli.setdefault(k["bagli_is_emri_no"], k)

    sayac = Counter()
    doluluk = Counter()
    for ie in vt.execute(
        "SELECT * FROM is_emirleri WHERE urun_kodu IS NOT NULL ORDER BY acilis_tarihi, is_emri_no"  # ana satırı gelmemişler beklenir
    ).fetchall():
        if ie["baglanti"] in KULLANICI_BAGLANTILARI:
            siparis_id, kalem_id, baglanti = ie["siparis_id"], ie["kalem_id"], ie["baglanti"]
        else:
            siparis_id, kalem_id, baglanti = _baglanti_bul(ie, siparisler, kalemler, erp_bagli, doluluk)
            vt.execute(
                "UPDATE is_emirleri SET siparis_id = ?, kalem_id = ?, baglanti = ? WHERE id = ?",
                (siparis_id, kalem_id, baglanti, ie["id"]),
            )
        if kalem_id and not uretimsiz_kapandi(ie):
            doluluk[kalem_id] += round(ie["plan_miktar"] or 1)
        sayac[baglanti or "baglanamadi"] += 1
    _urunlere_dagit(vt, sayac)
    return sayac


def _urunlere_dagit(vt, sayac):
    """Sipariş satırına bağlı iş emirlerini o satırın ürün kartlarına adet sırasıyla dağıtır ve ürünü ERP'nin
    gösterdiği aşamaya ilerletir (asamalar.erp_asamasi; geri götürmez). Birden çok adetlik iş emrinde stoğa
    giren miktar kadar ürün "Montaj tamamlandı" sayılır."""
    yuvalar = defaultdict(list)  # kalem → her adet için bir iş emri
    stoga_giren = {}
    for ie in vt.execute(
        "SELECT id, kalem_id, plan_miktar, durum, gercek_miktar FROM is_emirleri WHERE kalem_id IS NOT NULL"
        " ORDER BY acilis_tarihi, is_emri_no"
    ):
        if not uretimsiz_kapandi(ie):
            yuvalar[ie["kalem_id"]].extend([ie["id"]] * max(1, round(ie["plan_miktar"] or 1)))
            stoga_giren[ie["id"]] = ie["gercek_miktar"] or 0
    kirilimi_giren = {r[0] for r in vt.execute(
        "SELECT DISTINCT is_emri_id FROM is_emri_satirlari WHERE COALESCE(gercek_miktar, 0) > 0"
    )}
    kacinci = Counter()  # iş emrinin kaçıncı ürünü
    for urun in vt.execute("SELECT id, kalem_id, adet_sira, asama, is_emri_id FROM urunler ORDER BY kalem_id, adet_sira").fetchall():
        sira = urun["adet_sira"] - 1
        ie_id = yuvalar[urun["kalem_id"]][sira] if sira < len(yuvalar[urun["kalem_id"]]) else None
        asama = urun["asama"]
        if ie_id:
            kacinci[ie_id] += 1
            asama = ileri(asama, erp_asamasi(stoga_giren[ie_id] >= kacinci[ie_id], ie_id in kirilimi_giren))
        if (ie_id, asama) != (urun["is_emri_id"], urun["asama"]):
            vt.execute("UPDATE urunler SET is_emri_id = ?, asama = ? WHERE id = ?", (ie_id, asama, urun["id"]))
            if asama != urun["asama"]:
                sayac[f"gecen:{asama}"] += 1


def baglanti_ozeti(sayac):
    """Bağlama sonucunun bir cümlelik özeti."""
    siparise = sayac["erp"] + sayac["aciklama"] + sayac["kullanici"]
    parcalar = [f"İş emirleri: {siparise} tanesi sipariş satırına bağlı"]
    if sayac["proje"]:
        parcalar.append(f"{sayac['proje']} tanesi projenin alt montajı ya da yarı mamulü")
    if sayac["stok"] + sayac["kullanici_stok"]:
        parcalar.append(f"{sayac['stok'] + sayac['kullanici_stok']} tanesi stok için")
    if sayac["baglanamadi"]:
        parcalar.append(f"{sayac['baglanamadi']} tanesi bağlanamadı (Yapılacaklar'da sorulur)")
    ozet = ", ".join(parcalar) + "."
    gecenler = [f'{sayac["gecen:" + asama]} ürün "{ad}"' for asama, ad in ASAMALAR.items() if sayac["gecen:" + asama]]
    if gecenler:
        ozet += f" Aşaması ilerleyen: {', '.join(gecenler)}."
    return ozet
