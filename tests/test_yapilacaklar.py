"""Yapılacaklar: bağlanamayan iş emirlerinin ekip tarafından siparişe, stoğa bağlanması ya da yok sayılması.
Veriler uydurmadır."""

from html import unescape

from test_is_emirleri import IE_BASLIKLAR, ie
from test_siparisler import ekip, excel, makine_siparisi, yukle  # noqa: F401 (pytest fikstürleri)

from oms_montaj.veritabani import baglanti


def baglantisiz_is_emirleri():
    return [
        ie(900109, 0, "KCN-90", "Hidrolik Cene", plan=2),  # açıklamasız: siparişteki çene satırı aday
        ie(900110, 0, "SCN-90", "Hidrolik Cene"),  # aday yok
        ie(900111, 0, "CP0009", "Disli Kutusu Montaji", envanter="Yarı Mamul"),
    ]


def yuklenmis(yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(baglantisiz_is_emirleri(), basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")


def ie_id(uygulama, no):
    with uygulama.app_context():
        return baglanti().execute("SELECT id FROM is_emirleri WHERE is_emri_no = ?", (no,)).fetchone()[0]


def test_baglanamayanlar_listelenir(istemci, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    sayfa = unescape(istemci.get("/yapilacaklar").get_data(as_text=True))
    assert 'Bağlanamayan iş emirleri <span class="soluk">(<span data-sayi-konu="baglanamayan">3</span>)</span>' in sayfa
    assert "900109" in sayfa and "900110" in sayfa and "900111" in sayfa
    # Çene iş emrinin adayı: siparişin 3. satırı, iki adedin iş emri yok
    assert "OZ-TS0001</strong> · 3. satır" in sayfa and "2 adedin iş emri yok" in sayfa
    assert '<span class="menu-sayi"' in sayfa


def test_siparis_satirina_baglanir_ve_geri_alinir(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    with uygulama.app_context():
        kalem = baglanti().execute("SELECT id FROM siparis_kalemleri WHERE urun_kodu = 'KCN-90'").fetchone()[0]
    cene = ie_id(uygulama, "900109")
    yanit = gonder(f"/yapilacaklar/is-emri/{cene}/bagla", secim=f"kalem:{kalem}")
    assert yanit.status_code == 302
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    assert "900109" in kart and "Malzeme hazırlık" in kart
    sayfa = unescape(istemci.get("/yapilacaklar").get_data(as_text=True))
    assert 'data-sayi-konu="baglanamayan">2<' in sayfa and "Elle bağlananlar" in sayfa and "elle siparişe bağlandı" in sayfa
    # ERP yüklemesi elle bağlantıyı değiştirmez
    yukle(excel(baglantisiz_is_emirleri(), basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    assert "900109" in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    # Geri alınınca yeniden sorulur
    gonder(f"/yapilacaklar/is-emri/{cene}/geri-al")
    assert 'data-sayi-konu="baglanamayan">3<' in istemci.get("/yapilacaklar").get_data(as_text=True)


def test_baska_siparise_stoga_ya_da_yok_sayilir(istemci, uygulama, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    # Ürünü siparişte olmayan iş emri, yazılan siparişin alt montajı olur (OZ- yazmasa da bulunur)
    gonder(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900111')}/bagla", secim="siparis", siparis_no="ts0001")
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    assert "Alt montajlar ve yarı mamuller" in kart and "CP0009" in kart
    gonder(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900110')}/bagla", secim="stok")
    assert 'data-sayi-konu="baglanamayan">1<' in istemci.get("/yapilacaklar").get_data(as_text=True)
    gonder(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900109')}/bagla", secim="yoksay")
    sayfa = unescape(istemci.get("/yapilacaklar").get_data(as_text=True))
    assert "Bağlanamayan iş emri yok" in sayfa and "takip edilmiyor" in sayfa and "elle stok olarak işaretlendi" in sayfa
    # Olmayan sipariş ve seçimsiz gönderim bağlamaz
    gonder(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900109')}/geri-al")
    gonder(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900109')}/bagla", secim="siparis", siparis_no="OZ-TS9999")
    gonder(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900109')}/bagla")
    sayfa = unescape(istemci.get("/yapilacaklar").get_data(as_text=True))
    assert '"OZ-TS9999" numaralı sipariş bulunamadı' in sayfa and "bir seçenek işaretleyin" in sayfa
    assert 'data-sayi-konu="baglanamayan">1<' in sayfa


def test_aile_suzgeci_ve_bolumler(istemci, ekip, yukle):  # noqa: F811
    yukle(excel(makine_siparisi()))
    yukle(excel(baglantisiz_is_emirleri() + [
        ie(900113, 0, "CP0010", "OVR Blok Montaji - BSP - [OVR-40--70-S]", envanter="Yarı Mamul"),
        ie(900114, 0, "OVR-70-S-CV", "Ekskavatore Monteli Vibro Cakici"),
        ie(900115, 0, "OVR-70-S-MNT", "Vibro Cakici Bakim"),
    ], basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    sayfa = unescape(istemci.get("/yapilacaklar").get_data(as_text=True))
    # Alt montajın ailesi adından okunur; ailesi bilinmeyen "Diğer"de
    assert 'data-sayi-aile="OVR">3<' in sayfa and 'data-sayi-aile="Çene">2<' in sayfa and 'data-sayi-aile="Diğer">1<' in sayfa
    assert 'class="suzgec-cip bos"' in sayfa  # bağlanamayan iş emri olmayan aileler soluk
    ovr = unescape(istemci.get("/yapilacaklar?aile=OVR").get_data(as_text=True))
    assert "900113" in ovr and "900114" in ovr and "900110" not in ovr
    # Bölümler: önce makine, sonra alt montajlar, en sonda bakım-onarım
    assert ovr.index("Makine <span") < ovr.index("Blok Montaji <span") < ovr.index("Bakım-onarım <span")
    assert "Çene ailesinde bağlanamayan iş emri yok" not in unescape(istemci.get("/yapilacaklar?aile=Çene").get_data(as_text=True))
    assert "PP ailesinde bağlanamayan iş emri yok" in unescape(istemci.get("/yapilacaklar?aile=PP").get_data(as_text=True))


def test_sayfa_yenilenmeden_kaydedilir(istemci, uygulama, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    with istemci.session_transaction() as oturum:
        anahtar = oturum.setdefault("csrf", "test-csrf")
    json = {"Accept": "application/json"}
    yanit = istemci.post(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900110')}/bagla",
                         data={"csrf": anahtar, "secim": "stok"}, headers=json)
    assert yanit.get_json()["tamam"] is True and yanit.get_json()["sayi"] == 2
    assert yanit.get_json()["mesaj"].startswith("İş emri 900110: elle stok olarak işaretlendi. Kaydedildi.")
    yanit = istemci.post(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900109')}/bagla",
                         data={"csrf": anahtar, "secim": "siparis", "siparis_no": "OZ-TS9999"}, headers=json)
    assert yanit.get_json()["tamam"] is False and "bulunamadı" in yanit.get_json()["mesaj"]
    # Betik yoksa süzgeç korunur ve sayfa bir sonraki iş emrinin yerine döner
    yanit = istemci.post(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900109')}/bagla",
                         data={"csrf": anahtar, "secim": "stok", "aile": "Çene", "sonraki": "ie-7"})
    assert yanit.headers["Location"].endswith("/yapilacaklar?aile=%C3%87ene#ie-7")


def test_projeye_ozel_urun_kodundaki_proje_kodundan_baglanir(istemci, ekip, yukle):  # noqa: F811
    from test_siparisler import satir

    yukle(excel(makine_siparisi() + [satir(6, "OZ-TS0001-PR-01", "Baglanti Catali")]))
    yukle(excel([ie(900112, 0, "OZ-TS0001-PR-01", "Baglanti Catali")], basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    assert "900112" not in istemci.get("/yapilacaklar").get_data(as_text=True)  # sorulmaz
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    diger = kart[kart.index("Aksesuarlar ve diğer kalemler"):]
    assert "OZ-TS0001-PR-01" in diger and "900112" in diger


def test_izleyici_baglayamaz(istemci, uygulama, ekle, giris, gonder, ekip, yukle):  # noqa: F811
    yuklenmis(yukle)
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    sayfa = istemci.get("/yapilacaklar").get_data(as_text=True)
    assert "900109" in sayfa and 'name="secim"' not in sayfa
    assert gonder(f"/yapilacaklar/is-emri/{ie_id(uygulama, '900109')}/bagla", secim="stok").status_code == 403
