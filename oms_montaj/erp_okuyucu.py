"""ERP okuyucu: ERP'den alınan Excel raporlarını okur ve uygulamanın anladığı kayıtlara çevirir.

Uygulamanın geri kalanı yalnızca buradaki kayıtları görür; ERP'ye doğrudan
bağlantı geldiğinde yalnızca bu dosya değişir. ERP eski Excel biçimi (.xls)
verir; .xlsx de okunur. Sütunlar başlık adıyla bulunur; sütunların sırası ve
fazladan sütunlar önemli değildir. Raporların yapısı: docs/ihtiyaclar.md, 2.3.
"""

from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
import xlrd

from .urun_kurallari import sade


class OkumaHatasi(Exception):
    """Dosya okunamadı ya da gerekli sütunlar yok; mesaj kullanıcıya gösterilir."""


# Rapor türleri; türü başlıklardaki bu sütunlar belirler.
RAPORLAR = {
    "siparis_talepleri": {"ad": "Sipariş talepleri", "imza": ("Sipariş No", "Sip.Sıra No", "Planlama Bilgisi")},
    "is_emirleri": {"ad": "İş emirleri", "imza": ("* İş Emri No", "* Sıra No")},
    "makine_numaralari": {"ad": "Makine numaraları", "imza": ("Kart No", "Şasi No", "Motor Seri No")},
    "cikis_yapilamayan": {"ad": "Çıkış yapılamayan malzeme", "imza": ("Isemri No / Sıra", "Gerceklesen Cikis Miktar"), "adim": 5},
    "stok": {"ad": "Stok raporu", "imza": ("MalzemeKodu", "EldekiMiktar"), "adim": 5},
}

# Sipariş talepleri raporu: kayıttaki alan → ERP'deki sütun başlığı
SIPARIS_SUTUNLARI = {
    "siparis_no": "Sipariş No",
    "sira_no": "Sip.Sıra No",
    "urun_kodu": "Ürün Kodu",
    "urun_adi": "Ürün Adı",
    "miktar": "Sipariş Miktar",
    "sevk_miktari": "Sevk/Kont.Gelen Miktarı",
    "birim": "Satış Birimi",
    "aciklama": "Açıklama",
    "planlama_bilgisi": "Planlama Bilgisi",
    "siparis_aciklama": "Sipariş Açıklama",
    "bagli_is_emri_no": "Bağlı İşemri No",
    "erp_durum": "Sip.Durumu",
    "erp_genel_durum": "Sipariş Ürün Genel Durum",
    "erp_urun_durumu": "Ürün Durumu",
    "detay_turu": "Sipariş Detay Türü",
    "musteri": "Firma Adı",
    "teslim_tarihi": "Uzlaşılan Sevk Tar.",
    "talep_tarihi": "Sip.Geliş Tarihi",
    "ilk_sevk_tarihi": "İlk Sevk Tarihi",
    "son_sevk_tarihi": "Son Sevk Tarihi",
}
ZORUNLU_SIPARIS = ("siparis_no", "sira_no", "urun_kodu", "miktar")

# Açık ve kapalı iş emirleri raporu (ikisi aynı biçimde): 0. satır ana ürün, diğerleri kırılımlar
IS_EMRI_SUTUNLARI = {
    "is_emri_no": "* İş Emri No",
    "sira_no": "* Sıra No",
    "urun_kodu": "* Ürün Kodu",
    "urun_adi": "* Ürün Adı",
    "durum": "* Durumu",
    "kaynak_tipi": "*Kaynak Tipi",
    "envanter_tipi": "Envanter Tipi",
    "plan_miktar": "*Plan Mkt.",
    "gercek_miktar": "Gerçek Mkt.",
    "kalan_miktar": "Kalan Mkt.",
    "acilis_tarihi": "İşEmri Açma Tarihi",
    "baslama_tarihi": "* İşEmri Başlama Tarihi",
    "tahmini_bitis": "Tahmini Bitiş Tarihi",
    "kapatma_tarihi": "İşEmri Kapatma Tarihi",
    "ilk_stok_giris": "İlk Stok Giriş Tar.",
    "son_stok_giris": "Son Stok Giriş Tar.",
    "aciklama": "Açıklama",
    "erp_siparis": "Sip. No",  # "…-<proje>-<sıra>-": iş emrinin bağlı olduğu sipariş satırı; yoksa "---"
}
ZORUNLU_IS_EMRI = ("is_emri_no", "sira_no", "urun_kodu", "durum")

