"""Sevkiyat: sevk edilen ürünlerin çeyrek dönemlere göre geçmişi.

Sevk tarihi ERP'deki "Son Sevk Tarihi"dir; adet "Sevk/Kont.Gelen Miktarı" (yoksa kapanmış
kalemin miktarı). Kayıtlar hiç silinmez: özet sayfasındaki "bu çeyrek" sayısı her çeyrek
başında sıfırdan başlar, geçmiş çeyrekler bu sayfada seçilerek incelenir. Sayılar ve pasta
yalnızca makineleri (ANA_URUNLER) içerir; yedek parça sevkiyatı ayrı, açılır bir bölümdedir.
"""

from collections import Counter, defaultdict
from datetime import date

from flask import Blueprint, render_template, request

from .erp_aktarim import IPTAL, kapali_mi
from .grafik import AILE_RENKLERI, halka
from .siparisler import TIPLER
from .urun_kurallari import ANA_URUNLER
from .veritabani import baglanti

bp = Blueprint("sevkiyat", __name__)

CEYREK_AYLARI = {1: "Ocak–Mart", 2: "Nisan–Haziran", 3: "Temmuz–Eylül", 4: "Ekim–Aralık"}


def ceyrek(gun):
    return gun.year, (gun.month - 1) // 3 + 1


def _sevk_edilenler(vt, kosul, *degerler):
    satirlar = vt.execute(
        "SELECT k.*, s.siparis_no, s.musteri, s.tip FROM siparis_kalemleri k JOIN siparisler s ON s.id = k.siparis_id"
        f" WHERE k.son_sevk_tarihi IS NOT NULL AND k.erp_durum != ? AND {kosul}",
        (IPTAL, *degerler),
    ).fetchall()
    kayitlar = []
    for kalem in satirlar:
        adet = round(kalem["sevk_miktari"] or (kalem["miktar"] if kapali_mi(kalem) else 0))
        if adet:
            kayitlar.append({"tarih": date.fromisoformat(kalem["son_sevk_tarihi"]), "kalem": kalem, "adet": adet})
    return kayitlar


def sevk_kayitlari(vt):
    """Sevk edilmiş makine kalemleri: tarih, kalem (sipariş bilgisiyle) ve sevk edilen adet."""
    return _sevk_edilenler(vt, f"k.aile IN ({', '.join('?' * len(ANA_URUNLER))})", *ANA_URUNLER)


def yedek_parca_sevkleri(vt, secilen):
    """Seçilen çeyrekte sevk edilen yedek parça siparişleri: sipariş başına kalem ve adet."""
    siparisler = {}
    for r in _sevk_edilenler(vt, "k.tur = 'parca'"):
        if ceyrek(r["tarih"]) != secilen:
            continue
        kalem = r["kalem"]
        s = siparisler.setdefault(kalem["siparis_no"], {
            "siparis_no": kalem["siparis_no"], "musteri": kalem["musteri"], "tarih": r["tarih"], "kalem": 0, "adet": 0,
        })
        s["tarih"] = max(s["tarih"], r["tarih"])
        s["kalem"] += 1
        s["adet"] += r["adet"]
    return sorted(siparisler.values(), key=lambda s: (s["tarih"], s["siparis_no"]), reverse=True)


def ceyrek_ozeti(kayitlar, secilen):
    secili = [r for r in kayitlar if ceyrek(r["tarih"]) == secilen]
    return {
        "urun": sum(r["adet"] for r in secili),
        "siparis": len({r["kalem"]["siparis_no"] for r in secili}),
        "kayitlar": secili,
    }


def _secilen_ceyrek(deger, varsayilan):
    try:
        yil, no = (int(p) for p in deger.split("-"))
        return (yil, no) if 1 <= no <= 4 else varsayilan
    except (AttributeError, ValueError):
        return varsayilan


@bp.route("/sevkiyat")
def liste():
    vt = baglanti()
    kayitlar = sevk_kayitlari(vt)
    bu = ceyrek(date.today())
    secilen = _secilen_ceyrek(request.args.get("ceyrek"), bu)
    adetler = Counter()
    for r in kayitlar:
        adetler[ceyrek(r["tarih"])] += r["adet"]
    ozet = ceyrek_ozeti(kayitlar, secilen)

    aileler = Counter()
    siparisler = {}
    for r in ozet["kayitlar"]:
        kalem = r["kalem"]
        aileler[kalem["aile"]] += r["adet"]
        s = siparisler.setdefault(kalem["siparis_no"], {
            "siparis_no": kalem["siparis_no"], "musteri": kalem["musteri"], "tip": kalem["tip"],
            "tarih": r["tarih"], "urunler": Counter(),
        })
        s["tarih"] = max(s["tarih"], r["tarih"])
        s["urunler"][kalem["aile"]] += r["adet"]
    for s in siparisler.values():
        s["urunler"] = [(aile, s["urunler"][aile]) for aile in ANA_URUNLER if s["urunler"][aile]]

    return render_template(
        "sevkiyat.html",
        ceyrekler=sorted(set(adetler) | {bu}, reverse=True),
        adetler=adetler,
        secilen=secilen,
        bu=bu,
        ozet=ozet,
        grafik=halka([(aile, aileler[aile], AILE_RENKLERI[aile], None) for aile in ANA_URUNLER]),
        siparisler=sorted(siparisler.values(), key=lambda s: (s["tarih"], s["siparis_no"]), reverse=True),
        yedek_parcalar=yedek_parca_sevkleri(vt, secilen),
        CEYREK_AYLARI=CEYREK_AYLARI,
        TIPLER=TIPLER,
    )
