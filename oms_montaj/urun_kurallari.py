"""Sipariş satırlarının nasıl yorumlandığı: hangi satır kart olur, hangi aileye girer;
açıklamadan renk ve yağ, planlama bilgisinden seri numaraları.

Kart kuralları (docs/ihtiyaclar.md, soru 34) şimdilik burada sabittir; planın
6. adımında Ayarlar'dan düzenlenebilir hale gelecek.
"""

import re

# Ürün kodunun harf öneki → aile
AILELER = {
    "SVR": "SVR",
    "OVR": "OVR",
    "OVF": "OVF",
    "WD": "WD",
    "PP": "PP",
    "SCN": "Çene",
    "KCN": "Çene",
    "CB": "Kiriş",
}
# Sipariş kartındaki bölümlerin sırası ve başlıkları
AILE_SIRASI = ["SVR", "OVR", "PP", "Çene", "Kiriş", "OVF", "WD"]
AILE_ADLARI = {
    "SVR": "SVR · Vinç asılı vibro çakıcı",
    "OVR": "OVR · Ekskavatöre monteli vibro çakıcı",
    "PP": "PP · Güç ünitesi",
    "Çene": "Çene",
    "Kiriş": "Kiriş",
    "OVF": "OVF · Zemin iyileştirme",
    "WD": "WD · Fitil sürücü",
}
VIBROHAMMER = {"SVR", "OVR"}
# Özetteki ve sevkiyattaki sayılara ve pastalara giren makineler; çene ve kiriş bunlara eşlik
# ettiğinden sayılmaz (kullanıcı kararı, 21/10/2026). Kartlarda ve listelerde görünmeye devam ederler.
ANA_URUNLER = ("SVR", "OVR", "PP", "OVF", "WD")
# Bu ailelerde seri no'su olmayan satır makine değil, makinenin bir parçasıdır
# (OVF-300-BF-LM-B gibi; kullanıcı kararı, 21/10/2026). Kart olmaz, sipariş kartında listelenir.
SERI_NOSUZ_PARCA = {"OVF", "WD"}

# Güç ünitesine (PP) takılan, dışarıdan alınan kalemler (soru 21): makine siparişinde montaj durumu izlenir.
# Kod listesi 6. adımda Ayarlar'a taşınır.
PP_EKLENTILERI = {"OZ04314": "Kablosuz kumanda seti", "OZ04082": "Uzaktan erişim modülü"}
EKLENTI_DURUMLARI = {
    "talep_acilacak": "Sipariş talebi açılacak",
    "talep_acildi": "Sipariş talebi açıldı, bekleniyor",
    "montaj_edilmedi": "Geldi, montaj edilmedi",
    "montaj_edildi": "PP'ye montaj edildi",
}
VARSAYILAN_EKLENTI_DURUMU = "talep_acilacak"


def pp_eklentisi_mi(urun_kodu, siparis_tipi_):
    return (urun_kodu or "").upper() in PP_EKLENTILERI and siparis_tipi_ != "yedek_parca"


# Satır türleri: kart ve servis satırlarının her adedi bir ürün kartı olur;
# aksesuar ve parçalar sipariş kartında listelenir; hizmet satırları (nakliye…) gösterilmez.
KARTLI_TURLER = {"kart", "servis"}

# ERP'deki "Sipariş Detay Türü" → sipariş tipi
SIPARIS_TIPLERI = {"makina": "makine", "yedek p.": "yedek_parca", "servis": "servis"}

TURKCE = str.maketrans("çğıöşüÇĞİIÖŞÜ", "cgiosuCGIIOSU")


def sade(metin):
    return re.sub(r"\s+", " ", str(metin).translate(TURKCE).lower()).strip()


def onek(urun_kodu):
    eslesme = re.match(r"[A-Za-z]+", urun_kodu or "")
    return eslesme.group().upper() if eslesme else ""


def dis_tedarik_mi(urun_kodu):
    """"OZ" + rakam kodlu kalemler satın alınır (dış tedarik): burada üretilmez, iş emri açılmaz;
    ERP'deki "Ürün Durumu" onlar için anlamsızdır. "OZ-<proje>-PR-01" gibi projeye özel ürünler
    ise burada üretilir ve iş emri açılır; dış tedarik sayılmaz."""
    return bool(re.match(r"OZ\d", (urun_kodu or "").upper()))


def siparis_tipi(detay_turu):
    return SIPARIS_TIPLERI.get(sade(detay_turu)) if detay_turu else None


