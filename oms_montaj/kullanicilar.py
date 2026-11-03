"""Ayarlar > Kullanıcılar: hesap açma, rol, etkinlik ve geçici şifre.

Deneme süresince ekipteki herkes hesapları yönetebilir; izleyiciler yalnızca
listeye bakar (docs/ihtiyaclar.md, soru 7b ve 40). Kimse kendi rolünü ya da
etkinliğini değiştiremez; böylece kimse yanlışlıkla kendini dışarıda bırakmaz.
Yeni hesap ve sıfırlanan şifre geçicidir; kişi ilk girişte kendi şifresini belirler.

Varsayılan atama da burada seçilir: hangi iş grubunun kartları kime atanır (atama.py).

Her kişinin görevi (menüde "Ekip" yerine yazar; eklerken sorulur), kartlardaki rengi ve fotoğrafı vardır.
Fotoğraf gerçek veridir: veri klasöründe kare kırpılıp küçültülerek saklanır, yalnızca giriş yapmış kişiye
gösterilir (kullanıcı kararları, 02/11/2026).
"""

import re
import time
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for

from .atama import ATAMA_GRUPLARI, kisi, kisi_rengi, varsayilan_atamayi_kaydet, varsayilan_atananlar
from .kimlik import ROLLER, ekip_gerekli, hesap_sorunu, kullanici_ekle, sifre_sorunu, sifreyi_degistir
from .veritabani import baglanti

bp = Blueprint("kullanicilar", __name__, url_prefix="/ayarlar/kullanicilar")


FOTOGRAF_KLASORU = "kullanici-fotograflari"
FOTOGRAF_BOYU = 256  # piksel, kare
RENK = re.compile(r"^#[0-9a-fA-F]{6}$")


def rol_sorunu(rol):
    return None if rol in ROLLER else "Bir rol seçin."


def unvan_sorunu(unvan):
    return None if unvan else "Kişinin görevini yazın (örneğin: Mekanik montaj takım lideri)."


def _fotograf_klasoru():
    return Path(current_app.config["VERI_KLASORU"]) / FOTOGRAF_KLASORU


@bp.app_context_processor
def kisi_degiskenleri():
    return {"kisi_bilgisi": kisi}


@bp.route("/")
def liste():
    vt = baglanti()
    kullanicilar = vt.execute("SELECT * FROM kullanicilar ORDER BY aktif DESC, ad_soyad COLLATE NOCASE").fetchall()
    atananlar = varsayilan_atananlar(vt)
    return render_template(
        "kullanicilar.html", kullanicilar=kullanicilar, ATAMA_GRUPLARI=ATAMA_GRUPLARI,
        atananlar={grup: {k["id"] for k in liste} for grup, liste in atananlar.items()},
    )


@bp.route("/atama", methods=["POST"])
@ekip_gerekli
def atama():
    """Varsayılan atama: her iş grubu için seçilen ekip üyeleri."""
    vt = baglanti()
    ekip = {r[0] for r in vt.execute("SELECT id FROM kullanicilar WHERE rol = 'ekip' AND aktif = 1")}
    secimler = {grup: [int(k) for k in request.form.getlist(grup) if k.isdigit() and int(k) in ekip]
                for grup in ATAMA_GRUPLARI}
    with vt:
        varsayilan_atamayi_kaydet(vt, secimler)
    flash("Varsayılan atama kaydedildi; kartlarda atanan kişi olarak görünür.")
    return redirect(url_for(".liste") + "#atama")


@bp.route("/yeni", methods=["GET", "POST"])
@ekip_gerekli
def yeni():
    hata = None
    form = request.form
    if request.method == "POST":
        ad_soyad = form.get("ad_soyad", "").strip()
        kullanici_adi = form.get("kullanici_adi", "").strip()
        rol = form.get("rol")
        unvan = form.get("unvan", "").strip()
        sifre = form.get("sifre", "")
        hata = (
            hesap_sorunu(ad_soyad, kullanici_adi)
            or unvan_sorunu(unvan)
            or rol_sorunu(rol)
            or sifre_sorunu(sifre, form.get("sifre_tekrar", ""))
        )
        if not hata:
            if kullanici_ekle(kullanici_adi, ad_soyad, rol, sifre, unvan=unvan) is None:
                hata = "Bu kullanıcı adı zaten var."
            else:
                flash(f"{ad_soyad} eklendi. İlk girişte kendi şifresini belirlemesi istenecek.")
                return redirect(url_for(".liste"))
    return render_template("kullanici_formu.html", kullanici=None, form=form, hata=hata)


