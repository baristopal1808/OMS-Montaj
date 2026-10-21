import pytest

from oms_montaj import uygulama_olustur
from oms_montaj.veritabani import GOCLER, ac


@pytest.mark.parametrize(
    "adres, baslik",
    [
        ("/", "Siparişler"),
        ("/pano", "Pano"),
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