def satir_turu(urun_kodu, detay_turu=None, planlama_bilgisi=None):
    """(tür, aile): tür kart, servis, aksesuar, parca ya da hizmet; aile yalnızca kartlı türlerde."""
    kod = (urun_kodu or "").upper()
    aile = AILELER.get(onek(kod))
    if kod.endswith("-MNT"):
        return "servis", aile
    if onek(kod) == "HZ":
        return "hizmet", None
    if siparis_tipi(detay_turu) == "yedek_parca":
        return "parca", None
    if "-HH" in kod:  # hidrolik hortum setleri, ailenin önekini taşısa da aksesuardır
        return "aksesuar", None
    if aile in SERI_NOSUZ_PARCA and not seri_nolar(planlama_bilgisi):
        return "aksesuar", None
    if aile:
        return "kart", aile
    return "aksesuar", None


def model(urun_kodu):
    """'SVR-120-NF-BSP' → 'SVR-NF'; 'OVR-60-SG' → 'OVR-SG'; diğerlerinde önek."""
    parcalar = (urun_kodu or "").upper().split("-")
    if len(parcalar) >= 3 and parcalar[0] in VIBROHAMMER and parcalar[1].isdigit():
        return f"{parcalar[0]}-{parcalar[2]}"
    return onek(urun_kodu)


def renk(aciklama):
    eslesme = re.search(r"renk\s*:\s*([^\r\n]+)", aciklama or "", re.IGNORECASE)
    return eslesme.group(1).strip() if eslesme else None


def yag(aciklama):
    """PP satırının açıklamasından yağ bilgisi: ('yagsiz', None), ('yagli', açıklama) ya da None.

    Yazım değişiyor: "yağsız sevk edilecektir", "<yağ adı> yağlı sevk" ya da
    yalnızca yağın adı ("… (ISO VG 68) - Hidrolik Yağ").
    """
    metin = sade(aciklama or "")
    if not metin:
        return None
    if "yagsiz" in metin:
        return "yagsiz", None
    if "yag" in metin or "iso vg" in metin or "oil" in metin:
        return "yagli", aciklama.strip()
    return None


# Motor seri no'ları iş emri açıklamalarında etiketsiz yazılıyor: "<proje> - 0000 111 1011 - …" (Volvo:
# 4+3+4 rakam, daha az 4+3+3; bir yıllık listede 421'e 120) ya da "<proje> / N5F00001 / STANDART / YAĞSIZ
# SEVK" (CAT: harf, rakam, harf, 5 rakam; ya da 3 harf, 5 rakam). Proje kodu (2 harf, 4 rakam) ve RAL
# kodu bu biçimlere uymaz.
MOTOR_SERI = re.compile(
    r"(?<!\w)(\d{4})[ .]{0,2}(\d{3})[ .]{0,2}(\d{3,4})(?!\w)|(?<!\w)([A-Z]\d[A-Z]\d{5}|[A-Z]{3}\d{5})(?!\w)"
)


# Model numarası bu sınırdan büyük ya da eşit güç üniteleri iki motorludur (PP-1072, PP-1102, PP-1536,
# PP-1592; kullanıcı kararı, 23/10/2026).
IKI_MOTOR_SINIRI = 1000


def motor_sayisi(urun_kodu):
    """Güç ünitesindeki motor sayısı: 'PP-1072-NF' → 2, 'PP-536-NF' → 1."""
    eslesme = re.match(r"PP-?(\d+)", (urun_kodu or "").upper())
    return 2 if eslesme and int(eslesme.group(1)) >= IKI_MOTOR_SINIRI else 1


def motor_seri_nolari(*metinler):
    """Metinlerde geçen motor seri no'ları, yazıldıkları sırayla ve birer kez: Volvo '0000 111 101', CAT 'N5F00001'."""
    bulunan = []
    for metin in metinler:
        for e in MOTOR_SERI.finditer((metin or "").upper()):
            no = " ".join(e.group(1, 2, 3)) if e.group(1) else e.group(4)
            if no not in bulunan:
                bulunan.append(no)
    return bulunan


def seri_nolar(planlama_bilgisi):
    """'A & B & C' → ['A', 'B', 'C']; boş ya da '-' ise boş liste."""
    parcalar = (p.strip() for p in (planlama_bilgisi or "").split("&"))
    return [p for p in parcalar if p and p != "-"]
