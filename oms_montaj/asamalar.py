"""Ürün kartlarının aşamaları (docs/ihtiyaclar.md, 3.1).

Anahtarlar veritabanında saklanır ve değişmez; adlar ileride Ayarlar'dan
düzenlenebilir hale gelecek (planın 6. adımı).
"""

ASAMALAR = {
    "siparis": "Sipariş",
    "malzeme_hazirlik": "Malzeme hazırlık",
    "montaj": "Montaj",
    "teste_hazir": "Teste hazır",
    "test": "Test",
    "temizlik": "Temizlik",
    "sevke_hazir": "Sevke hazır",
    "sevk_edildi": "Sevk edildi",
    "stokta": "Stokta",
}
