"""Ürün sayfası (tek bir makinenin, fiziksel ürünün kendi sayfası) ve iş emri sayfası.

Ürün sayfası siparişteki ürüne tıklayınca açılır (sipariş kutusundaki ürün kutucuğu, sevk edilecek
makineler listesi, sipariş kartındaki ürün); siparişe tıklayınca ise bütün kalemleriyle sipariş kartı açılır.
Sayfada makinenin bilgileri, numaraları (şasi no, motor seri no; kilitli), iş emri ve iş emrinin kırılımları
(alt montajlar: tamamlanan ve bekleyen) görünür. İş emrinin eksik malzemeleri ve imalattan beklenen yarı
mamulleri (kırılıma tıklayınca açılır) ve "iş emri stoğa girmiş ama ERP İmalatta" uyarısı da burada görünür
ve cevaplanır. Kontrol listesi, notlar ve fotoğraflar 4. adımda.

İş emri sayfası bir ürüne dağıtılmamış iş emirleri (alt montaj, yarı mamul, stok) için de aynı bilgileri verir.
"""

import io
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from .erp_aktarim import IPTAL, kapali_mi
from .is_emri_aktarim import BAGLANTILAR, is_emri_durumu, kirilim_durumu
from .kimlik import ekip_gerekli, guvenli_adres
from .numaralar import (
    KAYNAKLAR, numara_alanlari, numara_degistir, numara_gecmisi, numara_yaz, sablon, urun_numaralari,
)
from .siparisler import TIPLER, siparis_durum_ozeti, teslim_bilgisi, yakin_revizyon
from .urun_kurallari import AILE_ADLARI, dis_tedarik_mi, pp_eklentisi_mi, renk, yag
from .uyarilar import (
    YARI_MAMUL, eksik_ozetleri, imalatta_uyarilari, is_emri_eksikleri, yari_mamul_geri_al, yari_mamul_isaretle,
)
from .veritabani import baglanti
from .yapilacaklar import is_emri_ailesi

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
    numaralar = urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"])
    # Eksik malzeme (çıkışı yapılmamış) ve "iş emri stoğa girmiş ama ERP İmalatta" uyarısı
    eksik = is_emri_eksikleri(vt, ie["is_emri_no"]) if ie else []
    eksik_zamani = vt.execute(
        "SELECT y.zaman FROM eksik_malzemeler e JOIN erp_yuklemeler y ON y.id = e.yukleme_id WHERE e.is_emri_no = ? LIMIT 1",
        (ie["is_emri_no"],),
    ).fetchone() if eksik else None
    # Güç ünitesinin opsiyonel ekipmanları: dışarıdan alınıp entegre edilir (kablosuz kumanda seti, uzaktan erişim modülü)
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
        numaralar=numaralar,
        numara_adlari={alan: ad for alan, ad, _, _ in numaralar},
        numara_gecmisi=numara_gecmisi(vt, urun_id),
        kalan=teslim_bilgisi(urun["teslim_tarihi"]) if acik else None,
        revize=revizyon if yakin_revizyon(revizyon) else None,
        renk=renk(urun["aciklama"]),
        yag=yag(urun["aciklama"]) if urun["aile"] == "PP" else None,
        dis_tedarik=dis_tedarik_mi(urun["urun_kodu"]),
        durum_ozeti=siparis_durum_ozeti(vt, siparis),
        eklentiler=eklentiler,
        eksik=eksik,
        eksik_ozet=eksik_ozetleri(vt, [ie["is_emri_no"]]).get(ie["is_emri_no"]) if eksik else None,
        eksik_sirasi={grup["sira"]: grup for grup in eksik},
        eksik_zamani=eksik_zamani[0] if eksik_zamani else None,
        imalatta=imalatta_uyarilari(vt, urun_id=urun_id),
        AILE_ADLARI=AILE_ADLARI,
        KAYNAKLAR=KAYNAKLAR,
        TIPLER=TIPLER,
    )


@bp.route("/urun/<int:urun_id>/numara/<alan>", methods=["POST"])
@ekip_gerekli
def numara(urun_id, alan):
    """Bir makine numarasını girer ya da değiştirir. Numarası olan (ERP'den okunan ya da girilmiş) alan
    kilitlidir: değiştirmek için sebep yazılır. Her giriş ve değişiklik geçmişe yazılır."""
    vt = baglanti()
    urun = urun_kaydi(vt, urun_id)
    if urun is None or alan not in numara_alanlari(urun["aile"], urun["urun_kodu"]):
        abort(404)
    ad, simdiki = next((a, d) for f, a, d, _ in urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"])
                       if f == alan)
    yeni = numara_yaz(request.form.get("deger"), alan)
    sebep = " ".join((request.form.get("sebep") or "").split()) or None
    if not yeni:
        flash(f"{ad} boş olamaz.")
    elif yeni == simdiki:
        flash(f"{ad} zaten {yeni}; değiştirilmedi.")
    elif simdiki and not sebep:
        flash(f"{ad} kilitli: değiştirmek için sebebini yazın.")
    else:
        with vt:
            numara_degistir(vt, urun_id, alan, simdiki, yeni, sebep if simdiki else None, g.kullanici["id"])
        flash(f"{ad} değiştirildi: {simdiki} → {yeni}." if simdiki else f"{ad} kaydedildi ve kilitlendi.")
    return redirect(url_for(".sayfa", urun_id=urun_id) + "#numaralar")