# Uygulamanın kendi "Makine numaraları" şablonu (ERP raporu değil): ekip şasi ve motor seri no'larını
# doldurup yükler. Satır, uygulamanın verdiği kart no ile bulunur.
NUMARA_SUTUNLARI = {
    "kart_no": "Kart No",
    "siparis_no": "Sipariş No",
    "urun_kodu": "Ürün Kodu",
    "seri_no": "Seri No",
    "sasi_no": "Şasi No",
    "motor_seri_no": "Motor Seri No",
}
ZORUNLU_NUMARA = ("kart_no", "sasi_no", "motor_seri_no")

TARIH_ALANLARI = {
    "teslim_tarihi", "talep_tarihi", "ilk_sevk_tarihi", "son_sevk_tarihi",
    "acilis_tarihi", "baslama_tarihi", "tahmini_bitis", "kapatma_tarihi", "ilk_stok_giris", "son_stok_giris",
}
SAYI_ALANLARI = {"miktar", "sevk_miktari", "plan_miktar", "gercek_miktar", "kalan_miktar"}
BOS_DEGERLER = {"---"}  # ERP'nin boş alan yerine yazdığı


def _xls_satirlari(yol):
    try:
        kitap = xlrd.open_workbook(yol)
    except Exception as hata:  # xlrd bozuk dosyada farklı hatalar verebilir
        raise OkumaHatasi(f"Excel dosyası okunamadı ({hata}).") from hata
    sayfa = kitap.sheet_by_index(0)
    for i in range(sayfa.nrows):
        satir = []
        for hucre in sayfa.row(i):
            if hucre.ctype == xlrd.XL_CELL_DATE:
                satir.append(xlrd.xldate_as_datetime(hucre.value, kitap.datemode))
            elif hucre.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                satir.append(None)
            else:
                satir.append(hucre.value)
        yield satir


def _xlsx_satirlari(yol):
    try:
        kitap = openpyxl.load_workbook(yol, read_only=True, data_only=True)
    except Exception as hata:  # bozuk dosyada openpyxl farklı hatalar verebilir
        raise OkumaHatasi(f"Excel dosyası okunamadı ({hata}).") from hata
    try:
        yield from kitap.worksheets[0].iter_rows(values_only=True)
    finally:
        kitap.close()


def _dolu(deger):
    return deger is not None and not (isinstance(deger, str) and not deger.strip())


def tablo_oku(yol):
    """İlk sayfayı (başlıklar, satırlar) olarak döndürür; her satır başlık → değer sözlüğüdür.

    Bazı raporların üstünde bir başlık satırı daha var; sütun başlıkları ilk 10
    satırdan en çok yazı içereni sayılır.
    """
    yol = Path(yol)
    uzanti = yol.suffix.lower()
    if uzanti == ".xls":
        ham = list(_xls_satirlari(yol))
    elif uzanti == ".xlsx":
        ham = list(_xlsx_satirlari(yol))
    else:
        raise OkumaHatasi("Yalnızca .xls ve .xlsx dosyaları okunabilir.")
    if not ham:
        raise OkumaHatasi("Dosya boş.")
    bas = max(range(min(10, len(ham))), key=lambda i: sum(isinstance(d, str) and _dolu(d) for d in ham[i]))
    basliklar = [str(d).strip() if d is not None else "" for d in ham[bas]]
    satirlar = [dict(zip(basliklar, satir)) for satir in ham[bas + 1 :] if any(_dolu(d) for d in satir)]
    return basliklar, satirlar


