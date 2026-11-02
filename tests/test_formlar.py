"""Montaj çıktıları: proje takip kartı, test öncesi kontrol, test ve kurulum formu; çıktıların aşama kuralı.
Şablonlar ve veriler uydurmadır (gerçek formlar testlere girmez); PDF'e çevirme sahte bir çeviriciyle yapılır."""

from datetime import datetime
from html import unescape
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook
from test_is_emirleri import IE_BASLIKLAR, is_emirleri
from test_siparisler import ekip, excel, makine_siparisi, yukle  # noqa: F401 (pytest fikstürleri)
from test_urunler import urun_id, yuklenmis

from oms_montaj.formlar import _sablon_oku, pp_modeli, sablonu_doldur, uygun_sablonlar, vibro_adi
from oms_montaj.urun_kurallari import yag_metni
from oms_montaj.veritabani import baglanti

TARIH_ETIKETI = "Form Veriliş Tarihi / Form Submission Date:"


def sablon_yap(yol, hucreler, birlesikler=()):
    """Uydurma bir form şablonu: {hücre: yazı}, birleşik aralıklar."""
    kitap = Workbook()
    sayfa = kitap.active
    for hucre, deger in hucreler.items():
        sayfa[hucre] = deger
    for aralik in birlesikler:
        sayfa.merge_cells(aralik)
    yol.parent.mkdir(parents=True, exist_ok=True)
    kitap.save(yol)


TEST_ONCESI = (
    {"J5": TARIH_ETIKETI, "U5": "Rapor No / Report No.:",
     "A7": "Motor Modeli\nEngine Model", "H7": "Sipariş Numarası\nOrder No.", "N7": "Ana Litre / Main Liter",
     "A9": "Motor Gücü\nMotor Power (kw) / Hp", "H9": "İş Emri Numarası\nWork Order No.", "N9": "Test sorusu",
     "A11": "Motor Seri Numarası\nEngine Serial No.", "H11": "Test Yapılacak Vibro Çakıcı\nTested Vibrohammer",
     "N11": "Test sorusu", "A13": "Motor Çalışma Devri\nEngine Working Speed (rpm)",
     "H13": "Vibro Çakıcı Seri Numarası\nTested Vibrohammer Seri No.", "N13": "Test sorusu"},
    ["J5:T5", "U5:AA5", "A7:C8", "D7:G8", "H7:K8", "L7:M8", "N7:Q8", "A9:C10", "D9:G10", "H9:K10", "L9:M10", "N9:Q10",
     "A11:C12", "D11:G12", "H11:K12", "L11:M12", "N11:Q12", "A13:C14", "D13:G14", "H13:K14", "L13:M14", "N13:Q14"],
)
TEST_FORMU = (
    {"A5": "Makine Modeli / Machine Model", "J5": TARIH_ETIKETI, "T5": "Rapor No / Report No.:",
     "A7": "Sipariş Numarası", "F7": "İş Emri Numarası", "J7": "Test Yapılan Vibro Çakıcı", "O7": "Vibro Çakıcı Seri Numarası",
     "T7": "Hortum Boyu"},
    ["A5:D5", "E5:I5", "J5:Q5", "R5:S5", "T5:V5", "W5:X5", "A7:B7", "C7:E7", "F7:H7", "J7:L7", "M7:N7", "O7:Q7", "R7:S7", "T7:V7"],
)
KURULUM = (
    {"A5": "Ürün Türü / Product Type", "H5": TARIH_ETIKETI, "V5": "Rapor No / Report No.:",
     "A7": "Sipariş Numarası", "H7": "Makine Modeli\nMachine Model", "Q7": "Motor Seri Numarası\nEngine Serial No.",
     "X7": "Motor Modeli\nEngine Model", "H9": "Uzaktan Erişim Var mı?\nIs Remote Access Avaible?", "O9": "☐"},
    ["A5:C5", "D5:G5", "H5:P5", "Q5:U5", "V5:Z5", "AA5:AC5", "A7:C8", "D7:G8", "H7:L8", "M7:P8", "Q7:S8", "T7:W8",
     "X7:Z8", "AA7:AC8", "H9:L10", "M9:N10", "O9:P10"],
)


