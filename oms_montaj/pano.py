"""Siparişler panosu (kullanıcı kararları, 02/11/2026): Planner'daki gibi aşama sütunlu pano.

Sütunlar Planner'daki sırayla: Siparişler · Sevke hazır / Stok · Son montaj & test · Montajı devam edenler ·
Malzeme hazırlık. Uygulamanın dokuz aşaması bu beş sütuna toplanır; kartın üstünde asıl aşama etiket olarak
yazar. Siparişler sütununda sipariş başına bir kart durur (iş emri açılmamış makineleriyle); bir makinenin iş
emri açılınca kendi kartıyla ilerler. Sevk edilenler son sütunun altında kapalı durur.

Kart olan makineler: SVR, OVR, PP, OVF, WD ve servis (bakım-onarım). Çene ve kiriş ayrı kart olmaz, vibro
kartında kısa satır olarak görünür; siparişte vibro yoksa kendi kartı olur. Hortum seti gibi aksesuarlar
siparişteki vibronun (yoksa makinenin) kartında görünür; güç ünitesinin opsiyonel ekipmanları güç ünitesinde.
Kart Planner'daki kontrol listesi yerine bilgi gösterir; altta teslim tarihi ve atanan kişi. Etikete (PP,
SVR-NF, Test…) ya da kişiye tıklayınca pano ona süzülür; birden çok etiket birlikte seçilebilir.

Stoktaki makineler (stok.py) "Sevke hazır / Stok" sütununda "Stok" etiketiyle durur; çene ve kiriş stokları
yalnızca Stok ekranında listelenir (kullanıcı, 03/11/2026). Siparişler sütunundaki kartta, iş emri bekleyen
makineden stokta varsa "Stokta var" yazar.
"""

import re
from collections import defaultdict
from datetime import date, timedelta

from .asamalar import ASAMALAR, SIRA
from .atama import atama_grubu, kisi, varsayilan_atananlar
from .erp_aktarim import IPTAL, kapali_mi
from .form_kurallari import FORM_TURLERI, basilan_formlar, forma_tabi_mi
from .numaralar import TEYITSIZ, urun_numaralari
from .siparisler import teslim_bilgisi
from .stok import DEPOLAR, atanabilecekler, stok_kartlari, stok_sayilari, test_durumu
from .urun_kurallari import (
    ANA_URUNLER, PP_EKLENTILERI, VARSAYILAN_EKLENTI_DURUMU, VIBROHAMMER, model, onek, pp_eklentisi_mi, renk, yag_metni,
)
from .uyarilar import eksik_ozetleri


SUTUNLAR = (
    ("siparisler", "Siparişler", ("siparis",)),
    ("sevke_hazir", "Sevke hazır / Stok", ("sevke_hazir", "stokta")),
    ("son_montaj", "Son montaj & test", ("montaj_tamamlandi", "teste_hazir", "test", "temizlik")),
    ("montaj", "Montajı devam edenler", ("montaj",)),
    ("malzeme", "Malzeme hazırlık", ("malzeme_hazirlik",)),
)
SUTUN = {asama: anahtar for anahtar, _, asamalar in SUTUNLAR for asama in asamalar}
TEK_ASAMALI = {anahtar for anahtar, _, asamalar in SUTUNLAR if len(asamalar) == 1}
SEVK_GUN = 30  # "Sevk edilenler" bölümünde son bu kadar günde sevk edilenler
BAKIM = "Bakım & onarım"
SIPARIS, SICAK, STOK = "Sipariş", "Sıcak sipariş", "Stok"
SICAK_GUN = 30  # talepten teslime bu kadar gün ya da daha az olan sipariş sıcaktır (kullanıcı, 02/11/2026)
# Kartın üstündeki aşama etiketi (birden çok aşamalı sütunlarda)
ASAMA_ETIKETLERI = {"test": "Test aşamasında", "temizlik": "Temizlik aşamasında"}
YARDIMCI = ("Çene", "Kiriş")  # vibronun kartında kısa satır olarak görünür
HAZIR_ASAMA = SIRA["montaj_tamamlandi"]  # çene ve kirişte bu aşama ve sonrası "hazır"


