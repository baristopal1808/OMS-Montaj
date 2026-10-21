"""Kullanıcı hesapları, giriş, ilk kurulum, şifre değiştirme ve her istekteki denetimler.

Her istekte:
- oturumdaki kullanıcı g.kullanici'ye yüklenir;
- form gönderimlerinde (POST) CSRF anahtarı denetlenir: başka bir sitenin,
  oturumu açık kullanıcı adına form göndermesini engeller;
- giriş yapmamış kullanıcı giriş sayfasına, hiç hesap yoksa kurulum sayfasına gider;
- geçici şifreyle giren kullanıcı önce kendi şifresini belirler.
"""

import re
import secrets
import sqlite3
from functools import wraps

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .veritabani import baglanti

bp = Blueprint("kimlik", __name__)

ROLLER = {"ekip": "Ekip", "izleyici": "İzleyici"}
EN_KISA_SIFRE = 8
KULLANICI_ADI = re.compile(r"^[\w.\-]{2,40}$")
ACIK_SAYFALAR = {"kimlik.giris", "kimlik.kurulum", "static"}
SIFRE_ONCESI_SAYFALAR = {"kimlik.sifre", "kimlik.cikis", "static"}


def kullanici_sayisi():
    return baglanti().execute("SELECT COUNT(*) FROM kullanicilar").fetchone()[0]


def kullanici_ekle(kullanici_adi, ad_soyad, rol, sifre, sifre_degismeli=True):
    """Yeni hesabın kimliğini döndürür; kullanıcı adı alınmışsa None."""
    try:
        with baglanti() as vt:
            imlec = vt.execute(
                "INSERT INTO kullanicilar (kullanici_adi, ad_soyad, rol, sifre_ozeti, sifre_degismeli)"
                " VALUES (?, ?, ?, ?, ?)",
                (kullanici_adi, ad_soyad, rol, generate_password_hash(sifre), int(sifre_degismeli)),
            )
    except sqlite3.IntegrityError:
        return None
    return imlec.lastrowid


def sifreyi_degistir(kullanici_id, sifre, sifre_degismeli):
    with baglanti() as vt:
        vt.execute(
            "UPDATE kullanicilar SET sifre_ozeti = ?, sifre_degismeli = ? WHERE id = ?",
            (generate_password_hash(sifre), int(sifre_degismeli), kullanici_id),
        )


def hesap_sorunu(ad_soyad, kullanici_adi):
    if not ad_soyad or not kullanici_adi:
        return "Ad soyad ve kullanıcı adı boş bırakılamaz."
    if not KULLANICI_ADI.match(kullanici_adi):
        return "Kullanıcı adı boşluksuz olmalı; harf, rakam, nokta, tire ve alt çizgi kullanılabilir."
    return None


def sifre_sorunu(sifre, tekrar):
    if len(sifre) < EN_KISA_SIFRE:
        return f"Şifre en az {EN_KISA_SIFRE} karakter olmalı."
    if sifre != tekrar:
        return "Şifreler birbirini tutmuyor."
    return None


def oturum_ac(kullanici_id):
    session.clear()
    session.permanent = True
    session["kullanici_id"] = kullanici_id


def guvenli_adres(adres):
    """Girişten sonra yalnızca bu sitenin bir sayfasına dönülür."""
    if adres and adres.startswith("/") and not adres.startswith("//") and "\\" not in adres:
        return adres
    return url_for("ekranlar.siparisler")


def csrf_anahtari():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def ekip_gerekli(gorunum):
    """İzleyiciler (müdürler) bakar ama değiştiremez; değiştiren sayfalar bununla korunur."""

    @wraps(gorunum)
    def sarili(*args, **kwargs):
        if g.kullanici is None or g.kullanici["rol"] != "ekip":
            abort(403)
        return gorunum(*args, **kwargs)

    return sarili


