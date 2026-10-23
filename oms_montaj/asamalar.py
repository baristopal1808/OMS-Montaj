"""Ürün kartlarının aşamaları (docs/ihtiyaclar.md, 3.1).

Anahtarlar veritabanında saklanır ve değişmez; adlar ileride Ayarlar'dan
düzenlenebilir hale gelecek (planın 6. adımı). Sıra önemlidir: ERP ürünü
yalnızca ileri götürür (ileri()).
"""

ASAMALAR = {
    "siparis": "Sipariş",
    "malzeme_hazirlik": "Malzeme hazırlık",
    "montaj": "Montaj",
    "montaj_tamamlandi": "Montaj tamamlandı",  # ERP'de iş emri tamamlandı, ürün stoğa girdi
    "teste_hazir": "Teste hazır",
    "test": "Test",
    "temizlik": "Temizlik",
    "sevke_hazir": "Sevke hazır",
    "sevk_edildi": "Sevk edildi",
    "stokta": "Stokta",
}
SIRA = {anahtar: i for i, anahtar in enumerate(ASAMALAR)}


def ileri(simdiki, hedef):
    """ERP'nin gösterdiği aşama yalnızca ileriyse geçerli olur; ekibin ileri aldığı ürün geri gelmez."""
    return hedef if SIRA[hedef] > SIRA[simdiki] else simdiki


def erp_asamasi(stoga_girdi, kirilim_girdi):
    """İş emri açılan ürünün ERP'ye göre aşaması: iş emri tamamlanıp ürün stoğa girdiyse "Montaj tamamlandı",
    kırılımlarından biri stoğa girdiyse "Montaj", yoksa "Malzeme hazırlık" (kullanıcı kararı, 23/10/2026)."""
    if stoga_girdi:
        return "montaj_tamamlandi"
    return "montaj" if kirilim_girdi else "malzeme_hazirlik"