def _urunler(vt, siparis_id=None):
    kosul = " AND k.siparis_id = ?" if siparis_id is not None else ""
    return vt.execute(
        "SELECT u.*, k.siparis_id, k.sira_no, k.urun_kodu, k.urun_adi, k.aile, k.tur, k.aciklama, k.teslim_tarihi,"
        " k.erp_durum, k.erp_genel_durum, k.son_sevk_tarihi, k.miktar, s.siparis_no, s.musteri, s.tip,"
        " i.is_emri_no FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
        " JOIN siparisler s ON s.id = k.siparis_id LEFT JOIN is_emirleri i ON i.id = u.is_emri_id"
        f" WHERE COALESCE(k.erp_durum, '') != ?{kosul} ORDER BY k.sira_no, u.adet_sira",
        (IPTAL,) if siparis_id is None else (IPTAL, siparis_id),
    ).fetchall()


def siparis_bagli_kalemleri(vt, siparis_id):
    """Bir siparişin makinelerinin yardımcı kalemleri (ürün sayfası için): bagli_kalemler'in sonucu."""
    kalemler = vt.execute(
        "SELECT k.*, s.tip FROM siparis_kalemleri k JOIN siparisler s ON s.id = k.siparis_id WHERE k.siparis_id = ?"
        " ORDER BY k.sira_no",
        (siparis_id,),
    ).fetchall()
    return bagli_kalemler(_urunler(vt, siparis_id), kalemler)


def _kisa_ad(ad):
    """Aksesuarın kısa adı: 'Hortum Seti - 30 m' → 'Hortum Seti'."""
    return re.split(r"\s+[-–(\[]", (ad or "").strip())[0][:28] or "Aksesuar"


def bagli_kalemler(urunler, kalemler):
    """Makinelerin kartında görünen yardımcı kalemler: {makine ürün id: {"cene": [ürün], "kiris": [ürün],
    "aksesuar": [kalem]}}. urunler: bir siparişin ürünleri; kalemler: aynı siparişin kalemleri. Çene ve kiriş
    siparişte vibro varsa vibroya (kiriş, adında modeli geçen vibroya), aksesuarlar vibroya, vibro yoksa
    siparişteki ilk makineye bağlanır."""
    vibrolar = [u for u in urunler if u["aile"] in VIBROHAMMER and u["tur"] == "kart"]
    makineler = vibrolar or [u for u in urunler if u["aile"] in ANA_URUNLER and u["tur"] == "kart"]
    if not makineler:
        return {}
    sonuc = defaultdict(lambda: {"cene": [], "kiris": [], "aksesuar": []})
    for u in urunler:
        if u["aile"] not in YARDIMCI or not vibrolar:
            continue
        hedef = vibrolar[0]
        if u["aile"] == "Kiriş":
            ad = (u["urun_adi"] or "").upper()
            hedef = next((v for v in vibrolar if model_kodu(v["urun_kodu"]) in ad), hedef)
        sonuc[hedef["id"]]["cene" if u["aile"] == "Çene" else "kiris"].append(u)
    for k in kalemler:
        if k["tur"] == "aksesuar" and k["erp_durum"] != IPTAL and not pp_eklentisi_mi(k["urun_kodu"], k["tip"]):
            sonuc[makineler[0]["id"]]["aksesuar"].append(k)
    return dict(sonuc)


def model_kodu(urun_kodu):
    """'SVR-50-NF-BSP' → 'SVR-50-NF' (kirişin adında böyle geçer: '[SVR-50-NF] - H Tipi')."""
    return re.sub(r"-BSP$", "", (urun_kodu or "").upper())


