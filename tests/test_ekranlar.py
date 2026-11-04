import pytest

from oms_montaj import uygulama_olustur
from oms_montaj.veritabani import GOCLER, ac


@pytest.mark.parametrize(
    "adres, baslik",
    [
        ("/", "Özet"),
        ("/siparisler", "Siparişler"),
        ("/sevkiyat", "Sevkiyat"),
        ("/yedek-parca", "Yedek parça"),
        ("/stok", "Stok"),
        ("/yapilacaklar", "Yapılacaklar"),
        ("/erp-yukleme", "ERP yükleme"),
        ("/arsiv", "Planner arşivi"),
        ("/ayarlar", "Ayarlar"),
        ("/ayarlar/kullanicilar/", "Kullanıcılar"),
    ],
)
def test_ekranlar_acilir(istemci, ekle, giris, adres, baslik):
    ekle()
    giris()
    yanit = istemci.get(adres)
    assert yanit.status_code == 200
    assert f"<h1>{baslik}</h1>" in yanit.get_data(as_text=True)


def test_yan_menu_giristen_sonra_gorunur(istemci, ekle, giris):
    ekle()
    giris()
    sayfa = istemci.get("/stok").get_data(as_text=True)
    assert 'class="yan"' in sayfa
    assert 'href="/stok" class="etkin" aria-current="page"' in sayfa
    assert 'href="/arsiv"' in sayfa and 'href="/pano"' not in sayfa  # pano artık Siparişler ekranı
    assert istemci.get("/pano").headers["Location"].endswith("/siparisler")


def test_tema_dugmesi_sag_ustte(istemci, ekle, giris):
    # Bilgisayarda sağ üstte, telefonda üst çubukta; seçim tarayıcıda saklanır, sayfa çizilmeden uygulanır
    ekle()
    giris()
    sayfa = istemci.get("/stok").get_data(as_text=True)
    assert sayfa.count("data-tema-dugmesi") == 2
    assert '<div class="ust-cubuk">' in sayfa
    assert 'localStorage.getItem("omsTema")' in sayfa
    assert 'html[data-tema="koyu"]' in istemci.get("/static/uygulama.css").get_data(as_text=True)


def test_gecici_sifreyle_menu_gosterilmez(istemci, ekle, giris):
    ekle(degismeli=True)
    giris()
    sayfa = istemci.get("/sifre").get_data(as_text=True)
    assert 'class="yan"' not in sayfa
    assert "Kendi şifrenizi belirleyin" in sayfa


def test_yazi_tipi_ve_gorunum_sunulur(istemci):
    assert istemci.get("/static/uygulama.css").status_code == 200
    assert istemci.get("/static/yazitipi/InterVariable.woff2").status_code == 200


def test_bilinmeyen_sayfa_404(istemci, ekle, giris):
    ekle()
    giris()
    assert istemci.get("/yok-boyle-sayfa").status_code == 404


def test_gocler_bir_kez_uygulanir(tmp_path):
    ayarlar = {"VERI_KLASORU": tmp_path, "SECRET_KEY": "test"}
    uygulama_olustur(ayarlar)
    uygulama_olustur(ayarlar)  # ikinci açılış hata vermemeli
    vt = ac(tmp_path / "oms-montaj.db")
    assert vt.execute("PRAGMA user_version").fetchone()[0] == len(GOCLER)
    vt.close()
