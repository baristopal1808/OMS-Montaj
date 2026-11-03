"""Uyarılar: çıkış yapılamayan (eksik) malzemeler ve "iş emri stoğa girmiş ama ERP İmalatta" uyarısı;
ekibin cevapları. Veriler uydurmadır."""

from html import unescape

from test_is_emirleri import IE_BASLIKLAR, is_emirleri
from test_siparisler import ekip, excel, makine_siparisi, yukle  # noqa: F401 (pytest fikstürleri)
from test_urunler import urun_id

from oms_montaj.erp_okuyucu import cikis_satirlari, rapor_turu
from oms_montaj.veritabani import baglanti

CIKIS_BASLIKLAR = [
    "Malzeme Kodu", "Malzeme Adı", "Malzeme Envanter Türü", "Ürün Agac Miktar", "Toplam Eldeki Miktar", "",
    "Gerceklesen Cikis Miktar", "Planlanan Takip Miktar", "Plan Birimi", "Ana Ürün Depo Miktar", "Üretim Depo Miktar",
    "Montaj Depo Miktar", "Montaj Üretim Depo Miktar", "Sevk Depo Miktar", "Ana Ürün Kodu", "Isemri No / Sıra",
]


def malzeme(ie_sira, kod, ad, plan, cikis, montaj=0, sevk=0, tur="Malzeme-Hizmet"):
    return {
        "Malzeme Kodu": kod, "Malzeme Adı": ad, "Malzeme Envanter Türü": tur, "Ürün Agac Miktar": plan,
        "Toplam Eldeki Miktar": montaj + sevk, "Gerceklesen Cikis Miktar": cikis, "Planlanan Takip Miktar": plan,
        "Plan Birimi": "Adet", "Ana Ürün Depo Miktar": 0, "Üretim Depo Miktar": 0, "Montaj Depo Miktar": montaj,
        "Montaj Üretim Depo Miktar": 0, "Sevk Depo Miktar": sevk, "Ana Ürün Kodu": "TEST", "Isemri No / Sıra": ie_sira,
    }


def cikis_raporu(hortum_plan=2):
    return [
        malzeme("900101 / 0", "MLZ0001", "Test Civata", plan=10, cikis=6, montaj=20),  # 4 eksik, depoda var
        malzeme("900101 / 25", "MLZ0002", "Test Hortum", plan=hortum_plan, cikis=0),  # depoda yok
        malzeme("900101 / 25", "MLZ0003", "Test Somun", plan=1, cikis=1),  # eksik değil
        malzeme("900102 / 0", "MLZ0004", "Test Pul", plan=3, cikis=1, sevk=1),  # 2 eksik, 1'i depoda
        malzeme("900199 / 0", "MLZ0005", "Test Conta", plan=1, cikis=0),  # iş emri listelerinde yok
    ]


def yuklenmis(yukle, **ie_degisen):  # noqa: F811
    yukle(excel(makine_siparisi()))
    liste = is_emirleri()
    for alan, deger in ie_degisen.items():
        liste[0][alan] = deger
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")


def json_gonder(istemci, adres, **veri):
    with istemci.session_transaction() as oturum:
        anahtar = oturum.setdefault("csrf", "test-csrf")
    return istemci.post(adres, data={"csrf": anahtar, **veri}, headers={"Accept": "application/json"}).get_json()


def test_cikis_raporu_okunur():
    basliklar = CIKIS_BASLIKLAR
    satirlar = [dict(zip(basliklar, [m.get(b) for b in basliklar])) for m in cikis_raporu()]
    assert rapor_turu(basliklar) == "cikis_yapilamayan"
    kayitlar = cikis_satirlari(basliklar, satirlar)
    assert kayitlar[1]["is_emri_no"] == "900101" and kayitlar[1]["sira_no"] == 25 and kayitlar[1]["plan_miktar"] == 2


