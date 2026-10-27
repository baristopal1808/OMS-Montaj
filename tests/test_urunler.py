"""Ürün sayfası, makine numaraları (şasi no, motor seri no) ve "Makine numaraları" şablonu.

Veriler uydurmadır: motor seri no'ları CLAUDE.md'deki biçimlerde (0000 111 101, N5F00001).
"""

import io
from datetime import datetime
from html import unescape

import openpyxl
from test_is_emirleri import IE_BASLIKLAR, ie, is_emirleri
from test_siparisler import ekip, excel, makine_siparisi, satir, yukle  # noqa: F401 (pytest fikstürleri)

from oms_montaj.numaralar import motor_listesi
from oms_montaj.urun_kurallari import motor_sayisi, motor_seri_nolari
from oms_montaj.veritabani import baglanti


def test_motor_seri_nolari_aciklamadan_okunur():
    assert motor_seri_nolari("OZ-TS0001 - 0000 111 101 - TEST FIRMA") == ["0000 111 101"]
    assert motor_seri_nolari("OZ-TS0001 - 0000 111 1011") == ["0000 111 1011"]  # Volvo'da çoğunlukla 4+3+4
    assert motor_seri_nolari("OZ-TS0001 / 0000  111  1012") == ["0000 111 1012"]
    assert motor_seri_nolari("OZ-TS0001-PP-01 / N5F00001 / STANDART / YAGSIZ SEVK") == ["N5F00001"]
    assert motor_seri_nolari("OZ-TS0001 - 0000111101 / 0000 111 102", "0000 111 101") == ["0000 111 101", "0000 111 102"]
    assert motor_seri_nolari("OZ-TS0001 projesi - RAL5017 - 9001") == []


def test_motor_sayisi_ve_okunma_sirasi():
    assert motor_sayisi("PP-1072-NF") == motor_sayisi("PP-1536-NF") == 2
    assert motor_sayisi("PP-536-NF") == motor_sayisi("PP-908-NF") == motor_sayisi("SVR-50-NF-BSP") == 1
    # Kırılım bazen başka bir güç ünitesinin motorunu yazıyor: iş emrinin kendi açıklaması önce gelir
    assert motor_listesi(["OZ-TS0001 / 0000 111 101", "OZ-TS0001 / 0000 111 109"], 1) == ["0000 111 101"]
    # İki motorlu: iki numara içeren ilk açıklama; hiçbirinde iki yoksa bulunanlar sırayla
    assert motor_listesi(["0000 111 101", "0000 111 102 - 0000 111 101"], 2) == ["0000 111 102", "0000 111 101"]
    assert motor_listesi(["0000 111 101", None, "N5F00001"], 2) == ["0000 111 101", "N5F00001"]


