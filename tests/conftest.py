"""Testler için ortak hazırlık. Her test boş bir geçici veri klasörüyle çalışır;
gerçek veriye (OMS Veri) dokunulmaz. Adlar ve şifreler uydurmadır."""

import pytest

from oms_montaj import uygulama_olustur
from oms_montaj.kimlik import kullanici_ekle

SIFRE = "gizli-sifre-1"


@pytest.fixture
def uygulama(tmp_path):
    return uygulama_olustur({"VERI_KLASORU": tmp_path, "TESTING": True, "SECRET_KEY": "test"})


@pytest.fixture
def istemci(uygulama):
    return uygulama.test_client()


@pytest.fixture
def gonder(istemci):
    """Formu, oturumdaki CSRF anahtarıyla birlikte gönderir."""

    def _gonder(adres, **veri):
        with istemci.session_transaction() as oturum:
            oturum.setdefault("csrf", "test-csrf")
            anahtar = oturum["csrf"]
        return istemci.post(adres, data={"csrf": anahtar, **veri})

    return _gonder


@pytest.fixture
def ekle(uygulama):
    """Veritabanına doğrudan hesap ekler."""

    def _ekle(kullanici_adi="test.kullanici", rol="ekip", sifre=SIFRE, degismeli=False):
        with uygulama.app_context():
            return kullanici_ekle(kullanici_adi, "TEST KULLANICI", rol, sifre, sifre_degismeli=degismeli)

    return _ekle


@pytest.fixture
def giris(gonder):
    def _giris(kullanici_adi="test.kullanici", sifre=SIFRE):
        return gonder("/giris", kullanici_adi=kullanici_adi, sifre=sifre)

    return _giris
