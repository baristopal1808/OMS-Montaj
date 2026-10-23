"""ERP yükleme ekranı: Excel raporları buradan yüklenir.

Her dosyanın bir kopyası veri klasöründeki yuklemeler/ altına konur (git'e
girmez); türü başlıklarından tanınır ve işlenir. Bir dosya ya bütünüyle
işlenir ya hiç işlenmez. İzleyiciler yükleme geçmişine bakar, yükleyemez.
"""

from datetime import datetime
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for

from .erp_aktarim import listede_olmayanlari_isaretle, siparis_ozeti, siparisleri_isle
from .erp_okuyucu import (
    RAPORLAR, OkumaHatasi, cikis_satirlari, is_emri_satirlari, numara_satirlari, rapor_turu, siparis_satirlari, tablo_oku,
)
from .is_emri_aktarim import baglanti_ozeti, is_emirlerini_bagla, is_emirlerini_isle, is_emri_ozeti
from .numaralar import numara_ozeti, numaralari_isle
from .uyarilar import eksik_ozeti, eksikleri_isle
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


# Birlikte yüklenen dosyalar bu sırayla işlenir: eksik malzemeler iş emirlerine, iş emirleri siparişlere bakar.
ISLEME_SIRASI = ("siparis_talepleri", "is_emirleri", "cikis_yapilamayan", "makine_numaralari")


def dosya_oku(dosya):
    """Yüklenen dosyanın kopyasını saklar ve okur: {"ad", "yol", "basliklar", "satirlar", "tur", "hata"}."""
    ad = dosya.filename
    uzanti = Path(ad).suffix.lower()
    if uzanti not in UZANTILAR:
        return {"ad": ad, "yol": None, "tur": None, "hata": "yalnızca .xls ve .xlsx dosyaları yüklenebilir."}
    yol = _kopyasini_kaydet(dosya, uzanti)
    try:
        basliklar, satirlar = tablo_oku(yol)
    except OkumaHatasi as hata:
        return {"ad": ad, "yol": yol, "tur": None, "hata": f"İşlenemedi: {hata}"}
    return {"ad": ad, "yol": yol, "basliklar": basliklar, "satirlar": satirlar, "tur": rapor_turu(basliklar), "hata": None}


def dosya_isle(okunan):
    """Okunan bir dosyayı işler: (kullanıcıya gösterilecek sonuç, dosyadaki sipariş numaraları, tanınan tür)."""
    ad, yol, tur = okunan["ad"], okunan["yol"], okunan["tur"]
    vt = baglanti()
    if okunan["hata"]:
        if yol:
            with vt:
                _yukleme_kaydi(vt, ad, yol.name, None, None, okunan["hata"])
        return f"{ad}: {okunan['hata']}", set(), None
    basliklar, satirlar = okunan["basliklar"], okunan["satirlar"]
    siparis_nolari = set()
    try:
        with vt:
            yukleme_id = _yukleme_kaydi(vt, ad, yol.name, tur, len(satirlar))
            if tur == "siparis_talepleri":
                kayitlar = siparis_satirlari(basliklar, satirlar)
                ozet = "Sipariş talepleri: " + siparis_ozeti(siparisleri_isle(vt, kayitlar, yukleme_id))
                siparis_nolari = {k["siparis_no"] for k in kayitlar}
            elif tur == "is_emirleri":
                ozet = "İş emirleri: " + is_emri_ozeti(is_emirlerini_isle(vt, is_emri_satirlari(basliklar, satirlar), yukleme_id))
            elif tur == "makine_numaralari":
                ozet = "Makine numaraları: " + numara_ozeti(
                    numaralari_isle(vt, numara_satirlari(basliklar, satirlar), g.kullanici["id"]))
            elif tur == "cikis_yapilamayan":
                ozet = "Çıkış yapılamayan malzeme: " + eksik_ozeti(
                    eksikleri_isle(vt, cikis_satirlari(basliklar, satirlar), yukleme_id))
            elif tur:
                rapor = RAPORLAR[tur]
                ozet = f"{rapor['ad']} raporu tanındı; bu rapor planın {rapor['adim']}. adımında işlenecek."
            else:
                ozet = ("Rapor türü tanınamadı. Şimdilik sipariş talepleri, iş emirleri ve çıkış yapılamayan malzeme"
                        " listeleri işlenebiliyor.")
            vt.execute("UPDATE erp_yuklemeler SET ozet = ? WHERE id = ?", (ozet, yukleme_id))
    except OkumaHatasi as hata:
        ozet = f"İşlenemedi: {hata}"
        tur = None
        with vt:
            _yukleme_kaydi(vt, ad, yol.name, None, None, ozet)
    return f"{ad}: {ozet}", siparis_nolari, tur


@bp.route("/erp-yukleme", methods=["GET", "POST"])
def yukleme():
    if request.method == "POST":
        if g.kullanici["rol"] != "ekip":
            abort(403)
        dosyalar = [d for d in request.files.getlist("dosyalar") if d.filename]
        if not dosyalar:
            flash("Dosya seçilmedi.")
        gorulen, turler = set(), set()
        okunanlar = sorted(
            (dosya_oku(dosya) for dosya in dosyalar),
            key=lambda o: ISLEME_SIRASI.index(o["tur"]) if o["tur"] in ISLEME_SIRASI else len(ISLEME_SIRASI),
        )
        for okunan in okunanlar:
            mesaj, siparis_nolari, tur = dosya_isle(okunan)
            gorulen |= siparis_nolari
            turler.add(tur)
            flash(mesaj)
        vt = baglanti()
        if gorulen:
            # Birlikte yüklenen sipariş listeleri ERP'nin bugünkü hâlidir.
            with vt:
                gizlenen, geri_gelen = listede_olmayanlari_isaretle(vt, gorulen)
            if gizlenen:
                flash(f"{gizlenen} açık sipariş yüklenen listede yok; açık siparişlerden çıkarıldı (kayıtları silinmedi,"
                      " Siparişler'de \"ERP listesinde yok\" süzgeciyle görülebilir).")
            if geri_gelen:
                flash(f"{geri_gelen} sipariş listede yeniden göründüğü için geri geldi.")
        if turler & {"siparis_talepleri", "is_emirleri"} and vt.execute("SELECT 1 FROM is_emirleri LIMIT 1").fetchone():
            # Sipariş ya da iş emri listesi değişince iş emirlerinin bağlantısı yeniden kurulur.
            with vt:
                flash(baglanti_ozeti(is_emirlerini_bagla(vt)))
        return redirect(url_for(".yukleme"))

    yuklemeler = baglanti().execute(
        "SELECT y.*, k.ad_soyad FROM erp_yuklemeler y LEFT JOIN kullanicilar k ON k.id = y.kullanici_id"
        " ORDER BY y.id DESC LIMIT 30"
    ).fetchall()
    return render_template("erp_yukleme.html", yuklemeler=yuklemeler, RAPORLAR=RAPORLAR)