def test_iki_motorlu_guc_unitesi(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi(s2={"Ürün Kodu": "PP-1072-NF"})))
    liste = is_emirleri()
    liste[0].update({"* Ürün Kodu": "PP-1072-NF", "Açıklama": "OZ-TS0001 / 0000 111 101 / 0000 111 102 / RAL5017"})
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    pp = urun_id(uygulama, "PP-1072-NF")
    sayfa = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    # Her motorun numarası kendi alanında (iş emri açıklamasında ikisi yan yana yazıyor); kartın başında da
    assert "<dt>Motor 1 seri no</dt>" in sayfa and "<dt>Motor 2 seri no</dt>" in sayfa
    assert "<strong>0000 111 101</strong>" in sayfa and "<strong>0000 111 102</strong>" in sayfa
    kart = unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    assert "Motor 1 seri no <strong>0000 111 101</strong>" in kart and "Motor 2 seri no <strong>0000 111 102</strong>" in kart
    makineler = unescape(istemci.get("/makineler").get_data(as_text=True))
    assert "Motor 1:</small> 0000 111 101" in makineler and "Motor 2:</small> 0000 111 102" in makineler
    # Ekip ikinci motoru sebebiyle değiştirir; birinci ERP'den okunmaya devam eder
    gonder(f"/urun/{pp}/numara/motor2_seri_no", deger="0000111103", sebep="TEST SEBEP")
    kart = unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    assert "Motor 1 seri no <strong>0000 111 101</strong>" in kart and "Motor 2 seri no <strong>0000 111 103</strong>" in kart
    # Şablonda iki motor ayrı sütunlarda; şablon yalnızca boş numarayı doldurur (motor 1 ERP'den okundu, kilitli)
    kitap = openpyxl.load_workbook(io.BytesIO(istemci.get("/makine-numaralari.xlsx").data))
    sayfa_ = kitap.active
    satirlar = {r[0].value: r for r in sayfa_.iter_rows(min_row=2)}
    assert [h.value for h in sayfa_[1]][8] == "Motor 2 Seri No"
    assert [satirlar[pp][i].value for i in (8, 9, 10)] == ["0000 111 103", "0000 111 101", "0000 111 102"]
    satirlar[pp][7].value = "0000 111 104"
    svr = urun_id(uygulama, "SVR-50-NF-BSP")
    satirlar[svr][6].value = "TEST-SASI-001"
    satirlar[svr][8].value = "0000 111 105"  # tek motorlu olmayan makinede yok sayılır
    tampon = io.BytesIO()
    kitap.save(tampon)
    yukle(tampon.getvalue(), ad="makine numaralari.xlsx")
    assert ("1 makinenin boş numarası dolduruldu; 1 makinede numara zaten vardı, kilitli olduğu için değiştirilmedi"
            in unescape(istemci.get("/erp-yukleme").get_data(as_text=True)))
    assert "Motor 1 seri no <strong>0000 111 101</strong>" in unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    with uygulama.app_context():
        assert baglanti().execute("SELECT sasi_no, motor2_seri_no FROM urunler WHERE id = ?", (svr,)).fetchone()[:] == (
            "TEST-SASI-001", None)


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
    assert "Şasi no yok" in kart  # SVR'nin şasi no'su girilmedi; eksik görünür
    # Sevk edilecek makineler listesinden de; motor seri no ve iş emri orada da görünür
    makineler = istemci.get("/makineler").get_data(as_text=True)
    assert f'data-adres="/urun/{pp}"' in makineler and "0000 111 101" in makineler and "900101" in makineler
    assert istemci.get("/urun/999999").status_code == 404