def rapor_turu(basliklar):
    var = {sade(b) for b in basliklar}
    for tur, rapor in RAPORLAR.items():
        if all(sade(sutun) in var for sutun in rapor["imza"]):
            return tur
    return None


def metin(deger):
    if not _dolu(deger):
        return None
    if isinstance(deger, float) and deger.is_integer():
        deger = int(deger)
    return str(deger).strip()


def sayi(deger):
    if not _dolu(deger):
        return None
    if isinstance(deger, (int, float)):
        return float(deger)
    try:
        return float(str(deger).strip().replace(",", "."))
    except ValueError:
        return None


def tarih(deger):
    """ISO tarih ('2026-11-03') ya da None. Excel gün sayısını ve gün/ay/yıl yazısını da tanır."""
    if not _dolu(deger):
        return None
    if isinstance(deger, datetime):
        return deger.date().isoformat()
    if isinstance(deger, date):
        return deger.isoformat()
    if isinstance(deger, (int, float)):
        if 20000 < deger < 80000:
            return (date(1899, 12, 30) + timedelta(days=int(deger))).isoformat()
        return None
    yazi = str(deger).strip()
    for bicim in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
        try:
            return datetime.strptime(yazi, bicim).date().isoformat()
        except ValueError:
            pass
    return None


def _kayitlar(basliklar, satirlar, sutunlar, zorunlu, anahtarlar, bos_degerler=()):
    """Satırları alan → değer kayıtlarına çevirir; eksik zorunlu sütunda OkumaHatasi. Sıra numarası
    tamsayıya çevrilir; anahtar alanlarından biri boş olan satır atlanır. bos_degerler boş sayılır."""
    bul = {sade(b): b for b in basliklar if b}
    sutun = {alan: bul.get(sade(baslik)) for alan, baslik in sutunlar.items()}
    eksik = [sutunlar[alan] for alan in zorunlu if sutun[alan] is None]
    if eksik:
        raise OkumaHatasi("Şu sütunlar bulunamadı: " + ", ".join(eksik) + ".")

    kayitlar = []
    for satir in satirlar:
        kayit = {}
        for alan, baslik in sutun.items():
            deger = satir.get(baslik) if baslik else None
            if alan in TARIH_ALANLARI:
                kayit[alan] = tarih(deger)
            elif alan in SAYI_ALANLARI:
                kayit[alan] = sayi(deger)
            else:
                kayit[alan] = metin(deger)
                if kayit[alan] in bos_degerler:
                    kayit[alan] = None
        if "sira_no" in kayit:
            sira = sayi(kayit["sira_no"])
            kayit["sira_no"] = int(sira) if sira is not None else None
        if all(kayit[alan] is not None for alan in anahtarlar):
            kayitlar.append(kayit)
    return kayitlar


def siparis_satirlari(basliklar, satirlar):
    """Sipariş talepleri raporunun satırlarını kayıtlara çevirir; eksik zorunlu sütunda OkumaHatasi."""
    return _kayitlar(basliklar, satirlar, SIPARIS_SUTUNLARI, ZORUNLU_SIPARIS, ("siparis_no", "urun_kodu", "sira_no"))


def is_emri_satirlari(basliklar, satirlar):
    """Açık ya da kapalı iş emirleri raporunun satırlarını kayıtlara çevirir (ana satır ve kırılımlar)."""
    return _kayitlar(basliklar, satirlar, IS_EMRI_SUTUNLARI, ZORUNLU_IS_EMRI,
                     ("is_emri_no", "urun_kodu", "sira_no"), BOS_DEGERLER)


def numara_satirlari(basliklar, satirlar):
    """"Makine numaraları" şablonunun satırlarını kayıtlara çevirir; kart no'su olmayan satır atlanır."""
    return _kayitlar(basliklar, satirlar, NUMARA_SUTUNLARI, ZORUNLU_NUMARA, ("kart_no",))