@pytest.fixture
def formlar_hazir(uygulama, tmp_path):
    """Uydurma şablonlar ve sahte PDF çevirici."""
    klasor = tmp_path / "formlar"
    sablon_yap(klasor / "test oncesi" / "FR-MT-901_R00_PP-536 NF Test Öncesi Kontrol Formu.xlsx", *TEST_ONCESI)
    sablon_yap(klasor / "test" / "FR-MT-902_R00_NF-VM-3XX-4XX-5XX Güç Ünitesi Test Formu.xlsx", *TEST_FORMU)
    sablon_yap(klasor / "FR-MT-903_R01_Güç Ünitesi Kurulum Formu.xlsx", *KURULUM)
    uygulama.config["PDF_CEVIRICI"] = lambda girdi, cikti: Path(cikti).write_bytes(b"%PDF-1.4 test")
    return klasor


def asama(uygulama, urun):
    with uygulama.app_context():
        return baglanti().execute("SELECT asama FROM urunler WHERE id = ?", (urun,)).fetchone()[0]


def son_form(uygulama, tmp_path):
    """Son hazırlanan formun kaydı ve Excel'inin ilk sayfası."""
    with uygulama.app_context():
        kayit = baglanti().execute("SELECT * FROM urun_formlari ORDER BY id DESC LIMIT 1").fetchone()
    pdf = tmp_path / kayit["dosya"]
    assert pdf.read_bytes().startswith(b"%PDF")
    return kayit, load_workbook(pdf.with_suffix(".xlsx")).active


def sayfa(istemci, adres):
    return unescape(istemci.get(adres).get_data(as_text=True))


MOTOR = {"motor_marka": "Volvo", "motor_model": "TEST-MOTOR-1", "guc_kw": "300", "devir": "1800"}


