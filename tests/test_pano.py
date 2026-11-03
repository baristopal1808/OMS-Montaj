"""Siparişler panosu (Planner'daki gibi aşama sütunları), varsayılan atama, sipariş kartının başlığındaki makine
satırları ve ürün sayfasındaki "Bu makineyle gelenler". Veriler uydurmadır."""

from datetime import datetime
from html import unescape

from test_siparisler import ekip, excel, makine_siparisi, satir, yukle  # noqa: F401 (pytest fikstürleri)
from test_urunler import urun_id, yuklenmis

from oms_montaj.veritabani import baglanti


def sayfa(istemci, adres):
    return unescape(istemci.get(adres).get_data(as_text=True))


def sutun(metin, anahtar):
    """Panonun bir sütununun HTML'i."""
    bas = metin.index(f'id="sutun-{anahtar}"')
    son = metin.find('<section class="pano-sutunu"', bas)
    return metin[bas:son if son != -1 else len(metin)]


def test_pano_kartlari_ve_suzgecler(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)  # PP (900101) ve SVR (900102) iş emri açıldı: Malzeme hazırlık
    pano = sayfa(istemci, "/siparisler")
    malzeme = sutun(pano, "malzeme")
    assert "PP-536-NF" in malzeme and "SVR-50-NF-BSP" in malzeme
    assert "OZ-TS0001" not in sutun(pano, "siparisler")  # bütün makinelerin iş emri açık
    # Kart bilgileri: Planner'daki kontrol listesi yerine bilgi olarak
    for beklenen in ("İE <strong>900101</strong>", "Yağsız sevk", "Çıktılar", "0/4", "İE <strong>900102</strong>", "RAL3020",
                     "Şasi no", ">KCN</a>", ">Sipariş</a>"):
        assert beklenen in malzeme, beklenen
    # Çene, kiriş ve hortum seti vibronun kartında kısa satır; kendi kartları yok
    assert "Çene 2" in malzeme and "Kiriş" in malzeme and "Hortum Seti" in malzeme and "KCN-90</strong>" not in pano
    # Etikete tıklayınca süzülür; birden çok etiket birlikte
    yalniz_pp = sayfa(istemci, "/siparisler?etiket=PP")
    assert "PP-536-NF" in yalniz_pp and "SVR-50-NF-BSP</strong>" not in yalniz_pp and "PP ×" in yalniz_pp
    assert "-536-NF</strong>" not in sayfa(istemci, "/siparisler?etiket=PP&etiket=SVR-NF")
    # Aşama değişince kart sütun değiştirir; grup sütununda asıl aşama etiket olarak yazar
    pp = urun_id(uygulama, "PP-536-NF")
    with uygulama.app_context():
        vt = baglanti()
        with vt:
            vt.execute("UPDATE urunler SET asama = 'test', form_muaf = 1 WHERE id = ?", (pp,))
    pano = sayfa(istemci, "/siparisler")
    son_montaj = sutun(pano, "son_montaj")
    assert "PP-536-NF" in son_montaj and ">Test aşamasında</a>" in son_montaj and "PP-536-NF" not in sutun(pano, "malzeme")
    assert "PP-536-NF" in sayfa(istemci, "/siparisler?etiket=Test aşamasında")