@bp.route("/is-emri/<is_emri_no>")
def is_emri(is_emri_no):
    """İş emrinin sayfası: alt montaj ve yarı mamul iş emirleri gibi bir ürüne dağıtılmamış iş emirleri de
    dahil; bilgileri, bağlantısı, eksik malzemeleri, imalattan beklenen yarı mamulleri ve kırılımları."""
    vt = baglanti()
    ie = vt.execute(
        "SELECT i.*, s.siparis_no, s.musteri, k.sira_no AS kalem_sira FROM is_emirleri i"
        " LEFT JOIN siparisler s ON s.id = i.siparis_id LEFT JOIN siparis_kalemleri k ON k.id = i.kalem_id"
        " WHERE i.is_emri_no = ?",
        (is_emri_no,),
    ).fetchone()
    if ie is None:
        abort(404)
    urun = vt.execute("SELECT id FROM urunler WHERE is_emri_id = ? ORDER BY adet_sira LIMIT 1", (ie["id"],)).fetchone()
    kirilimlar = [
        {"satir": s, "durum": kirilim_durumu(s)}
        for s in vt.execute("SELECT * FROM is_emri_satirlari WHERE is_emri_id = ? ORDER BY sira_no", (ie["id"],))
    ]
    eksik = is_emri_eksikleri(vt, is_emri_no)
    veri = vt.execute(
        "SELECT y.zaman FROM eksik_malzemeler e JOIN erp_yuklemeler y ON y.id = e.yukleme_id WHERE e.is_emri_no = ? LIMIT 1",
        (is_emri_no,),
    ).fetchone()
    return render_template(
        "is_emri.html",
        ie=ie,
        ie_durumu=is_emri_durumu(ie),
        urun=urun,
        kirilimlar=kirilimlar,
        tamamlanan=sum(1 for k in kirilimlar if k["durum"][1] == "kapali"),
        eksik=eksik,
        eksik_ozet=eksik_ozetleri(vt, [is_emri_no]).get(is_emri_no),
        eksik_sirasi={grup["sira"]: grup for grup in eksik},
        eksik_zamani=veri[0] if veri else None,
        aile=is_emri_ailesi(ie["urun_kodu"], ie["urun_adi"]),
        BAGLANTILAR=BAGLANTILAR,
    )


@bp.route("/is-emri/<is_emri_no>/yari-mamul", methods=["POST"])
@ekip_gerekli
def yari_mamul(is_emri_no):
    """İmalattan beklenen yarı mamulleri "geldi" işaretler (seçilenler ya da kırılımın hepsi) ya da işareti geri alır."""
    vt = baglanti()
    try:
        sira = int(request.form.get("sira", ""))
    except ValueError:
        abort(400)
    kodlar = [r[0] for r in vt.execute(
        "SELECT malzeme_kodu FROM eksik_malzemeler WHERE is_emri_no = ? AND sira_no = ? AND envanter_turu = ?",
        (is_emri_no, sira, YARI_MAMUL),
    )]
    if not kodlar:
        abort(404)
    with vt:
        if geri := request.form.get("geri_al"):
            yari_mamul_geri_al(vt, is_emri_no, sira, geri)
            flash(f"{geri}: \"Geldi\" işareti geri alındı.")
        else:
            secilen = kodlar if request.form.get("islem") == "hepsi" else [k for k in request.form.getlist("sec") if k in kodlar]
            if secilen:
                yari_mamul_isaretle(vt, is_emri_no, [(sira, k) for k in secilen], g.kullanici["id"])
                flash(f"{len(secilen)} yarı mamul \"geldi\" işaretlendi.")
            else:
                flash("Gelen yarı mamulleri işaretleyin ya da \"Hepsi geldi\"ye basın.")
    adres = guvenli_adres(request.form.get("sonra") or url_for(".is_emri", is_emri_no=is_emri_no))
    return redirect(f"{adres}?acik=yari-{sira}#yari-{sira}")


@bp.route("/makine-numaralari.xlsx")
def sablon_indir():
    """Bütün makinelerin satır satır yer aldığı "Makine numaraları" şablonu."""
    return send_file(
        io.BytesIO(sablon(baglanti())),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"makine-numaralari-{date.today():%Y-%m-%d}.xlsx",
    )
