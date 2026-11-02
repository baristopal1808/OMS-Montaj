"""Aşama değiştirme, notlar ve ürünün zaman akışı; sipariş kartında listede görünmeyen satırların kontrolü.
Veriler uydurmadır."""

from datetime import datetime
from html import unescape

from test_is_emirleri import IE_BASLIKLAR, is_emirleri
from test_siparisler import ekip, excel, makine_siparisi, satir, yukle  # noqa: F401 (pytest fikstürleri)
from test_urunler import urun_id, yuklenmis

from oms_montaj.veritabani import baglanti


def sayfa(istemci, adres):
    return unescape(istemci.get(adres).get_data(as_text=True))


def akis(istemci, urun):
    metin = sayfa(istemci, f"/urun/{urun}")
    return metin[metin.index('id="asama"'):metin.index('id="numaralar"')]


def asama(uygulama, urun):
    with uygulama.app_context():
        return baglanti().execute("SELECT asama FROM urunler WHERE id = ?", (urun,)).fetchone()[0]


def test_asama_ileri_ve_geri_alinir(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    # Vibro çakıcıda montaj formu kuralı yok; aşama serbestçe ileri alınır (güç ünitesi: test_formlar.py)
    yuklenmis(yukle)
    pp = urun_id(uygulama, "SVR-50-NF-BSP")
    assert asama(uygulama, pp) == "malzeme_hazirlik"
    gonder(f"/urun/{pp}/asama", asama="test")  # ileri alırken not isteğe bağlı
    assert asama(uygulama, pp) == "test"
    # Geri alırken sebep zorunlu
    gonder(f"/urun/{pp}/asama", asama="montaj", **{"not": "   "})
    assert asama(uygulama, pp) == "test"
    assert "Aşama geri alınmadı" in sayfa(istemci, f"/urun/{pp}")
    gonder(f"/urun/{pp}/asama", asama="montaj", **{"not": "TEST NOT: testte kaçak çıktı"})
    assert asama(uygulama, pp) == "montaj"
    metin = akis(istemci, pp)
    for beklenen in ("Aşama: Malzeme hazırlık → Test", "TEST NOT: testte kaçak çıktı", "Aşama: Test → Montaj", "TEST KULLANICI",
                     "İş emri 900102 açıldı", "Sipariş talebi onaylandı"):
        assert beklenen in metin, beklenen
    assert metin.index("Aşama: Test → Montaj") < metin.index("Aşama: Malzeme hazırlık → Test")  # yeniden eskiye
    assert '<li class="simdiki" aria-current="step">Montaj</li>' in metin
    # Aynı aşama değişiklik sayılmaz; "Stokta" seçilemez
    gonder(f"/urun/{pp}/asama", asama="montaj")
    assert "zaten \"Montaj\" aşamasında" in sayfa(istemci, f"/urun/{pp}")
    assert gonder(f"/urun/{pp}/asama", asama="stokta").status_code == 400


def test_erp_geri_alinan_urunu_yeniden_itmez(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    gonder(f"/urun/{pp}/asama", asama="siparis", **{"not": "TEST NOT: yanlış iş emri"})
    # Aynı iş emri listesi yeniden yüklenince ERP'de gelişme yok: ürün ekibin bıraktığı aşamada kalır
    yuklenmis(yukle)
    assert asama(uygulama, pp) == "siparis"
    # İş emri tamamlanınca (yeni gelişme) ERP ürünü ileri götürür; akışta ERP yüklemesi olarak görünür. Montaj
    # formları basılmadığı için güç ünitesi Montaj'da bekler (form kuralı: test_formlar.py)
    liste = is_emirleri()
    liste[0].update({"Gerçek Mkt.": 1, "Kalan Mkt.": 0, "* Durumu": "Kapalı", "İşEmri Kapatma Tarihi": datetime(2026, 10, 20),
                     "İlk Stok Giriş Tar.": datetime(2026, 10, 20)})
    yukle(excel(liste, basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    assert asama(uygulama, pp) == "montaj"
    metin = akis(istemci, pp)
    assert "Aşama: Sipariş → Montaj" in metin and "ERP yüklemesi" in metin


def test_not_yazilir_ve_yazan_duzeltir(istemci, uygulama, ekle, giris, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    pp = urun_id(uygulama, "PP-536-NF")
    gonder(f"/urun/{pp}/not", metin="  TEST NOT 1\nikinci satır  ")
    gonder(f"/urun/{pp}/not", metin="   ")
    assert "Not boş olamaz" in sayfa(istemci, f"/urun/{pp}")
    with uygulama.app_context():
        olay = baglanti().execute("SELECT id, metin FROM urun_olaylari WHERE tur = 'not'").fetchone()
    assert olay["metin"] == "TEST NOT 1\nikinci satır"
    # Yazan düzeltir; önceki hâli saklanır, not silinemez
    gonder(f"/urun/{pp}/not/{olay['id']}", metin="TEST NOT 2")
    metin = akis(istemci, pp)
    assert "TEST NOT 2" in metin and "düzeltildi" in metin and "Önceki hâli" in metin and "TEST NOT 1" in metin
    gonder(f"/urun/{pp}/not/{olay['id']}", metin="")
    assert "Not silinemez" in sayfa(istemci, f"/urun/{pp}")
    # Başkası düzeltemez; izleyici not yazamaz
    ekle("test.ikinci")
    giris("test.ikinci")
    assert "Düzeltmeyi kaydet" not in akis(istemci, pp)
    assert gonder(f"/urun/{pp}/not/{olay['id']}", metin="TEST NOT 3").status_code == 403
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert 'name="metin"' not in sayfa(istemci, f"/urun/{pp}") and "TEST NOT 2" in akis(istemci, pp)
    assert gonder(f"/urun/{pp}/not", metin="TEST NOT 4").status_code == 403
    assert gonder(f"/urun/{pp}/asama", asama="test").status_code == 403


def test_eksik_satir_kontrol_edilir(istemci, gonder, ekip, yukle):  # noqa: F811
    satirlar = makine_siparisi()
    del satirlar[3]  # 4. satır listede yok
    yukle(excel(satirlar))
    uyari = "Siparişin 4. satırı yüklenen ERP listelerinin hiçbirinde görünmedi"
    assert uyari in sayfa(istemci, "/siparisler/OZ-TS0001")
    gonder("/siparisler/eksik-satir/OZ-TS0001")
    kart = sayfa(istemci, "/siparisler/OZ-TS0001")
    assert uyari not in kart and "TEST KULLANICI kontrol etti: satır silinmiş" in kart
    # Başka bir satır da görünmez olursa uyarı yeniden çıkar; geri alınabilir
    satirlar.append(satir(7, "OZ00002", "Test Pul"))  # 6. satır da yok
    yukle(excel(satirlar))
    assert "Siparişin 4, 6. satırları yüklenen ERP listelerinin" in sayfa(istemci, "/siparisler/OZ-TS0001")
    gonder("/siparisler/eksik-satir/OZ-TS0001")
    assert "kontrol etti: satırlar silinmiş" in sayfa(istemci, "/siparisler/OZ-TS0001")
    gonder("/siparisler/eksik-satir/OZ-TS0001", islem="geri_al")
    assert "Siparişin 4, 6. satırları yüklenen" in sayfa(istemci, "/siparisler/OZ-TS0001")
