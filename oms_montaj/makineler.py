"""Makineler: sevk edilecek makinelerin proje (sipariş) proje dökümü.

Özetten açılır: planlama durumu pastasından (?planlama=İmalatta), haftalık teslim
takviminden (?bas=…&bit=… ya da ?teslim=gecikti) ve aile pastasından (?aile=PP).
Makine: ANA_URUNLER ailelerinden, açık siparişte, iptal edilmemiş, onay beklemeyen ve ERP'de
kapanmamış kalemin "Sevk edildi" aşamasında olmayan ürün kartı. Onay bekleyen kalemler kesin
olmadığından sevk edilecekler arasında sayılmaz.
"""

from collections import Counter
from datetime import date

from flask import Blueprint, render_template, request

from .erp_aktarim import BEKLEMEDE, IPTAL, kapali_mi
from .grafik import PLANLAMA_RENKLERI
from .siparisler import TIPLER, teslim_bilgisi
from .urun_kurallari import AILE_SIRASI, ANA_URUNLER
from .veritabani import baglanti

bp = Blueprint("makineler", __name__)

BELIRTILMEMIS = "Belirtilmemiş"
PLANLAMA_SECENEKLERI = [*PLANLAMA_RENKLERI, BELIRTILMEMIS]


def sevk_edilecek_makineler(vt):
    satirlar = vt.execute(
        "SELECT u.id, u.seri_no, u.asama, u.adet_sira, k.aile, k.urun_kodu, k.urun_adi, k.miktar, k.teslim_tarihi,"
        " k.erp_urun_durumu, k.bagli_is_emri_no, k.erp_durum, k.erp_genel_durum,"
        " s.siparis_no, s.musteri, s.tip, s.erp_listede"
        " FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id"
        " WHERE COALESCE(k.erp_durum, '') NOT IN (?, ?) AND u.asama != 'sevk_edildi'"
        f" AND k.aile IN ({', '.join('?' * len(ANA_URUNLER))})"
        " ORDER BY k.teslim_tarihi, s.siparis_no, k.sira_no, u.adet_sira",
        (IPTAL, BEKLEMEDE, *ANA_URUNLER),
    ).fetchall()
    return [m for m in satirlar if not kapali_mi(m) and m["erp_listede"]]


def _tarih(deger):
    try:
        return date.fromisoformat(deger).isoformat()
    except (TypeError, ValueError):
        return None


@bp.route("/makineler")
def liste():
    secim = {alan: request.args.get(alan, "").strip() for alan in ("planlama", "aile", "teslim", "bas", "bit")}
    bugun = date.today().isoformat()
    bas, bit = _tarih(secim["bas"]), _tarih(secim["bit"])
    makineler = sevk_edilecek_makineler(baglanti())

    # Tarih ve aile süzgeçleri; planlama seçicisinin sayıları bunlardan sonra sayılır.
    if secim["teslim"] == "gecikti":
        makineler = [m for m in makineler if m["teslim_tarihi"] and m["teslim_tarihi"] < bugun]
    if bas:
        makineler = [m for m in makineler if m["teslim_tarihi"] and bas <= m["teslim_tarihi"] <= (bit or "9999-12-31")]
    if secim["aile"]:
        makineler = [m for m in makineler if m["aile"] == secim["aile"]]
    planlama_sayilari = Counter(m["erp_urun_durumu"] or BELIRTILMEMIS for m in makineler)
    if secim["planlama"]:
        makineler = [m for m in makineler if (m["erp_urun_durumu"] or BELIRTILMEMIS) == secim["planlama"]]

    gruplar = {}
    for makine in makineler:
        grup = gruplar.setdefault(makine["siparis_no"], {
            "siparis_no": makine["siparis_no"], "musteri": makine["musteri"], "tip": makine["tip"],
            "teslim": makine["teslim_tarihi"], "makineler": [],
        })
        grup["makineler"].append(makine)
        if makine["teslim_tarihi"] and (not grup["teslim"] or makine["teslim_tarihi"] < grup["teslim"]):
            grup["teslim"] = makine["teslim_tarihi"]
    for grup in gruplar.values():
        grup["kalan"] = teslim_bilgisi(grup["teslim"])

    aileler = Counter(m["aile"] for m in makineler)
    return render_template(
        "makineler.html",
        gruplar=sorted(gruplar.values(), key=lambda g: (g["teslim"] or "9999", g["siparis_no"])),
        toplam=len(makineler),
        aileler=[(aile, aileler[aile]) for aile in AILE_SIRASI if aileler[aile]],
        planlama_sayilari=planlama_sayilari,
        planlama_secenekleri=[p for p in PLANLAMA_SECENEKLERI if planlama_sayilari[p]]
        + sorted(p for p in planlama_sayilari if p not in PLANLAMA_SECENEKLERI),
        secim=secim,
        tarih_araligi=(bas, bit) if bas else None,
        TIPLER=TIPLER,
    )
