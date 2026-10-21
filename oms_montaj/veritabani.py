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
    # 2: ERP yüklemeleri, siparişler, sipariş kalemleri ve ürün kartları
    """
    CREATE TABLE erp_yuklemeler (
        id INTEGER PRIMARY KEY,
        zaman TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        kullanici_id INTEGER REFERENCES kullanicilar(id),
        dosya_adi TEXT NOT NULL,
        kayit_adi TEXT NOT NULL,      -- veri klasöründeki yuklemeler/ altındaki kopyası
        tur TEXT,                     -- tanınan rapor türü; tanınmadıysa boş
        satir_sayisi INTEGER,
        ozet TEXT
    );

    CREATE TABLE siparisler (
        id INTEGER PRIMARY KEY,
        siparis_no TEXT NOT NULL UNIQUE,
        musteri TEXT,
        tip TEXT,                     -- makine, yedek_parca, servis
        talep_tarihi TEXT,            -- talebin onaylanıp ERP'ye girildiği gün
        notu TEXT,                    -- sipariş talebindeki "Not"
        ilk_yukleme_id INTEGER REFERENCES erp_yuklemeler(id),
        son_yukleme_id INTEGER REFERENCES erp_yuklemeler(id)
    );

    CREATE TABLE siparis_kalemleri (
        id INTEGER PRIMARY KEY,
        siparis_id INTEGER NOT NULL REFERENCES siparisler(id),
        sira_no INTEGER NOT NULL,
        urun_kodu TEXT NOT NULL,
        urun_adi TEXT,
        miktar REAL NOT NULL,
        sevk_miktari REAL,
        birim TEXT,
        aciklama TEXT,
        planlama_bilgisi TEXT,        -- seri no'lar, " & " ile ayrılmış
        bagli_is_emri_no TEXT,
        erp_durum TEXT,               -- Onaylı, Beklemede, İptal, Kapalı
        erp_genel_durum TEXT,         -- Açık, Kapalı
        erp_urun_durumu TEXT,         -- planlama biriminin elle girdiği: İmalatta, Montajda…
        detay_turu TEXT,              -- MAKİNA, YEDEK P., SERVİS
        teslim_tarihi TEXT,           -- müşteriyle uzlaşılan sevk tarihi
        ilk_sevk_tarihi TEXT,
        son_sevk_tarihi TEXT,
        tur TEXT NOT NULL,            -- kart, servis, aksesuar, parca, hizmet
        aile TEXT,                    -- kart ve servis satırlarında: SVR, OVR, PP, Çene…
        son_yukleme_id INTEGER REFERENCES erp_yuklemeler(id),
        UNIQUE (siparis_id, sira_no)
    );

    CREATE TABLE urunler (
        id INTEGER PRIMARY KEY,
        kalem_id INTEGER REFERENCES siparis_kalemleri(id),
        adet_sira INTEGER NOT NULL,   -- kalemin kaçıncı adedi
        seri_no TEXT,
        asama TEXT NOT NULL,
        olusturma TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE (kalem_id, adet_sira)
    );
    """,
    # 3: en son yüklenen sipariş listesinde bulunmayan açık siparişler gizlenir (silinmez)
    """
    ALTER TABLE siparisler ADD COLUMN erp_listede INTEGER NOT NULL DEFAULT 1;
    """,
    # 4: satırın kendi "Sipariş Açıklama"sı (iptal edilen satırda çoğu zaman iptal sebebi: "Yanlış")
    """
    ALTER TABLE siparis_kalemleri ADD COLUMN siparis_aciklama TEXT;
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
