"""Açık ve kapalı iş emirleri listelerinin yüklenmesi, siparişe bağlanması ve sipariş kartında görünmesi.

Excel dosyaları test anında uydurma veriyle üretilir; sütun başlıkları ERP'ninkilerle aynıdır.
"""

from datetime import datetime
from html import unescape

from test_siparisler import ekip, excel, makine_siparisi, yukle  # noqa: F401 (ekip ve yukle pytest fikstürleri)

from oms_montaj.erp_okuyucu import is_emri_satirlari, rapor_turu

IE_BASLIKLAR = [
    "Tipi", "* Durumu", "* İş Emri No", "* Sıra No", "* Ürün Kodu", "* Ürün Adı", "*Plan Mkt.", "Gerçek Mkt.",
    "Kalan Mkt.", "* İşEmri Başlama Tarihi", "*Kaynak Tipi", "Açıklama", "İşEmri Açma Tarihi", "Tahmini Bitiş Tarihi",
    "İşEmri Kapatma Tarihi", "İlk Stok Giriş Tar.", "Son Stok Giriş Tar.", "Sip. No", "Envanter Tipi",
]


def ie(no, sira, kod, ad="TEST URUN", durum="Açık", plan=1, gercek=0, aciklama=None, sip_no="---",
       envanter="Son Ürün", kapatma=None, ilk_giris=None):
    return {
        "Tipi": "Otomatik", "* Durumu": durum, "* İş Emri No": no, "* Sıra No": sira, "* Ürün Kodu": kod,
        "* Ürün Adı": ad, "*Plan Mkt.": plan, "Gerçek Mkt.": gercek, "Kalan Mkt.": plan - gercek,
        "* İşEmri Başlama Tarihi": datetime(2026, 10, 1), "*Kaynak Tipi": "Montaj", "Açıklama": aciklama,
        "İşEmri Açma Tarihi": datetime(2026, 10, 1), "Tahmini Bitiş Tarihi": datetime(2026, 11, 20),
        "İşEmri Kapatma Tarihi": kapatma, "İlk Stok Giriş Tar.": ilk_giris, "Son Stok Giriş Tar.": ilk_giris,
        "Sip. No": sip_no, "Envanter Tipi": envanter,
    }


def is_emirleri():
    """makine_siparisi() (OZ-TS0001) için bağlantının her yolundan bir iş emri."""
    return [
        # ERP bağlantısı: sipariş satırının "Bağlı İşemri No"su (2. satır PP) ve kırılımı
        ie(900101, 0, "PP-536-NF", sip_no="SS-SA1-OZ-TS0001-2-"),
        ie(900101, 25, "CP0001", "PP Yag Tanki Montaji", envanter="Yarı Mamul", sip_no="SS-SA1-OZ-TS0001-2-"),
        # ERP bağlantısı: iş emrinin "Sip. No"su (1. satır SVR)
        ie(900102, 0, "SVR-50-NF-BSP", sip_no="SS-SA1-OZ-TS0001-1-"),
        # Açıklamadaki proje kodu, aynı ürün; 2 adetin biri stoğa girmiş
        ie(900103, 0, "KCN-90", plan=2, gercek=1, aciklama="OZ-TS0001 projesi için üretilecektir.",
           ilk_giris=datetime(2026, 10, 15)),
        # Proje kodu var, ürün siparişte yok: alt montaj
        ie(900104, 0, "CP0002", "Disli Kutusu Montaji", envanter="Yarı Mamul", aciklama="OZ-TS0001 projesi için"),
        # Stok için
        ie(900105, 0, "OVR-70-S", aciklama="Stok için üretilecektir."),
        # Bağlantı yok
        ie(900106, 0, "SCN-90"),
        # Üretim girişi olmadan kapatılmış (4. satır kiriş)
        ie(900107, 0, "CB-HS5080-00", durum="Kapalı", aciklama="OZ-TS0001 projesi", kapatma=datetime(2026, 10, 10)),
    ]


def test_is_emri_raporu_okunur():
    basliklar = IE_BASLIKLAR
    satirlar = [dict(zip(basliklar, (r.get(b) for b in basliklar))) for r in is_emirleri()]
    assert rapor_turu(basliklar) == "is_emirleri"
    kayitlar = is_emri_satirlari(basliklar, satirlar)
    assert len(kayitlar) == 8
    assert kayitlar[0]["is_emri_no"] == "900101" and kayitlar[0]["sira_no"] == 0
    assert kayitlar[2]["erp_siparis"] == "SS-SA1-OZ-TS0001-1-"
    assert kayitlar[5]["erp_siparis"] is None  # "---" boş sayılır
    assert kayitlar[0]["acilis_tarihi"] == "2026-10-01"