def bagli_satiri(bagli):
    """Vibro kartındaki kısa satır: [(metin, hazır mı)] — 'Çene 2', 'Kiriş', 'Hortum Seti'."""
    parcalar = []
    for anahtar, ad in (("cene", "Çene"), ("kiris", "Kiriş")):
        liste = bagli.get(anahtar, [])
        if liste:
            hazir = sum(1 for u in liste if u["asama"] in ASAMALAR and SIRA[u["asama"]] >= HAZIR_ASAMA)
            parcalar.append((f"{ad} {len(liste)}" if len(liste) > 1 else ad, hazir == len(liste)))
    adlar = list(dict.fromkeys(_kisa_ad(k["urun_adi"]) for k in bagli.get("aksesuar", [])))
    parcalar += [(ad, False) for ad in adlar[:3]]
    if len(adlar) > 3:
        parcalar.append((f"+{len(adlar) - 3} kalem", False))
    return parcalar


def _etiket(ad, sinif="", aile=None):
    """Kartın etiketi; aile, etiketin rengini verir (grafiklerdeki aile rengi)."""
    return {"ad": ad, "sinif": sinif, "aile": aile}


def pano_verisi(vt, ozetler, secim):
    """Panonun sütunları ve kartları. ozetler: siparisler.tum_ozetler (süzülmüş); secim: etiket, kisi, ara
    sonucu (siparis_idleri), teslim, tarih aralığı."""
    acik = {o["siparis"]["id"]: o for o in ozetler if o["durum"] == "acik" and o["siparis"]["tip"] != "yedek_parca"}
    atananlar = varsayilan_atananlar(vt)
    urunler = defaultdict(list)
    for u in _urunler(vt):
        urunler[u["siparis_id"]].append(u)
    kalemler = defaultdict(list)
    for k in vt.execute("SELECT k.*, s.tip FROM siparis_kalemleri k JOIN siparisler s ON s.id = k.siparis_id"):
        kalemler[k["siparis_id"]].append(k)
    motorlar = {r["urun_kodu"]: r for r in vt.execute("SELECT * FROM motor_bilgileri")}
    basilan = basilan_formlar(vt)
    ie_nolari = [u["is_emri_no"] for liste in urunler.values() for u in liste if u["is_emri_no"]]
    eksikler = eksik_ozetleri(vt, ie_nolari) if ie_nolari else {}
    bugun = date.today().isoformat()
    sevk_siniri = (date.today() - timedelta(days=SEVK_GUN)).isoformat()

    kartlar = {anahtar: [] for anahtar, _, _ in SUTUNLAR}
    stokta = stok_sayilari(vt)
    sevk_edilenler = []
    for siparis_id, liste in urunler.items():
        ozet = acik.get(siparis_id)
        bagli = bagli_kalemler(liste, kalemler[siparis_id])
        vibrolu = any(u["aile"] in VIBROHAMMER and u["tur"] == "kart" for u in liste)
        siparis_bekleyenler = []
        for u in liste:
            kartli = u["tur"] == "servis" or u["aile"] in ANA_URUNLER or (u["aile"] in YARDIMCI and not vibrolu)
            if not kartli:
                continue
            sevk = u["asama"] == "sevk_edildi" or kapali_mi(u)
            if sevk:
                if sevk_siniri <= (u["son_sevk_tarihi"] or "") <= bugun and u["tip"] != "yedek_parca":
                    sevk_edilenler.append(u)
                continue
            if ozet is None:
                continue
            if u["asama"] == "siparis":
                siparis_bekleyenler.append(u)
                continue
            kart = _urun_karti(vt, u, ozet, bagli.get(u["id"], {}), motorlar, basilan, eksikler, atananlar,
                               kalemler[siparis_id])
            kartlar[SUTUN.get(u["asama"], "malzeme")].append(kart)
        if ozet and (siparis_bekleyenler or not any(
                u["tur"] == "servis" or u["aile"] in ANA_URUNLER or u["aile"] in YARDIMCI for u in liste)):
            kartlar["siparisler"].append(_siparis_karti(ozet, liste, siparis_bekleyenler, atananlar, stokta))
    # Ürünü olmayan (yalnızca aksesuar) açık siparişler de Siparişler sütununda
    for siparis_id, ozet in acik.items():
        if siparis_id not in urunler:
            kartlar["siparisler"].append(_siparis_karti(ozet, [], [], atananlar, stokta))
    # Stoktaki makineler (çene ve kiriş Stok ekranında)
    for u in stok_kartlari(vt):
        if u["aile"] in ANA_URUNLER:
            kartlar["sevke_hazir"].append(_stok_karti(vt, u, motorlar, atananlar))

    secili = set(secim.get("etiketler") or ())
    kisi = secim.get("kisi")
    siparis_idleri = secim.get("siparis_idleri")
    teslim = secim.get("teslim")
    aralik = secim.get("tarih_araligi")

    def gorunur(kart):
        if secili and not secili <= {e["ad"] for e in kart["etiketler"]}:
            return False
        if kisi and kisi not in {k["id"] for k in kart["atananlar"]}:
            return False
        if siparis_idleri is not None and kart["siparis_id"] not in siparis_idleri:
            return False
        if teslim and (kart["kalan"][1] if kart["kalan"] else "") != teslim:
            return False
        if aralik and not (kart["teslim"] and aralik[0] <= kart["teslim"] <= aralik[1]):
            return False
        return True

    sutunlar = []
    for anahtar, ad, _ in SUTUNLAR:
        gorunen = sorted((k for k in kartlar[anahtar] if gorunur(k)), key=lambda k: (k["teslim"] or "9999", k["baslik"]))
        sutunlar.append({"anahtar": anahtar, "ad": ad, "kartlar": gorunen})
    sevk_edilenler.sort(key=lambda u: u["son_sevk_tarihi"] or "", reverse=True)
    return {"sutunlar": sutunlar, "sevk_edilenler": sevk_edilenler, "toplam": sum(len(v) for v in kartlar.values())}


