"""Stoktaki makineler (stok.py): depo stok raporlarından adet kadar "Stok" kartı, stok iş emrinin bağlanması, test
sorusu, siparişe atama, depoda adet azalınca kartların kalkması, elle ekleme ve stoktan çıkarma. Veriler uydurmadır."""

from datetime import datetime
from html import unescape

from test_is_emirleri import IE_BASLIKLAR, ie
from test_pano import sutun
from test_siparisler import ekip, excel, makine_siparisi, satir, sorgu, yukle  # noqa: F401 (pytest fikstürleri)

from oms_montaj.stok import depo_bul, stok_ailesi

STOK_BASLIKLAR = ["EtkinlikGöstergesi", "MalzemeKodu", "MalzemeAdı", "EldekiMiktar", "DepoKodu"]


def depo_raporu(adetler):
    satirlar = [{"EtkinlikGöstergesi": "Aktif", "MalzemeKodu": kod, "MalzemeAdı": "TEST URUN", "EldekiMiktar": adet}
                for kod, adet in adetler.items()]
    satirlar.append({"MalzemeKodu": "OZ00002", "MalzemeAdı": "TEST CIVATA", "EldekiMiktar": 0})  # miktarı olmayan atlanır
    return excel(satirlar, basliklar=STOK_BASLIKLAR)


def is_emirleri():
    return [
        # Siparişin güç ünitesi: tamamlandı, stoğa girdi (montaj üretim deposunda; stok sayılmaz)
        ie(900101, 0, "PP-536-NF", durum="Kapalı", gercek=1, sip_no="SS-SA1-OZ-TS0001-2-",
           kapatma=datetime(2026, 10, 20), ilk_giris=datetime(2026, 10, 20)),
        # Stok için açılmış, stoğa girmiş güç ünitesi; açıklamasında motor seri no
        ie(900111, 0, "PP-540C-NF-T4", durum="Kapalı", gercek=1, aciklama="Stok için üretilmiştir. 0000 111 101",
           kapatma=datetime(2026, 9, 1), ilk_giris=datetime(2026, 9, 1)),
    ]


SEVK = {"PP-540C-NF-T4": 2, "KCN-60": 3, "SVR-50-NF-BSP": 1, "OZ00001": 5, "OVR-120-S-02-00": 1}
MONTAJ_URETIM = {"PP-536-NF": 1, "PP-540C-NF-T4": 1, "SVR-82-NF-02-02-02-00": 4}


def hazirla(yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="acik kapali is emirleri.xlsx")
    yukle(depo_raporu(SEVK), ad="sevk depo stok raporu.xlsx")
    yukle(depo_raporu(MONTAJ_URETIM), ad="montaj üretim depo stok raporu.xlsx")


def sayfa(istemci, adres):
    return unescape(istemci.get(adres).get_data(as_text=True))


def stok_kartlari(uygulama, kod=None):
    return sorgu(uygulama, "SELECT * FROM urunler WHERE kalem_id IS NULL AND stok_cikis IS NULL"
                 + (" AND stok_kodu = ?" if kod else "") + " ORDER BY id", *([kod] if kod else []))


