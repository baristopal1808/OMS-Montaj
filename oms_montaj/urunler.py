"""Ürün sayfası (tek bir makinenin, fiziksel ürünün kendi sayfası) ve iş emri sayfası.

Ürün sayfası siparişteki ürüne tıklayınca açılır (sipariş kutusundaki ürün kutucuğu, sevk edilecek
makineler listesi, sipariş kartındaki ürün); siparişe tıklayınca ise bütün kalemleriyle sipariş kartı açılır.
Sayfada makinenin bilgileri, numaraları (şasi no, motor seri no; kilitli), iş emri ve iş emrinin kırılımları
(alt montajlar: tamamlanan ve bekleyen) görünür. ERP'den okunan motor seri no teyit edilene kadar "!" ile
görünür; teyit edilince nihai numara olur. İş emrinin eksik malzemeleri ve yarı mamulleri (kırılıma tıklayınca
açılır) ve "iş emri stoğa girmiş ama ERP İmalatta" uyarısı da burada görünür ve cevaplanır. Ekip aşamayı
burada değiştirir ve not yazar; kartın zaman akışı (zaman_akisi.py) da burada görünür. Kontrol listesi ve
fotoğraflar 4. adımın sonraki parçalarında.

İş emri sayfası bir ürüne dağıtılmamış iş emirleri (alt montaj, yarı mamul, stok) için de aynı bilgileri verir.
"""

import io
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from .asamalar import ASAMALAR, SIRA, geri_mi
from .erp_aktarim import IPTAL, kapali_mi
from .form_kurallari import FORM_TURLERI, basilan_formlar, eksik_formlar, form_durumlari, forma_tabi_mi
from .is_emri_aktarim import BAGLANTILAR, is_emri_durumu, kirilim_durumu
from .kimlik import ekip_gerekli, guvenli_adres
from .numaralar import (
    KAYNAKLAR, MOTOR_ALANLARI, TEYIT, TEYITSIZ, numara_alanlari, numara_degistir, numara_gecmisi, numara_yaz, sablon,
    urun_numaralari,
)
from .pano import siparis_bagli_kalemleri
from .siparisler import TIPLER, teslim_bilgisi, yakin_revizyon
from .stok import CIKIS_SEBEPLERI, atanabilecekler, karsilanmaz_kaydi, stok_kartlari
from .urun_kurallari import AILE_ADLARI, dis_tedarik_mi, pp_eklentisi_mi, renk
from .uyarilar import (
    HAZIR_DURUMLAR, eksik_ozetleri, imalatta_uyarilari, is_emri_eksikleri, yari_mamul_geri_al, yari_mamul_isaretle,
)
from .veritabani import baglanti
from .yapilacaklar import is_emri_ailesi
from .zaman_akisi import akis, asama_degistir, not_duzelt, not_ekle

bp = Blueprint("urunler", __name__)

# Ekibin seçebileceği aşamalar; "Stokta" siparişe bağlanmamış ürünler içindir (5. adım).
SECILEBILIR_ASAMALAR = {anahtar: ad for anahtar, ad in ASAMALAR.items() if anahtar != "stokta"}


@bp.app_context_processor
def sablon_degiskenleri():
    return {"TEYITSIZ": TEYITSIZ}


def urun_kaydi(vt, urun_id):
    """Ürün, sipariş satırının ve siparişin bilgileriyle. Stok kartında (stok.py) sipariş satırı yoktur: ürün kodu,
    adı ve ailesi kartın kendisinden gelir, sipariş alanları boştur."""
    return vt.execute(
        "SELECT u.*, k.siparis_id, k.sira_no, COALESCE(k.urun_kodu, u.stok_kodu) AS urun_kodu,"
        " COALESCE(k.urun_adi, u.stok_adi) AS urun_adi, COALESCE(k.aile, u.stok_aile) AS aile,"
        " COALESCE(k.miktar, 1) AS miktar, k.aciklama, k.teslim_tarihi, k.erp_urun_durumu, k.erp_durum,"
        " k.erp_genel_durum, k.bagli_is_emri_no, k.son_sevk_tarihi,"
        " CASE WHEN u.kalem_id IS NULL THEN 'kart' ELSE k.tur END AS tur,"
        " y.zaman AS veri_zamani, s.siparis_no, s.musteri, s.tip"
        " FROM urunler u LEFT JOIN siparis_kalemleri k ON k.id = u.kalem_id LEFT JOIN siparisler s ON s.id = k.siparis_id"
        " LEFT JOIN erp_yuklemeler y ON y.id = k.son_yukleme_id WHERE u.id = ?",
        (urun_id,),
    ).fetchone()


