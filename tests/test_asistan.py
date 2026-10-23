"""Yapay zekâ asistanı (deneme): araçların veritabanından okuduğu bilgiler ve sayfanın açılıp kapanması.
Testler Anthropic'e bağlanmaz; araç işlevleri doğrudan çağrılır. Veriler uydurmadır."""

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


def test_asistan_kapaliyken_gorunmez(istemci, ekip):  # noqa: F811
    assert istemci.get("/asistan").status_code == 404
    assert "/asistan" not in istemci.get("/").get_data(as_text=True)


def test_asistan_acikken_anahtar_yoksa_soyler(uygulama, istemci, ekip, anahtarsiz, gonder):  # noqa: F811
    uygulama.config["ASISTAN_ACIK"] = True
    sayfa = istemci.get("/asistan").get_data(as_text=True)
    assert "API anahtarı tanımlı değil" in sayfa and 'href="/asistan"' in sayfa
    cevap = gonder("/asistan", soru="OZ-TS0001 siparişinin özeti nedir?").get_data(as_text=True)
    assert "API anahtarı tanımlı değil" in cevap


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
        assert bilgi["pp_ye_takilacak_kalemler"][0]["montaj_durumu"] == "Sipariş talebi açılacak"
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
