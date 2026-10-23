"""Yapılacaklar: uygulamanın ekipten cevap beklediği her şey tek listede. Üç konu var:

- Eksik malzeme: açık iş emrinde çıkışı yapılmamış malzeme varsa iş emri başına bir kez "bilginiz var mı?"
  diye sorulur (uyarilar.py).
- ERP'de "İmalatta": iş emri stoğa girmiş ama planlama biriminin ürün durumu hâlâ "İmalatta"; her ürün ve
  iş emri için ayrı sorulur (uyarilar.py).
- Bağlanamayan iş emirleri: ERP'de hangi siparişe ait olduğu bulunamayan (sipariş satırında bağlı değil,
  açıklamasında proje kodu ya da "stok" geçmiyor) iş emrinin neye ait olduğunu ekip seçer: aynı ürünü
  bekleyen bir sipariş satırı, başka bir sipariş (ürün siparişte yoksa alt montajı olarak), stok ya da takip
  edilmeyecek. Açık olanlar ve son KAPALI_GUN günde kapananlar sorulur. Seçim elle bağlantı olarak saklanır,
  ERP yüklemesi değiştirmez; geri alınınca uygulama yeniden kendisi bağlamayı dener.

Liste konuya ve ürün ailesine göre süzülür (SVR, OVR, PP, Çene, Kiriş…); bir aile seçilince iş emirleri
bölümlere ayrılır: makinenin kendisi, alt montaj ve yarı mamuller (adlarına göre: motor-pompa hattı,
dişli kutusu montajı…) ve bakım-onarım. Cevaplar sayfa yenilenmeden kaydedilir (uygulama.js); liste
yerinde kalır. Sonraki adımlarda test soruları ve sevk onayları da buraya gelir.
"""

import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from .erp_aktarim import IPTAL, KAPALI
from .is_emri_aktarim import BAGLANTILAR, KULLANICI_BAGLANTILARI, is_emirlerini_bagla, is_emri_durumu
from .kimlik import ekip_gerekli, guvenli_adres
from .urun_kurallari import AILE_SIRASI, AILELER, onek, sade, satir_turu
from .uyarilar import (
    DEPO_DURUMLARI, EKSIK_CEVAPLARI, IMALATTA_CEVAPLARI, bekleyen_eksikler, bekleyen_imalatta, depo_durumu, depolar,
    eksik_cevapla, eksik_miktari, imalatta_cevapla, imalatta_uyarilari, is_emri_eksikleri,
)
from .veritabani import baglanti

bp = Blueprint("yapilacaklar", __name__)

KAPALI_GUN = 60  # bu kadar gün içinde kapanmış, bağlanamayan iş emirleri de sorulur
DIGER = "Diğer"
AILE_SECENEKLERI = [*AILE_SIRASI, DIGER]
KONULAR = {
    "eksik": "Eksik malzeme",
    "imalatta": "ERP'de İmalatta",
    "baglanamayan": "Bağlanamayan iş emri",
}
# Alt montaj ve yarı mamullerin kodu aileyi göstermiyor (CP1150, P7…); aile ürün adında yazıyor:
# "OVR Blok Montaji - [OVR-40--70-S]", "PP Hortum Seti Montaji".
ADDAKI_AILE = re.compile(r"(?<![A-Z])(SVR|OVR|OVF|WD|PP|SCN|KCN|CB)(?![A-Z])")
MAKINE_BOLUMU = {"Çene": "Çene", "Kiriş": "Kiriş"}  # diğer ailelerde "Makine"
BAKIM_BOLUMU = "Bakım-onarım"


def is_emri_ailesi(urun_kodu, urun_adi):
    """İş emrinin ürün ailesi: ürün kodunun önekinden, olmazsa ürün adında geçen aileden; yoksa 'Diğer'."""
    if aile := AILELER.get(onek(urun_kodu)):
        return aile
    if eslesme := ADDAKI_AILE.search((urun_adi or "").upper()):
        return AILELER[eslesme.group(1)]
    ad = sade(urun_adi or "")
    if "cene" in ad:
        return "Çene"
    if "kiris" in ad:
        return "Kiriş"
    return DIGER


