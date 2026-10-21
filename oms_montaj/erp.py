"""ERP yükleme ekranı: Excel raporları buradan yüklenir.

Her dosyanın bir kopyası veri klasöründeki yuklemeler/ altına konur (git'e
girmez); türü başlıklarından tanınır ve işlenir. Bir dosya ya bütünüyle
işlenir ya hiç işlenmez. İzleyiciler yükleme geçmişine bakar, yükleyemez.
"""

from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from .erp_aktarim import listede_olmayanlari_isaretle, siparis_ozeti, siparisleri_isle
from .erp_okuyucu import RAPORLAR, OkumaHatasi, rapor_turu, siparis_satirlari, tablo_oku
from .veritabani import baglanti

bp = Blueprint("erp", __name__)

UZANTILAR = (".xls", ".xlsx")


def _yukleme_kaydi(vt, dosya_adi, kayit_adi, tur, satir_sayisi, ozet=None):
    return vt.execute(
        "INSERT INTO erp_yuklemeler (kullanici_id, dosya_adi, kayit_adi, tur, satir_sayisi, ozet)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (g.kullanici["id"], dosya_adi, kayit_adi, tur, satir_sayisi, ozet),
    ).lastrowid


def _kopyasini_kaydet(dosya, uzanti):
    klasor = Path(current_app.config["VERI_KLASORU"]) / "yuklemeler"
    klasor.mkdir(exist_ok=True)
    zaman = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    no = 1
    while (klasor / f"{zaman}_{no}{uzanti}").exists():
        no += 1
    yol = klasor / f"{zaman}_{no}{uzanti}"
    dosya.save(yol)
    return yol


def dosya_isle(dosya):
    """Yüklenen bir dosyayı işler: (kullanıcıya gösterilecek sonuç, dosyadaki sipariş numaraları)."""
    ad = dosya.filename
    uzanti = Path(ad).suffix.lower()
    if uzanti not in UZANTILAR:
        return f"{ad}: yalnızca .xls ve .xlsx dosyaları yüklenebilir.", set()
    yol = _kopyasini_kaydet(dosya, uzanti)
    vt = baglanti()
    siparis_nolari = set()
    try:
        basliklar, satirlar = tablo_oku(yol)
        tur = rapor_turu(basliklar)
        with vt:
            yukleme_id = _yukleme_kaydi(vt, ad, yol.name, tur, len(satirlar))
            if tur == "siparis_talepleri":
                kayitlar = siparis_satirlari(basliklar, satirlar)
                ozet = "Sipariş talepleri: " + siparis_ozeti(siparisleri_isle(vt, kayitlar, yukleme_id))
                siparis_nolari = {k["siparis_no"] for k in kayitlar}
            elif tur:
                rapor = RAPORLAR[tur]
                ozet = f"{rapor['ad']} raporu tanındı; bu rapor planın {rapor['adim']}. adımında işlenecek."
            else:
                ozet = "Rapor türü tanınamadı. Şimdilik sipariş talepleri listeleri işlenebiliyor."
            vt.execute("UPDATE erp_yuklemeler SET ozet = ? WHERE id = ?", (ozet, yukleme_id))
    except OkumaHatasi as hata:
        ozet = f"İşlenemedi: {hata}"
        with vt:
            _yukleme_kaydi(vt, ad, yol.name, None, None, ozet)
    return f"{ad}: {ozet}", siparis_nolari


@bp.route("/erp-yukleme", methods=["GET", "POST"])
def yukleme():
    if request.method == "POST":
        if g.kullanici["rol"] != "ekip":
            abort(403)
        dosyalar = [d for d in request.files.getlist("dosyalar") if d.filename]
        if not dosyalar:
            flash("Dosya seçilmedi.")
        gorulen = set()
        for dosya in dosyalar:
            mesaj, siparis_nolari = dosya_isle(dosya)
            gorulen |= siparis_nolari
            flash(mesaj)
        if gorulen:
            # Birlikte yüklenen sipariş listeleri ERP'nin bugünkü hâlidir.
            vt = baglanti()
            with vt:
                gizlenen, geri_gelen = listede_olmayanlari_isaretle(vt, gorulen)
            if gizlenen:
                flash(f"{gizlenen} açık sipariş yüklenen listede yok; açık siparişlerden çıkarıldı (kayıtları silinmedi,"
                      " Siparişler'de \"ERP listesinde yok\" süzgeciyle görülebilir).")
            if geri_gelen:
                flash(f"{geri_gelen} sipariş listede yeniden göründüğü için geri geldi.")
        return redirect(url_for(".yukleme"))

    yuklemeler = baglanti().execute(
        "SELECT y.*, k.ad_soyad FROM erp_yuklemeler y LEFT JOIN kullanicilar k ON k.id = y.kullanici_id"
        " ORDER BY y.id DESC LIMIT 30"
    ).fetchall()
    return render_template("erp_yukleme.html", yuklemeler=yuklemeler, RAPORLAR=RAPORLAR)
