"""Ürün sayfası: tek bir makinenin (fiziksel ürünün) kendi sayfası.

Siparişteki ürüne tıklayınca açılır (sipariş kutusundaki ürün kutucuğu, sevk edilecek makineler
listesi, sipariş kartındaki ürün); siparişe tıklayınca ise bütün kalemleriyle sipariş kartı açılır.
Sayfada makinenin bilgileri, numaraları (şasi no, motor seri no), iş emri ve iş emrinin kırılımları
(alt montajlar: tamamlanan ve bekleyen) görünür. Kontrol listesi, notlar ve fotoğraflar 4. adımda.
"""

import io
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from .erp_aktarim import IPTAL, kapali_mi
from .is_emri_aktarim import is_emri_durumu, kirilim_durumu
from .kimlik import ekip_gerekli
from .numaralar import KAYNAKLAR, NUMARA_ALANLARI, numara_yaz, numaralari_kaydet, sablon, urun_numaralari
from .siparisler import TIPLER, teslim_bilgisi, yakin_revizyon
from .urun_kurallari import AILE_ADLARI, dis_tedarik_mi, renk, yag
from .veritabani import baglanti

bp = Blueprint("urunler", __name__)


def urun_kaydi(vt, urun_id):
    return vt.execute(
        "SELECT u.*, k.siparis_id, k.sira_no, k.urun_kodu, k.urun_adi, k.aile, k.miktar, k.aciklama, k.teslim_tarihi,"
        " k.erp_urun_durumu, k.erp_durum, k.erp_genel_durum, k.bagli_is_emri_no, k.son_sevk_tarihi, k.tur,"
        " y.zaman AS veri_zamani, s.siparis_no, s.musteri, s.tip"
        " FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id"
        " LEFT JOIN erp_yuklemeler y ON y.id = k.son_yukleme_id WHERE u.id = ?",
        (urun_id,),
    ).fetchone()


@bp.route("/urun/<int:urun_id>")
def sayfa(urun_id):
    vt = baglanti()
    urun = urun_kaydi(vt, urun_id)
    if urun is None:
        abort(404)
    ie = vt.execute("SELECT * FROM is_emirleri WHERE id = ?", (urun["is_emri_id"],)).fetchone() if urun["is_emri_id"] else None
    kirilimlar = []
    if ie:
        kirilimlar = [
            {"satir": s, "durum": kirilim_durumu(s)}
            for s in vt.execute("SELECT * FROM is_emri_satirlari WHERE is_emri_id = ? ORDER BY sira_no", (ie["id"],))
        ]
    revizyon = vt.execute(
        "SELECT MAX(y.zaman) FROM siparis_revizyonlari r JOIN erp_yuklemeler y ON y.id = r.yukleme_id"
        " WHERE r.siparis_id = ? AND r.sira_no = ?",
        (urun["siparis_id"], urun["sira_no"]),
    ).fetchone()[0]
    acik = urun["erp_durum"] != IPTAL and not kapali_mi(urun) and urun["asama"] != "sevk_edildi"
    return render_template(
        "urun.html",
        urun=urun,
        ie=ie,
        ie_durumu=is_emri_durumu(ie) if ie else None,
        kirilimlar=kirilimlar,
        tamamlanan=sum(1 for k in kirilimlar if k["durum"][1] == "kapali"),
        numaralar=urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"]),
        kalan=teslim_bilgisi(urun["teslim_tarihi"]) if acik else None,
        revize=revizyon if yakin_revizyon(revizyon) else None,
        renk=renk(urun["aciklama"]),
        yag=yag(urun["aciklama"]) if urun["aile"] == "PP" else None,
        dis_tedarik=dis_tedarik_mi(urun["urun_kodu"]),
        AILE_ADLARI=AILE_ADLARI,
        KAYNAKLAR=KAYNAKLAR,
        TIPLER=TIPLER,
    )


@bp.route("/urun/<int:urun_id>/numaralar", methods=["POST"])
@ekip_gerekli
def numaralar(urun_id):
    vt = baglanti()
    urun = urun_kaydi(vt, urun_id)
    if urun is None:
        abort(404)
    degerler = {alan: numara_yaz(request.form.get(alan), alan) for alan in NUMARA_ALANLARI.get(urun["aile"], ())}
    if any(degerler[alan] != urun[alan] for alan in degerler):
        with vt:
            numaralari_kaydet(vt, urun_id, degerler, g.kullanici["id"])
        flash("Makine numaraları kaydedildi.")
    return redirect(url_for(".sayfa", urun_id=urun_id))


@bp.route("/makine-numaralari.xlsx")
def sablon_indir():
    """Bütün makinelerin satır satır yer aldığı "Makine numaraları" şablonu."""
    return send_file(
        io.BytesIO(sablon(baglanti())),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"makine-numaralari-{date.today():%Y-%m-%d}.xlsx",
    )
