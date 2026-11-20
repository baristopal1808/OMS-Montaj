"""Kontrol listesi: güç ünitesinin ve vibrohammerın maddeleri, Sevke hazır kuralı, motor açılışı (kabin testinden
sonra, günüyle; WhatsApp mesajı), motor eksperi, müşterinin kabin seri no'su, stoktan atama ve göçün muafiyeti.
Veriler uydurmadır."""

import sqlite3
from datetime import date, timedelta
from html import unescape

from test_is_emirleri import IE_BASLIKLAR, ie
from test_siparisler import ekip, excel, makine_siparisi, satir, sorgu, yukle  # noqa: F401 (pytest fikstürleri)

from oms_montaj.bicim import tarih
from oms_montaj.motor_acilisi import mesaj_metni, telefon_duzelt
from oms_montaj.veritabani import GOCLER, baglanti

DUN = (date.today() - timedelta(days=1)).isoformat()
YARIN = (date.today() + timedelta(days=1)).isoformat()
EKSIKLER = "Kablosuz Kumanda Seti montajı, motor açılışı, metal etiket"
TEST_TELEFONU = "0500 000 00 00"  # uydurma


def kontrolu_tamamla(gonder, urun, maddeler=("motor_acilisi", "metal_etiket")):
    """Kontrol listesinin kurala giren maddelerini işaretler (opsiyonel ekipman hariç). Motor açılışı ancak kabin
    testi bittikten sonra (Temizlik ve sonrası) işaretlenir."""
    for madde in maddeler:
        gonder(f"/urun/{urun}/kontrol/{madde}", islem="yapildi", tarih=DUN)


def sayfa(istemci, adres):
    return unescape(istemci.get(adres).get_data(as_text=True))


def asama(uygulama, urun):
    return sorgu(uygulama, "SELECT asama FROM urunler WHERE id = ?", urun)[0]["asama"]


def urun_id(uygulama, kod):
    return sorgu(uygulama, "SELECT u.id FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
                 " WHERE k.urun_kodu = ? ORDER BY u.adet_sira", kod)[0]["id"]


def ilerlet(uygulama, urun, asama_="temizlik"):
    """Ürünü doğrudan bir aşamaya getirir; güç ünitesinin çıktı kuralı bu testlerin konusu değil (muaf)."""
    with uygulama.app_context():
        vt = baglanti()
        with vt:
            vt.execute("UPDATE urunler SET asama = ?, form_muaf = 1 WHERE id = ?", (asama_, urun))


def is_emirleri():
    """Siparişin güç ünitesinin (900101) ve vibrosunun (900102) iş emirleri; güç ünitesinde pompa montajı kırılımı."""
    return [
        ie(900101, 0, "PP-536-NF", sip_no="SS-SA1-OZ-TS0001-2-", aciklama="OZ-TS0001 - 0000 111 101 - TEST FIRMA"),
        ie(900101, 25, "CP0001", "PP Yag Tanki Montaji", envanter="Yarı Mamul", sip_no="SS-SA1-OZ-TS0001-2-"),
        ie(900101, 30, "CP0005", "POMPA MONTAJI - [NF/VM] - 100CC", envanter="Yarı Mamul", sip_no="SS-SA1-OZ-TS0001-2-"),
        ie(900102, 0, "SVR-50-NF-BSP", sip_no="SS-SA1-OZ-TS0001-1-"),
    ]


def hazirla(yukle, ekipman=True):  # noqa: F811
    satirlar = makine_siparisi() + ([satir(6, "OZ04314", "PP Kablosuz Kumanda Seti")] if ekipman else [])
    yukle(excel(satirlar))
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")