def _kisiler(atananlar, aile):
    return [kisi(k) for k in atananlar.get(atama_grubu(aile), [])]


def _kaynak_etiketi(ozet):
    """Siparişe bağlı kartın etiketi: talepten teslime SICAK_GUN gün ya da daha az ise "Sıcak sipariş"."""
    talep, teslim = ozet["siparis"]["talep_tarihi"], ozet["teslim"]
    if talep and teslim and (date.fromisoformat(teslim) - date.fromisoformat(talep[:10])).days <= SICAK_GUN:
        return _etiket(SICAK, "sicak")
    return _etiket(SIPARIS, "kaynak")


def _cene_etiketleri(ceneler):
    """Çenelerin etiketleri, kodlarının önekiyle: KCN, SCN, ACN."""
    return [_etiket(o, "aile", "Çene") for o in dict.fromkeys(onek(u["urun_kodu"]) for u in ceneler)]


def _eklenti_cumlesi(ad, durum):
    """Opsiyonel ekipmanın tek cümlelik durumu ve rengi: 'Uzaktan erişim modülü montajı tamamlandı' (yeşil)."""
    return {
        "montaj_edildi": (f"{ad} montajı tamamlandı", "hazir"),
        "montaj_edilmedi": (f"{ad} geldi, montaj bekliyor", "bekliyor"),
        "talep_acildi": (f"{ad} bekleniyor (sipariş talebi açıldı)", "uyari-sari"),
    }.get(durum, (f"{ad} için sipariş talebi açılacak", "uyari"))


