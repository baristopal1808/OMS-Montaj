from conftest import SIFRE


def test_ekip_kullanici_ekler_ayni_ad_reddedilir(istemci, ekle, giris, gonder):
    ekle()
    giris()
    veri = dict(ad_soyad="TEST KULLANICI", kullanici_adi="test.izleyici", rol="izleyici", sifre=SIFRE, sifre_tekrar=SIFRE)
    assert gonder("/ayarlar/kullanicilar/yeni", **veri).status_code == 302
    yanit = gonder("/ayarlar/kullanicilar/yeni", **veri)
    assert "Bu kullanıcı adı zaten var." in yanit.get_data(as_text=True)
    assert "test.izleyici" in istemci.get("/ayarlar/kullanicilar/").get_data(as_text=True)


def test_izleyici_bakar_ama_degistiremez(istemci, ekle, giris, gonder):
    ekip = ekle()
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert istemci.get("/ayarlar/kullanicilar/").status_code == 200
    assert istemci.get("/ayarlar/kullanicilar/yeni").status_code == 403
    assert gonder(f"/ayarlar/kullanicilar/{ekip}", ad_soyad="TEST KULLANICI", rol="izleyici").status_code == 403


def test_kimse_kendi_rolunu_ve_etkinligini_degistiremez(istemci, ekle, giris, gonder):
    kimlik = ekle()
    giris()
    gonder(f"/ayarlar/kullanicilar/{kimlik}", ad_soyad="TEST KULLANICI", rol="izleyici")
    sayfa = istemci.get("/ayarlar/kullanicilar/").get_data(as_text=True)
    assert "Ekip" in sayfa and "Pasif" not in sayfa
    assert istemci.get("/").status_code == 200


def test_sifre_sifirlanan_kisi_yeniden_sifre_belirler(istemci, ekle, giris, gonder):
    ekle()
    diger = ekle("test.diger")
    giris()
    gonder(f"/ayarlar/kullanicilar/{diger}", ad_soyad="TEST KULLANICI", rol="ekip", aktif="on", sifre="gecici-sifre-9", sifre_tekrar="gecici-sifre-9")
    gonder("/cikis")
    giris("test.diger", "gecici-sifre-9")
    assert istemci.get("/").headers["Location"].endswith("/sifre")
