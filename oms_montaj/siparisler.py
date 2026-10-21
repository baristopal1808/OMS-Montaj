"""Siparişler: ana ekrandaki liste ve sipariş kartı.

Siparişin durumu ve teslim tarihi kalemlerinden hesaplanır: iptal edilmemiş
kalemlerin hepsi ERP'de kapandıysa sipariş "ERP'de kapandı", açık kalemlerin
hepsi onay bekliyorsa "Onay bekliyor" sayılır. Teslim tarihi açık kalemlerin
en yakın uzlaşılan sevk tarihidir; onay bekleyen kalemler kesin olmadığından
başka açık kalem varsa sayılmaz. Onay bekleyen siparişler listede teslim
sütunlarına değil, en sağdaki ayrı sütuna dizilir.
"""

from collections import Counter, defaultdict
from datetime import date

from flask import Blueprint, abort, render_template, request

from .erp_aktarim import BEKLEMEDE, IPTAL, eksik_siralar, kapali_mi
from .urun_kurallari import AILE_ADLARI, AILE_SIRASI, ANA_URUNLER, VIBROHAMMER, dis_tedarik_mi, renk, yag
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
# Açık siparişler bu üç sütunda, her sütunda teslim tarihine göre yukarıdan aşağı dizilir.
TESLIM_SUTUNLARI = (("gecikti", "Gecikenler"), ("yaklasan", f"{YAKLASAN_GUN} gün içinde"), ("", "Planlananlar"))
ONAY_SUTUNU = ("onay", "Onay bekleyen projeler")


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


def ozetle(siparis, kalemler):
    """Listede ve kartın başında gösterilen özet."""
    gorunen = [k for k in kalemler if k["tur"] != "hizmet"]
    durum = siparis_durumu(gorunen)
    if durum in ("acik", "onay_bekliyor") and not siparis["erp_listede"]:
        durum = "listede_yok"  # en son yüklenen ERP listesinde yok
    etkin = [k for k in gorunen if k["erp_durum"] != IPTAL] or gorunen
    acik = [k for k in etkin if not kapali_mi(k)]
    kesin = [k for k in acik if k["erp_durum"] != BEKLEMEDE]
    teslim = min((k["teslim_tarihi"] for k in (kesin or acik or etkin) if k["teslim_tarihi"]), default=None)
    urunler = Counter()
    for kalem in etkin:
        if kalem["aile"]:
            urunler[kalem["aile"]] += round(kalem["miktar"] or 0)
    return {
        "siparis": siparis,
        "durum": durum,
        "teslim": teslim,
        "kalan": teslim_bilgisi(teslim) if durum in ("acik", "onay_bekliyor") else None,
        "son_sevk": max((k["son_sevk_tarihi"] for k in etkin if k["son_sevk_tarihi"]), default=None),
        "urunler": [(aile, urunler[aile]) for aile in AILE_SIRASI if urunler[aile]],
        "diger_kalem": sum(1 for k in etkin if not k["aile"]),
        "aileler": set(urunler),
        # Haftalık takvimden gelen tarih süzgeci için: açık makine kalemlerinin teslim tarihleri
        "makine_teslimleri": {k["teslim_tarihi"] for k in kesin if k["aile"] in ANA_URUNLER and k["teslim_tarihi"]},
    }


def tum_ozetler(vt):
    kalemler = defaultdict(list)
    for kalem in vt.execute("SELECT * FROM siparis_kalemleri"):
        kalemler[kalem["siparis_id"]].append(kalem)
    return [ozetle(s, kalemler[s["id"]]) for s in vt.execute("SELECT * FROM siparisler")]


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

    ozet = ozetle(siparis, kalemler)
    bolumler = {aile: [] for aile in AILE_SIRASI}
    servis, listelenen, iptal_edilenler = [], [], []
    for kalem in kalemler:
        if kalem["tur"] == "hizmet":
            continue
        satir = {
            "kalem": kalem,
            "urunler": urunler[kalem["id"]],
            "renk": renk(kalem["aciklama"]),
            "pp": kalem["aile"] == "PP",
            "yag": yag(kalem["aciklama"]) if kalem["aile"] == "PP" else None,
            "kapali": kapali_mi(kalem),
            "dis_tedarik": dis_tedarik_mi(kalem["urun_kodu"]),
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
        eksik=eksik_siralar(k["sira_no"] for k in kalemler),
        son_veri=max((k["veri_zamani"] for k in kalemler if k["veri_zamani"]), default=None),
        DURUMLAR=DURUMLAR,
        TIPLER=TIPLER,
        AILE_ADLARI=AILE_ADLARI,
    )
