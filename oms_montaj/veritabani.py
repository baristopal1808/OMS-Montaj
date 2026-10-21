"""SQLite veritabanı: istek başına bağlantı ve şema göçleri.

Şemanın sürümü veritabanının içinde (PRAGMA user_version) tutulur. Uygulama her
açılışta eksik göçleri sırayla uygular; böylece sunucudaki veritabanı yeni
sürüme veri kaybetmeden geçer. Yayınlanmış bir göç değiştirilmez; yenisi
listenin sonuna eklenir.
"""

import sqlite3
from contextlib import closing

from flask import current_app, g

GOCLER = [
    # 1: kullanıcılar
    """
    CREATE TABLE kullanicilar (
        id INTEGER PRIMARY KEY,
        kullanici_adi TEXT NOT NULL UNIQUE COLLATE NOCASE,
        ad_soyad TEXT NOT NULL,
        rol TEXT NOT NULL CHECK (rol IN ('ekip', 'izleyici')),
        sifre_ozeti TEXT NOT NULL,
        sifre_degismeli INTEGER NOT NULL DEFAULT 1,
        aktif INTEGER NOT NULL DEFAULT 1,
        olusturma TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
    );
    """,
]


def ac(yol):
    baglanti_ = sqlite3.connect(yol)
    baglanti_.row_factory = sqlite3.Row
    baglanti_.execute("PRAGMA foreign_keys = ON")
    return baglanti_


def goc_uygula(baglanti_):
    surum = baglanti_.execute("PRAGMA user_version").fetchone()[0]
    for no in range(surum + 1, len(GOCLER) + 1):
        baglanti_.executescript(f"BEGIN; {GOCLER[no - 1]} PRAGMA user_version = {no}; COMMIT;")


def hazirla(uygulama):
    with closing(ac(uygulama.config["VERITABANI"])) as baglanti_:
        # WAL: biri yazarken diğerleri okumaya devam edebilir.
        baglanti_.execute("PRAGMA journal_mode = WAL")
        goc_uygula(baglanti_)
    uygulama.teardown_appcontext(kapat)


def baglanti():
    """Bu isteğin veritabanı bağlantısı; istek bitince kapanır."""
    if "vt" not in g:
        g.vt = ac(current_app.config["VERITABANI"])
    return g.vt


def kapat(_hata=None):
    vt = g.pop("vt", None)
    if vt is not None:
        vt.close()