@bp.route("/<int:kullanici_id>", methods=["GET", "POST"])
@ekip_gerekli
def duzenle(kullanici_id):
    kullanici = baglanti().execute("SELECT * FROM kullanicilar WHERE id = ?", (kullanici_id,)).fetchone()
    if kullanici is None:
        abort(404)
    kendisi = kullanici["id"] == g.kullanici["id"]
    hata = None
    form = request.form
    if request.method == "POST":
        ad_soyad = form.get("ad_soyad", "").strip()
        unvan = form.get("unvan", "").strip()
        renk = form.get("renk", "") if RENK.match(form.get("renk", "")) else kullanici["renk"]
        rol = kullanici["rol"] if kendisi else form.get("rol")
        aktif = True if kendisi else "aktif" in form
        sifre = "" if kendisi else form.get("sifre", "")
        hata = (
            ("Ad soyad boş bırakılamaz." if not ad_soyad else None)
            or unvan_sorunu(unvan)
            or rol_sorunu(rol)
            or (sifre_sorunu(sifre, form.get("sifre_tekrar", "")) if sifre else None)
        )
        if not hata:
            with baglanti() as vt:
                vt.execute(
                    "UPDATE kullanicilar SET ad_soyad = ?, unvan = ?, renk = ?, rol = ?, aktif = ? WHERE id = ?",
                    (ad_soyad, unvan, renk, rol, int(aktif), kullanici_id),
                )
            if sifre:
                sifreyi_degistir(kullanici_id, sifre, sifre_degismeli=True)
            flash("Kaydedildi.")
            return redirect(url_for(".liste"))
    return render_template(
        "kullanici_formu.html", kullanici=kullanici, kendisi=kendisi, form=form, hata=hata,
        renk=kisi_rengi(kullanici), kisi_=kisi(kullanici),
    )


@bp.route("/<int:kullanici_id>/fotograf", methods=["GET", "POST"])
def fotograf(kullanici_id):
    """GET: kişinin fotoğrafı. POST (ekip): fotoğraf yükler ya da kaldırır; kare kırpılıp küçültülür."""
    vt = baglanti()
    kullanici = vt.execute("SELECT * FROM kullanicilar WHERE id = ?", (kullanici_id,)).fetchone()
    if kullanici is None:
        abort(404)
    klasor = _fotograf_klasoru()
    if request.method == "GET":
        if not kullanici["fotograf"] or not (klasor / kullanici["fotograf"]).is_file():
            abort(404)
        yanit = send_file(klasor / kullanici["fotograf"], mimetype="image/jpeg", max_age=3600)
        return yanit
    if g.kullanici["rol"] != "ekip":
        abort(403)
    adres = url_for(".duzenle", kullanici_id=kullanici_id) + "#fotograf"
    if request.form.get("islem") == "kaldir":
        with vt:
            vt.execute("UPDATE kullanicilar SET fotograf = NULL WHERE id = ?", (kullanici_id,))
        flash("Fotoğraf kaldırıldı; baş harfler görünür.")
        return redirect(adres)
    dosya = request.files.get("fotograf")
    if not dosya or not dosya.filename:
        flash("Bir fotoğraf seçin.")
        return redirect(adres)
    try:
        with Image.open(dosya.stream) as acilan:
            resim = ImageOps.fit(ImageOps.exif_transpose(acilan).convert("RGB"), (FOTOGRAF_BOYU, FOTOGRAF_BOYU))
    except (UnidentifiedImageError, OSError):
        flash("Fotoğraf okunamadı; JPG ya da PNG bir resim seçin.")
        return redirect(adres)
    klasor.mkdir(parents=True, exist_ok=True)
    ad = f"{kullanici_id}-{int(time.time())}.jpg"
    resim.save(klasor / ad, "JPEG", quality=88)
    with vt:
        vt.execute("UPDATE kullanicilar SET fotograf = ? WHERE id = ?", (ad, kullanici_id))
    flash("Fotoğraf kaydedildi; kartlarda baş harflerin yerine görünür.")
    return redirect(adres)
