"""Özet ve sevkiyat sayfalarındaki grafiklerin hesabı. Grafikler sunucuda SVG olarak çizilir.

Renkler dataviz rehberinin paletinden; her aile her grafikte aynı rengi taşır (renk
sıralamaya göre değil, aileye göre verilir). Pastada son dilim ilk dilime de komşu
olduğundan sıra halka olarak denetlendi: komşu her çift renk körlüğü benzetiminde
ΔE ≥ 9,2, normal görmede ≥ 27,6 (OKLab ×100). Bazı renkler beyaz zeminde 3:1'in
altında kaldığından her pastanın yanında adları ve sayılarıyla bir açıklama listesi
bulunur.
"""

import math

AILE_RENKLERI = {
    "SVR": "#2a78d6",
    "OVR": "#eb6834",
    "PP": "#1baf7a",
    "Çene": "#6250d6",
    "Kiriş": "#e87ba4",
    "OVF": "#008300",
    "WD": "#eda100",
}
# Planlama durumu sıralı bir ilerlemedir: açıktan koyuya tek renk (mavi) rampa.
PLANLAMA_RENKLERI = {
    "İmalatta": "#86b6ef",
    "Montajda": "#3987e5",
    "Hazır": "#1c5cab",
    "Sevke Hazır": "#0d366b",
}
DIGER_RENK = "#c3c2b7"  # belirtilmemiş ya da tanınmayan değerler: nötr gri

YARICAP = 52
BOSLUK = 2  # dilimler arasında zemin renginde boşluk (piksel)


def halka(dilimler):
    """Pasta (halka) grafik: dilimler (ad, sayı, renk, adres) listesi; sayısı 0 olanlar atlanır."""
    dilimler = [d for d in dilimler if d[1]]
    toplam = sum(d[1] for d in dilimler)
    cevre = 2 * math.pi * YARICAP
    sonuc, kayma = [], 0.0
    for ad, sayi, renk, adres in dilimler:
        uzunluk = cevre * sayi / toplam
        sonuc.append({
            "ad": ad,
            "sayi": sayi,
            "yuzde": round(100 * sayi / toplam),
            "renk": renk,
            "adres": adres,
            "uzunluk": round(uzunluk - (BOSLUK if len(dilimler) > 1 else 0), 2),
            "kayma": round(kayma, 2),
        })
        kayma += uzunluk
    return {"toplam": toplam, "cevre": round(cevre, 2), "yaricap": YARICAP, "dilimler": sonuc}