@bp.route("/urun/<int:urun_id>")
def sayfa(urun_id):
    vt = baglanti()
    urun = urun_kaydi(vt, urun_id)
    if urun is None:
        abort(404)
    stokta = urun["kalem_id"] is None  # stok kartı: sipariş satırı yok (stok.py)
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
    acik = not stokta and urun["erp_durum"] != IPTAL and not kapali_mi(urun) and urun["asama"] != "sevk_edildi"
    numaralar = urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"])
    numara_adlari = {alan: ad for alan, ad, _, _ in numaralar}
    gecmis = numara_gecmisi(vt, urun_id)
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
        numara_adlari=numara_adlari,
        numara_gecmisi=gecmis,
        akis=akis(vt, urun, numara_adlari),
        asama_secenekleri=SECILEBILIR_ASAMALAR,
        asama_sirasi=SIRA,
        # Her numaranın son kaydı (kim girdi ya da teyit etti); geçmiş yeniden eskiye sıralı
        son_kayit={alan: next((d for d in gecmis if d["alan"] == alan), None) for alan, _, _, _ in numaralar},
        TEYIT=TEYIT,
        kalan=teslim_bilgisi(urun["teslim_tarihi"]) if acik else None,
        revize=revizyon if yakin_revizyon(revizyon) else None,
        renk=renk(urun["aciklama"], urun["aile"]),
        dis_tedarik=dis_tedarik_mi(urun["urun_kodu"]),
        eklentiler=eklentiler,
        eksik=eksik,
        eksik_ozet=eksik_ozetleri(vt, [ie["is_emri_no"]]).get(ie["is_emri_no"]) if eksik else None,
        eksik_sirasi={grup["sira"]: grup for grup in eksik},
        eksik_zamani=eksik_zamani[0] if eksik_zamani else None,
        imalatta=imalatta_uyarilari(vt, urun_id=urun_id),
        # Bu makineyle gelenler: çene, kiriş, aksesuarlar (vibroda; vibrosuz siparişte makinede)
        bagli=None if stokta else siparis_bagli_kalemleri(vt, urun["siparis_id"]).get(urun_id),
        formlar=form_durumlari(vt, urun) if not stokta and urun["aile"] == "PP" and urun["tur"] == "kart" else None,
        # Stok kartı: atanabileceği siparişler; iş emri açılmamış sipariş ürünü: stoktaki aynı kodlu makineler
        stokta=stokta,
        atanabilecek=atanabilecekler(vt, urun["urun_kodu"]) if stokta else [],
        stoktakiler=stok_kartlari(vt, urun["urun_kodu"]) if (
            not stokta and acik and urun["asama"] == "siparis" and not urun["is_emri_id"] and not urun["stoktan_atama"]
        ) else [],
        karsilanmaz=karsilanmaz_kaydi(vt, urun_id) if not stokta else None,  # "stoktan karşılanmayacak" işareti
        CIKIS_SEBEPLERI=CIKIS_SEBEPLERI,
        forma_tabi=forma_tabi_mi(urun),
        motor_eksik=[ad for alan, ad, deger, kaynak in numaralar if alan in MOTOR_ALANLARI and (not deger or kaynak in TEYITSIZ)],
        yeni_form=request.args.get("form", type=int),
        AILE_ADLARI=AILE_ADLARI,
        KAYNAKLAR=KAYNAKLAR,
        TIPLER=TIPLER,
    )


def _metin(deger):
    """Formdan gelen not: baştaki ve sondaki boşluklar atılır, satır sonları kalır; boşsa None."""
    return (deger or "").strip() or None


@bp.route("/urun/<int:urun_id>/asama", methods=["POST"])
@ekip_gerekli
def asama(urun_id):
    """Ekip ürünün aşamasını ileri ya da geri alır; notla birlikte zaman akışına yazılır. Not ileri alırken
    isteğe bağlı, geri alırken zorunludur (kullanıcı kararı, 02/11/2026)."""
    vt = baglanti()
    urun = urun_kaydi(vt, urun_id)
    if urun is None:
        abort(404)
    yeni = request.form.get("asama")
    if yeni not in SECILEBILIR_ASAMALAR or urun["kalem_id"] is None:  # stok kartının aşaması değişmez; siparişe atanır
        abort(400)
    metin = _metin(request.form.get("not"))
    if yeni == urun["asama"]:
        flash(f"Ürün zaten \"{ASAMALAR[yeni]}\" aşamasında; aşama değişmedi. Not yazmak için \"Not ekle\"yi kullanın.")
    elif geri_mi(urun["asama"], yeni) and not metin:
        flash(f"Aşama geri alınmadı: \"{ASAMALAR[urun['asama']]}\" aşamasından \"{ASAMALAR[yeni]}\" aşamasına geri alırken sebebini yazın.")
    elif SIRA[yeni] > SIRA[urun["asama"]] and forma_tabi_mi(urun) and (
        eksik := eksik_formlar(basilan_formlar(vt, [urun_id]).get(urun_id, set()), yeni)
    ):
        flash(f"Aşama değişmedi: \"{ASAMALAR[yeni]}\" aşamasına geçmeden önce şu çıktılar alınmalı (aşama kutusundaki düğmeler): "
              f"{', '.join(FORM_TURLERI[t].lower() for t in eksik)}.")
    else:
        with vt:
            asama_degistir(vt, urun_id, urun["asama"], yeni, metin, g.kullanici["id"])
        flash(f"{urun['urun_kodu']} ({urun['siparis_no']}): aşama değişti: "
              f"{ASAMALAR[urun['asama']]} → {ASAMALAR[yeni]}.")
    # Panodaki kartın menüsünden gelindiyse panoya, ürün sayfasından gelindiyse ürün sayfasına döner
    sonra = request.form.get("sonra")
    return redirect(guvenli_adres(sonra) if sonra else url_for(".sayfa", urun_id=urun_id) + "#akis")