def test_depo_ve_stok_kurallari():
    assert depo_bul("sevk depo stok raporu.xls") == "sevk"
    assert depo_bul("MONTAJ ÜRETİM DEPO.xlsx") == "montaj_uretim"
    assert depo_bul("montaj depo stok raporu.xls") == "montaj"
    assert depo_bul("stok raporu.xls") is None
    # Makine, çene ve kiriş kart olur; alt montaj kodları (rakamlı ekler, "MONTAJ") ve aksesuarlar olmaz
    assert stok_ailesi("PP-551-NF/VM-STAGE IV") == "PP"
    assert stok_ailesi("CB-HS5080-00") == "Kiriş"
    # OVF ve WD'de makine ile parçası aynı önekli: yalnızca siparişte ya da iş emrinde makine olarak görülen kod
    # (ya da ekibin elle eklediği) stok kartı olur
    assert stok_ailesi("WD-28-43-VD") is None and stok_ailesi("OVF-300-BF-LM-B") is None
    assert stok_ailesi("WD-28-43-VD", {"WD-28-43-VD"}) == "WD" and stok_ailesi("WD-28-43-VD", elle=True) == "WD"
    assert stok_ailesi("WD-28-43-VD-02-02-00", elle=True) is None
    assert stok_ailesi("KCN-60") == "Çene" and stok_ailesi("ACN-90") == "Çene"
    for kod in ("OVR-120-S-02-00", "SVR-82-NF-05-00-JIC", "PP-536-POMPA ANA MONTAJI", "SCN-350-01-00-MON", "OZ00001",
                "PP-536-MNT"):
        assert stok_ailesi(kod) is None, kod
    # Siparişte kart satırı ya da iş emrinde son ürün olarak görülen kod biçiminden bağımsız kart olur
    assert stok_ailesi("SVR-40-VM-02-02-15", {"SVR-40-VM-02-02-15"}) == "SVR"


def test_depo_raporundan_stok_kartlari(istemci, uygulama, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(is_emirleri(), basliklar=IE_BASLIKLAR), ad="acik kapali is emirleri.xlsx")
    yukle(depo_raporu(SEVK), ad="sevk depo stok raporu.xlsx")
    assert not stok_kartlari(uygulama)  # iki deponun raporu birlikte gerekli
    assert "montaj üretim deposunun stok raporları" in sayfa(istemci, "/stok")
    yukle(depo_raporu(MONTAJ_URETIM), ad="montaj üretim depo stok raporu.xlsx")
    yukleme = sayfa(istemci, "/erp-yukleme")
    assert "Stok: 7 yeni stok kartı açıldı, 1 stok kartına ERP'deki stok iş emri bağlandı." in yukleme
    assert "Montaj üretim deposu: 3 malzemenin stoğu var; 2 adet makine, çene ya da kiriş." in yukleme

    pp = stok_kartlari(uygulama, "PP-540C-NF-T4")
    assert sorted(k["depo"] for k in pp) == ["montaj_uretim", "sevk", "sevk"]
    assert sum(1 for k in pp if k["is_emri_id"]) == 1
    assert len(stok_kartlari(uygulama, "KCN-60")) == 3 and len(stok_kartlari(uygulama, "SVR-50-NF-BSP")) == 1
    assert not stok_kartlari(uygulama, "PP-536-NF")  # siparişin güç ünitesi depoda ama stok değil

    # Panoda yalnızca makineler; çeneler Stok ekranında
    pano = sutun(sayfa(istemci, "/siparisler"), "sevke_hazir")
    assert pano.count("PP-540C-NF-T4</strong>") == 3 and ">Stok</a>" in pano and "KCN-60" not in pano
    assert "0000 111 101 !" in pano  # stok iş emrinin açıklamasından okunan motor seri no, teyit bekliyor
    stok = sayfa(istemci, "/stok")
    for beklenen in ("PP-540C-NF-T4", "KCN-60", "SVR-50-NF-BSP", "Çeneler ve kirişler", "900111", "Sorulacak"):
        assert beklenen in stok, beklenen
    assert "OVR-120-S-02-00" not in stok and "SVR-82-NF-02" not in stok

    # Montaj üretim deposundaki makinede test sorulur
    mu = next(k for k in pp if k["depo"] == "montaj_uretim")
    urun = sayfa(istemci, f"/urun/{mu['id']}")
    assert "Testi yapıldı mı?" in urun and "Sorulacak" in urun and 'id="asama"' not in urun