def test_is_emirleri_siparise_baglanir(istemci, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="acik is emirleri.xlsx")
    sayfa = unescape(istemci.get("/erp-yukleme").get_data(as_text=True))
    assert "7 iş emri okundu (6 açık, 1 kapalı)" in sayfa
    assert ("İş emirleri: 4 tanesi sipariş satırına bağlı, 1 tanesi projenin alt montajı ya da yarı mamulü,"
            " 1 tanesi stok için, 1 tanesi bağlanamadı (Yapılacaklar'da sorulur).") in sayfa
    # 900103 iki çene için, biri stoğa girmiş: o çene "Montaj tamamlandı", öbürü "Malzeme hazırlık"
    assert 'Aşaması ilerleyen: 3 ürün "Malzeme hazırlık", 1 ürün "Montaj tamamlandı".' in sayfa

    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    for beklenen in ("900101", "900102", "900103", "Kısmen tamamlandı", "1/2 stoğa girdi",
                     "Üretim girişi olmadan kapatıldı", "Alt montajlar ve yarı mamuller", "CP0002", "Malzeme hazırlık"):
        assert beklenen in kart, beklenen
    assert "900105" not in kart and "900106" not in kart
    assert "iş emri listelerinde yok" not in kart
    # Seri no ve iş emri no ürünün satırında aynı düzeyde; seri no'su olmayan kirişte "Seri no yok" yazmaz
    assert "Seri no yok" not in kart
    assert '<span class="bilgi">İş emri <a class="duz-baglanti" href="/is-emri/900107"><strong>900107</strong></a></span>' in kart
    assert '<span class="bilgi">Seri no <strong>OZ-TS0001-VH-01</strong></span>' in kart


def test_asama_erpye_gore_ilerler_geri_gelmez(istemci, uygulama, ekip, yukle):  # noqa: F811
    from oms_montaj.veritabani import baglanti

    def asamalar():
        with uygulama.app_context():
            return dict(baglanti().execute(
                "SELECT k.urun_kodu || '/' || u.adet_sira, u.asama FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
            ).fetchall())

    yukle(excel(makine_siparisi()))
    liste = is_emirleri()
    liste[1]["Gerçek Mkt."] = 1  # PP'nin (900101) bir kırılımı stoğa girdi: montaj başladı
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    assert asamalar()["PP-536-NF/1"] == "montaj"
    assert (asamalar()["KCN-90/1"], asamalar()["KCN-90/2"]) == ("montaj_tamamlandi", "malzeme_hazirlik")
    assert asamalar()["SVR-50-NF-BSP/1"] == "malzeme_hazirlik"
    # İş emri tamamlanınca "Montaj tamamlandı"; ekibin ileri aldığı ürün ERP yüzünden geri gelmez
    with uygulama.app_context():
        vt = baglanti()
        with vt:
            vt.execute("UPDATE urunler SET asama = 'test' WHERE kalem_id = (SELECT id FROM siparis_kalemleri"
                       " WHERE urun_kodu = 'SVR-50-NF-BSP')")
    liste[0].update({"* Durumu": "Kapalı", "Gerçek Mkt.": 1, "İşEmri Kapatma Tarihi": datetime(2026, 10, 20)})
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    assert asamalar()["PP-536-NF/1"] == "montaj_tamamlandi" and asamalar()["SVR-50-NF-BSP/1"] == "test"
    assert "Montaj tamamlandı" in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)


def test_once_is_emri_sonra_siparis_yuklenince_de_baglanir(istemci, ekip, yukle):  # noqa: F811
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="acik is emirleri.xlsx")
    yukle(excel(makine_siparisi()))
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    assert "900102" in kart and "Malzeme hazırlık" in kart


