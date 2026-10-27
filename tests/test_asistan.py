"""Yapay zekâ asistanı (deneme): araçların veritabanından okuduğu bilgiler ve sağ alttaki sohbet kutusu.
Testler Anthropic'e bağlanmaz; araç işlevleri doğrudan çağrılır, soru soran işlev sahtesiyle değiştirilir.
Veriler uydurmadır."""

import json
import sqlite3

import pytest
from test_is_emirleri import IE_BASLIKLAR
from test_siparisler import ekip, excel, yukle  # noqa: F401 (pytest fikstürleri)
from test_urunler import eklentili_siparis, motorlu_is_emirleri

from oms_montaj import asistan, uygulama_olustur


@pytest.fixture
def anahtarsiz(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OMS_ANAHTAR_DOSYASI", raising=False)


def test_asistan_kapaliyken_gorunmez(istemci, ekip, gonder):  # noqa: F811
    assert "data-asistan" not in istemci.get("/").get_data(as_text=True)
    assert gonder("/asistan/sor", soru="deneme").status_code == 404


def test_sohbet_kutusu_her_sayfada_ve_karsilar(uygulama, istemci, ekip, anahtarsiz, gonder):  # noqa: F811
    uygulama.config["ASISTAN_ACIK"] = True
    for adres in ("/", "/siparisler", "/yapilacaklar"):
        sayfa = istemci.get(adres).get_data(as_text=True)
        assert "data-asistan" in sayfa and "Merhaba TEST, hoş geldiniz. Size nasıl yardımcı olabilirim" in sayfa
    assert "API anahtarı tanımlı değil" in sayfa and 'href="/asistan"' not in sayfa  # menüde ayrı sayfa yok
    cevap = gonder("/asistan/sor", soru="OZ-TS0001 siparişinin özeti nedir?").get_json()
    assert "API anahtarı tanımlı değil" in cevap["cevap"] and cevap["ozet"] == "bu ay 0 soru · ≈ 0.000 $"
    assert "OZ-TS0001 siparişinin özeti nedir?" in istemci.get("/").get_data(as_text=True)  # konuşmada kalır


def test_ozel_simge_sayfaya_gomulur(uygulama, istemci, ekip, anahtarsiz):  # noqa: F811
    uygulama.config["ASISTAN_ACIK"] = True
    assert "ozel-ikon" not in istemci.get("/").get_data(as_text=True)  # dosya yoksa uygulamanın simgesi
    klasor = uygulama.config["VERI_KLASORU"] / "marka" / "ai-logo"
    klasor.mkdir(parents=True)
    simge = klasor / "oms-ai-ikon.svg"
    simge.write_text('<?xml version="1.0"?>\n<svg class="oms-ikon" viewBox="0 0 10 10"><style>.oms-ikon rect{fill:#111}</style>'
                     '<rect width="10" height="10"/></svg>', encoding="utf-8")
    sayfa = istemci.get("/").get_data(as_text=True)
    # <img> değil, sayfanın içinde: üzerine gelince canlandırma çalışır
    assert 'class="ak-ac ozel-ikon"' in sayfa and '<svg class="oms-ikon"' in sayfa and "<?xml" not in sayfa
    assert '<span class="ak-etiket" aria-hidden="true">Montaj Asistanı</span>' in sayfa  # üzerine gelince kayan yazı
    # Betik içeren dosya gömülmez
    simge.write_text('<svg class="oms-ikon"><script>alert(1)</script></svg>', encoding="utf-8")
    sayfa = istemci.get("/").get_data(as_text=True)
    assert "alert(1)" not in sayfa and "ozel-ikon" not in sayfa


def test_konusma_hafizasi_ve_maliyet(uygulama, istemci, ekip, gonder, monkeypatch):  # noqa: F811
    uygulama.config["ASISTAN_ACIK"] = True
    gelen = []

    def sahte_sor(soru, gecmis=()):
        gelen.append(list(gecmis))
        return {"cevap": f"**Cevap:** {soru}\n- birinci madde", "araclar": ["siparis_bilgisi"],
                "giris": 1000, "cikis": 100, "maliyet": 0.00015}

    monkeypatch.setattr(asistan, "sor", sahte_sor)
    istemci.get("/")  # konuşma burada başlar
    gonder("/asistan/sor", soru="OZ-TS0001 nedir?")
    cevap = gonder("/asistan/sor", soru="Devam sorusu").get_json()
    assert gelen == [[], [("OZ-TS0001 nedir?", "**Cevap:** OZ-TS0001 nedir?\n- birinci madde")]]
    assert "<strong>Cevap:</strong> Devam sorusu" in cevap["cevap"] and "<li>birinci madde</li>" in cevap["cevap"]
    assert "Bakılan: siparis_bilgisi" in cevap["cevap"] and cevap["ozet"] == "bu ay 2 soru · ≈ 0.000 $"
    sayfa = istemci.get("/siparisler").get_data(as_text=True)  # başka sayfada da konuşma sürer
    assert "OZ-TS0001 nedir?" in sayfa and "Devam sorusu" in sayfa
    # Yeni konuşma öncekileri hatırlamaz (aynı saniyede sorulmuş olsalar da)
    assert gonder("/asistan/yeni").get_json() == {"tamam": True}
    assert "Devam sorusu" not in istemci.get("/").get_data(as_text=True)
    gonder("/asistan/sor", soru="Yeni soru")
    assert gelen[-1] == []
    assert gonder("/asistan/sor", soru="  ").status_code == 400


def test_asistan_metni_guvenli_bicimlenir():
    from oms_montaj.bicim import asistan_metni

    html = str(asistan_metni("# Özet\n**OZ-TS0001**: açık\n- SVR <script>x</script>\n- PP\n\nSon satır"))
    assert html == ("<p><strong>Özet</strong></p><p><strong>OZ-TS0001</strong>: açık</p>"
                    "<ul><li>SVR &lt;script&gt;x&lt;/script&gt;</li><li>PP</li></ul><p>Son satır</p>")


def test_baska_porttaki_kopya_ayri_cerez_kullanir(tmp_path, monkeypatch):
    monkeypatch.setenv("OMS_PORT", "8091")
    kopya = uygulama_olustur({"VERI_KLASORU": tmp_path, "SECRET_KEY": "test"})
    assert kopya.config["SESSION_COOKIE_NAME"] == "session_8091"
    monkeypatch.delenv("OMS_PORT")
    assert uygulama_olustur({"VERI_KLASORU": tmp_path, "SECRET_KEY": "test"}).config["SESSION_COOKIE_NAME"] == "session"


def test_anahtar_dosyadan_okunur(tmp_path, monkeypatch):
    dosya = tmp_path / "anahtar.txt"
    dosya.write_text("﻿test-anahtar\n", encoding="utf-8")  # Not Defteri'nin BOM'u atılır
    monkeypatch.setenv("OMS_ANAHTAR_DOSYASI", str(dosya))
    assert asistan.api_anahtari() == "test-anahtar"


def test_asistan_araclari(uygulama, ekip, yukle):  # noqa: F811
    yukle(excel(eklentili_siparis()))
    yukle(excel(motorlu_is_emirleri(), basliklar=IE_BASLIKLAR), ad="is emirleri.xlsx")
    with uygulama.app_context():
        bilgi = json.loads(asistan.siparis_bilgisi("oz-ts0001"))
        assert bilgi["musteri"] == "TEST FIRMA" and bilgi["durum"] == "Açık"
        pp = next(u for u in bilgi["urunler"] if u["aile"] == "PP")
        assert pp["is_emri"]["no"] == "900101" and pp["asama"] == "Malzeme hazırlık"
        assert pp["numaralar"]["Motor seri no"].startswith("0000 111 101")
        svr = next(u for u in bilgi["urunler"] if u["aile"] == "SVR")
        assert svr["numaralar"]["Şasi no"] == "girilmedi"
        assert bilgi["opsiyonel_ekipmanlar"][0]["montaj_durumu"] == "Sipariş talebi açılacak"
        assert "bulunamadi" in json.loads(asistan.siparis_bilgisi("OZ-TS9999"))

        bulunan = json.loads(asistan.siparis_ara("TS0001"))
        assert bulunan[0]["siparis_no"] == "OZ-TS0001"
        makine = json.loads(asistan.makine_ara("0000 111"))
        assert makine[0]["urun"].startswith("PP-536-NF")
        sevk = json.loads(asistan.sevk_edilecek_makineler_listesi())
        assert sevk["makine_sayisi"] == 2  # SVR ve PP; çene ve kiriş makine sayılmaz
        assert json.loads(asistan.sevk_edilecek_makineler_listesi(sadece_gecikenler=True))["makine_sayisi"] == 0


def test_deneme_verisi_araci(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path

    monkeypatch.setenv("OMS_VERI_KLASORU", str(tmp_path))
    yol = Path(__file__).resolve().parent.parent / "araclar" / "asistan_deneme_verisi.py"
    tanim = importlib.util.spec_from_file_location("asistan_deneme_verisi", yol)
    arac = importlib.util.module_from_spec(tanim)
    tanim.loader.exec_module(arac)
    arac.main()
    arac.main()  # ikinci kez çalışınca dokunmaz
    vt = sqlite3.connect(tmp_path / "oms-montaj.db")
    assert vt.execute("SELECT COUNT(*) FROM siparisler").fetchone()[0] == 5
    assert vt.execute("SELECT COUNT(*) FROM is_emirleri WHERE kalem_id IS NOT NULL").fetchone()[0] >= 4
    vt.close()
    uygulama_olustur({"VERI_KLASORU": tmp_path, "SECRET_KEY": "test"})  # oluşan veritabanı uygulamayla açılır