def bolum_basligi(urun_adi):
    """Alt montajın bölüm başlığı: köşeli parantezdeki modeller, ölçüler ve baştaki aile adı atılır.
    'PP - Sogutucu Blok Montaji - 1400 lpm' → 'Sogutucu Blok Montaji'."""
    ad = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", urun_adi or "")
    parcalar = [p.strip() for p in re.split(r"\s+-\s+", ad) if p.strip() and not ADDAKI_AILE.fullmatch(p.strip().upper())]
    ad = re.sub(r"^(SVR|OVR|OVF|WD|PP)\s+", "", parcalar[0] if parcalar else "", flags=re.IGNORECASE)
    return " ".join(k for k in ad.split() if not re.search(r"\d", k)).strip(" -")


def bolum(ie, aile):
    """(bölüm anahtarı, başlık): makinenin kendisi, bakım-onarım ya da alt montajın adı."""
    kod = (ie["urun_kodu"] or "").upper()
    if kod.endswith("-MNT"):
        return "~bakim", BAKIM_BOLUMU
    if ie["envanter_tipi"] == "Son Ürün" and satir_turu(kod)[0] == "kart":
        return "!makine", MAKINE_BOLUMU.get(aile, "Makine")
    baslik = bolum_basligi(ie["urun_adi"]) or kod
    # "Motor Pompa Hatti", "Motor-Pompa Hattı" aynı bölüm
    return re.sub(r"[^a-z]", "", sade(baslik)) or kod, baslik


def baglanamayanlar(vt):
    sinir = (date.today() - timedelta(days=KAPALI_GUN)).isoformat()
    return vt.execute(
        "SELECT * FROM is_emirleri WHERE baglanti IS NULL AND urun_kodu IS NOT NULL"
        " AND (durum != 'Kapalı' OR kapatma_tarihi >= ?) ORDER BY durum = 'Kapalı', acilis_tarihi DESC, is_emri_no",
        (sinir,),
    ).fetchall()


def yapilacak_sayisi(vt):
    return len(baglanamayanlar(vt)) + len(bekleyen_eksikler(vt)) + len(bekleyen_imalatta(vt))


def gruplar(ogeler, secili_aile, aile_al, ie_al=lambda o: o):
    """Ekranda gösterilecek gruplar: [(başlık, [öğe…])]. Aile seçilmemişse ailelere, seçilmişse iş emrinin
    bölümlerine ayrılır (önce makine, sonra en kalabalık alt montajlar, en sonda bakım-onarım)."""
    if not secili_aile:
        aileler = defaultdict(list)
        for oge in ogeler:
            aileler[aile_al(oge)].append(oge)
        return [(aile, aileler[aile]) for aile in AILE_SECENEKLERI if aileler[aile]]
    bolumler, basliklar = defaultdict(list), {}
    for oge in ogeler:
        anahtar, baslik = bolum(ie_al(oge), secili_aile)
        bolumler[anahtar].append(oge)
        basliklar.setdefault(anahtar, baslik)
    sira = sorted(bolumler, key=lambda a: (a != "!makine", a == "~bakim", -len(bolumler[a]), basliklar[a]))
    return [(basliklar[a], bolumler[a]) for a in sira]


def adaylar(vt, urun_kodu):
    """Aynı ürünü bekleyen açık sipariş satırları; ürün kartı boşta (iş emri bağlanmamış) olanlar önce."""
    return vt.execute(
        "SELECT k.id, k.sira_no, k.miktar, k.teslim_tarihi, s.siparis_no, s.musteri,"
        " (SELECT COUNT(*) FROM urunler u WHERE u.kalem_id = k.id AND u.is_emri_id IS NULL"
        "  AND u.asama != 'sevk_edildi') AS bos"
        " FROM siparis_kalemleri k JOIN siparisler s ON s.id = k.siparis_id"
        " WHERE k.urun_kodu = ? AND COALESCE(k.erp_durum, '') NOT IN (?, ?) AND COALESCE(k.erp_genel_durum, '') != ?"
        " AND s.erp_listede = 1 ORDER BY bos = 0, k.teslim_tarihi, s.siparis_no",
        (urun_kodu, IPTAL, KAPALI, KAPALI),
    ).fetchall()