def test_eksik_malzeme_gosterilir_ve_sorulur(istemci, uygulama, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    yukle(excel(cikis_raporu(), basliklar=CIKIS_BASLIKLAR), ad="cikis.xlsx")
    yukleme = unescape(istemci.get("/erp-yukleme").get_data(as_text=True))
    assert ("Çıkış yapılamayan malzeme: 5 satır okundu; 3 iş emrinde 4 malzemenin çıkışı yapılmamış"
            " (1 tanesi depoda var). 1 iş emri iş emirleri listesinde yok") in yukleme

    # Yapılacaklar: iş emri başına bir soru (900199 iş emri listelerinde olmadığından sorulmaz)
    sayfa = unescape(istemci.get("/yapilacaklar?konu=eksik").get_data(as_text=True))
    assert 'data-sayi-konu="eksik">2<' in sayfa and 'id="eksik-900101"' in sayfa and 'id="eksik-900102"' in sayfa
    assert "2 malzemenin</strong> çıkışı yapılmamış" in sayfa and "1 depoda var" in sayfa and "1 depoda yok" in sayfa
    assert "Bağlanamayan iş emirleri" not in sayfa  # konu süzgeci

    # Ürün sayfası: kırılımlar tıklanır (açılınca eksikleri), depoda olan ve olmayan ayrı
    pp = urun_id(uygulama, "PP-536-NF")
    urun = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    for beklenen in ("Eksik malzeme", '<details class="kirilim" id="eksik-25">', "PP Yag Tanki Montaji", "MLZ0001",
                     "MLZ0002", "Depoda var, çıkışı yapılmamış", "Depoda yok", "Montaj depo 20", "Bilginiz var mı?"):
        assert beklenen in urun, beklenen
    assert "kırılım ·" not in urun and 'id="yari-mamul"' not in urun  # yarı mamul yok
    assert '<details class="kirilim" id="eksik-25" open>' in unescape(
        istemci.get(f"/urun/{pp}?acik=eksik-25").get_data(as_text=True))  # kırılım tablosundaki bağlantı açar
    assert "MLZ0003" not in urun  # çıkışı tamam
    # Sipariş kartında iş emrinin yanında
    kart = unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    assert "2 malzeme eksik" in kart and "1 malzeme eksik" in kart

    # Cevap: soru kalkar, ürün sayfasında cevap görünür
    assert json_gonder(istemci, "/yapilacaklar/eksik/900101/cevap", cevap="yanlis")["tamam"] is False
    cevap = json_gonder(istemci, "/yapilacaklar/eksik/900101/cevap", cevap="bekleniyor")
    assert cevap["tamam"] is True and "Biliyorum, bekleniyor" in cevap["mesaj"]
    assert 'data-sayi-konu="eksik">1<' in istemci.get("/yapilacaklar").get_data(as_text=True)
    urun = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    assert "Ekibin cevabı: <strong>Biliyorum, bekleniyor</strong>" in urun and "Bilginiz var mı?" not in urun

    # Aynı rapor yeniden yüklenince sorulmaz; eksik artınca yeniden sorulur
    yukle(excel(cikis_raporu(), basliklar=CIKIS_BASLIKLAR), ad="cikis.xlsx")
    assert 'data-sayi-konu="eksik">1<' in istemci.get("/yapilacaklar").get_data(as_text=True)
    yukle(excel(cikis_raporu(hortum_plan=3), basliklar=CIKIS_BASLIKLAR), ad="cikis.xlsx")
    sayfa = unescape(istemci.get("/yapilacaklar").get_data(as_text=True))
    assert 'data-sayi-konu="eksik">2<' in sayfa and "Sonra yeni eksik geldi" in sayfa


def test_yari_mamuller(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    rapor = cikis_raporu() + [
        # Montajı aynı iş emrinin 25. kırılımında yapılıyor (CP0001) ve siparişin alt montaj iş emrinde (900104)
        malzeme("900101 / 0", "CP0001", "PP Yag Tanki Montaji", plan=1, cikis=0, tur="Yarı Mamul"),
        malzeme("900101 / 0", "CP0002", "Disli Kutusu Montaji", plan=1, cikis=0, tur="Yarı Mamul"),
        # Üreten kırılımı yok: depoda yok / depoda var
        malzeme("900101 / 25", "YRM0001", "Test Susturucu", plan=1, cikis=0, tur="Yarı Mamul"),
        malzeme("900101 / 25", "YRM0002", "Test Egzoz Borusu", plan=1, cikis=0, montaj=1, tur="Yarı Mamul"),
        malzeme("900104 / 0", "YRM0003", "Test Blok", plan=1, cikis=0, tur="Yarı Mamul"),  # alt montaj iş emri
    ]
    yukle(excel(rapor, basliklar=CIKIS_BASLIKLAR), ad="cikis.xlsx")
    assert "ayrıca 5 yarı mamulün çıkışı yapılmamış" in unescape(istemci.get("/erp-yukleme").get_data(as_text=True))
    # Yarı mamuller sorulmaz: 900104'te yalnızca yarı mamul var, soru yok
    sayfa = unescape(istemci.get("/yapilacaklar?konu=eksik").get_data(as_text=True))
    assert 'data-sayi-konu="eksik">2<' in sayfa and 'id="eksik-900104"' not in sayfa
    # Ürün sayfasında ayrı bölüm; durum ERP'den: üreten kırılım, depo
    pp = urun_id(uygulama, "PP-536-NF")
    urun = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    yari = urun[urun.index('id="yari-mamul"'):]
    assert "depo-imalat" not in yari and "<strong>3 yarı mamul</strong> henüz hazır değil · 1 tanesi hazır" in yari
    for beklenen in ("Montajı bekliyor", "Sıra 25 kırılımı", "İş emri 900104", "Bekleniyor", "Depoda var", "Montaj depo 1"):
        assert beklenen in yari, beklenen
    assert "MLZ0002" not in yari
    kart = unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    assert "3 yarı mamul bekleniyor" in kart and "1 yarı mamul bekleniyor" in kart  # PP ve alt montaj (900104)
    # Kırılım stoğa girince yarı mamulü "Montajı tamamlandı" olur
    liste = is_emirleri()
    liste[1]["Gerçek Mkt."] = 1  # 900101'in 25. kırılımı (CP0001)
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    urun = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    assert "Montajı tamamlandı" in urun and "<strong>2 yarı mamul</strong> henüz hazır değil · 2 tanesi hazır" in urun
    # ERP'nin göstermediği hazır parça işaretlenir; sayfa o kırılımı açık getirir
    yanit = gonder("/is-emri/900101/yari-mamul", sira="25", islem="secilen", sec="YRM0001", sonra=f"/urun/{pp}")
    assert yanit.headers["Location"].endswith(f"/urun/{pp}?acik=yari-25#yari-25")
    urun = unescape(istemci.get(f"/urun/{pp}?acik=yari-25").get_data(as_text=True))
    assert '<details class="kirilim" id="yari-25" open>' in urun and "2 hazır" in urun and "TEST KULLANICI" in urun
    # "Hepsi hazır" yalnızca hazır olmayanları işaretler
    gonder("/is-emri/900101/yari-mamul", sira="0", islem="hepsi")
    with uygulama.app_context():
        isaretli = {r[0] for r in baglanti().execute("SELECT malzeme_kodu FROM gelen_yari_mamuller")}
    assert isaretli == {"YRM0001", "CP0002"}
    assert "Bütün yarı mamuller hazır" in unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    assert "3 yarı mamul bekleniyor" not in unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    # İşaretler rapor yeniden yüklenince kalır; geri alınabilir
    yukle(excel(rapor, basliklar=CIKIS_BASLIKLAR), ad="cikis.xlsx")
    assert "Bütün yarı mamuller hazır" in unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    gonder("/is-emri/900101/yari-mamul", sira="25", geri_al="YRM0001")
    assert "<strong>1 yarı mamul</strong> henüz hazır değil" in unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    # Ürüne dağıtılmamış (alt montaj) iş emrinin kendi sayfası
    ie_sayfasi = unescape(istemci.get("/is-emri/900104").get_data(as_text=True))
    assert "İş emri 900104" in ie_sayfasi and "YRM0003" in ie_sayfasi and "alt montaj / yarı mamul" in ie_sayfasi
    assert istemci.get("/is-emri/999999").status_code == 404
    assert gonder("/is-emri/900101/yari-mamul", sira="7", islem="hepsi").status_code == 404  # 7. sırada yarı mamul yok


def test_yari_mamulun_rotasi(istemci, uygulama, ekip, yukle):  # noqa: F811
    # 26/10/2026 raporundan beri malzemenin rotası var: rotası olan parça imalatta işlenir, olmayan montajda yapılır
    yuklenmis(yukle)
    rapor = [
        {**malzeme("900101 / 25", "YRM0001", "Test Mil", plan=1, cikis=0, tur="Yarı Mamul"), "Rota Kodu": "U_TEST"},
        {**malzeme("900101 / 25", "YRM0002", "Test Kontrol Blogu Montaji", plan=1, cikis=0, tur="Yarı Mamul"), "Rota Kodu": "null"},
    ]
    yukle(excel(rapor, basliklar=CIKIS_BASLIKLAR + ["Rota Kodu"]), ad="cikis.xlsx")
    with uygulama.app_context():
        rotalar = dict(baglanti().execute("SELECT malzeme_kodu, rota_kodu FROM eksik_malzemeler"))
    assert rotalar == {"YRM0001": "U_TEST", "YRM0002": ""}
    urun = unescape(istemci.get(f"/urun/{urun_id(uygulama, 'PP-536-NF')}").get_data(as_text=True))
    yari = urun[urun.index('id="yari-mamul"'):]
    for beklenen in ("İmalattan bekleniyor", "Rota: U_TEST", "1 imalattan bekleniyor", "1 montajı bekliyor"):
        assert beklenen in yari, beklenen


def test_takip_edilmeyen_is_emri_sorulmaz(istemci, uygulama, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    yukle(excel([malzeme("900106 / 0", "MLZ0006", "Test Pim", plan=1, cikis=0)], basliklar=CIKIS_BASLIKLAR), ad="cikis.xlsx")
    assert 'id="eksik-900106"' in istemci.get("/yapilacaklar").get_data(as_text=True)  # 900106 bağlanamadı ama sorulur
    with uygulama.app_context():
        from oms_montaj.veritabani import baglanti

        ie = baglanti().execute("SELECT id FROM is_emirleri WHERE is_emri_no = '900106'").fetchone()[0]
    json_gonder(istemci, f"/yapilacaklar/is-emri/{ie}/bagla", secim="yoksay")
    assert 'id="eksik-900106"' not in istemci.get("/yapilacaklar").get_data(as_text=True)


def test_imalatta_farki_bilgi_olarak_gorunur(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    # PP'nin iş emri stoğa girmiş (900101), sipariş satırında ERP ürün durumu "İmalatta". Ekibe sorulmaz
    # (kullanıcı kararı, 02/11/2026); kartta fark bilgi olarak görünür, gerçek durum uygulamanın aşamasından.
    yuklenmis(yukle, **{"Gerçek Mkt.": 1})
    pp = urun_id(uygulama, "PP-536-NF")
    bilgi = "Planlama ERP'de: <strong>İmalatta</strong> · bizde: <strong>Montaj</strong>"
    assert bilgi in unescape(istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True))
    urun = unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))
    assert bilgi in urun and "Ürün nerede?" not in urun and "Emin misiniz?" not in urun
    assert 'data-sayi-konu="imalatta"' not in istemci.get("/yapilacaklar").get_data(as_text=True)
    with uygulama.app_context():
        ie = baglanti().execute("SELECT is_emri_id FROM urunler WHERE id = ?", (pp,)).fetchone()[0]
    assert gonder(f"/yapilacaklar/imalatta/{pp}/{ie}/cevap", cevap="montajda").status_code == 404
    # ERP'deki durum değişince bilgi kalkar
    yukle(excel(makine_siparisi(s2={"Ürün Durumu": "Montajda"})))
    assert "Planlama ERP'de" not in unescape(istemci.get(f"/urun/{pp}").get_data(as_text=True))


def test_izleyici_cevaplayamaz(istemci, uygulama, ekle, giris, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    yukle(excel(cikis_raporu(), basliklar=CIKIS_BASLIKLAR), ad="cikis.xlsx")
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert 'name="cevap"' not in istemci.get("/yapilacaklar").get_data(as_text=True)
    assert gonder("/yapilacaklar/eksik/900101/cevap", cevap="bekleniyor").status_code == 403
