"""Ayarlar > Kullanıcılar: hesap açma, rol, etkinlik ve geçici şifre.

Deneme süresince ekipteki herkes hesapları yönetebilir; izleyiciler yalnızca
listeye bakar (docs/ihtiyaclar.md, soru 7b ve 40). Kimse kendi rolünü ya da
etkinliğini değiştiremez; böylece kimse yanlışlıkla kendini dışarıda bırakmaz.
Yeni hesap ve sıfırlanan şifre geçicidir; kişi ilk girişte kendi şifresini belirler.
"""

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .kimlik import ROLLER, ekip_gerekli, hesap_sorunu, kullanici_ekle, sifre_sorunu, sifreyi_degistir
from .veritabani import baglanti

bp = Blueprint("kullanicilar", __name__, url_prefix="/ayarlar/kullanicilar")


def rol_sorunu(rol):
    return None if rol in ROLLER else "Bir rol seçin."


@bp.route("/")
def liste():
    kullanicilar = baglanti().execute(
        "SELECT * FROM kullanicilar ORDER BY aktif DESC, ad_soyad COLLATE NOCASE"
    ).fetchall()
    return render_template("kullanicilar.html", kullanicilar=kullanicilar)


@bp.route("/yeni", methods=["GET", "POST"])
@ekip_gerekli
def yeni():
    hata = None
    form = request.form
    if request.method == "POST":
        ad_soyad = form.get("ad_soyad", "").strip()
        kullanici_adi = form.get("kullanici_adi", "").strip()
        rol = form.get("rol")
        sifre = form.get("sifre", "")
        hata = (
            hesap_sorunu(ad_soyad, kullanici_adi)
            or rol_sorunu(rol)
            or sifre_sorunu(sifre, form.get("sifre_tekrar", ""))
        )
        if not hata:
            if kullanici_ekle(kullanici_adi, ad_soyad, rol, sifre) is None:
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
        rol = kullanici["rol"] if kendisi else form.get("rol")
        aktif = True if kendisi else "aktif" in form
        sifre = "" if kendisi else form.get("sifre", "")
        hata = (
            ("Ad soyad boş bırakılamaz." if not ad_soyad else None)
            or rol_sorunu(rol)
            or (sifre_sorunu(sifre, form.get("sifre_tekrar", "")) if sifre else None)
        )
        if not hata:
            with baglanti() as vt:
                vt.execute(
                    "UPDATE kullanicilar SET ad_soyad = ?, rol = ?, aktif = ? WHERE id = ?",
                    (ad_soyad, rol, int(aktif), kullanici_id),
                )
            if sifre:
                sifreyi_degistir(kullanici_id, sifre, sifre_degismeli=True)
            flash("Kaydedildi.")
            return redirect(url_for(".liste"))
    return render_template(
        "kullanici_formu.html", kullanici=kullanici, kendisi=kendisi, form=form, hata=hata
    )