@bp.app_context_processor
def sablon_degiskenleri():
    def sayi():
        return yapilacak_sayisi(baglanti()) if g.get("kullanici") else 0

    return {
        "yapilacak_sayisi": sayi, "eksik_miktari": eksik_miktari, "depo_durumu": depo_durumu, "depolar": depolar,
        "DEPO_DURUMLARI": DEPO_DURUMLARI, "EKSIK_CEVAPLARI": EKSIK_CEVAPLARI, "IMALATTA_CEVAPLARI": IMALATTA_CEVAPLARI,
    }


def _ie_ailesi(ie):
    return is_emri_ailesi(ie["urun_kodu"], ie["urun_adi"])


@bp.route("/yapilacaklar")
def liste():
    vt = baglanti()
    secili_aile = request.args.get("aile", "")
    secili_aile = secili_aile if secili_aile in AILE_SECENEKLERI else ""
    secili_konu = request.args.get("konu", "")
    secili_konu = secili_konu if secili_konu in KONULAR else ""

    # Her konunun öğeleri ve aileleri; sayılar öbür süzgece göre sayılır.
    ogeler = {
        "eksik": [(o, _ie_ailesi(o[0])) for o in bekleyen_eksikler(vt)],
        "imalatta": [(u, u["aile"]) for u in bekleyen_imalatta(vt)],
        "baglanamayan": [(ie, _ie_ailesi(ie)) for ie in baglanamayanlar(vt)],
    }
    aile_sayilari = Counter(a for konu, liste_ in ogeler.items() if secili_konu in ("", konu) for _, a in liste_)
    konu_sayilari = {konu: sum(1 for _, a in liste_ if secili_aile in ("", a)) for konu, liste_ in ogeler.items()}
    secilen = {konu: [o for o, a in liste_ if secili_aile in ("", a)] for konu, liste_ in ogeler.items()}

    eksik_gruplari = gruplar(secilen["eksik"], secili_aile, lambda o: _ie_ailesi(o[0]), lambda o: o[0])
    imalatta_gruplari = gruplar(secilen["imalatta"], "", lambda u: u["aile"]) if not secili_aile else [("", secilen["imalatta"])]
    baglanamayan_gruplari = gruplar(secilen["baglanamayan"], secili_aile, _ie_ailesi)
    sirali = [ie["id"] for _, isler in baglanamayan_gruplari for ie in isler]
    elle = vt.execute(
        "SELECT i.*, s.siparis_no, k.sira_no, u.ad_soyad FROM is_emirleri i"
        " LEFT JOIN siparisler s ON s.id = i.siparis_id LEFT JOIN siparis_kalemleri k ON k.id = i.kalem_id"
        f" LEFT JOIN kullanicilar u ON u.id = i.baglayan_id WHERE i.baglanti IN ({', '.join('?' * len(KULLANICI_BAGLANTILARI))})"
        " ORDER BY i.baglama_zamani DESC",
        KULLANICI_BAGLANTILARI,
    ).fetchall()
    return render_template(
        "yapilacaklar.html",
        secili_aile=secili_aile,
        secili_konu=secili_konu,
        aile_sayilari=aile_sayilari,
        konu_sayilari=konu_sayilari,
        is_emri_ailesi=_ie_ailesi,
        eksik_gruplari=eksik_gruplari,
        eksik_ayrintilari={o[0]["is_emri_no"]: is_emri_eksikleri(vt, o[0]["is_emri_no"]) for o in secilen["eksik"]},
        imalatta_gruplari=imalatta_gruplari,
        baglanamayan_gruplari=baglanamayan_gruplari,
        # Sayfa yenilenmeden kaydedilemezse (betik kapalı) sayfa bir sonraki iş emrinin yerine döner.
        sonraki=dict(zip(sirali, sirali[1:])),
        adaylar={ie["id"]: adaylar(vt, ie["urun_kodu"]) for ie in secilen["baglanamayan"]},
        elle=elle,
        is_emri_durumu=is_emri_durumu,
        AILE_SECENEKLERI=AILE_SECENEKLERI,
        KONULAR=KONULAR,
        BAGLANTILAR=BAGLANTILAR,
        KAPALI_GUN=KAPALI_GUN,
    )