def test_formlar_ve_asama_kurali(istemci, uygulama, gonder, ekip, yukle, formlar_hazir, tmp_path):  # noqa: F811
    yuklenmis(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    # Motor seri no teyit edilmeden (ya da girilmeden) form basılmaz
    assert "Motor seri no teyit edilmedi" in sayfa(istemci, f"/urun/{pp}/form/kodlama")
    gonder(f"/urun/{pp}/form/kodlama", **MOTOR, tarih="2026-11-02")
    assert "Önce motor seri no girilip teyit edilmeli" in sayfa(istemci, f"/urun/{pp}/form/kodlama")
    gonder(f"/urun/{pp}/numara/motor_seri_no/teyit", deger="0000 111 101", teyit="1")  # ERP'den okunan numara
    # Motor bilgisi ayrı kaydedildiği için hata olsa da kaldı; HP kW'tan hesaplandı
    with uygulama.app_context():
        motor = baglanti().execute("SELECT * FROM motor_bilgileri WHERE urun_kodu = 'PP-536-NF'").fetchone()
    assert (motor["model"], motor["guc_kw"], motor["guc_hp"], motor["devir"]) == ("TEST-MOTOR-1", 300, 402, 1800)

    # İş emri ERP'de tamamlanınca güç ünitesi formlar basılmadığı için Montaj'da bekler
    liste = is_emirleri()
    liste[0].update({"Gerçek Mkt.": 1, "Kalan Mkt.": 0, "* Durumu": "Kapalı", "İşEmri Kapatma Tarihi": datetime(2026, 10, 20),
                     "İlk Stok Giriş Tar.": datetime(2026, 10, 20)})
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    assert asama(uygulama, pp) == "montaj"
    urun = sayfa(istemci, f"/urun/{pp}")
    assert 'çıktılar alınınca ürün kendiliğinden "Montaj tamamlandı" aşamasına geçecek' in urun
    assert urun.count('<a class="cikti" href=') == 4 and "cikti basildi" not in urun  # dördü de gri
    gonder(f"/urun/{pp}/asama", asama="montaj_tamamlandi")
    assert "şu çıktılar alınmalı (aşama kutusundaki düğmeler): proje takip kartı, test öncesi kontrol formu" in sayfa(
        istemci, f"/urun/{pp}")

    # Proje takip kartı: uygulamanın kendi tasarımı; motor bilgisi artık kendiliğinden, yağ sipariş talebinden gelir
    form = sayfa(istemci, f"/urun/{pp}/form/kodlama")
    assert "VOLVO TEST-MOTOR-1" in form and "300 kW / 402 HP" in form and "SVR-50-NF" in form
    assert 'name="yag" value="Yağsız sevk"' in form
    yanit = gonder(f"/urun/{pp}/form/kodlama", vibro="SVR-50-NF", vibro_seri="OZ-TS0001-VH-01", yag="Yağsız sevk",
                   tarih="2026-11-02")
    kayit, s = son_form(uygulama, tmp_path)
    assert yanit.headers["Location"].endswith(f"/urun/{pp}?form={kayit['id']}#asama")
    assert (s["C1"].value, s["A4"].value, s["C4"].value, s["B6"].value, s["B7"].value, s["B8"].value, s["B9"].value) == (
        "PROJE TAKİP KARTI", "OZ-TS0001", "OZ-TS0001-PP-01", "SVR-50-NF", "VOLVO 0000 111 101", "900101", "Yağsız sevk")
    assert "PP-536-NF" in str(s["B5"].value) and "TEST-MOTOR-1" in str(s["B5"].value)
    # Ürün sayfasında düğmesi yeşil; hazır olduğu ve PDF'in bağlantısı görünür
    urun = sayfa(istemci, f"/urun/{pp}?form={kayit['id']}")
    assert "Proje takip kartı hazır." in urun and urun.count("cikti basildi") == 1
    assert asama(uygulama, pp) == "montaj"  # test öncesi kontrol formu da gerekli

    # Test öncesi kontrol formu: şablondaki etiketlerin yanına yazılır; tarih boş hücre yoksa etiketin sonuna
    form = sayfa(istemci, f"/urun/{pp}/form/test_oncesi")
    assert "FR-MT-901_R00_PP-536 NF Test Öncesi Kontrol Formu" in form
    gonder(f"/urun/{pp}/form/test_oncesi", sablon="FR-MT-901_R00_PP-536 NF Test Öncesi Kontrol Formu.xlsx",
           vibro="SVR-50-NF", vibro_seri="OZ-TS0001-VH-01", tarih="2026-11-02")
    kayit, s = son_form(uygulama, tmp_path)
    assert kayit["tur"] == "test_oncesi" and kayit["sablon"].startswith("FR-MT-901")
    assert [s[h].value for h in ("D7", "D9", "D11", "D13", "L7", "L9", "L11", "L13")] == [
        "VOLVO TEST-MOTOR-1", "300 kW / 402 HP", "0000 111 101", "1800 rpm", "OZ-TS0001", "900101", "SVR-50-NF",
        "OZ-TS0001-VH-01"]
    assert s["J5"].value == f"{TARIH_ETIKETI} 02/11/2026" and s["N7"].value == "Ana Litre / Main Liter"
    # İki form basıldı: ürün ERP'nin gösterdiği aşamaya geçer; akışta görünür
    assert asama(uygulama, pp) == "montaj_tamamlandi"
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "Formlar basıldı; ürün ERP'nin gösterdiği aşamaya geçti." in urun and "Proje takip kartı basıldı" in urun

    # Test formu basılmadan "Test"e geçilmez; test formu model serisine göre seçilir
    gonder(f"/urun/{pp}/asama", asama="teste_hazir")
    gonder(f"/urun/{pp}/asama", asama="test")
    assert asama(uygulama, pp) == "teste_hazir"
    gonder(f"/urun/{pp}/form/test", sablon="FR-MT-902_R00_NF-VM-3XX-4XX-5XX Güç Ünitesi Test Formu.xlsx",
           vibro="SVR-50-NF", vibro_seri="", tarih="2026-11-03")
    _, s = son_form(uygulama, tmp_path)
    assert [s[h].value for h in ("E5", "R5", "C7", "I7", "M7", "R7", "W7")] == [
        "PP-536-NF", "03/11/2026", "OZ-TS0001", "900101", "SVR-50-NF", None, None]
    gonder(f"/urun/{pp}/asama", asama="test")
    assert asama(uygulama, pp) == "test"

    # Kurulum formu basılmadan "Sevke hazır"a geçilmez
    gonder(f"/urun/{pp}/asama", asama="sevke_hazir")
    assert asama(uygulama, pp) == "test"
    gonder(f"/urun/{pp}/form/kurulum", sablon="FR-MT-903_R01_Güç Ünitesi Kurulum Formu.xlsx", tarih="2026-11-04")
    _, s = son_form(uygulama, tmp_path)
    assert [s[h].value for h in ("D5", "Q5", "D7", "M7", "T7", "AA7", "M9")] == [
        "Güç Ünitesi", "04/11/2026", "OZ-TS0001", "PP-536-NF", "0000 111 101", "VOLVO TEST-MOTOR-1", "Yok"]
    gonder(f"/urun/{pp}/asama", asama="sevke_hazir")
    assert asama(uygulama, pp) == "sevke_hazir"
    # PDF açılır; geri alırken form istenmez
    yanit = istemci.get(f"/urun/{pp}/form-dosyasi/{kayit['id']}")
    assert yanit.status_code == 200 and yanit.mimetype == "application/pdf"
    assert istemci.get(f"/urun/{pp}/form-dosyasi/9999").status_code == 404


def test_form_kurali_vibroda_ve_muafta_yok(istemci, uygulama, gonder, ekip, yukle, formlar_hazir):  # noqa: F811
    yuklenmis(yukle)
    pp, svr = urun_id(uygulama, "PP-536-NF"), urun_id(uygulama, "SVR-50-NF-BSP")
    gonder(f"/urun/{svr}/asama", asama="sevke_hazir")
    assert asama(uygulama, svr) == "sevke_hazir"
    assert istemci.get(f"/urun/{svr}/form/kodlama").status_code == 404  # formlar yalnızca güç ünitesinde
    # Kural başladığında Montaj tamamlandı ya da ileri aşamada olan ürün muaf
    with uygulama.app_context():
        vt = baglanti()
        with vt:
            vt.execute("UPDATE urunler SET form_muaf = 1 WHERE id = ?", (pp,))
    gonder(f"/urun/{pp}/asama", asama="sevke_hazir")
    assert asama(uygulama, pp) == "sevke_hazir"
    assert "çıktılar isteğe bağlı" in sayfa(istemci, f"/urun/{pp}")


def test_izleyici_form_basamaz(istemci, uygulama, gonder, ekle, giris, ekip, yukle, formlar_hazir):  # noqa: F811
    yuklenmis(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    form = sayfa(istemci, f"/urun/{pp}/form/kodlama")
    assert "PDF'i hazırla" not in form and f"/urun/{pp}/form/kodlama" not in sayfa(istemci, f"/urun/{pp}")
    assert gonder(f"/urun/{pp}/form/kodlama", **MOTOR).status_code == 403


def test_musterinin_vibro_oneki(istemci, uygulama, gonder, ekip, yukle, formlar_hazir, tmp_path):  # noqa: F811
    (tmp_path / "marka").mkdir(exist_ok=True)
    (tmp_path / "marka" / "musteriler.txt").write_text("# uydurma\nTS0;#123456;vibro=VH\n", encoding="utf-8")
    yuklenmis(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    assert 'value="VH-50-NF"' in sayfa(istemci, f"/urun/{pp}/form/kodlama")


def test_sablon_secimi():
    adlar = [
        "FR-MT-901_R00_PP-536 NF Test Öncesi Kontrol Formu", "FR-MT-902_R00_PP-536 VM Test Öncesi Kontrol Formu",
        "FR-MT-903_R00_PP-551 NF Stage IV Test Öncesi Kontrol Formu", "FR-MT-904_R00_PP-551 NF Stage V Test Öncesi Kontrol Formu",
        "FR-MT-905_R00_PP-551 NF-VM Stage V Test Öncesi Kontrol Formu", "FR-MT-906_R00_PP-540 NF Test Öncesi Kontrol Formu",
        "FR-MT-907_R00_NF-VM-3XX-4XX-5XX Güç Ünitesi Test Formu", "FR-MT-908_R00_NF-VM-7XX Güç Ünitesi Test Formu",
        "FR-MT-909_R00_NF-VM-1XXX Güç Ünitesi Test Formu", "FR-MT-910_R01_Güç Ünitesi Kurulum Formu",
    ]
    butun = {}
    for ad in adlar:
        sablon = _sablon_oku(Path(ad + ".xlsx"))
        butun.setdefault(sablon.tur, []).append(sablon)

    def uyan(tur, kod):
        return [s.dokuman for s in uygun_sablonlar(tur, kod, butun)]

    assert pp_modeli("PP-551-NF/VM-STAGE V") == (551, frozenset({"NF", "VM"}), "V")
    assert pp_modeli("PP-1102-S5-VM-MNT") == (1102, frozenset({"VM"}), "V")
    assert pp_modeli("PP-540C-NF-T4") == (540, frozenset({"NF"}), None)
    assert uyan("test_oncesi", "PP-536-NF") == ["901"] and uyan("test_oncesi", "PP-536-VM") == ["902"]
    assert uyan("test_oncesi", "PP-551-NF-STAGE V") == ["904"] and uyan("test_oncesi", "PP-551-NF/VM-STAGE V") == ["905"]
    assert uyan("test_oncesi", "PP-551-NF") == ["903", "904"]  # Stage belirsiz: seçilir
    assert uyan("test_oncesi", "PP-540C-NF-T4") == ["906"] and uyan("test_oncesi", "PP-908-NF") == []
    assert uyan("test", "PP-422-NF") == ["907"] and uyan("test", "PP-768-VM") == ["908"] and uyan("test", "PP-1072-NF") == ["909"]
    assert uyan("test", "PP-908-NF") == []  # 9XX serisinin formu yok
    assert uyan("kurulum", "PP-536-NF") == ["910"]
    assert vibro_adi("SVR-120-NF-BSP") == "SVR-120-NF" and vibro_adi("SVR-80-NF-BSP", "VH") == "VH-80-NF"


def test_iki_motorlu_form(tmp_path):
    # Motor 1 ve Motor 2 ara etiketlerinin yanına ayrı ayrı; tek hücre varsa alt alta
    yol = tmp_path / "iki.xlsx"
    sablon_yap(yol, {"A10": "Motor Modeli", "A14": "Motor Seri Numarası", "D14": "Motor 1 (F10'lu)", "J14": "Motor 2 (F10'suz)",
                     "O14": "Yağ seviyesi kontrol edildi mi?", "A20": "Motor Seri Numarası"},
               ["A10:C11", "D10:I11", "J10:N11", "A14:C15", "D14:F15", "G14:I15", "J14:K15", "L14:N15", "O14:W14",
                "A20:C21", "D20:G21"])
    s = sablonu_doldur(yol, {"motor_modeli": "VOLVO TEST-MOTOR-2", "motor_seri": ["0000 111 101", "0000 111 102"]}).active
    assert (s["D10"].value, s["J10"].value) == ("VOLVO TEST-MOTOR-2", "VOLVO TEST-MOTOR-2")
    assert (s["G14"].value, s["L14"].value, s["O14"].value) == ("0000 111 101", "0000 111 102", "Yağ seviyesi kontrol edildi mi?")
    assert s["D20"].value == "0000 111 101\n0000 111 102" and s["D20"].alignment.wrap_text
    assert s.page_setup.orientation == "landscape" and s.page_setup.fitToHeight == 1


def test_yag_metni():
    # Sipariş talebindeki yağ yazımları farklı; yağın adı bulunursa yazılır (ekip form ekranında düzeltebilir)
    assert yag_metni("Yağsız sevk edilecektir.") == "Yağsız sevk"
    assert yag_metni("TEST YAG 46 (ISO VG 46) -\nHidrolik Yağ") == "TEST YAG 46 (ISO VG 46)"
    assert yag_metni("Renk: Standart\nİçerisine yağ konulacaktır.") == "Yağlı sevk"
    assert yag_metni("Renk: Standart") == "" and yag_metni(None) == ""