def test_stoktan_siparise_atama(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle)
    svr = stok_kartlari(uygulama, "SVR-50-NF-BSP")[0]
    hedef = sorgu(uygulama, "SELECT u.id FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
                  " WHERE k.urun_kodu = 'SVR-50-NF-BSP'")[0]["id"]
    # İş emri açılmamış sipariş ürünü stoktaki makineyi gösterir; panoda ve sipariş kartında "Stokta var"
    assert "Stokta aynı üründen var (1)" in sayfa(istemci, f"/urun/{hedef}")
    assert "Stokta var (1)" in sayfa(istemci, "/siparisler/OZ-TS0001")
    assert "Stokta var: <strong>SVR-50-NF-BSP</strong>" in sutun(sayfa(istemci, "/siparisler"), "siparisler")
    assert "OZ-TS0001" in sayfa(istemci, f"/urun/{svr['id']}")  # stok kartında atanabilecek sipariş

    gonder(f"/urun/{svr['id']}/not", metin="TEST NOT: depoda raf 3")
    gonder(f"/urun/{svr['id']}/numara/sasi_no", deger="TS-0001")
    yanit = gonder(f"/stok/{svr['id']}/ata", hedef=hedef)
    assert yanit.headers["Location"].endswith(f"/urun/{hedef}#asama")
    assert not stok_kartlari(uygulama, "SVR-50-NF-BSP")
    atanan = sorgu(uygulama, "SELECT * FROM urunler WHERE id = ?", hedef)[0]
    # Sevk deposundaki makine test edilmiş sayılır: Temizlik'ten devam eder; numara ve not taşınır
    assert atanan["asama"] == "temizlik" and atanan["stoktan_atama"] and atanan["sasi_no"] == "TS-0001"
    urun = sayfa(istemci, f"/urun/{hedef}")
    for beklenen in ("Stoktan atandı", "Stoktan bu siparişe atandı (Sevk deposu, test edildi).", "TEST NOT: depoda raf 3",
                     "TS-0001"):
        assert beklenen in urun, beklenen
    assert "Stoktan atandı" in sayfa(istemci, "/siparisler/OZ-TS0001")

    # Sonraki yüklemelerde yeni stok kartı açılmaz (makine artık siparişin), iş emri dağıtımı ona dokunmaz
    hazirla(yukle)
    assert not stok_kartlari(uygulama, "SVR-50-NF-BSP")
    assert sorgu(uygulama, "SELECT asama FROM urunler WHERE id = ?", hedef)[0]["asama"] == "temizlik"
    # Atanamaz: iş emri açılmış ya da stoktan atanmış ürün
    pp = stok_kartlari(uygulama, "PP-540C-NF-T4")[0]
    gonder(f"/stok/{pp['id']}/ata", hedef=hedef)
    assert stok_kartlari(uygulama, "PP-540C-NF-T4")[0]["id"] == pp["id"]


