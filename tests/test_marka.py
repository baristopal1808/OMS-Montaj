import io
from pathlib import Path

from PIL import Image

DENEME_LOGO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect width="10" height="10"/></svg>'


def test_logo_yokken_yazi_gorunur(istemci, ekle):
    ekle()
    sayfa = istemci.get("/giris").get_data(as_text=True)
    assert '<span class="logo-yazi">OMS</span>' in sayfa
    assert "MONTAJ" in sayfa
    assert istemci.get("/marka/logo").status_code == 404


def test_logo_varsa_giris_yapmadan_gosterilir(istemci, uygulama, ekle):
    ekle()
    (Path(uygulama.config["VERI_KLASORU"]) / "marka" / "oms-logo.svg").write_text(DENEME_LOGO, encoding="utf-8")
    assert '<img class="logo" src="/marka/logo?s=' in istemci.get("/giris").get_data(as_text=True)
    yanit = istemci.get("/marka/logo")
    assert yanit.status_code == 200
    assert yanit.mimetype == "image/svg+xml"
    assert "default-src 'none'" in yanit.headers["Content-Security-Policy"]


def test_png_logonun_bos_kenarlari_kirpilir(istemci, uygulama, ekle):
    ekle()
    resim = Image.new("RGBA", (400, 300), (0, 0, 0, 0))
    resim.paste((0, 0, 0, 255), (100, 100, 300, 150))
    resim.save(Path(uygulama.config["VERI_KLASORU"]) / "marka" / "oms-logo.png")
    yanit = istemci.get("/marka/logo")
    assert yanit.mimetype == "image/png"
    assert Image.open(io.BytesIO(yanit.data)).size == (200, 50)


def test_acilis_yalnizca_sayfa_ilk_acildiginda_oynar(istemci, gonder):
    assert 'id="acilis"' in istemci.get("/kurulum").get_data(as_text=True)
    hatali = gonder("/kurulum", ad_soyad="", kullanici_adi="", sifre="", sifre_tekrar="")
    assert 'id="acilis"' not in hatali.get_data(as_text=True)
