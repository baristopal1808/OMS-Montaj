"""Ürün sayfası, makine numaraları (şasi no, motor seri no) ve "Makine numaraları" şablonu.

Veriler uydurmadır: motor seri no'ları CLAUDE.md'deki biçimlerde (0000 111 101, N5F00001).
"""

import io
from datetime import datetime
from html import unescape

import openpyxl
from test_is_emirleri import IE_BASLIKLAR, ie, is_emirleri
from test_siparisler import ekip, excel, makine_siparisi, yukle  # noqa: F401 (pytest fikstürleri)

from oms_montaj.urun_kurallari import motor_seri_nolari
from oms_montaj.veritabani import baglanti


def test_motor_seri_nolari_aciklamadan_okunur():
    assert motor_seri_nolari("OZ-TS0001 - 0000 111 101 - TEST FIRMA") == ["0000 111 101"]
    assert motor_seri_nolari("OZ-TS0001-PP-01 / N5F00001 / STANDART / YAGSIZ SEVK") == ["N5F00001"]
    assert motor_seri_nolari("OZ-TS0001 - 0000111101 / 0000 111 102", "0000 111 101") == ["0000 111 101", "0000 111 102"]
    assert motor_seri_nolari("OZ-TS0001 projesi - RAL5017 - 9001") == []


def motorlu_is_emirleri():
    liste = is_emirleri()
    liste[0]["Açıklama"] = "OZ-TS0001 - 0000 111 101 - TEST FIRMA"  # 900101: PP
    return liste


def urun_id(uygulama, urun_kodu, adet=1):
    with uygulama.app_context():
        return baglanti().execute(
            "SELECT u.id FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id WHERE k.urun_kodu = ? AND u.adet_sira = ?",
            (urun_kodu, adet),
        ).fetchone()[0]


def yuklenmis(yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(motorlu_is_emirleri(), basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")


def test_urun_sayfasi(istemci, uygulama, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    sayfa = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    for beklenen in ("PP-536-NF", "OZ-TS0001-PP-01", "Malzeme hazırlık", "900101", "Açık", "Yağsız sevk",
                     "<strong>1</strong> kırılımdan", "CP0001", "PP Yag Tanki Montaji", "Motor seri no",
                     "ERP iş emri açıklamasından", "0000 111 101"):
        assert beklenen in sayfa, beklenen
    assert "SVR-50-NF-BSP" not in sayfa  # yalnızca bu ürün
    # Sipariş kartında her makine kendi sayfasına gider; motor seri no görünür.
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    assert f'href="/urun/{pp}"' in kart and "0000 111 101" in kart
    # Sevk edilecek makineler listesinden de
    assert f'data-adres="/urun/{pp}"' in istemci.get("/makineler").get_data(as_text=True)
    assert istemci.get("/urun/999999").status_code == 404


def test_numaralar_elle_girilir(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    pp, svr = urun_id(uygulama, "PP-536-NF"), urun_id(uygulama, "SVR-50-NF-BSP")
    gonder(f"/urun/{svr}/numaralar", sasi_no="  TEST-SASI-001 ")
    gonder(f"/urun/{pp}/numaralar", motor_seri_no="0000111102")
    assert "TEST-SASI-001" in istemci.get(f"/urun/{svr}").get_data(as_text=True)
    sayfa = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    assert 'value="0000 111 102"' in sayfa and "Ekip girdi" in sayfa  # ekibin girdiği ERP'den okunanın önüne geçer
    gonder(f"/urun/{pp}/numaralar", motor_seri_no="")
    assert "ERP iş emri açıklamasından" in unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))


def test_izleyici_numara_giremez(istemci, uygulama, ekle, giris, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    svr = urun_id(uygulama, "SVR-50-NF-BSP")
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert 'name="sasi_no"' not in istemci.get(f"/urun/{svr}").get_data(as_text=True)
    assert gonder(f"/urun/{svr}/numaralar", sasi_no="TEST-SASI-001").status_code == 403


def test_makine_numaralari_sablonu(istemci, uygulama, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    svr = urun_id(uygulama, "SVR-50-NF-BSP")
    yanit = istemci.get("/makine-numaralari.xlsx")
    assert yanit.status_code == 200
    kitap = openpyxl.load_workbook(io.BytesIO(yanit.data))
    sayfa = kitap.active
    basliklar = [h.value for h in sayfa[1]]
    assert basliklar[:8] == ["Kart No", "Sipariş No", "Müşteri", "Ürün Kodu", "Ürün Adı", "Seri No", "Şasi No", "Motor Seri No"]
    satirlar = {r[0].value: r for r in sayfa.iter_rows(min_row=2)}
    assert set(satirlar) == {urun_id(uygulama, "SVR-50-NF-BSP"), urun_id(uygulama, "PP-536-NF")}  # yalnızca makineler
    assert satirlar[urun_id(uygulama, "PP-536-NF")][8].value == "0000 111 101"  # ERP'den okunan, bilgi için
    satirlar[svr][6].value = "TEST-SASI-002"
    sayfa.append([999999, "OZ-TS0001", None, "SVR-50-NF-BSP", None, None, "TEST-SASI-003", None])  # eşleşmeyen
    tampon = io.BytesIO()
    kitap.save(tampon)
    yukle(tampon.getvalue(), ad="makine numaralari.xlsx")
    assert ("Makine numaraları: 3 satır okundu; 1 makinenin numarası güncellendi; 1 satır hiçbir makineyle eşleşmedi"
            in unescape(istemci.get("/erp-yukleme").get_data(as_text=True)))
    assert "TEST-SASI-002" in istemci.get(f"/urun/{svr}").get_data(as_text=True)


def test_kirilim_aciklamasindaki_motor_seri_no(istemci, uygulama, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    liste = is_emirleri()
    liste[1]["Açıklama"] = "OZ-TS0001-PP-01 / N5F00001 / STANDART / YAGSIZ SEVK"  # 900101'in kırılımı
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    pp = urun_id(uygulama, "PP-536-NF")
    assert "N5F00001" in istemci.get(f"/urun/{pp}").get_data(as_text=True)


def test_motor_pompa_hatti_alt_montajinda_motor_seri_no(istemci, uygulama, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    liste = [ie(900108, 0, "P10-MPH-M01-R01", "Motor Pompa Hatti", envanter="Yarı Mamul",
                aciklama="OZ-TS0001 / 0000 111 103 / STANDART", ilk_giris=datetime(2026, 10, 2))]
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    assert "Alt montajlar ve yarı mamuller" in kart and "0000 111 103" in kart
    # Siparişte tek güç ünitesi var: onun motor seri no'su da bu
    pp = urun_id(uygulama, "PP-536-NF")
    assert "projenin motor-pompa hattı iş emrinden" in unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