@bp.app_context_processor
def sablon_degiskenleri():
    return {"csrf_anahtari": csrf_anahtari, "ROLLER": ROLLER}


@bp.before_app_request
def denetle():
    g.kullanici = None
    kullanici_id = session.get("kullanici_id")
    if kullanici_id is not None:
        g.kullanici = baglanti().execute(
            "SELECT * FROM kullanicilar WHERE id = ? AND aktif = 1", (kullanici_id,)
        ).fetchone()
        if g.kullanici is None:
            session.clear()

    if request.method == "POST":
        anahtar = session.get("csrf")
        if not anahtar or not secrets.compare_digest(anahtar, request.form.get("csrf", "")):
            abort(400)

    if request.endpoint in ACIK_SAYFALAR:
        return None
    if g.kullanici is None:
        if kullanici_sayisi() == 0:
            return redirect(url_for("kimlik.kurulum"))
        return redirect(url_for("kimlik.giris", sonra=request.path))
    if g.kullanici["sifre_degismeli"] and request.endpoint not in SIFRE_ONCESI_SAYFALAR:
        return redirect(url_for("kimlik.sifre"))
    return None


@bp.route("/giris", methods=["GET", "POST"])
def giris():
    if kullanici_sayisi() == 0:
        return redirect(url_for("kimlik.kurulum"))
    hata = None
    if request.method == "POST":
        kullanici = baglanti().execute(
            "SELECT * FROM kullanicilar WHERE kullanici_adi = ? AND aktif = 1",
            (request.form.get("kullanici_adi", "").strip(),),
        ).fetchone()
        if kullanici and check_password_hash(kullanici["sifre_ozeti"], request.form.get("sifre", "")):
            oturum_ac(kullanici["id"])
            return redirect(guvenli_adres(request.args.get("sonra")))
        hata = "Kullanıcı adı ya da şifre yanlış."
    return render_template("giris.html", hata=hata)


@bp.route("/kurulum", methods=["GET", "POST"])
def kurulum():
    """Hiç hesap yokken ilk hesabı açar; ilk hesaptan sonra kapanır."""
    if kullanici_sayisi() > 0:
        return redirect(url_for("kimlik.giris"))
    hata = None
    if request.method == "POST":
        ad_soyad = request.form.get("ad_soyad", "").strip()
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "")
        hata = hesap_sorunu(ad_soyad, kullanici_adi) or sifre_sorunu(
            sifre, request.form.get("sifre_tekrar", "")
        )
        if not hata:
            oturum_ac(kullanici_ekle(kullanici_adi, ad_soyad, "ekip", sifre, sifre_degismeli=False))
            flash("Hesabınız açıldı. Ekibin diğer hesaplarını Ayarlar > Kullanıcılar'dan ekleyebilirsiniz.")
            return redirect(url_for("ekranlar.siparisler"))
    return render_template("kurulum.html", hata=hata)


@bp.route("/sifre", methods=["GET", "POST"])
def sifre():
    hata = None
    if request.method == "POST":
        mevcut = request.form.get("mevcut_sifre", "")
        yeni = request.form.get("yeni_sifre", "")
        if not check_password_hash(g.kullanici["sifre_ozeti"], mevcut):
            hata = "Şu anki şifreniz yanlış."
        elif yeni == mevcut:
            hata = "Yeni şifre eskisinden farklı olmalı."
        else:
            hata = sifre_sorunu(yeni, request.form.get("yeni_sifre_tekrar", ""))
        if not hata:
            sifreyi_degistir(g.kullanici["id"], yeni, sifre_degismeli=False)
            flash("Şifreniz değiştirildi.")
            return redirect(url_for("ekranlar.siparisler"))
    return render_template("sifre.html", hata=hata, zorunlu=bool(g.kullanici["sifre_degismeli"]))


@bp.route("/cikis", methods=["POST"])
def cikis():
    session.clear()
    return redirect(url_for("kimlik.giris"))