def test_depoda_azalinca_ve_elle(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle)
    pp = stok_kartlari(uygulama, "PP-540C-NF-T4")
    mu = next(k for k in pp if k["depo"] == "montaj_uretim")
    gonder(f"/stok/{mu['id']}/test", test="bekliyor")
    # Sevk deposunda bir adet azaldı: ekibin bilgi girmediği bir kart kalkar, test cevabı girilen kalır
    yukle(depo_raporu({**SEVK, "PP-540C-NF-T4": 1}), ad="sevk depo stok raporu.xlsx")
    assert "1 stok kartı depoda kalmadığı için kalktı" in sayfa(istemci, "/erp-yukleme")
    kalan = stok_kartlari(uygulama, "PP-540C-NF-T4")
    assert len(kalan) == 2 and mu["id"] in {k["id"] for k in kalan}
    assert sum(1 for k in kalan if k["is_emri_id"]) == 1  # stok iş emri kalan karta bağlı
    # Montaj üretim deposunda kalmadı, sevk deposunda bir tane var: bilgi girilmiş kart kalır (test edilip sevk deposuna
    # geçmiş olabilir), bilgisiz kart kalkar
    yukle(depo_raporu({"PP-536-NF": 1}), ad="montaj üretim depo stok raporu.xlsx")
    kalan = stok_kartlari(uygulama, "PP-540C-NF-T4")
    assert [(k["id"], k["depo"]) for k in kalan] == [(mu["id"], "sevk")]
    # Hiçbir depoda kalmadı: bilgi girilmiş kart silinmez, "depo raporunda görünmüyor" olur
    yukle(depo_raporu({"KCN-60": 3}), ad="sevk depo stok raporu.xlsx")
    kart = sorgu(uygulama, "SELECT * FROM urunler WHERE id = ?", mu["id"])[0]
    assert kart["depoda_yok"] and "Depo raporunda görünmüyor" in sayfa(istemci, f"/urun/{mu['id']}")
    assert "Raporda görünmüyor" in sayfa(istemci, "/stok")

    # Depo adı anlaşılamayan dosya işlenmez
    yukle(depo_raporu(SEVK), ad="stok raporu.xlsx")
    assert "hangi depoya ait olduğu anlaşılamadı" in sayfa(istemci, "/erp-yukleme")

    # Elle ekleme: makine kodu kabul edilir, alt montaj kodu edilmez
    yanit = gonder("/stok/ekle", urun_kodu=" ovr-70-s-cv ", depo="", test="")
    yeni = stok_kartlari(uygulama, "OVR-70-S-CV")
    assert len(yeni) == 1 and yeni[0]["stok_kaynagi"] == "elle"
    assert yanit.headers["Location"].endswith(f"/urun/{yeni[0]['id']}#stok")
    assert "OVR-70-S-CV" in sutun(sayfa(istemci, "/siparisler"), "sevke_hazir")
    gonder("/stok/ekle", urun_kodu="OVR-120-S-02-00", depo="sevk", test="")
    assert not stok_kartlari(uygulama, "OVR-120-S-02-00")
    # Stoktan çıkarma: kart silinmez, listelerden kalkar
    gonder(f"/stok/{yeni[0]['id']}/cikar", sebep="yanlis", aciklama="TEST")
    assert not stok_kartlari(uygulama, "OVR-70-S-CV")
    stok = sayfa(istemci, "/stok")
    assert "Stoktan çıkarılanlar (1)" in stok and "Yanlış kart (böyle bir makine yok): TEST" in stok
    assert "OVR-70-S-CV" not in sutun(sayfa(istemci, "/siparisler"), "sevke_hazir")

    # İş emri elle girilir: başka ürünün iş emri kabul edilmez
    kart = stok_kartlari(uygulama, "KCN-60")[0]
    gonder(f"/stok/{kart['id']}/is-emri", is_emri_no="900101")
    assert "başka bir ürünün" in sayfa(istemci, f"/urun/{kart['id']}")


def test_erpde_siparise_baglanan_stok_makinesi(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    hazirla(yukle)
    ie_li = next(k for k in stok_kartlari(uygulama, "PP-540C-NF-T4") if k["is_emri_id"])
    gonder(f"/urun/{ie_li['id']}/not", metin="TEST NOT: stok makinesi")
    # Planlama stok iş emrini yeni siparişe bağladı: stok kartı o siparişin ürün kartına kendiliğinden geçer
    satirlar = makine_siparisi() + [satir(1, "PP-540C-NF-T4", "Guc Unitesi", siparis_no="OZ-TS0002",
                                          planlama="OZ-TS0002-PP-01", is_emri=900111)]
    yukle(excel(satirlar))
    assert "1 stok makinesi ERP'de siparişe bağlandığı için o siparişe atandı" in sayfa(istemci, "/erp-yukleme")
    atanan = sorgu(uygulama, "SELECT u.* FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
                   " JOIN siparisler s ON s.id = k.siparis_id WHERE s.siparis_no = 'OZ-TS0002'")[0]
    assert atanan["stoktan_atama"] and atanan["is_emri_id"] == ie_li["is_emri_id"]
    assert ie_li["id"] not in {k["id"] for k in stok_kartlari(uygulama)}
    urun = sayfa(istemci, f"/urun/{atanan['id']}")
    assert "ERP'de stok iş emri bu siparişe bağlandı" in urun and "TEST NOT: stok makinesi" in urun
