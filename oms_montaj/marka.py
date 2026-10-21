"""Şirket logosu.

Logo dosyası git'e girmez; veri klasöründeki marka/ altında durur (geliştirmede
"OMS Veri/uygulama/marka/oms-logo.svg" ya da "oms-logo.png"). Dosya yoksa
ekranlarda logonun yerinde "OMS" yazısı görünür. Logo giriş sayfasında da
gösterildiği için giriş yapmadan açılabilir.

PNG logolar çoğu zaman bir sayfanın ortasında durur; çevresindeki boşluk
kalırsa logo küçük ve altındaki yazıdan uzak görünür. Bu yüzden PNG logonun
saydam ya da beyaz kenarları kırpılır ve resim ekran için küçültülür.

Müşteri logoları: marka/musteriler.txt dosyasının her satırı "KOD;#renk" ya da
"KOD;#renk;logo-dosyasi.png" biçimindedir (# ile başlayan satır açıklamadır). Müşteri
kodu sipariş numarasının "OZ-"den sonraki üç karakteridir. Logo dosyası yazılmamışsa
marka/musteri-KOD.png (ya da .svg) aranır. Sipariş kutularında zemin müşterinin rengine
döner, yazılar beyazlaşır, logo arkada beyaz bir filigran olarak görünür. Dosyada
olmayan müşterilerde OMS logosu ve OMS kırmızısı kullanılır; "*;#renk" satırı bu rengi
değiştirir. Müşteri kodları gerçek müşteriyi tanıttığı için git'e girmez; bu dosyada durur.
"""

import io
import re
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


MUSTERI_AYARI = "musteriler.txt"
RENK = re.compile(r"^#[0-9a-fA-F]{6}$")
KOD = re.compile(r"^[A-Za-z0-9]{2,8}$")
LOGO_ADI = re.compile(r"^[\w.-]+\.(png|svg)$", re.IGNORECASE)  # klasör adı içeremez
DIGERLERI = "*"  # dosyada adı geçmeyen müşteriler
VARSAYILAN_RENK = "#c41e24"  # OMS kırmızısı (uygulamanın vurgu rengi); logo OMS logosu


def _marka_klasoru():
    return Path(current_app.config["VERI_KLASORU"]) / "marka"


@lru_cache(maxsize=2)
def _musteri_ayarlari(yol, _surum):
    """{KOD: (renk, logo dosyasının adı ya da None)}"""
    ayarlar = {}
    for satir in Path(yol).read_text(encoding="utf-8-sig").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or ";" not in satir:
            continue
        kod, renk, *kalan = (p.strip() for p in satir.split(";"))
        logo = kalan[0] if kalan and LOGO_ADI.match(kalan[0]) else None
        if (kod == DIGERLERI or KOD.match(kod)) and RENK.match(renk):
            ayarlar[kod.upper()] = (renk, logo)
    return ayarlar


def _musteriler():
    ayar = _marka_klasoru() / MUSTERI_AYARI
    if not ayar.is_file():
        return {}
    durum = ayar.stat()  # dosya değişince yeniden okunur; saat aynı kalsa da boyut değişir
    return _musteri_ayarlari(str(ayar), (durum.st_mtime_ns, durum.st_size))


def _musteri_kodu(siparis_no):
    kod = (siparis_no or "")[3:6].upper()
    return kod if (siparis_no or "").upper().startswith("OZ-") and KOD.match(kod) else None


def musteri_logo_dosyasi(kod):
    ayarlar = _musteriler()
    yazilan = (ayarlar.get(kod) or ayarlar.get(DIGERLERI) or (None, None))[1]
    for ad in ([yazilan] if yazilan else []) + [f"musteri-{kod}.svg", f"musteri-{kod}.png"]:
        dosya = _marka_klasoru() / ad
        if dosya.is_file():
            return dosya
    return None


def musteri_markasi(siparis_no):
    """Siparişin müşterisinin rengi ve logosu: {"renk", "logo"}. Müşteri tanımlı değilse OMS."""
    kod = _musteri_kodu(siparis_no)
    ayarlar = _musteriler()
    renk = (ayarlar.get(kod) or ayarlar.get(DIGERLERI) or (VARSAYILAN_RENK,))[0]
    dosya = musteri_logo_dosyasi(kod) if kod else None
    logo = url_for("marka.musteri_logosu", kod=kod, s=int(dosya.stat().st_mtime)) if dosya else logo_adresi()
    return {"renk": renk, "logo": logo}


@bp.app_context_processor
def sablon_degiskenleri():
    return {"logo_adresi": logo_adresi, "musteri_markasi": musteri_markasi}


def _logo_yaniti(dosya):
    if dosya.suffix == ".png":
        yanit = Response(hazir_png(str(dosya), dosya.stat().st_mtime), mimetype="image/png")
        yanit.cache_control.max_age = 3600
        return yanit
    yanit = send_from_directory(dosya.parent, dosya.name, max_age=3600)
    # SVG içine betik konmuş olsa bile çalışmasın.
    yanit.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    return yanit


@bp.route("/marka/musteri/<kod>")
def musteri_logosu(kod):
    dosya = musteri_logo_dosyasi(kod.upper()) if KOD.match(kod) else None
    if dosya is None:
        abort(404)
    return _logo_yaniti(dosya)


@bp.route("/marka/logo")
def logo():
    dosya = logo_dosyasi()
    if dosya is None:
        abort(404)
    return _logo_yaniti(dosya)
