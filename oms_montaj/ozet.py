"""Özet: girişte açılan ana ekran; montaj ekibini ilgilendiren durumların bir bakışta görünümü.

Bilgisayar ekranında kaydırmadan sığacak şekilde düzenlenir. Sevk edilecek ürün: açık
siparişlerde, iptal edilmemiş ve ERP'de kapanmamış kalemlerin "Sevk edildi" aşamasında
olmayan makineleri (ANA_URUNLER; çene ve kiriş sayılmaz). Yedek parça siparişleri kendi
ekranında izlenir, buradaki sayılara girmez. Grafikler sunucuda çizilir.
"""

from collections import Counter
from datetime import date, timedelta

from flask import Blueprint, render_template, url_for

from .grafik import AILE_RENKLERI, DIGER_RENK, PLANLAMA_RENKLERI, halka
from .makineler import sevk_edilecek_makineler
from .sevkiyat import ceyrek, ceyrek_ozeti, sevk_kayitlari
from .siparisler import TIPLER, YAKLASAN_GUN, acik_mi, son_siparis_yuklemesi, tum_ozetler
from .urun_kurallari import ANA_URUNLER
from .veritabani import baglanti

bp = Blueprint("ozet", __name__)

BELIRTILMEMIS = "Belirtilmemiş"
HAFTA_SAYISI = 8
SUTUN_YUKSEKLIGI = 100  # piksel; en yüksek sütun
TABLO_SATIRI = 6  # özet tablosunda gösterilen en çok sipariş; kalanı Siparişler'de


def haftalik_takvim(urunler, bugun):
    """Teslim tarihine göre ürün adetleri: gecikenler, bu haftadan başlayarak 8 hafta, sonrası."""
    pazartesi = bugun - timedelta(days=bugun.weekday())
    # "alt" sütunun altında görünür; "aralik" fareyle üzerine gelince. Sütuna tıklayınca
    # Siparişler o haftanın (bu hafta için bugünden başlayarak) siparişleriyle açılır.
    sutunlar = [{"ad": "Geciken", "alt": "", "aralik": "teslimi geçmiş", "sayi": 0, "geciken": True,
                 "adres": url_for("makineler.liste", teslim="gecikti")}]
    for i in range(HAFTA_SAYISI):
        bas = pazartesi + timedelta(weeks=i)
        bitis = bas + timedelta(days=6)
        ad = "Bu hafta" if i == 0 else f"{bas.isocalendar().week}. hf"
        sutunlar.append({"ad": ad, "alt": f"{bas:%d.%m}", "aralik": f"{bas:%d.%m}–{bitis:%d.%m}", "sayi": 0,
                         "geciken": False,
                         "adres": url_for("makineler.liste", bas=max(bas, bugun).isoformat(), bit=bitis.isoformat())})
    sonra = pazartesi + timedelta(weeks=HAFTA_SAYISI)
    sutunlar.append({"ad": "Sonra", "alt": f"{sonra:%d.%m}+", "aralik": f"{sonra:%d.%m} ve sonrası", "sayi": 0,
                     "geciken": False, "adres": url_for("makineler.liste", bas=sonra.isoformat())})
    tarihsiz = 0
    for urun in urunler:
        if not urun["teslim_tarihi"]:
            tarihsiz += 1
            continue
        teslim = date.fromisoformat(urun["teslim_tarihi"])
        if teslim < bugun:
            sutunlar[0]["sayi"] += 1
        else:
            sutunlar[min((teslim - pazartesi).days // 7, HAFTA_SAYISI) + 1]["sayi"] += 1
    en_cok = max((s["sayi"] for s in sutunlar), default=0) or 1
    for sutun in sutunlar:
        sutun["yukseklik"] = round(SUTUN_YUKSEKLIGI * sutun["sayi"] / en_cok)
    return sutunlar, tarihsiz


@bp.route("/")
def ana():
    vt = baglanti()
    bugun = date.today()
    tumu = [o for o in tum_ozetler(vt) if acik_mi(o) and o["siparis"]["tip"] != "yedek_parca"]
    # Onay bekleyen siparişler kesin olmadığından açık sipariş ve teslim sayılarına girmez.
    acik = [o for o in tumu if o["durum"] == "acik"]
    urunler = sevk_edilecek_makineler(vt)
    yaklasanlar = sorted(
        (o for o in acik if o["teslim"] and date.fromisoformat(o["teslim"]) <= bugun + timedelta(days=YAKLASAN_GUN)),
        key=lambda o: o["teslim"],
    )
    takvim, tarihsiz = haftalik_takvim(urunler, bugun)

    aileler = Counter(u["aile"] for u in urunler)
    durumlar = Counter(u["erp_urun_durumu"] or BELIRTILMEMIS for u in urunler)
    planlama_sirasi = list(PLANLAMA_RENKLERI) + sorted(d for d in durumlar if d not in PLANLAMA_RENKLERI)
    bu_ceyrek = ceyrek(bugun)

    return render_template(
        "ozet.html",
        sayilar={
            "acik": len(acik),
            "urun": len(urunler),
            "geciken": sum(1 for o in acik if o["kalan"] and o["kalan"][1] == "gecikti"),
            "geciken_urun": takvim[0]["sayi"],
            "yaklasan": sum(1 for o in acik if o["kalan"] and o["kalan"][1] == "yaklasan"),
            "onay": sum(1 for o in tumu if o["durum"] == "onay_bekliyor"),
        },
        sevk=ceyrek_ozeti(sevk_kayitlari(vt), bu_ceyrek),
        bu_ceyrek=bu_ceyrek,
        aile_grafigi=halka([
            (aile, aileler[aile], AILE_RENKLERI[aile], url_for("makineler.liste", aile=aile))
            for aile in ANA_URUNLER
        ]),
        planlama_grafigi=halka([
            (durum, durumlar[durum], PLANLAMA_RENKLERI.get(durum, DIGER_RENK), url_for("makineler.liste", planlama=durum))
            for durum in planlama_sirasi
        ]),
        takvim=takvim,
        tarihsiz=tarihsiz,
        yaklasanlar=yaklasanlar[:TABLO_SATIRI],
        yaklasan_toplam=len(yaklasanlar),
        son_yukleme=son_siparis_yuklemesi(vt),
        YAKLASAN_GUN=YAKLASAN_GUN,
        TIPLER=TIPLER,
    )
