"""Kontrol listesi: güç ünitesinin ve vibrohammerın maddeleri, Sevke hazır kuralı, motor açılışının günü, ERP'den
pompa montajı, motor eksperi, müşterinin kabin seri no'su, stoktan atama ve göçün muafiyeti. Veriler uydurmadır."""

import sqlite3
from datetime import date, timedelta
from html import unescape

from test_is_emirleri import IE_BASLIKLAR, ie
from test_siparisler import ekip, excel, makine_siparisi, satir, sorgu, yukle  # noqa: F401 (pytest fikstürleri)

from oms_montaj.bicim import tarih
from oms_montaj.veritabani import GOCLER, baglanti

DUN = (date.today() - timedelta(days=1)).isoformat()
YARIN = (date.today() + timedelta(days=1)).isoformat()
EKSIKLER = "pompa montajı, Kablosuz Kumanda Seti montajı, motor açılışı, metal etiket"


def kontrolu_tamamla(gonder, urun, maddeler=("pompa_montaji", "motor_acilisi", "metal_etiket")):
    """Kontrol listesinin kurala giren maddelerini işaretler (opsiyonel ekipman hariç)."""
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


def is_emirleri(pompa_tamam=False):
    """Siparişin güç ünitesinin (900101) ve vibrosunun (900102) iş emirleri; güç ünitesinde pompa montajı kırılımı."""
    return [
        ie(900101, 0, "PP-536-NF", sip_no="SS-SA1-OZ-TS0001-2-", aciklama="OZ-TS0001 - 0000 111 101 - TEST FIRMA"),
        ie(900101, 25, "CP0001", "PP Yag Tanki Montaji", envanter="Yarı Mamul", sip_no="SS-SA1-OZ-TS0001-2-"),
        ie(900101, 30, "CP0005", "POMPA MONTAJI - [NF/VM] - 100CC", envanter="Yarı Mamul", sip_no="SS-SA1-OZ-TS0001-2-",
           gercek=1 if pompa_tamam else 0),
        ie(900102, 0, "SVR-50-NF-BSP", sip_no="SS-SA1-OZ-TS0001-1-"),
    ]


def hazirla(yukle, pompa_tamam=False, ekipman=True):  # noqa: F811
    satirlar = makine_siparisi() + ([satir(6, "OZ04314", "PP Kablosuz Kumanda Seti")] if ekipman else [])
    yukle(excel(satirlar))
    yukle(excel(is_emirleri(pompa_tamam), basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")


def test_guc_unitesinin_kontrol_listesi_ve_sevke_hazir_kurali(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    urun = sayfa(istemci, f"/urun/{pp}")
    for beklenen in ("Kontrol listesi", "Pompa montajı tamamlandı", "ERP: 0/1 pompa kırılımı stoğa girdi",
                     "Kablosuz Kumanda Seti montajı", "Sipariş talebi açılacak", "Motor açılışı yapıldı", "Motor eksperi",
                     "Eksper yapılacak mı?", "Metal etiket yapıştırıldı", "Müşterinin kabin seri no'su",
                     f"Sevke hazır'a geçmeden önce tamamlanmalı: {EKSIKLER}."):
        assert beklenen in urun, beklenen
    assert 'title="Kontrol: 0/4"' in sayfa(istemci, "/siparisler")

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

    kontrolu_tamamla(gonder, pp)
    gonder(f"/urun/{pp}/asama", asama="sevke_hazir")
    assert asama(uygulama, pp) == "temizlik"
    assert "tamamlanmalı: Kablosuz Kumanda Seti montajı." in sayfa(istemci, f"/urun/{pp}")
    kalem = sorgu(uygulama, "SELECT id FROM siparis_kalemleri WHERE urun_kodu = 'OZ04314'")[0]["id"]
    gonder(f"/siparisler/kalem/{kalem}/montaj", montaj_durumu="montaj_edildi")
    urun = sayfa(istemci, f"/urun/{pp}")
    for beklenen in ("Kontrol listesi tamamlandı.", f"Yapıldığı gün {tarih(DUN)}", "Kontrol listesi: motor açılışı yapıldı",
                     "Kontrol listesi: metal etiket yapıştırıldı", "Kontrol listesi: pompa montajı tamamlandı"):
        assert beklenen in urun, beklenen
    assert 'title="Kontrol: 4/4"' in sayfa(istemci, "/siparisler")
    gonder(f"/urun/{pp}/asama", asama="sevke_hazir")  # motor eksperi kurala girmez
    assert asama(uygulama, pp) == "sevke_hazir"

    # Geri alınan işaret yeniden eksik olur; geri alırken (aşamayı geri almak) kural sorulmaz
    gonder(f"/urun/{pp}/kontrol/metal_etiket", islem="geri_al")
    gonder(f"/urun/{pp}/asama", asama="sevk_edildi")
    assert asama(uygulama, pp) == "sevke_hazir"
    assert "Kontrol listesi: metal etiket işareti geri alındı" in sayfa(istemci, f"/urun/{pp}")
    gonder(f"/urun/{pp}/asama", asama="temizlik", **{"not": "TEST NOT: temizlik eksik"})
    assert asama(uygulama, pp) == "temizlik"


def test_pompa_montaji_erpden(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle, pompa_tamam=True, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "ERP: 1/1 pompa kırılımı stoğa girdi" in urun and "ERP'de tamamlandı; işaretlemeye gerek yok." in urun
    assert "tamamlanmalı: motor açılışı, metal etiket." in urun
    assert 'title="Kontrol: 1/3"' in sayfa(istemci, "/siparisler")


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


def test_musterinin_kabin_seri_nosu(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="  TS-K001 ")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert 'value="TS-K001"' in urun and "Müşterinin kabin seri no'su girildi: TS-K001" in urun
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="TS-K002")
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="TS-K002")
    urun = sayfa(istemci, f"/urun/{pp}")
    assert "değiştirildi: TS-K001 → TS-K002" in urun and "Müşterinin kabin seri no'su değişmedi." in urun
    gonder(f"/urun/{pp}/kontrol/kabin_seri_no", deger="")
    assert "Müşterinin kabin seri no'su silindi (önceki: TS-K002)" in sayfa(istemci, f"/urun/{pp}")
    assert 'title="Kontrol: 0/3"' in sayfa(istemci, "/siparisler")  # kurala girmez


def test_izleyici_isaretleyemez(istemci, uygulama, gonder, ekle, giris, ekip, yukle):  # noqa: F811
    hazirla(yukle, ekipman=False)
    pp = urun_id(uygulama, "PP-536-NF")
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
    assert "Motor açılışı yapıldı" in stok_pp and "kabin seri no" not in stok_pp  # stoktaki makinede de liste var
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