def _urun_karti(vt, u, ozet, bagli, motorlar, basilan, eksikler, atananlar, kalemler):
    """Ürün kartı. Bilgiler her kartta aynı sırada ve tek satırda: [(ad ya da None, değer, sınıf)]; adı
    olmayan satır tek cümledir (opsiyonel ekipman)."""
    aile = u["aile"]
    servis = u["tur"] == "servis"
    etiketler = []
    if aile:
        etiketler.append(_etiket(model(u["urun_kodu"]) if aile in ANA_URUNLER else onek(u["urun_kodu"]), "aile", aile))
    etiketler += _cene_etiketleri(bagli.get("cene", []))
    etiketler.append(_kaynak_etiketi(ozet))
    if SUTUN.get(u["asama"], "malzeme") not in TEK_ASAMALI:
        etiketler.append(_etiket(ASAMA_ETIKETLERI.get(u["asama"], ASAMALAR[u["asama"]]), "asama"))
    if servis:
        etiketler.append(_etiket(BAKIM, "bakim"))
    motor = motorlar.get(u["urun_kodu"]) if aile == "PP" else None
    bilgiler = []
    if u["seri_no"] and servis:
        bilgiler.append(("Seri no", u["seri_no"], ""))
    for alan, ad, deger, kaynak in urun_numaralari(vt, u, aile, u["siparis_id"], u["urun_kodu"]):
        bilgiler.append((ad, (deger + (" !" if kaynak in TEYITSIZ else "")) if deger else "girilmedi",
                         "teyitsiz" if kaynak in TEYITSIZ else "" if deger else "soluk"))
    if r := renk(u["aciklama"], aile):
        bilgiler.append(("Renk", r, ""))
    if aile == "PP" and not servis:
        y = yag_metni(u["aciklama"])
        bilgiler.append(("Yağ", y or "bilgi yok", "" if y else "uyari"))
        for k in kalemler:
            if pp_eklentisi_mi(k["urun_kodu"], u["tip"]) and k["erp_durum"] != IPTAL:
                ad = PP_EKLENTILERI.get((k["urun_kodu"] or "").upper(), _kisa_ad(k["urun_adi"]))
                bilgiler.append((None, *_eklenti_cumlesi(ad, k["montaj_durumu"] or VARSAYILAN_EKLENTI_DURUMU)))
        if forma_tabi_mi(u):
            alinan = len(basilan.get(u["id"], set()))
            bilgiler.append(("Çıktılar", f"{alinan}/{len(FORM_TURLERI)}", "hazir" if alinan == len(FORM_TURLERI) else ""))
    eksik = eksikler.get(u["is_emri_no"]) if u["is_emri_no"] else None
    return {
        "tur": "urun",
        "id": u["id"],
        "siparis_id": u["siparis_id"],
        "siparis_no": u["siparis_no"],
        "baslik": u["urun_kodu"],
        "asama": u["asama"],
        "motor": motor["model"] if motor else None,
        "is_emri": u["is_emri_no"],
        "etiketler": etiketler,
        "sicak": any(e["sinif"] == "sicak" for e in etiketler),
        "bilgiler": bilgiler,
        "bagli": bagli_satiri(bagli) if bagli else [],
        "teslim": u["teslim_tarihi"] or ozet["teslim"],
        "kalan": teslim_bilgisi(u["teslim_tarihi"] or ozet["teslim"]),
        "eksik": eksik["toplam"] if eksik else 0,
        "atananlar": _kisiler(atananlar, aile),
    }


