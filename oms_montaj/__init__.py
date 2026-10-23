"""OMS Montaj iş takip uygulaması.

uygulama_olustur() Flask uygulamasını kurar. Gerçek veri (veritabanı, gizli
anahtar; ileride fotoğraflar ve yüklenen Excel'ler) veri klasöründe durur:
geliştirmede "OMS Veri/uygulama", sunucuda OMS_VERI_KLASORU ortam değişkeninin
gösterdiği klasör. İkisi de git'in dışındadır.
"""

import os
import secrets
from datetime import date, timedelta
from pathlib import Path

from flask import Flask, render_template

from . import (
    ekranlar, erp, kimlik, kullanicilar, makineler, marka, ozet, sevkiyat, siparisler, urunler, veritabani, yedek_parca,
)
from .asamalar import ASAMALAR
from .bicim import SUZGECLER
from .grafik import AILE_RENKLERI
from .simgeler import simge

SURUM = "0.1"
KOK = Path(__file__).resolve().parent.parent
VARSAYILAN_VERI_KLASORU = KOK / "OMS Veri" / "uygulama"

HATA_METINLERI = {
    400: "İstek geçersiz. Sayfayı yenileyip yeniden deneyin.",
    403: "Bu işlem için yetkiniz yok.",
    404: "Aradığınız sayfa bulunamadı.",
    413: "Dosya çok büyük; en fazla 50 MB yüklenebilir.",
}


def gizli_anahtar(klasor):
    """Oturum çerezlerini imzalayan anahtar; ilk çalışmada üretilir, veri klasöründe saklanır."""
    dosya = klasor / "gizli-anahtar.txt"
    if not dosya.exists():
        dosya.write_text(secrets.token_hex(32), encoding="utf-8")
    return dosya.read_text(encoding="utf-8").strip()


def hata_sayfasi(hata):
    return render_template("hata.html", kod=hata.code, metin=HATA_METINLERI[hata.code]), hata.code


def uygulama_olustur(ayarlar=None):
    uygulama = Flask(__name__)
    uygulama.config.update(
        VERI_KLASORU=Path(os.environ.get("OMS_VERI_KLASORU", VARSAYILAN_VERI_KLASORU)),
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=30),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )
    uygulama.config.update(ayarlar or {})

    klasor = Path(uygulama.config["VERI_KLASORU"])
    (klasor / "marka").mkdir(parents=True, exist_ok=True)
    uygulama.config["VERITABANI"] = klasor / "oms-montaj.db"
    if not uygulama.config.get("SECRET_KEY"):
        uygulama.config["SECRET_KEY"] = gizli_anahtar(klasor)

    veritabani.hazirla(uygulama)
    uygulama.register_blueprint(kimlik.bp)
    uygulama.register_blueprint(kullanicilar.bp)
    uygulama.register_blueprint(ozet.bp)
    uygulama.register_blueprint(siparisler.bp)
    uygulama.register_blueprint(sevkiyat.bp)
    uygulama.register_blueprint(yedek_parca.bp)
    uygulama.register_blueprint(makineler.bp)
    uygulama.register_blueprint(urunler.bp)
    uygulama.register_blueprint(erp.bp)
    uygulama.register_blueprint(ekranlar.bp)
    uygulama.register_blueprint(marka.bp)
    for kod in HATA_METINLERI:
        uygulama.register_error_handler(kod, hata_sayfasi)
    uygulama.jinja_env.filters.update(SUZGECLER)
    uygulama.jinja_env.globals.update(simge=simge, SURUM=SURUM, ASAMALAR=ASAMALAR, AILE_RENKLERI=AILE_RENKLERI)
    uygulama.context_processor(lambda: {"YIL": date.today().year})
    return uygulama