def _siparis_no(metin):
    """'ts0001' ya da 'OZ-TS0001' → 'OZ-TS0001'."""
    metin = "".join((metin or "").split()).upper()
    return metin if metin.startswith("OZ-") or not metin else f"OZ-{metin.removeprefix('OZ')}"


def _yanit(tamam, mesaj, yer=None):
    """Sayfa yenilenmeden gönderildiyse (uygulama.js) JSON; değilse geldiği sayfaya ya da listeye (aynı
    süzgeçle) dönülür: başarıda bir sonraki sorunun, hatada aynı sorunun yerine."""
    if request.accept_mimetypes.best == "application/json":
        return jsonify(tamam=tamam, mesaj=mesaj, sayi=yapilacak_sayisi(baglanti()))
    flash(mesaj)
    if sonra := request.form.get("sonra"):
        return redirect(guvenli_adres(sonra))
    adres = url_for(".liste", aile=request.form.get("aile") or None, konu=request.form.get("konu") or None)
    yer = request.form.get("sonraki") if tamam else yer
    return redirect(f"{adres}#{yer}" if yer else adres)


@bp.route("/yapilacaklar/is-emri/<int:ie_id>/bagla", methods=["POST"])
@ekip_gerekli
def bagla(ie_id):
    vt = baglanti()
    ie = vt.execute("SELECT * FROM is_emirleri WHERE id = ?", (ie_id,)).fetchone()
    if ie is None:
        abort(404)
    secim = request.form.get("secim", "")
    siparis_id = kalem_id = None
    nereye = ""
    if secim.startswith("kalem:"):
        kalem = vt.execute(
            "SELECT k.id, k.siparis_id, k.sira_no, s.siparis_no FROM siparis_kalemleri k"
            " JOIN siparisler s ON s.id = k.siparis_id WHERE k.id = ?",
            (secim[6:],),
        ).fetchone()
        if kalem is None:
            abort(400)
        siparis_id, kalem_id, tur = kalem["siparis_id"], kalem["id"], "kullanici"
        nereye = f' ({kalem["siparis_no"]}, {kalem["sira_no"]}. satır)'
    elif secim == "siparis":
        no = _siparis_no(request.form.get("siparis_no"))
        siparis = vt.execute("SELECT id FROM siparisler WHERE siparis_no = ?", (no,)).fetchone()
        if siparis is None:
            return _yanit(False, f'"{no or "boş"}" numaralı sipariş bulunamadı; iş emri {ie["is_emri_no"]} bağlanmadı.',
                          f"ie-{ie_id}")
        # Siparişte aynı ürün varsa o satıra, yoksa siparişin alt montajı olarak
        kalem = vt.execute(
            "SELECT id, sira_no FROM siparis_kalemleri WHERE siparis_id = ? AND urun_kodu = ? AND COALESCE(erp_durum, '') != ?"
            " ORDER BY sira_no",
            (siparis["id"], ie["urun_kodu"], IPTAL),
        ).fetchone()
        siparis_id, kalem_id, tur = siparis["id"], kalem["id"] if kalem else None, "kullanici"
        nereye = f' ({no}, {kalem["sira_no"]}. satır)' if kalem else f" ({no}, alt montaj)"
    elif secim == "stok":
        tur = "kullanici_stok"
    elif secim == "yoksay":
        tur = "yok_sayildi"
    else:
        return _yanit(False, f'İş emri {ie["is_emri_no"]} için bir seçenek işaretleyin.', f"ie-{ie_id}")
    with vt:
        vt.execute(
            "UPDATE is_emirleri SET siparis_id = ?, kalem_id = ?, baglanti = ?, baglayan_id = ?, baglama_zamani = ?"
            " WHERE id = ?",
            (siparis_id, kalem_id, tur, g.kullanici["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ie_id),
        )
        is_emirlerini_bagla(vt)  # ürün kartlarına dağıtılır, aşama güncellenir
    return _yanit(True, f'İş emri {ie["is_emri_no"]}: {BAGLANTILAR[tur]}{nereye}. Kaydedildi. Yanlışsa sayfanın'
                        ' altındaki "Elle bağlananlar"dan geri alabilirsiniz.')


@bp.route("/yapilacaklar/is-emri/<int:ie_id>/geri-al", methods=["POST"])
@ekip_gerekli
def geri_al(ie_id):
    vt = baglanti()
    ie = vt.execute("SELECT is_emri_no, baglanti FROM is_emirleri WHERE id = ?", (ie_id,)).fetchone()
    if ie is None or ie["baglanti"] not in KULLANICI_BAGLANTILARI:
        abort(404)
    with vt:
        vt.execute(
            "UPDATE is_emirleri SET siparis_id = NULL, kalem_id = NULL, baglanti = NULL, baglayan_id = NULL,"
            " baglama_zamani = NULL WHERE id = ?",
            (ie_id,),
        )
        is_emirlerini_bagla(vt)
    flash(f'İş emri {ie["is_emri_no"]} için seçim geri alındı.')
    return redirect(f'{url_for(".liste", aile=request.form.get("aile") or None)}#ie-{ie_id}')


@bp.route("/yapilacaklar/eksik/<is_emri_no>/cevap", methods=["POST"])
@ekip_gerekli
def eksik_cevap(is_emri_no):
    vt = baglanti()
    if not vt.execute("SELECT 1 FROM eksik_malzemeler WHERE is_emri_no = ? LIMIT 1", (is_emri_no,)).fetchone():
        abort(404)
    cevap = request.form.get("cevap", "")
    if cevap not in EKSIK_CEVAPLARI:
        return _yanit(False, f"İş emri {is_emri_no} için bir cevap işaretleyin.", f"eksik-{is_emri_no}")
    with vt:
        eksik_cevapla(vt, is_emri_no, cevap, g.kullanici["id"])
    return _yanit(True, f'İş emri {is_emri_no}: "{EKSIK_CEVAPLARI[cevap]}" kaydedildi. Yeni bir malzeme eksik'
                        " görünürse ya da eksik miktarı artarsa yeniden sorulur.")


@bp.route("/yapilacaklar/imalatta/<int:urun_id>/<int:ie_id>/cevap", methods=["POST"])
@ekip_gerekli
def imalatta_cevap(urun_id, ie_id):
    vt = baglanti()
    uyari = next((u for u in imalatta_uyarilari(vt, urun_id=urun_id) if u["is_emri_id"] == ie_id), None)
    if uyari is None:
        abort(404)
    cevap = request.form.get("cevap", "")
    if cevap not in IMALATTA_CEVAPLARI:
        return _yanit(False, f"{uyari['urun_kodu']} için bir cevap işaretleyin.", f"imalatta-{urun_id}-{ie_id}")
    with vt:
        imalatta_cevapla(vt, urun_id, ie_id, cevap, g.kullanici["id"])
    return _yanit(True, f'{uyari["urun_kodu"]} (iş emri {uyari["is_emri_no"]}): "{IMALATTA_CEVAPLARI[cevap]}"'
                        " kaydedildi. ERP'deki ürün durumu değişince uyarı kendiliğinden kalkar.")