def test_varsayilan_atama(istemci, uygulama, gonder, ekle, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    ekle("test.ikinci")
    with uygulama.app_context():
        idler = dict(baglanti().execute("SELECT kullanici_adi, id FROM kullanicilar"))
    ben, ikinci = idler["test.kullanici"], idler["test.ikinci"]
    gonder("/ayarlar/kullanicilar/atama", pp=str(ben), diger=str(ikinci))
    ayar = sayfa(istemci, "/ayarlar/kullanicilar/")
    assert "Varsayılan atama kaydedildi" in ayar and f'name="pp" value="{ben}" checked' in ayar
    pano = sayfa(istemci, "/siparisler")
    kartlar = pano[pano.index('<div class="pano">'):]
    assert kartlar.count('class="kisi-baloncugu') == 2 and ">TK</a>" in kartlar  # menüdeki kendi yuvarlağı hariç
    # Kişiye tıklayınca yalnızca onun kartları; "Bana atananlar"
    bana = sayfa(istemci, f"/siparisler?kisi={ben}")
    assert "PP-536-NF" in bana and "SVR-50-NF-BSP</strong>" not in bana
    assert "SVR-50-NF-BSP" in sayfa(istemci, f"/siparisler?kisi={ikinci}")
    # İzleyici atama yapamaz
    ekle("test.izleyici", rol="izleyici")
    gonder("/giris", kullanici_adi="test.izleyici", sifre="gizli-sifre-1")
    assert gonder("/ayarlar/kullanicilar/atama", pp=str(ben)).status_code == 403


def test_siparis_karti_basligi_ve_gelenler(istemci, uygulama, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    kart = sayfa(istemci, "/siparisler/OZ-TS0001")
    baslik = kart[kart.index('class="baslik-makineler"'):kart.index("</ul>", kart.index('class="baslik-makineler"'))]
    assert "SVR-50-NF-BSP" in baslik and "İş emri <strong>900102</strong>" in baslik and "Renk <strong>RAL3020</strong>" in baslik
    assert "PP-536-NF" in baslik and "Yağsız sevk" in baslik and "KCN-90" not in baslik  # yalnızca makineler
    # Ürün satırlarında yağ ve renk yazmaz
    urunler = kart[kart.index('id="aile-SVR"'):]
    assert "Renk:" not in urunler and "Yağsız sevk" not in urunler
    # Vibronun sayfasında bu makineyle gelenler
    svr = sayfa(istemci, f"/urun/{urun_id(uygulama, 'SVR-50-NF-BSP')}")
    gelenler = svr[svr.index('id="gelenler"'):]
    for beklenen in ("KCN-90", "OZ-TS0001-HC-02", "CB-HS5080-00", "Hortum Seti"):
        assert beklenen in gelenler, beklenen
    assert 'id="gelenler"' not in sayfa(istemci, f"/urun/{urun_id(uygulama, 'PP-536-NF')}")


def test_sicak_siparis_ve_cene_etiketleri(istemci, ekip, yukle):  # noqa: F811
    # Talepten (01/12/2029) teslime (20/12/2029) 30 günden az: sıcak sipariş; ACN de çene sayılır
    satirlar = makine_siparisi(s1={"Uzlaşılan Sevk Tar.": datetime(2029, 12, 20)})
    satirlar.append(satir(6, "ACN-TEST-1", "TEST CENE", planlama="OZ-TS0001-HC-03"))
    yukle(excel(satirlar))
    siparisler = sutun(sayfa(istemci, "/siparisler"), "siparisler")
    assert ">Sıcak sipariş</a>" in siparisler and "is-karti siparis-mini sicak" in siparisler
    assert ">KCN</a>" in siparisler and ">ACN</a>" in siparisler
    yukle(excel(makine_siparisi()))  # talepten teslime 45 gün: yalnızca "Sipariş"
    siparisler = sutun(sayfa(istemci, "/siparisler"), "siparisler")
    assert ">Sipariş</a>" in siparisler and "Sıcak sipariş" not in siparisler


def test_karttan_asama_degisir(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    svr = urun_id(uygulama, "SVR-50-NF-BSP")
    assert f'action="/urun/{svr}/asama"' in sayfa(istemci, "/siparisler")
    yanit = gonder(f"/urun/{svr}/asama", asama="montaj", sonra="/siparisler?etiket=SVR-NF")
    assert yanit.headers["Location"].endswith("/siparisler?etiket=SVR-NF")
    pano = sayfa(istemci, "/siparisler")
    assert "SVR-50-NF-BSP" in sutun(pano, "montaj") and "SVR-50-NF-BSP (OZ-TS0001): aşama değişti" in pano
    # Geri alırken sebep yine zorunlu
    gonder(f"/urun/{svr}/asama", asama="siparis", sonra="/siparisler")
    assert "SVR-50-NF-BSP" in sutun(sayfa(istemci, "/siparisler"), "montaj")