@bp.route("/urun/<int:urun_id>/not", methods=["POST"])
@ekip_gerekli
def not_yaz(urun_id):
    vt = baglanti()
    if urun_kaydi(vt, urun_id) is None:
        abort(404)
    if metin := _metin(request.form.get("metin")):
        with vt:
            not_ekle(vt, urun_id, metin, g.kullanici["id"])
        flash("Not kaydedildi.")
    else:
        flash("Not boş olamaz.")
    return redirect(url_for(".sayfa", urun_id=urun_id) + "#akis")


@bp.route("/urun/<int:urun_id>/not/<int:olay_id>", methods=["POST"])
@ekip_gerekli
def not_duzeltme(urun_id, olay_id):
    """Notu (ya da aşama değişikliğinin notunu) yalnızca yazan kişi düzeltir; önceki hâli saklanır, not silinmez."""
    vt = baglanti()
    olay = vt.execute("SELECT * FROM urun_olaylari WHERE id = ? AND urun_id = ?", (olay_id, urun_id)).fetchone()
    if olay is None:
        abort(404)
    if olay["kullanici_id"] != g.kullanici["id"]:
        abort(403)
    metin = _metin(request.form.get("metin"))
    if not metin:
        flash("Not silinemez; boş bırakılamaz.")
    elif metin == olay["metin"]:
        flash("Not değişmedi.")
    else:
        with vt:
            not_duzelt(vt, olay, metin)
        flash("Not düzeltildi; önceki hâli saklandı.")
    return redirect(url_for(".sayfa", urun_id=urun_id) + "#akis")


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


@bp.route("/urun/<int:urun_id>/numara/<alan>/teyit", methods=["POST"])
@ekip_gerekli
def numara_teyit(urun_id, alan):
    """ERP'den okunan motor seri no'sunu teyit eder: numara ekibin numarası (nihai, kilitli) olarak yazılır,
    geçmişe "teyit edildi" diye girer."""
    vt = baglanti()
    urun = urun_kaydi(vt, urun_id)
    if urun is None or alan not in MOTOR_ALANLARI or alan not in numara_alanlari(urun["aile"], urun["urun_kodu"]):
        abort(404)
    ad, deger, kaynak = next((a, d, k) for f, a, d, k in urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"])
                             if f == alan)
    if kaynak not in TEYITSIZ:
        flash(f"{ad} ERP'den okunmuş bir numara değil; teyit gerekmiyor.")
    elif request.form.get("deger") != deger:
        flash(f"{ad} bu arada değişmiş; yeni numarayı kontrol edip yeniden teyit edin.")
    elif not request.form.get("teyit"):
        flash(f"{ad} teyit edilmedi: önce kutucuğu işaretleyin.")
    else:
        with vt:
            numara_degistir(vt, urun_id, alan, None, deger, TEYIT, g.kullanici["id"])
        flash(f"{ad} {deger} teyit edildi; artık nihai numara.")
    return redirect(url_for(".sayfa", urun_id=urun_id) + "#numaralar")


@bp.route("/is-emri/<is_emri_no>")
def is_emri(is_emri_no):
    """İş emrinin sayfası: alt montaj ve yarı mamul iş emirleri gibi bir ürüne dağıtılmamış iş emirleri de
    dahil; bilgileri, bağlantısı, eksik malzemeleri, yarı mamulleri ve kırılımları."""
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
    """Yarı mamulleri "Hazır" işaretler (seçilenler ya da kırılımın hazır olmayanlarının hepsi) ya da işareti geri alır."""
    vt = baglanti()
    try:
        sira = int(request.form.get("sira", ""))
    except ValueError:
        abort(400)
    grup = next((gr for gr in is_emri_eksikleri(vt, is_emri_no) if gr["sira"] == sira and gr["yari_mamuller"]), None)
    if grup is None:
        abort(404)
    kodlar = [m["malzeme_kodu"] for m in grup["yari_mamuller"] if m["durum"] not in HAZIR_DURUMLAR]
    with vt:
        if geri := request.form.get("geri_al"):
            yari_mamul_geri_al(vt, is_emri_no, sira, geri)
            flash(f"{geri}: \"Hazır\" işareti geri alındı.")
        else:
            secilen = kodlar if request.form.get("islem") == "hepsi" else [k for k in request.form.getlist("sec") if k in kodlar]
            if secilen:
                yari_mamul_isaretle(vt, is_emri_no, [(sira, k) for k in secilen], g.kullanici["id"])
                flash(f"{len(secilen)} yarı mamul \"Hazır\" işaretlendi.")
            else:
                flash("Hazır olan yarı mamulleri işaretleyin ya da \"Hepsi hazır\"a basın.")
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
