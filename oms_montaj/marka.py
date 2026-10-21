"""Şirket logosu.

Logo dosyası git'e girmez; veri klasöründeki marka/ altında durur (geliştirmede
"OMS Veri/uygulama/marka/oms-logo.svg" ya da "oms-logo.png"). Dosya yoksa
ekranlarda logonun yerinde "OMS" yazısı görünür. Logo giriş sayfasında da
gösterildiği için giriş yapmadan açılabilir.

PNG logolar çoğu zaman bir sayfanın ortasında durur; çevresindeki boşluk
kalırsa logo küçük ve altındaki yazıdan uzak görünür. Bu yüzden PNG logonun
saydam ya da beyaz kenarları kırpılır ve resim ekran için küçültülür.
"""

import io
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, send_from_directory, url_for
from PIL import Image, ImageChops

bp = Blueprint("marka", __name__)

LOGO_ADLARI = ("oms-logo.svg", "oms-logo.png")
EN_GENIS_PNG = 1200  # piksel; ekranda bundan büyüğüne gerek yok


@lru_cache(maxsize=4)
def hazir_png(yol, _degisme_zamani):
    """Kenarları kırpılmış ve küçültülmüş PNG; dosya değişince yeniden hazırlanır."""
    with Image.open(yol) as acilan:
        resim = acilan.convert("RGBA")
    beyaz = Image.new("RGBA", resim.size, (255, 255, 255, 255))
    beyaz.alpha_composite(resim)
    kutu = ImageChops.difference(beyaz.convert("RGB"), Image.new("RGB", resim.size, "white")).getbbox()
    if kutu:
        resim = resim.crop(kutu)
    if resim.width > EN_GENIS_PNG:
        resim = resim.resize((EN_GENIS_PNG, round(resim.height * EN_GENIS_PNG / resim.width)), Image.LANCZOS)
    tampon = io.BytesIO()
    resim.save(tampon, "PNG", optimize=True)
    return tampon.getvalue()


def logo_dosyasi():
    klasor = Path(current_app.config["VERI_KLASORU"]) / "marka"
    for ad in LOGO_ADLARI:
        if (klasor / ad).is_file():
            return klasor / ad
    return None


def logo_adresi():
    """Logonun adresi; dosya değişince adres de değişir, tarayıcı eskisini göstermez."""
    dosya = logo_dosyasi()
    return url_for("marka.logo", s=int(dosya.stat().st_mtime)) if dosya else None


@bp.app_context_processor
def sablon_degiskenleri():
    return {"logo_adresi": logo_adresi}


@bp.route("/marka/logo")
def logo():
    dosya = logo_dosyasi()
    if dosya is None:
        abort(404)
    if dosya.suffix == ".png":
        yanit = Response(hazir_png(str(dosya), dosya.stat().st_mtime), mimetype="image/png")
        yanit.cache_control.max_age = 3600
        return yanit
    yanit = send_from_directory(dosya.parent, dosya.name, max_age=3600)
    # SVG içine betik konmuş olsa bile çalışmasın.
    yanit.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    return yanit
