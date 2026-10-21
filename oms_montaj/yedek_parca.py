"""Yedek parça: yedek parça siparişlerinin takibi.

Yedek parça siparişinin kalemleri ürün kartı açmaz; sipariş bir bütün olarak izlenir
(docs/ihtiyaclar.md, soru 25). Aşamaları (Hazırlanıyor, Sevke hazır…) elle ilerletmek
planın 4. adımında gelecek; şimdilik ERP'deki durum, adetler ve sevk bilgisi görünür.
"""

from collections import Counter, defaultdict

from flask import Blueprint, render_template, request

from .erp_aktarim import IPTAL
from .siparisler import DURUMLAR, acik_mi, sira_anahtari, son_siparis_yuklemesi, tum_ozetler
from .urun_kurallari import dis_tedarik_mi
from .veritabani import baglanti

bp = Blueprint("yedek_parca", __name__)

SUZGECLER = {"acik": "Açık", "kapali": "Sevk edildi", "tumu": "Tümü"}


@bp.route("/yedek-parca")
def liste():
    secim = request.args.get("durum", "acik")
    secim = secim if secim in SUZGECLER else "acik"
    vt = baglanti()
    kalemler = defaultdict(list)
    for kalem in vt.execute(
        "SELECT k.* FROM siparis_kalemleri k JOIN siparisler s ON s.id = k.siparis_id"
        " WHERE s.tip = 'yedek_parca' AND k.tur = 'parca' AND k.erp_durum != ?",
        (IPTAL,),
    ):
        kalemler[kalem["siparis_id"]].append(kalem)

    satirlar = []
    for ozet in tum_ozetler(vt):
        if ozet["siparis"]["tip"] != "yedek_parca" or ozet["durum"] == "iptal" and secim != "tumu":
            continue
        parcalar = kalemler[ozet["siparis"]["id"]]
        # Dış tedarik (OZ + rakam) parçaların ERP "Ürün Durumu" anlamsızdır; yalnızca burada üretilenler sayılır.
        uretilen = [k for k in parcalar if not dis_tedarik_mi(k["urun_kodu"])]
        durumlar = Counter(k["erp_urun_durumu"] for k in uretilen if k["erp_urun_durumu"])
        satirlar.append({
            **ozet,
            "kalem": len(parcalar),
            "adet": round(sum(k["miktar"] or 0 for k in parcalar)),
            "sevk_adet": round(sum(k["sevk_miktari"] or 0 for k in parcalar)),
            "planlama": durumlar.most_common(1)[0][0] if durumlar else ("Dış tedarik" if parcalar and not uretilen else None),
        })

    sayilar = {
        "acik": sum(1 for s in satirlar if acik_mi(s)),
        "kapali": sum(1 for s in satirlar if s["durum"] == "kapali"),
        "tumu": len(satirlar),
    }
    if secim == "acik":
        satirlar = [s for s in satirlar if acik_mi(s)]
    elif secim == "kapali":
        satirlar = [s for s in satirlar if s["durum"] == "kapali"]
    satirlar.sort(key=sira_anahtari)
    return render_template(
        "yedek_parca.html",
        satirlar=satirlar,
        secim=secim,
        sayilar=sayilar,
        son_yukleme=son_siparis_yuklemesi(vt),
        SUZGECLER=SUZGECLER,
        DURUMLAR=DURUMLAR,
    )
