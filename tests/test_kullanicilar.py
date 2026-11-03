import io

from conftest import SIFRE
from PIL import Image


def test_ekip_kullanici_ekler_ayni_ad_reddedilir(istemci, ekle, giris, gonder):
    ekle()
    giris()
    veri = dict(ad_soyad="TEST KULLANICI", kullanici_adi="test.izleyici", rol="izleyici", sifre=SIFRE, sifre_tekrar=SIFRE)
    # Görevi sorulur; yazılmadan eklenmez
    assert "Kişinin görevini yazın" in gonder("/ayarlar/kullanicilar/yeni", **veri).get_data(as_text=True)
    veri["unvan"] = "TEST GOREV"
    assert gonder("/ayarlar/kullanicilar/yeni", **veri).status_code == 302
    yanit = gonder("/ayarlar/kullanicilar/yeni", **veri)
    assert "Bu kullanıcı adı zaten var." in yanit.get_data(as_text=True)
    assert "TEST GOREV · test.izleyici" in istemci.get("/ayarlar/kullanicilar/").get_data(as_text=True)


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
    gonder(f"/ayarlar/kullanicilar/{diger}", ad_soyad="TEST KULLANICI", unvan="TEST GOREV", rol="ekip", aktif="on",
           sifre="gecici-sifre-9", sifre_tekrar="gecici-sifre-9")
    gonder("/cikis")
    giris("test.diger", "gecici-sifre-9")
    assert istemci.get("/").headers["Location"].endswith("/sifre")


def test_gorev_renk_ve_fotograf(istemci, ekle, giris, gonder):
    kimlik = ekle()
    giris()
    gonder(f"/ayarlar/kullanicilar/{kimlik}", ad_soyad="TEST KULLANICI", unvan="TEST GOREV", renk="#16181d")
    sayfa = istemci.get("/").get_data(as_text=True)
    assert '<span class="yan-rol">TEST GOREV</span>' in sayfa and "--kisi: #16181d" in sayfa  # menüde "Ekip" yerine
    # Fotoğraf kare kırpılıp küçültülür; baş harflerin yerine görünür; kaldırılabilir
    resim = io.BytesIO()
    Image.new("RGB", (400, 300), (200, 30, 30)).save(resim, "PNG")
    resim.seek(0)
    with istemci.session_transaction() as oturum:
        anahtar = oturum["csrf"]
    yanit = istemci.post(f"/ayarlar/kullanicilar/{kimlik}/fotograf", data={"csrf": anahtar, "fotograf": (resim, "test.png")},
                         content_type="multipart/form-data")
    assert yanit.status_code == 302
    assert f"/ayarlar/kullanicilar/{kimlik}/fotograf?s=" in istemci.get("/").get_data(as_text=True)
    foto = istemci.get(f"/ayarlar/kullanicilar/{kimlik}/fotograf")
    assert foto.mimetype == "image/jpeg" and Image.open(io.BytesIO(foto.data)).size == (256, 256)
    gonder(f"/ayarlar/kullanicilar/{kimlik}/fotograf", islem="kaldir")
    assert istemci.get(f"/ayarlar/kullanicilar/{kimlik}/fotograf").status_code == 404
