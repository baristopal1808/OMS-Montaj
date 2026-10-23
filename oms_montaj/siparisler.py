"""Siparişler: ana ekrandaki liste ve sipariş kartı.

Siparişin durumu ve teslim tarihi kalemlerinden hesaplanır: iptal edilmemiş
kalemlerin hepsi ERP'de kapandıysa sipariş "ERP'de kapandı", açık kalemlerin
hepsi onay bekliyorsa "Onay bekliyor" sayılır. Teslim tarihi açık kalemlerin
en yakın uzlaşılan sevk tarihidir; onay bekleyen kalemler kesin olmadığından
başka açık kalem varsa sayılmaz. Onay bekleyen siparişler listede teslim
sütunlarına değil, en sağdaki ayrı sütuna dizilir.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from .erp_aktarim import BEKLEMEDE, IPTAL, REVIZYON_ADLARI, eksik_siralar, kapali_mi
from .is_emri_aktarim import is_emri_durumu
from .kimlik import ekip_gerekli, guvenli_adres
from .numaralar import urun_numaralari
from .urun_kurallari import (
    AILE_ADLARI, AILE_SIRASI, ANA_URUNLER, EKLENTI_DURUMLARI, VARSAYILAN_EKLENTI_DURUMU, VIBROHAMMER,
    dis_tedarik_mi, pp_eklentisi_mi, renk, yag,
)
from .veritabani import baglanti

bp = Blueprint("siparisler", __name__)

DURUMLAR = {
    "acik": "Açık",
    "onay_bekliyor": "Onay bekliyor",
    "kapali": "ERP'de kapandı",
    "iptal": "İptal",
    "listede_yok": "ERP listesinde yok",
}
DURUM_SUZGECLERI = {**DURUMLAR, "tumu": "Tümü"}
TIPLER = {"makine": "Makine", "yedek_parca": "Yedek parça", "servis": "Servis"}
AILE_SUZGECLERI = {"vibrohammer": "Vibrohammer (SVR + OVR)", **{aile: aile for aile in AILE_SIRASI}}
YAKLASAN_GUN = 14  # teslimine bu kadar gün kalan sipariş turuncu görünür
REVIZYON_GUN = 30  # bu kadar gün içindeki revizyon kutuda ve satırda "Revize" etiketiyle görünür
# Açık siparişler bu üç sütunda, her sütunda teslim tarihine göre yukarıdan aşağı dizilir.
TESLIM_SUTUNLARI = (("gecikti", "Gecikenler"), ("yaklasan", f"{YAKLASAN_GUN} gün içinde"), ("", "Planlananlar"))
ONAY_SUTUNU = ("onay", "Onay bekleyen projeler")
# Sipariş kartının ve ürün sayfasının başındaki "Siparişin durumu": ürünlerin iş emri durumu
URUN_DURUMLARI = {
    "kapali": "İş emri tamamlandı",
    "kismen": "Kısmen tamamlandı",
    "acik": "İş emri açık",
    "yok": "İş emri açılmadı",
    "sevk": "Sevk edildi",
}


def urun_is_emri_sinifi(asama, kalem, ie):
    """Ürünün iş emri durumu sınıfı (URUN_DURUMLARI anahtarı); ie: ürüne dağıtılmış iş emri ya da None."""
    if asama == "sevk_edildi" or kapali_mi(kalem):
        return "sevk"
    return is_emri_durumu(ie)[1] if ie else "yok"


def siparis_durum_ozeti(vt, siparis):
    """Siparişteki ürünlerin iş emri durumları ve PP'ye takılacak kalemlerin montaj durumları:
    {"toplam", "urunler": [(sınıf, ad, adet)], "eklentiler": [(durum, ad, adet)]}."""
    urunler = Counter()
    for u in vt.execute(
        "SELECT u.asama, k.erp_durum, k.erp_genel_durum, i.durum, i.gercek_miktar FROM urunler u"
        " JOIN siparis_kalemleri k ON k.id = u.kalem_id LEFT JOIN is_emirleri i ON i.id = u.is_emri_id"
        " WHERE k.siparis_id = ? AND COALESCE(k.erp_durum, '') != ? AND k.tur IN ('kart', 'servis')",
        (siparis["id"], IPTAL),
    ):
        ie = {"durum": u["durum"], "gercek_miktar": u["gercek_miktar"]} if u["durum"] else None
        urunler[urun_is_emri_sinifi(u["asama"], u, ie)] += 1
    eklentiler = Counter(
        k["montaj_durumu"] or VARSAYILAN_EKLENTI_DURUMU
        for k in vt.execute(
            "SELECT urun_kodu, montaj_durumu FROM siparis_kalemleri WHERE siparis_id = ? AND COALESCE(erp_durum, '') != ?",
            (siparis["id"], IPTAL),
        )
        if pp_eklentisi_mi(k["urun_kodu"], siparis["tip"])
    )
    return {
        "toplam": sum(urunler.values()),
        "urunler": [(s, ad, urunler[s]) for s, ad in URUN_DURUMLARI.items() if urunler[s]],
        "eklentiler": [(d, ad, eklentiler[d]) for d, ad in EKLENTI_DURUMLARI.items() if eklentiler[d]],
    }


def siparis_durumu(kalemler):
    etkin = [k for k in kalemler if k["erp_durum"] != IPTAL]
    if not etkin:
        return "iptal"
    acik = [k for k in etkin if not kapali_mi(k)]
    if not acik:
        return "kapali"
    if all(k["erp_durum"] == BEKLEMEDE for k in acik):
        return "onay_bekliyor"
    return "acik"


def teslim_bilgisi(teslim, bugun=None):
    """Teslim tarihine kalan süre: (metin, sınıf) ya da None."""
    if not teslim:
        return None
    gun = (date.fromisoformat(teslim) - (bugun or date.today())).days
    if gun < 0:
        return f"{-gun} gün geçti", "gecikti"
    if gun == 0:
        return "Bugün", "yaklasan"
    return f"{gun} gün kaldı", "yaklasan" if gun <= YAKLASAN_GUN else ""


def yakin_revizyon(zaman):
    """Revizyon (yükleme zamanı 'YYYY-AA-GG SS:DD:ss') son REVIZYON_GUN gün içindeyse True."""
    return bool(zaman) and date.fromisoformat(zaman[:10]) >= date.today() - timedelta(days=REVIZYON_GUN)


def ozetle(siparis, kalemler, son_revizyon=None, urun_idleri=None):
    """Listede ve kartın başında gösterilen özet. urun_idleri: kalem → ürün kartları (ürün kutucuğunun adresi için)."""
    gorunen = [k for k in kalemler if k["tur"] != "hizmet"]
    durum = siparis_durumu(gorunen)
    if durum in ("acik", "onay_bekliyor") and not siparis["erp_listede"]:
        durum = "listede_yok"  # en son yüklenen ERP listesinde yok
    etkin = [k for k in gorunen if k["erp_durum"] != IPTAL] or gorunen
    acik = [k for k in etkin if not kapali_mi(k)]
    kesin = [k for k in acik if k["erp_durum"] != BEKLEMEDE]
    teslim = min((k["teslim_tarihi"] for k in (kesin or acik or etkin) if k["teslim_tarihi"]), default=None)
    urunler = Counter()
    kartlar = defaultdict(list)
    for kalem in etkin:
        if kalem["aile"]:
            urunler[kalem["aile"]] += round(kalem["miktar"] or 0)
            kartlar[kalem["aile"]].extend((urun_idleri or {}).get(kalem["id"], []))
    return {
        "siparis": siparis,
        "durum": durum,
        "teslim": teslim,
        "kalan": teslim_bilgisi(teslim) if durum in ("acik", "onay_bekliyor") else None,
        "son_sevk": max((k["son_sevk_tarihi"] for k in etkin if k["son_sevk_tarihi"]), default=None),
        "urunler": [(aile, urunler[aile]) for aile in AILE_SIRASI if urunler[aile]],
        "diger_kalem": sum(1 for k in etkin if not k["aile"]),
        "aileler": set(urunler),
        # Siparişte o aileden tek makine varsa ürün kutucuğu doğrudan onun sayfasını açar.
        "tek_urun": {aile: idler[0] for aile, idler in kartlar.items() if len(idler) == 1},
        "revizyon": son_revizyon if yakin_revizyon(son_revizyon) else None,
        # Haftalık takvimden gelen tarih süzgeci için: açık makine kalemlerinin teslim tarihleri
        "makine_teslimleri": {k["teslim_tarihi"] for k in kesin if k["aile"] in ANA_URUNLER and k["teslim_tarihi"]},
    }


def tum_ozetler(vt):
    kalemler = defaultdict(list)
    for kalem in vt.execute("SELECT * FROM siparis_kalemleri"):
        kalemler[kalem["siparis_id"]].append(kalem)
    son_revizyon = dict(vt.execute(
        "SELECT r.siparis_id, MAX(y.zaman) FROM siparis_revizyonlari r"
        " JOIN erp_yuklemeler y ON y.id = r.yukleme_id GROUP BY r.siparis_id"
    ).fetchall())
    urun_idleri = defaultdict(list)
    for urun in vt.execute("SELECT id, kalem_id FROM urunler ORDER BY adet_sira"):
        urun_idleri[urun["kalem_id"]].append(urun["id"])
    return [
        ozetle(s, kalemler[s["id"]], son_revizyon.get(s["id"]), urun_idleri)
        for s in vt.execute("SELECT * FROM siparisler")
    ]


def acik_mi(ozet):
    return ozet["durum"] in ("acik", "onay_bekliyor")


def _tarih_araligi(bas, bit):
    """Haftalık takvimden gelen ?bas=…&bit=… (YYYY-AA-GG); bit yoksa sonu açık."""
    try:
        bas = date.fromisoformat(bas).isoformat()
        bit = date.fromisoformat(bit).isoformat() if bit else "9999-12-31"
    except ValueError:
        return None
    return bas, bit


def son_siparis_yuklemesi(vt):
    return vt.execute("SELECT MAX(zaman) FROM erp_yuklemeler WHERE tur = 'siparis_talepleri'").fetchone()[0]


def sira_anahtari(ozet):
    if ozet["durum"] in ("acik", "onay_bekliyor"):
        return 0, ozet["teslim"] or "9999", ozet["siparis"]["siparis_no"]
    son_sevk = -date.fromisoformat(ozet["son_sevk"]).toordinal() if ozet["son_sevk"] else 0
    return 1, son_sevk, ozet["siparis"]["siparis_no"]


def _arama(vt, metin):
    desen = f"%{metin}%"
    return {
        satir[0]
        for satir in vt.execute(
            "SELECT DISTINCT s.id FROM siparisler s"
            " LEFT JOIN siparis_kalemleri k ON k.siparis_id = s.id LEFT JOIN urunler u ON u.kalem_id = k.id"
            " WHERE s.siparis_no LIKE ? OR s.musteri LIKE ? OR k.urun_kodu LIKE ? OR k.urun_adi LIKE ?"
            " OR k.bagli_is_emri_no LIKE ? OR u.seri_no LIKE ?",
            (desen,) * 6,
        )
    }


@bp.route("/siparisler")
def liste():
    secim = {alan: request.args.get(alan, "").strip() for alan in ("ara", "durum", "tip", "aile", "teslim", "bas", "bit")}
    secim["durum"] = secim["durum"] if secim["durum"] in DURUM_SUZGECLERI else "acik"
    teslim_sutunu = dict(TESLIM_SUTUNLARI).get(secim["teslim"]) if secim["teslim"] else None
    vt = baglanti()
    ozetler = tum_ozetler(vt)
    toplam = len(ozetler)

    # Yedek parça siparişleri kendi ekranında izlenir; burada yalnızca tipiyle seçilince görünür.
    if secim["tip"] != "yedek_parca":
        ozetler = [o for o in ozetler if o["siparis"]["tip"] != "yedek_parca"]
    tarih_araligi = _tarih_araligi(secim["bas"], secim["bit"])
    if tarih_araligi:
        bas, bit = tarih_araligi
        ozetler = [o for o in ozetler if any(bas <= t <= bit for t in o["makine_teslimleri"])]
    if secim["ara"]:
        bulunan = _arama(vt, secim["ara"])
        ozetler = [o for o in ozetler if o["siparis"]["id"] in bulunan]
    if secim["tip"]:
        ozetler = [o for o in ozetler if o["siparis"]["tip"] == secim["tip"]]
    if secim["aile"]:
        aileler = VIBROHAMMER if secim["aile"] == "vibrohammer" else {secim["aile"]}
        ozetler = [o for o in ozetler if o["aileler"] & aileler]

    durumlar = Counter(o["durum"] for o in ozetler)
    sayilar = {**durumlar, "acik": durumlar["acik"] + durumlar["onay_bekliyor"], "tumu": len(ozetler)}
    if secim["durum"] == "acik":
        ozetler = [o for o in ozetler if o["durum"] in ("acik", "onay_bekliyor")]
    elif secim["durum"] != "tumu":
        ozetler = [o for o in ozetler if o["durum"] == secim["durum"]]

    ozetler.sort(key=sira_anahtari)
    sutunlar = None
    if secim["durum"] in ("acik", "onay_bekliyor"):
        kesin = [o for o in ozetler if o["durum"] == "acik"]
        sutunlar = [
            (sinif, ad, [o for o in kesin if (o["kalan"][1] if o["kalan"] else "") == sinif])
            for sinif, ad in TESLIM_SUTUNLARI
            if secim["durum"] == "acik" and (teslim_sutunu is None or sinif == secim["teslim"])
        ]
        if teslim_sutunu is None:
            sutunlar.append((*ONAY_SUTUNU, [o for o in ozetler if o["durum"] == "onay_bekliyor"]))
    return render_template(
        "siparisler.html",
        ozetler=ozetler,
        sutunlar=sutunlar,
        teslim_sutunu=teslim_sutunu,
        tarih_araligi=tarih_araligi,
        toplam=toplam,
        sayilar=sayilar,
        secim=secim,
        son_yukleme=son_siparis_yuklemesi(vt),
        DURUMLAR=DURUMLAR,
        DURUM_SUZGECLERI=DURUM_SUZGECLERI,
        TIPLER=TIPLER,
        AILE_SUZGECLERI=AILE_SUZGECLERI,
    )


@bp.route("/siparisler/<path:siparis_no>")
def kart(siparis_no):
    vt = baglanti()
    siparis = vt.execute("SELECT * FROM siparisler WHERE siparis_no = ?", (siparis_no,)).fetchone()
    if siparis is None:
        abort(404)
    kalemler = vt.execute(
        "SELECT k.*, y.zaman AS veri_zamani FROM siparis_kalemleri k"
        " LEFT JOIN erp_yuklemeler y ON y.id = k.son_yukleme_id WHERE k.siparis_id = ? ORDER BY k.sira_no",
        (siparis["id"],),
    ).fetchall()
    urunler = defaultdict(list)
    for urun in vt.execute(
        "SELECT u.* FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
        " WHERE k.siparis_id = ? ORDER BY u.adet_sira",
        (siparis["id"],),
    ):
        urunler[urun["kalem_id"]].append(urun)

    revizyonlar = vt.execute(
        "SELECT r.*, y.zaman, k.urun_kodu FROM siparis_revizyonlari r JOIN erp_yuklemeler y ON y.id = r.yukleme_id"
        " LEFT JOIN siparis_kalemleri k ON k.siparis_id = r.siparis_id AND k.sira_no = r.sira_no"
        " WHERE r.siparis_id = ? ORDER BY r.id DESC",
        (siparis["id"],),
    ).fetchall()
    revize_siralar = {r["sira_no"] for r in revizyonlar if yakin_revizyon(r["zaman"])}

    is_emirleri = vt.execute(
        "SELECT * FROM is_emirleri WHERE siparis_id = ? ORDER BY acilis_tarihi, is_emri_no", (siparis["id"],)
    ).fetchall()
    kalem_is_emirleri = defaultdict(list)
    for ie in is_emirleri:
        if ie["kalem_id"]:
            kalem_is_emirleri[ie["kalem_id"]].append(ie)
    is_emri_haritasi = {ie["id"]: ie for ie in is_emirleri}

    # "Siparişin durumu" kutusundan gelinince yalnızca o durumdaki kalemler: ?goster=ud-acik ya da ek-talep_acildi
    goster = request.args.get("goster", "")
    ud_suzgec = goster[3:] if goster.startswith("ud-") and goster[3:] in URUN_DURUMLARI else None
    ek_suzgec = goster[3:] if goster.startswith("ek-") and goster[3:] in EKLENTI_DURUMLARI else None

    ozet = ozetle(siparis, kalemler, revizyonlar[0]["zaman"] if revizyonlar else None)
    bolumler = {aile: [] for aile in AILE_SIRASI}
    servis, listelenen, iptal_edilenler = [], [], []
    for kalem in kalemler:
        if kalem["tur"] == "hizmet":
            continue
        gorunen = urunler[kalem["id"]]
        if ud_suzgec:
            gorunen = [u for u in gorunen
                       if urun_is_emri_sinifi(u["asama"], kalem, is_emri_haritasi.get(u["is_emri_id"])) == ud_suzgec]
            if not gorunen or kalem["erp_durum"] == IPTAL:
                continue
        if ek_suzgec and not (pp_eklentisi_mi(kalem["urun_kodu"], siparis["tip"]) and kalem["erp_durum"] != IPTAL
                              and (kalem["montaj_durumu"] or VARSAYILAN_EKLENTI_DURUMU) == ek_suzgec):
            continue
        satir = {
            "kalem": kalem,
            "urunler": gorunen,
            "renk": renk(kalem["aciklama"]),
            "pp": kalem["aile"] == "PP",
            "yag": yag(kalem["aciklama"]) if kalem["aile"] == "PP" else None,
            "kapali": kapali_mi(kalem),
            "dis_tedarik": dis_tedarik_mi(kalem["urun_kodu"]),
            "revize": kalem["sira_no"] in revize_siralar,
            "is_emirleri": kalem_is_emirleri[kalem["id"]],
            # Ürün kartlarına dağıtılmamış iş emirleri (üretimsiz kapatılan, adetten fazla açılan) ilk üründe görünür.
            "dagitilmamis": [ie for ie in kalem_is_emirleri[kalem["id"]]
                             if ie["id"] not in {u["is_emri_id"] for u in urunler[kalem["id"]]}],
            # Makinelerin numaraları (şasi no, motor seri no): girilmiş ya da ERP'den okunmuş; yoksa "yok" yazar
            "numaralar": {u["id"]: urun_numaralari(vt, u, kalem["aile"], siparis["id"]) for u in urunler[kalem["id"]]},
            "eklenti": pp_eklentisi_mi(kalem["urun_kodu"], siparis["tip"]),
        }
        if kalem["erp_durum"] == IPTAL and ozet["durum"] != "iptal":
            # Devam eden siparişte iptal edilmiş (çoğu zaman yanlış girilip düzeltilmiş) satır
            iptal_edilenler.append(satir)
        elif kalem["tur"] == "kart":
            bolumler[kalem["aile"]].append(satir)
        elif kalem["tur"] == "servis":
            servis.append(satir)
        else:
            listelenen.append(satir)

    return render_template(
        "siparis_karti.html",
        ozet=ozet,
        bolumler=[(aile, satirlar) for aile, satirlar in bolumler.items() if satirlar],
        servis=servis,
        listelenen=listelenen,
        iptal_edilenler=iptal_edilenler,
        revizyonlar=revizyonlar,
        REVIZYON_ADLARI=REVIZYON_ADLARI,
        is_emri_haritasi=is_emri_haritasi,
        alt_is_emirleri=[ie for ie in is_emirleri if not ie["kalem_id"]],
        # Durum kutusundan seçilen: (seçim, adı) ya da None
        suzgec=(goster, URUN_DURUMLARI.get(ud_suzgec) or EKLENTI_DURUMLARI.get(ek_suzgec)) if ud_suzgec or ek_suzgec else None,
        is_emri_yuklu=vt.execute("SELECT 1 FROM is_emirleri LIMIT 1").fetchone() is not None,
        is_emri_durumu=is_emri_durumu,
        urun_is_emri_sinifi=urun_is_emri_sinifi,
        durum_ozeti=siparis_durum_ozeti(vt, siparis),
        REVIZYON_GUN=REVIZYON_GUN,
        eksik=eksik_siralar(k["sira_no"] for k in kalemler),
        son_veri=max((k["veri_zamani"] for k in kalemler if k["veri_zamani"]), default=None),
        DURUMLAR=DURUMLAR,
        TIPLER=TIPLER,
        AILE_ADLARI=AILE_ADLARI,
    )


@bp.route("/siparisler/kalem/<int:kalem_id>/montaj", methods=["POST"])
@ekip_gerekli
def montaj_durumu(kalem_id):
    """PP'ye takılan kalemin (kablosuz kumanda seti, uzaktan erişim modülü) montaj durumunu kaydeder."""
    durum = request.form.get("montaj_durumu")
    if durum not in EKLENTI_DURUMLARI:
        abort(400)
    vt = baglanti()
    kalem = vt.execute(
        "SELECT k.id, s.siparis_no FROM siparis_kalemleri k JOIN siparisler s ON s.id = k.siparis_id WHERE k.id = ?",
        (kalem_id,),
    ).fetchone()
    if kalem is None:
        abort(404)
    with vt:
        vt.execute(
            "UPDATE siparis_kalemleri SET montaj_durumu = ?, montaj_degisme = ?, montaj_degistiren_id = ? WHERE id = ?",
            (durum, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), g.kullanici["id"], kalem_id),
        )
    sonra = request.form.get("sonra")
    return redirect(guvenli_adres(sonra) if sonra else url_for(".kart", siparis_no=kalem["siparis_no"]))
