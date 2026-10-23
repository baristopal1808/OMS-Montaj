"""Ürün sayfası: tek bir makinenin (fiziksel ürünün) kendi sayfası.

Siparişteki ürüne tıklayınca açılır (sipariş kutusundaki ürün kutucuğu, sevk edilecek makineler
listesi, sipariş kartındaki ürün); siparişe tıklayınca ise bütün kalemleriyle sipariş kartı açılır.
Sayfada makinenin bilgileri, numaraları (şasi no, motor seri no), iş emri ve iş emrinin kırılımları
(alt montajlar: tamamlanan ve bekleyen) görünür. İş emrinin eksik malzemeleri (kırılım kırılım) ve "iş emri
stoğa girmiş ama ERP İmalatta" uyarısı da burada görünür ve cevaplanır. Kontrol listesi, notlar ve
fotoğraflar 4. adımda.
"""

import io
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from .erp_aktarim import IPTAL, kapali_mi
from .is_emri_aktarim import is_emri_durumu, kirilim_durumu
from .kimlik import ekip_gerekli
from .numaralar import KAYNAKLAR, numara_alanlari, numara_yaz, numaralari_kaydet, sablon, urun_numaralari
from .siparisler import TIPLER, siparis_durum_ozeti, teslim_bilgisi, yakin_revizyon
from .urun_kurallari import AILE_ADLARI, dis_tedarik_mi, pp_eklentisi_mi, renk, yag
from .uyarilar import eksik_ozetleri, imalatta_uyarilari, is_emri_eksikleri
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
    siparis = {"id": urun["siparis_id"], "tip": urun["tip"]}
    # Güç ünitesine takılacak, dışarıdan alınan kalemler (kablosuz kumanda seti, uzaktan erişim modülü)
    # Eksik malzeme (çıkışı yapılmamış) ve "iş emri stoğa girmiş ama ERP İmalatta" uyarısı
    eksik = is_emri_eksikleri(vt, ie["is_emri_no"]) if ie else []
    eksik_zamani = vt.execute(
        "SELECT y.zaman FROM eksik_malzemeler e JOIN erp_yuklemeler y ON y.id = e.yukleme_id WHERE e.is_emri_no = ? LIMIT 1",
        (ie["is_emri_no"],),
    ).fetchone() if eksik else None
    eklentiler = [
        k for k in vt.execute(
            "SELECT id, urun_kodu, urun_adi, miktar, montaj_durumu FROM siparis_kalemleri"
            " WHERE siparis_id = ? AND COALESCE(erp_durum, '') != ? ORDER BY sira_no",
            (urun["siparis_id"], IPTAL),
        )
        if pp_eklentisi_mi(k["urun_kodu"], urun["tip"])
    ] if urun["aile"] == "PP" else []
    return render_template(
        "urun.html",
        urun=urun,
        ie=ie,
        ie_durumu=is_emri_durumu(ie) if ie else None,
        kirilimlar=kirilimlar,
        tamamlanan=sum(1 for k in kirilimlar if k["durum"][1] == "kapali"),
        numaralar=urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"]),
        kalan=teslim_bilgisi(urun["teslim_tarihi"]) if acik else None,
        revize=revizyon if yakin_revizyon(revizyon) else None,
        renk=renk(urun["aciklama"]),
        yag=yag(urun["aciklama"]) if urun["aile"] == "PP" else None,
        dis_tedarik=dis_tedarik_mi(urun["urun_kodu"]),
        durum_ozeti=siparis_durum_ozeti(vt, siparis),
        eklentiler=eklentiler,
        eksik=eksik,
        eksik_ozet=eksik_ozetleri(vt, [ie["is_emri_no"]]).get(ie["is_emri_no"]) if eksik else None,
        eksik_sirasi={sira: len(liste) for sira, _, liste in eksik},
        eksik_zamani=eksik_zamani[0] if eksik_zamani else None,
        imalatta=imalatta_uyarilari(vt, urun_id=urun_id),
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
    degerler = {alan: numara_yaz(request.form.get(alan), alan) for alan in numara_alanlari(urun["aile"], urun["urun_kodu"])}
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
