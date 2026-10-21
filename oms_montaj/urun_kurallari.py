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


def siparis_tipi(detay_turu):
    return SIPARIS_TIPLERI.get(sade(detay_turu)) if detay_turu else None


def satir_turu(urun_kodu, detay_turu=None):
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


def seri_nolar(planlama_bilgisi):
    """'A & B & C' → ['A', 'B', 'C']; boş ya da '-' ise boş liste."""
    parcalar = (p.strip() for p in (planlama_bilgisi or "").split("&"))
    return [p for p in parcalar if p and p != "-"]