def _stok_karti(vt, u, motorlar, atananlar):
    """Stoktaki makinenin kartı: etiketleri (model, Stok, test durumu), numaraları, deposu ve atanabilir siparişler."""
    aile = u["aile"]
    etiketler = [_etiket(model(u["urun_kodu"]), "aile", aile), _etiket(STOK, "stok")]
    test = test_durumu(u)
    if test != "edildi":
        etiketler.append(_etiket("Test bekliyor" if test else "Testi sorulacak", "asama"))
    bilgiler = []
    for alan, ad, deger, kaynak in urun_numaralari(vt, u, aile, None, u["urun_kodu"]):
        bilgiler.append((ad, (deger + (" !" if kaynak in TEYITSIZ else "")) if deger else "girilmedi",
                         "teyitsiz" if kaynak in TEYITSIZ else "" if deger else "soluk"))
    if u["depoda_yok"]:
        bilgiler.append(("Depo", "raporda görünmüyor", "uyari"))
    else:
        bilgiler.append(("Depo", DEPOLAR.get(u["depo"], "yazılmadı"), "" if u["depo"] else "soluk"))
    # Atanabilir siparişler: aynı ürünü bekleyen, iş emri açılmamış; makine atanmadıkça o siparişe ait değil
    atanabilir = atanabilecekler(vt, u["urun_kodu"])
    if atanabilir:
        nolar = list(dict.fromkeys(b["siparis_no"] for b in atanabilir))
        bilgiler.append(("Atanabilir", ", ".join(nolar[:2]) + (f" +{len(nolar) - 2}" if len(nolar) > 2 else ""), ""))
    motor = motorlar.get(u["urun_kodu"]) if aile == "PP" else None
    return {
        "tur": "stok",
        "id": u["id"],
        "siparis_id": None,
        "siparis_no": None,
        "baslik": u["urun_kodu"],
        "asama": "stokta",
        "motor": motor["model"] if motor else None,
        "is_emri": u["is_emri_no"],
        "etiketler": etiketler,
        "sicak": False,
        "bilgiler": bilgiler,
        "bagli": [],
        "teslim": None,
        "kalan": None,
        "eksik": 0,
        "atananlar": _kisiler(atananlar, aile),
    }


def _siparis_karti(ozet, urunler, bekleyenler, atananlar, stokta=None):
    """Siparişler sütunundaki sipariş kartı: siparişin bütün makineleri ve çeneleri etiketlerle (kullanıcı,
    02/11/2026); iş emri açılmamış makineler başlıkta."""
    s = ozet["siparis"]
    makineler = [u for u in urunler if u["tur"] == "servis" or u["aile"] in ANA_URUNLER]
    etiketler = list({e["ad"]: e for e in (
        _etiket(model(u["urun_kodu"]) if u["aile"] in ANA_URUNLER else onek(u["urun_kodu"]), "aile", u["aile"])
        for u in makineler if u["aile"]
    )}.values())
    etiketler += _cene_etiketleri([u for u in urunler if u["aile"] == "Çene"])
    etiketler.append(_kaynak_etiketi(ozet))
    if s["tip"] == "servis":
        etiketler.append(_etiket(BAKIM, "bakim"))
    kisiler = {}
    for u in makineler or urunler or [{"aile": None}]:
        for k in _kisiler(atananlar, u["aile"]):
            kisiler[k["id"]] = k
    return {
        "tur": "siparis",
        "id": s["id"],
        "siparis_id": s["id"],
        "siparis_no": s["siparis_no"],
        "baslik": s["siparis_no"],
        "kodlar": list(dict.fromkeys(u["urun_kodu"] for u in bekleyenler)),
        # İş emri bekleyen makinelerden stokta olanlar: [(kod, stoktaki adet)]; "stoktan karşılanmayacak" işaretli değil
        "stokta": [(kod, stokta[kod.upper()]) for kod in dict.fromkeys(
                       u["urun_kodu"] for u in bekleyenler if not u["stoktan_karsilanmaz"])
                   if stokta and stokta[kod.upper()]],
        "etiketler": etiketler,
        "sicak": any(e["sinif"] == "sicak" for e in etiketler),
        "revizyon": ozet["revizyon"],
        "diger_kalem": ozet["diger_kalem"] if not urunler else 0,
        "teslim": ozet["teslim"],
        "kalan": ozet["kalan"],
        "atananlar": list(kisiler.values()),
    }