def test_kapali_listede_yalniz_kirilimi_olan_is_emri(istemci, uygulama, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="acik is emirleri.xlsx")
    # 900101 açık; bitmiş bir kırılımı kapalı listede, ana satırı yok
    kirilim = [ie(900101, 30, "CP0003", "PP Filtre Montaji", durum="Kapalı", gercek=1, envanter="Yarı Mamul",
                  sip_no="SS-SA1-OZ-TS0001-2-")]
    yukle(excel(kirilim, basliklar=IE_BASLIKLAR), ad="kapali is emirleri.xlsx")
    assert "1 iş emrinin yalnızca kırılımları var" in istemci.get("/erp-yukleme").get_data(as_text=True)
    with uygulama.app_context():
        from oms_montaj.veritabani import baglanti
        vt = baglanti()
        ana = vt.execute("SELECT * FROM is_emirleri WHERE is_emri_no = '900101'").fetchone()
        assert (ana["urun_kodu"], ana["durum"]) == ("PP-536-NF", "Açık")
        kirilimlar = vt.execute("SELECT sira_no, durum FROM is_emri_satirlari WHERE is_emri_id = ? ORDER BY sira_no",
                                (ana["id"],)).fetchall()
        assert [tuple(k) for k in kirilimlar] == [(25, "Açık"), (30, "Kapalı")]  # iki listeden birleşti


def test_kapanan_is_emri(istemci, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="acik is emirleri.xlsx")
    kapali = [ie(900101, 0, "PP-536-NF", durum="Kapalı", gercek=1, sip_no="SS-SA1-OZ-TS0001-2-",
                 kapatma=datetime(2026, 10, 20), ilk_giris=datetime(2026, 10, 20))]
    yukle(excel(kapali, basliklar=IE_BASLIKLAR), ad="kapali is emirleri.xlsx")
    assert "1 iş emri ERP'de kapandı" in unescape(istemci.get("/erp-yukleme").get_data(as_text=True))
    kart = unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    assert "ERP'de iş emri tamamlandı" in kart and "kapanış 20/10/2026" in kart


def test_erp_kapanis_notu_aciklamadan_silinir():
    from oms_montaj.erp_okuyucu import kapanis_notunu_sil

    not_ = "NOLU İŞEMRİNİN PLAN MİKTAR <= GERÇEKLEŞEN MIKTAR DURUMUNDAN DOLAYI ZAMANLANMIS GOREV TARAFINDAN KAPATILDI."
    assert kapanis_notunu_sil(f"OZ-TS0001 / 0000 111 1011 / STANDART0 {not_}", 0) == "OZ-TS0001 / 0000 111 1011 / STANDART"
    # Sıra numarası motor seri no'suna yapışmış olsa da ayrılır
    assert kapanis_notunu_sil(f"OZ-TS0001 - 0000 111 101125 {not_}", 25) == "OZ-TS0001 - 0000 111 1011"
    # Kırılım ana satırın açıklamasını taşıyorsa notun numarası 0
    assert kapanis_notunu_sil(f"OZ-TS0001 - TEST FIRMA0 {not_}", 25) == "OZ-TS0001 - TEST FIRMA"
    assert kapanis_notunu_sil(f"0 {not_}", 0) is None
    # Birden çok kez kapanmış iş emrinde not tekrar ediyor
    assert kapanis_notunu_sil(f"OZ-TS0001 - 0000 111 10110 {not_}0 {not_}", 0) == "OZ-TS0001 - 0000 111 1011"
    assert kapanis_notunu_sil("OZ-TS0001 projesi için", 0) == "OZ-TS0001 projesi için"


def test_siparisin_durum_ozeti(istemci, uygulama, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="acik is emirleri.xlsx")
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    ozet = kart[kart.index('class="durum-ozeti"'):]
    ozet = ozet[:ozet.index("</div>")]
    # SVR ve PP açık, iki çene kısmen, kirişin iş emri üretimsiz kapandığı için açılmadı sayılır
    for beklenen in ("5 ürün", "<strong>2</strong> Kısmen tamamlandı", "<strong>2</strong> İş emri açık",
                     "<strong>1</strong> İş emri açılmadı"):
        assert beklenen in ozet, beklenen
    assert "ud-serit-acik" in kart and "ud-serit-yok" in kart
    # Bir duruma tıklayınca yalnızca o durumdaki kalemler görünür
    assert 'href="/siparisler/OZ-TS0001?goster=ud-acik#kalemler"' in kart
    acik = istemci.get("/siparisler/OZ-TS0001?goster=ud-acik").get_data(as_text=True)
    assert "SVR-50-NF-BSP" in acik and "PP-536-NF" in acik and "KCN-90" not in acik and "CB-HS5080-00" not in acik
    assert "bütün kalemleri göster" in acik
    yok = istemci.get("/siparisler/OZ-TS0001?goster=ud-yok").get_data(as_text=True)
    assert "CB-HS5080-00" in yok and "SVR-50-NF-BSP" not in yok
    # Tanınmayan seçim yok sayılır
    assert "SVR-50-NF-BSP" in istemci.get("/siparisler/OZ-TS0001?goster=ud-xx").get_data(as_text=True)