def test_guc_unitesinin_kontrol_listesi_ve_sevke_hazir_kurali(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    urun = sayfa(istemci, f"/urun/{pp}")
    for beklenen in ("Kontrol listesi", "Kablosuz Kumanda Seti montajı", "Sipariş talebi açılacak", "Motor açılışı",
                     "kabin testi tamamlanınca sorulur", "Motor eksperi", "Eksper yapılacak mı?", "Metal etiket yapıştırıldı",
                     f"Sevke hazır'a geçmeden önce tamamlanmalı: {EKSIKLER}."):
        assert beklenen in urun, beklenen
    # Pompa montajı sorulmaz (iş emrine tüketildiyse takılmıştır); kabin seri no yalnızca isteyen müşteride
    assert "Pompa montajı" not in urun and "kabin seri no" not in urun
    assert 'title="Kontrol: 0/3"' in sayfa(istemci, "/siparisler")

    # Kontrol listesi tamamlanmadan Sevke hazır'a da Sevk edildi'ye de geçilmez
    ilerlet(uygulama, pp)
    assert "kontrol listesi</a> tamamlanmalı" in sayfa(istemci, f"/urun/{pp}")  # aşama kutusunda da
    for hedef in ("sevke_hazir", "sevk_edildi"):
        gonder(f"/urun/{pp}/asama", asama=hedef)
        assert asama(uygulama, pp) == "temizlik"
    assert f"aşamasına geçmeden önce kontrol listesi tamamlanmalı: {EKSIKLER}." in sayfa(istemci, f"/urun/{pp}")

    # Motor açılışında yapıldığı gün sorulur; ileri bir gün olamaz
    gonder(f"/urun/{pp}/kontrol/motor_acilisi", islem="yapildi", tarih=YARIN)
    gonder(f"/urun/{pp}/kontrol/motor_acilisi", islem="yapildi")
    assert "yapıldığı günü yazın" in sayfa(istemci, f"/urun/{pp}")
    assert not sorgu(uygulama, "SELECT 1 FROM kontrol_isaretleri")
    assert gonder(f"/urun/{pp}/kontrol/motor_acilisi", islem="yanlis").status_code == 400
    assert gonder(f"/urun/{pp}/kontrol/ekipman", islem="yapildi").status_code == 404  # kendi bölümünden değişir
    assert gonder(f"/urun/{pp}/kontrol/pompa_montaji", islem="yapildi").status_code == 404  # madde kalktı

    kontrolu_tamamla(gonder, pp)
    gonder(f"/urun/{pp}/asama", asama="sevke_hazir")
    assert asama(uygulama, pp) == "temizlik"
    assert "tamamlanmalı: Kablosuz Kumanda Seti montajı." in sayfa(istemci, f"/urun/{pp}")
    kalem = sorgu(uygulama, "SELECT id FROM siparis_kalemleri WHERE urun_kodu = 'OZ04314'")[0]["id"]
    gonder(f"/siparisler/kalem/{kalem}/montaj", montaj_durumu="montaj_edildi")
    urun = sayfa(istemci, f"/urun/{pp}")
    for beklenen in ("Kontrol listesi tamamlandı.", f"Yapıldığı gün {tarih(DUN)}", "Kontrol listesi: motor açılışı yapıldı",
                     "Kontrol listesi: metal etiket yapıştırıldı"):
        assert beklenen in urun, beklenen
    assert 'title="Kontrol: 3/3"' in sayfa(istemci, "/siparisler")
    gonder(f"/urun/{pp}/asama", asama="sevke_hazir")  # motor eksperi kurala girmez
    assert asama(uygulama, pp) == "sevke_hazir"

    # Geri alınan işaret yeniden eksik olur; geri alırken (aşamayı geri almak) kural sorulmaz
    gonder(f"/urun/{pp}/kontrol/metal_etiket", islem="geri_al")
    gonder(f"/urun/{pp}/asama", asama="sevk_edildi")
    assert asama(uygulama, pp) == "sevke_hazir"
    assert "Kontrol listesi: metal etiket işareti geri alındı" in sayfa(istemci, f"/urun/{pp}")
    gonder(f"/urun/{pp}/asama", asama="temizlik", **{"not": "TEST NOT: temizlik eksik"})
    assert asama(uygulama, pp) == "temizlik"


def test_motor_acilisi_testten_sonra_ve_whatsapp(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
    # Kabin testi bitmeden motor açılışı işaretlenmez
    gonder(f"/urun/{pp}/kontrol/motor_acilisi", islem="yapildi", tarih=DUN)
    assert "kabin testi tamamlanınca" in sayfa(istemci, f"/urun/{pp}")
    assert not sorgu(uygulama, "SELECT 1 FROM kontrol_isaretleri")

    # Telefon girilmeden pencere açılır ama mesaj düğmesi Ayarlar'a yönlendirir
    ilerlet(uygulama, pp, "test")
    gonder(f"/urun/{pp}/asama", asama="temizlik")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "Kabin testi tamamlandı: motor açılışı gerekli" in urun and "telefon numarasını girin" in urun
    assert "Kabin testi tamamlandı: motor açılışı gerekli" not in sayfa(istemci, f"/urun/{pp}")  # bir kez açılır

    # Ayarlar'dan hitap ve telefon girilince hazır mesaj WhatsApp'ta açılır
    gonder("/ayarlar/motor-acilisi", hitap="TEST KULLANICI Bey", telefon=TEST_TELEFONU, mesaj="")
    ilerlet(uygulama, pp, "test")
    gonder(f"/urun/{pp}/asama", asama="temizlik")
    urun = sayfa(istemci, f"/urun/{pp}")
    mesaj = ("Merhaba TEST KULLANICI Bey, 0000 111 101 seri numaralı motorumuzun bulunduğu kabin testi tamamlandı. "
             "Motor açılışı gereklidir. Ne zaman müsaitsiniz?")
    assert "Kabin testi tamamlandı: motor açılışı gerekli" in urun and mesaj in urun
    assert "whatsapp://send?phone=905000000000&text=Merhaba%20TEST%20KULLANICI%20Bey%2C%200000%20111%20101" in urun
    assert "https://web.whatsapp.com/send?phone=905000000000" in urun
    # Pano üzerinden aşama değişince de pencere açılır (panoya dönülür)
    ilerlet(uygulama, pp, "test")
    gonder(f"/urun/{pp}/asama", asama="temizlik", sonra="/siparisler")
    assert mesaj in sayfa(istemci, "/siparisler")

    # "WhatsApp'ta aç"a basılınca zaman akışına yazılır; açılış yapılınca mesaj önerilmez
    assert gonder(f"/urun/{pp}/acilis-haberi").get_json() == {"tamam": True}
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "WhatsApp'tan haber verildi" in urun and "Motor açılışı için WhatsApp'tan haber verildi" in urun
    kontrolu_tamamla(gonder, pp, ("motor_acilisi",))
    assert "whatsapp://" not in sayfa(istemci, f"/urun/{pp}")
    assert gonder(f"/urun/{pp}/acilis-haberi").status_code == 404


def test_cat_motorunda_mesaj_onerilmez(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
    gonder("/ayarlar/motor-acilisi", hitap="TEST KULLANICI Bey", telefon=TEST_TELEFONU, mesaj="")
    with uygulama.app_context():
        vt = baglanti()
        with vt:
            vt.execute("INSERT INTO motor_bilgileri (urun_kodu, marka, model, zaman) VALUES ('PP-536-NF', 'CAT', 'TEST-MOTOR-2', '2026-11-19')")
    ilerlet(uygulama, pp, "test")
    gonder(f"/urun/{pp}/asama", asama="temizlik")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "Motor açılışı yapıldı mı?" in urun and "whatsapp://" not in urun


def test_motor_acilisi_ayarlari(istemci, uygulama, gonder, ekle, giris, ekip, yukle):  # noqa: F811
    assert "Motor açılışı bildirimi" in sayfa(istemci, "/ayarlar/motor-acilisi")
    gonder("/ayarlar/motor-acilisi", hitap="TEST KULLANICI Bey", telefon="12", mesaj="")
    assert "Telefon numarası anlaşılamadı" in sayfa(istemci, "/ayarlar/motor-acilisi")
    gonder("/ayarlar/motor-acilisi", hitap="TEST KULLANICI Bey", telefon=TEST_TELEFONU, mesaj="Motor hazır.")
    assert "{motor} geçmeli" in sayfa(istemci, "/ayarlar/motor-acilisi")
    assert not sorgu(uygulama, "SELECT 1 FROM ayarlar")
    gonder("/ayarlar/motor-acilisi", hitap="TEST KULLANICI Bey", telefon=TEST_TELEFONU, mesaj="Selam {hitap}: {motor} hazır.")
    ekran = sayfa(istemci, "/ayarlar/motor-acilisi")
    assert 'value="905000000000"' in ekran and "Selam TEST KULLANICI Bey: 0000 111 101 hazır." in ekran
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert gonder("/ayarlar/motor-acilisi", hitap="X", telefon="", mesaj="").status_code == 403


def test_mesaj_ve_telefon_bicimi():
    assert telefon_duzelt("0500 000 00 00") == telefon_duzelt("500 000 00 00") == "905000000000"
    assert telefon_duzelt("+90 (500) 000-00-00") == telefon_duzelt("0090-500-000-00-00") == "905000000000"
    assert telefon_duzelt("123") is None
    sablon = "Merhaba {hitap}, {motor} seri numaralı motorumuzun bulunduğu kabin testi tamamlandı."
    assert mesaj_metni(sablon, "", ["0000 111 101"]) == "Merhaba, 0000 111 101 seri numaralı motorumuzun bulunduğu kabin testi tamamlandı."
    assert mesaj_metni(sablon, "TEST KULLANICI Bey", ["0000 111 101", "0000 111 102"]) == (
        "Merhaba TEST KULLANICI Bey, 0000 111 101 ve 0000 111 102 seri numaralı motorlarımızın bulunduğu kabin testi tamamlandı.")


def test_vibronun_metal_etiketi_ve_muaf_urun(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle, ekipman=False)
    svr, kcn, pp = (urun_id(uygulama, kod) for kod in ("SVR-50-NF-BSP", "KCN-90", "PP-536-NF"))
    urun = sayfa(istemci, f"/urun/{svr}")
    assert "Metal etiket yapıştırıldı" in urun and "Motor açılışı" not in urun and "kabin seri no" not in urun
    gonder(f"/urun/{svr}/asama", asama="sevke_hazir")
    assert asama(uygulama, svr) != "sevke_hazir"
    kontrolu_tamamla(gonder, svr, ("metal_etiket",))
    gonder(f"/urun/{svr}/asama", asama="sevke_hazir")
    assert asama(uygulama, svr) == "sevke_hazir"
    # Çenede (ve kirişte) liste yok; listede olmayan madde işaretlenemez
    assert 'id="kontrol"' not in sayfa(istemci, f"/urun/{kcn}")
    assert gonder(f"/urun/{kcn}/kontrol/metal_etiket", islem="yapildi").status_code == 404
    assert gonder(f"/urun/{svr}/kontrol/motor_acilisi", islem="yapildi", tarih=DUN).status_code == 404
    # Kural başladığında Sevke hazır ya da Sevk edildi aşamasında olan ürün muaf: liste bilgi olarak görünür
    ilerlet(uygulama, pp, "sevke_hazir")
    with uygulama.app_context():
        vt = baglanti()
        with vt:
            vt.execute("UPDATE urunler SET kontrol_muaf = 1 WHERE id = ?", (pp,))
    gonder(f"/urun/{pp}/asama", asama="sevk_edildi")
    assert asama(uygulama, pp) == "sevk_edildi"
    assert "liste aşamaya bağlı değil" in sayfa(istemci, f"/urun/{pp}")


def test_motor_eksperi(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
    gonder(f"/urun/{pp}/kontrol/eksper", islem="yapilacak")
    assert "Eksper bekleniyor" in sayfa(istemci, f"/urun/{pp}")
    assert "Motor eksperi bekleniyor" in sayfa(istemci, "/siparisler")
    gonder(f"/urun/{pp}/kontrol/eksper", islem="yapildi")  # gün yazılmadı
    assert "yapıldığı günü yazın" in sayfa(istemci, f"/urun/{pp}")
    gonder(f"/urun/{pp}/kontrol/eksper", islem="yapildi", tarih=DUN)
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "Eksper yapıldı" in urun and f"Yapıldığı gün {tarih(DUN)}" in urun
    assert "Motor eksperi yapılacak (eksper bekleniyor)" in urun and "Motor eksperi yapıldı" in urun
    assert "Motor eksperi bekleniyor" not in sayfa(istemci, "/siparisler")
    # Cevap değiştirilebilir: geri alınınca yeniden sorulur
    gonder(f"/urun/{pp}/kontrol/eksper", islem="geri_al")
    assert "Eksper yapılacak mı?" in sayfa(istemci, f"/urun/{pp}")
    gonder(f"/urun/{pp}/kontrol/eksper", islem="yapilmayacak")
    assert "Eksper yapılmayacak" in sayfa(istemci, f"/urun/{pp}")


def test_musterinin_kabin_seri_nosu(istemci, uygulama, gonder, ekip, yukle, tmp_path):  # noqa: F811
    hazirla(yukle, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
    assert gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="TS-K000").status_code == 404  # müşteri istemiyor
    # Yalnızca müşteri ayarında "kabin_seri=evet" yazan müşterinin güç ünitesinde sorulur (renk boş bırakılabilir)
    (tmp_path / "marka" / "musteriler.txt").write_text("TS0;;kabin_seri=evet\n", encoding="utf-8")
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="  TS-K001 ")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert 'value="TS-K001"' in urun and "Müşterinin kabin seri no'su girildi: TS-K001" in urun
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="TS-K002")
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="TS-K002")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "değiştirildi: TS-K001 → TS-K002" in urun and "Müşterinin kabin seri no'su değişmedi." in urun
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="")
    assert "Müşterinin kabin seri no'su silindi (önceki: TS-K002)" in sayfa(istemci, f"/urun/{pp}")
    assert 'title="Kontrol: 0/2"' in sayfa(istemci, "/siparisler")  # kurala girmez


