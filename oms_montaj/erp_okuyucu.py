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
    "is_emirleri": {"ad": "İş emirleri", "imza": ("* İş Emri No", "* Sıra No"), "adim": 3},
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
TARIH_ALANLARI = {"teslim_tarihi", "talep_tarihi", "ilk_sevk_tarihi", "son_sevk_tarihi"}
SAYI_ALANLARI = {"miktar", "sevk_miktari"}


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


def siparis_satirlari(basliklar, satirlar):
    """Sipariş talepleri raporunun satırlarını kayıtlara çevirir; eksik zorunlu sütunda OkumaHatasi."""
    bul = {sade(b): b for b in basliklar if b}
    sutun = {alan: bul.get(sade(baslik)) for alan, baslik in SIPARIS_SUTUNLARI.items()}
    eksik = [SIPARIS_SUTUNLARI[alan] for alan in ZORUNLU_SIPARIS if sutun[alan] is None]
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
        sira = sayi(kayit["sira_no"])
        kayit["sira_no"] = int(sira) if sira is not None else None
        if kayit["siparis_no"] and kayit["urun_kodu"] and kayit["sira_no"] is not None:
            kayitlar.append(kayit)
    return kayitlar