def test_numaralar_kilitli(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    pp, svr = urun_id(uygulama, "PP-536-NF"), urun_id(uygulama, "SVR-50-NF-BSP")
    # Boş şasi no bir kez girilir, sonra kilitlenir
    sayfa = unescape(istemci.get(f"/urun/{svr}").get_data(as_text=True))
    assert "Kaydedince kilitlenir" in sayfa and "<dt>Şasi no</dt><dd><a" in sayfa
    gonder(f"/urun/{svr}/numara/sasi_no", deger="  TEST-SASI-001 ")
    sayfa = unescape(istemci.get(f"/urun/{svr}").get_data(as_text=True))
    assert "<strong>TEST-SASI-001</strong>" in sayfa and "Kaydedince kilitlenir" not in sayfa and "İlk giriş" in sayfa
    # ERP'den okunan motor seri no da kilitli: sebepsiz değişmez
    gonder(f"/urun/{pp}/numara/motor_seri_no", deger="0000111102")
    sayfa = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    assert "kilitli: değiştirmek için sebebini yazın" in sayfa and "<strong>0000 111 102</strong>" not in sayfa
    assert "<dt>Motor seri no</dt><dd><a" in sayfa and "Değiştirme sebebi" in sayfa
    gonder(f"/urun/{pp}/numara/motor_seri_no", deger="0000111102", sebep="TEST SEBEP")
    sayfa = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    assert "<strong>0000 111 102</strong>" in sayfa and "ekip girdi" in sayfa
    gecmis = sayfa[sayfa.index("Değişiklik geçmişi"):]
    assert "0000 111 101" in gecmis and "TEST SEBEP" in gecmis  # eski numara, yeni numara ve sebep saklanır
    # Makinede olmayan alan girilmez
    assert gonder(f"/urun/{svr}/numara/motor_seri_no", deger="0000111102").status_code == 404


def test_izleyici_numara_giremez(istemci, uygulama, ekle, giris, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    svr = urun_id(uygulama, "SVR-50-NF-BSP")
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert 'name="deger"' not in istemci.get(f"/urun/{svr}").get_data(as_text=True)
    assert gonder(f"/urun/{svr}/numara/sasi_no", deger="TEST-SASI-001").status_code == 403


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
    assert satirlar[urun_id(uygulama, "PP-536-NF")][9].value == "0000 111 101"  # ERP'den okunan, bilgi için
    satirlar[svr][6].value = "TEST-SASI-002"
    sayfa.append([999999, "OZ-TS0001", None, "SVR-50-NF-BSP", None, None, "TEST-SASI-003", None])  # eşleşmeyen
    tampon = io.BytesIO()
    kitap.save(tampon)
    yukle(tampon.getvalue(), ad="makine numaralari.xlsx")
    assert ("Makine numaraları: 3 satır okundu; 1 makinenin boş numarası dolduruldu; 1 satır hiçbir makineyle eşleşmedi"
            in unescape(istemci.get("/erp-yukleme").get_data(as_text=True)))
    assert "TEST-SASI-002" in istemci.get(f"/urun/{svr}").get_data(as_text=True)


def eklentili_siparis():
    return makine_siparisi() + [satir(6, "OZ04314", "PP Kablosuz Kumanda Seti")]


def test_pp_eklentisinin_montaj_durumu(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yukle(excel(eklentili_siparis()))
    kart = unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    assert 'name="montaj_durumu"' in kart and "<strong>1</strong> Sipariş talebi açılacak" in kart
    with uygulama.app_context():
        kalem_id = baglanti().execute("SELECT id FROM siparis_kalemleri WHERE urun_kodu = 'OZ04314'").fetchone()[0]
    assert gonder(f"/siparisler/kalem/{kalem_id}/montaj", montaj_durumu="yanlis").status_code == 400
    yanit = gonder(f"/siparisler/kalem/{kalem_id}/montaj", montaj_durumu="montaj_edildi", sonra="/siparisler/OZ-TS0001")
    assert yanit.status_code == 302 and yanit.headers["Location"].endswith("/siparisler/OZ-TS0001")
    kart = unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    assert 'value="montaj_edildi" selected' in kart and "<strong>1</strong> Montaj tamamlandı" in kart
    assert "Opsiyonel ekipmanlar" in kart
    secili = istemci.get("/siparisler/OZ-TS0001?goster=ek-montaj_edildi").get_data(as_text=True)
    assert "OZ04314" in secili and "SVR-50-NF-BSP" not in secili
    # Güç ünitesinin sayfasında da görünür
    pp = urun_id(uygulama, "PP-536-NF")
    assert "Güç ünitesinin opsiyonel ekipmanları" in unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    # ERP yüklemesi ekibin girdiği durumu değiştirmez
    yukle(excel(eklentili_siparis()))
    assert 'value="montaj_edildi" selected' in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)


def test_izleyici_montaj_durumunu_degistiremez(istemci, uygulama, ekle, giris, gonder, ekip, yukle):  # noqa: F811
    yukle(excel(eklentili_siparis()))
    with uygulama.app_context():
        kalem_id = baglanti().execute("SELECT id FROM siparis_kalemleri WHERE urun_kodu = 'OZ04314'").fetchone()[0]
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert 'name="montaj_durumu"' not in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    assert gonder(f"/siparisler/kalem/{kalem_id}/montaj", montaj_durumu="montaj_edildi").status_code == 403


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