def test_izleyici_isaretleyemez(istemci, uygulama, gonder, ekle, giris, ekip, yukle):  # noqa: F811
    hazirla(yukle, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
    ilerlet(uygulama, pp)
    kontrolu_tamamla(gonder, pp, ("motor_acilisi",))
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "Motor açılışı yapıldı" in urun and f"/urun/{pp}/kontrol/" not in urun
    assert gonder(f"/urun/{pp}/kontrol/metal_etiket", islem="yapildi").status_code == 403


def test_stok_makinesinin_isaretleri_siparise_gecer(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    from test_stok import hazirla as stok_hazirla, stok_kartlari

    stok_hazirla(yukle)
    svr = stok_kartlari(uygulama, "SVR-50-NF-BSP")[0]
    pp = stok_kartlari(uygulama, "PP-540C-NF-T4")[0]
    stok_pp = sayfa(istemci, f"/urun/{pp['id']}")
    assert "Motor açılışı" in stok_pp and "kabin seri no" not in stok_pp  # stoktaki makinede de liste var
    kontrolu_tamamla(gonder, svr["id"], ("metal_etiket",))
    hedef = urun_id(uygulama, "SVR-50-NF-BSP")
    gonder(f"/stok/{svr['id']}/ata", hedef=hedef)
    assert sorgu(uygulama, "SELECT DISTINCT urun_id FROM kontrol_isaretleri")[0]["urun_id"] == hedef
    urun = sayfa(istemci, f"/urun/{hedef}")
    assert "Kontrol listesi tamamlandı." in urun and "Kontrol listesi: metal etiket yapıştırıldı" in urun


def test_kontrol_kuralinin_muafiyeti():
    # Göç 24: kural başladığında Sevke hazır ya da Sevk edildi aşamasındaki ürünler muaftır
    vt = sqlite3.connect(":memory:")
    for goc in GOCLER[:23]:
        vt.executescript(goc)
    vt.execute("INSERT INTO siparisler (id, siparis_no) VALUES (1, 'OZ-TS0001')")
    vt.execute("INSERT INTO siparis_kalemleri (id, siparis_id, sira_no, urun_kodu, miktar, tur) VALUES (1, 1, 1, 'PP-536-NF', 3, 'kart')")
    for urun, asama_ in ((1, "sevke_hazir"), (2, "sevk_edildi"), (3, "temizlik")):
        vt.execute("INSERT INTO urunler (id, kalem_id, adet_sira, asama) VALUES (?, 1, ?, ?)", (urun, urun, asama_))
    vt.executescript(GOCLER[23])
    assert dict(vt.execute("SELECT id, kontrol_muaf FROM urunler")) == {1: 1, 2: 1, 3: 0}
    vt.close()
