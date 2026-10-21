from conftest import SIFRE


def test_hesap_yokken_kuruluma_gider(istemci):
    yanit = istemci.get("/")
    assert yanit.status_code == 302
    assert yanit.headers["Location"].endswith("/kurulum")


def test_kurulum_ilk_hesabi_acar_sonra_kapanir(istemci, gonder):
    yanit = gonder(
        "/kurulum",
        ad_soyad="TEST KULLANICI",
        kullanici_adi="test.kullanici",
        sifre=SIFRE,
        sifre_tekrar=SIFRE,
    )
    assert yanit.status_code == 302
    assert istemci.get("/").status_code == 200
    assert istemci.get("/kurulum").headers["Location"].endswith("/giris")


def test_kurulum_kisa_sifreyi_kabul_etmez(gonder):
    yanit = gonder("/kurulum", ad_soyad="TEST KULLANICI", kullanici_adi="test.kullanici", sifre="kisa", sifre_tekrar="kisa")
    assert "en az 8 karakter" in yanit.get_data(as_text=True)


def test_giris_yapmadan_sayfa_acilmaz(istemci, ekle):
    ekle()
    yanit = istemci.get("/pano")
    assert yanit.status_code == 302
    assert "/giris?sonra=/pano" in yanit.headers["Location"]


def test_yanlis_sifreyle_girilmez(istemci, ekle, giris):
    ekle()
    yanit = giris(sifre="yanlis-sifre")
    assert "Kullanıcı adı ya da şifre yanlış." in yanit.get_data(as_text=True)
    assert istemci.get("/").status_code == 302


def test_dogru_sifreyle_girilir_ve_istenen_sayfaya_donulur(istemci, ekle, gonder):
    ekle()
    yanit = gonder("/giris?sonra=/stok", kullanici_adi="TEST.KULLANICI", sifre=SIFRE)
    assert yanit.headers["Location"].endswith("/stok")
    assert istemci.get("/stok").status_code == 200


def test_giristen_sonra_baska_siteye_gidilmez(ekle, gonder):
    ekle()
    yanit = gonder("/giris?sonra=//baska.site", kullanici_adi="test.kullanici", sifre=SIFRE)
    assert yanit.headers["Location"] == "/"


def test_csrf_anahtari_olmayan_form_reddedilir(istemci, ekle):
    ekle()
    yanit = istemci.post("/giris", data={"kullanici_adi": "test.kullanici", "sifre": SIFRE})
    assert yanit.status_code == 400


def test_gecici_sifreyle_giren_once_sifresini_belirler(istemci, ekle, giris, gonder):
    ekle(degismeli=True)
    giris()
    assert istemci.get("/").headers["Location"].endswith("/sifre")

    yanit = gonder("/sifre", mevcut_sifre=SIFRE, yeni_sifre=SIFRE, yeni_sifre_tekrar=SIFRE)
    assert "eskisinden farklı" in yanit.get_data(as_text=True)

    gonder("/sifre", mevcut_sifre=SIFRE, yeni_sifre="yeni-sifre-2", yeni_sifre_tekrar="yeni-sifre-2")
    assert istemci.get("/").status_code == 200


def test_pasif_hesap_giremez(istemci, uygulama, ekle, giris):
    kimlik = ekle()
    with uygulama.app_context():
        from oms_montaj.veritabani import baglanti

        with baglanti() as vt:
            vt.execute("UPDATE kullanicilar SET aktif = 0 WHERE id = ?", (kimlik,))
    giris()
    assert istemci.get("/").status_code == 302


def test_cikis_oturumu_kapatir(istemci, ekle, giris, gonder):
    ekle()
    giris()
    gonder("/cikis")
    assert istemci.get("/").status_code == 302
