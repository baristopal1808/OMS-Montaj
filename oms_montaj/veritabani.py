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
    # 5: sipariş talebi revizyonları (yüklemeden yüklemeye değişenler); seri no'su olmayan OVF ve
    # WD satırları makine değil, makinenin parçasıdır (kartları kaldırılır, kalem listede kalır)
    """
    CREATE TABLE siparis_revizyonlari (
        id INTEGER PRIMARY KEY,
        siparis_id INTEGER NOT NULL REFERENCES siparisler(id),
        sira_no INTEGER,              -- boşsa siparişin kendisi (not)
        alan TEXT NOT NULL,           -- değişen alan ya da yeni_satir, iptal, iptal_kalkti
        eski TEXT,
        yeni TEXT,
        yukleme_id INTEGER NOT NULL REFERENCES erp_yuklemeler(id)
    );
    CREATE INDEX siparis_revizyonlari_siparis ON siparis_revizyonlari (siparis_id);

    UPDATE siparis_kalemleri SET tur = 'aksesuar', aile = NULL
     WHERE tur = 'kart' AND aile IN ('OVF', 'WD')
       AND trim(replace(replace(COALESCE(planlama_bilgisi, ''), '&', ''), '-', '')) = '';
    DELETE FROM urunler WHERE kalem_id IN (SELECT id FROM siparis_kalemleri WHERE tur NOT IN ('kart', 'servis'));
    """,
    # 6: iş emirleri (açık ve kapalı listelerden), kırılımları ve sipariş satırına bağlantısı
    """
    CREATE TABLE is_emirleri (
        id INTEGER PRIMARY KEY,
        is_emri_no TEXT NOT NULL UNIQUE,
        urun_kodu TEXT,               -- ana ürün (0. satır); ana satır henüz yüklenmediyse boş
        urun_adi TEXT,
        durum TEXT,                   -- ERP: Açık, Kapalı
        kaynak_tipi TEXT,             -- Montaj, Üretim, Bakım-Onarım
        envanter_tipi TEXT,           -- Son Ürün, Yarı Mamul
        plan_miktar REAL,
        gercek_miktar REAL,           -- stoğa girilen
        kalan_miktar REAL,
        acilis_tarihi TEXT,
        baslama_tarihi TEXT,
        tahmini_bitis TEXT,
        kapatma_tarihi TEXT,
        ilk_stok_giris TEXT,
        son_stok_giris TEXT,
        aciklama TEXT,
        erp_siparis TEXT,             -- ERP'nin "Sip. No"su: …-<proje>-<sıra>-
        siparis_id INTEGER REFERENCES siparisler(id),
        kalem_id INTEGER REFERENCES siparis_kalemleri(id),
        baglanti TEXT,                -- erp, aciklama, proje, stok, kullanici; boşsa bağlanamadı
        ilk_yukleme_id INTEGER REFERENCES erp_yuklemeler(id),
        son_yukleme_id INTEGER REFERENCES erp_yuklemeler(id)
    );
    CREATE INDEX is_emirleri_siparis ON is_emirleri (siparis_id);
    CREATE INDEX is_emirleri_kalem ON is_emirleri (kalem_id);

    CREATE TABLE is_emri_satirlari (  -- kırılımlar: 0 dışındaki sıralar (alt montajlar, işlemler)
        id INTEGER PRIMARY KEY,
        is_emri_id INTEGER NOT NULL REFERENCES is_emirleri(id),
        sira_no INTEGER NOT NULL,
        urun_kodu TEXT NOT NULL,
        urun_adi TEXT,
        durum TEXT,
        envanter_tipi TEXT,
        plan_miktar REAL,
        gercek_miktar REAL,
        kalan_miktar REAL,
        UNIQUE (is_emri_id, sira_no)
    );

    ALTER TABLE urunler ADD COLUMN is_emri_id INTEGER REFERENCES is_emirleri(id);
    """,
    # 7: makine numaraları (ekibin girdiği; ERP'den okunanın önüne geçer) ve kırılımların açıklaması
    #    (motor seri no'ları çoğu zaman motor montajı kırılımının açıklamasında yazıyor)
    """
    ALTER TABLE urunler ADD COLUMN sasi_no TEXT;
    ALTER TABLE urunler ADD COLUMN motor_seri_no TEXT;
    ALTER TABLE urunler ADD COLUMN numara_degisme TEXT;          -- son değişikliğin zamanı
    ALTER TABLE urunler ADD COLUMN numara_degistiren_id INTEGER REFERENCES kullanicilar(id);
    ALTER TABLE is_emri_satirlari ADD COLUMN aciklama TEXT;
    """,
    # 8: PP'ye takılan, dışarıdan alınan kalemlerin (kablosuz kumanda seti, uzaktan erişim modülü) montaj
    #    durumu; ekip girer, ERP yüklemesi değiştirmez
    """
    ALTER TABLE siparis_kalemleri ADD COLUMN montaj_durumu TEXT;
    ALTER TABLE siparis_kalemleri ADD COLUMN montaj_degisme TEXT;
    ALTER TABLE siparis_kalemleri ADD COLUMN montaj_degistiren_id INTEGER REFERENCES kullanicilar(id);
    """,
    # 9: iş emrinin elle bağlanması (Yapılacaklar): kim, ne zaman; seçimin türü baglanti sütununda
    #    (kullanici: siparişe, kullanici_stok: stok, yok_sayildi: takip edilmiyor)
    """
    ALTER TABLE is_emirleri ADD COLUMN baglayan_id INTEGER REFERENCES kullanicilar(id);
    ALTER TABLE is_emirleri ADD COLUMN baglama_zamani TEXT;
    """,
    # 10: yapay zekâ asistanına sorulan sorular: konuşma hafızası ve maliyet takibi
    """
    CREATE TABLE asistan_sorulari (
        id INTEGER PRIMARY KEY,
        kullanici_id INTEGER REFERENCES kullanicilar(id),
        zaman TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        soru TEXT NOT NULL,
        cevap TEXT,
        hata TEXT,
        araclar TEXT,                 -- bakılan kayıtlar (araç adları, virgülle)
        giris INTEGER,                -- token
        cikis INTEGER,
        maliyet REAL                  -- dolar, yaklaşık
    );
    """,
    # 11: iki motorlu güç ünitelerinde (PP-1072, PP-1536…) ikinci motorun seri no'su (ekibin girdiği)
    """
    ALTER TABLE urunler ADD COLUMN motor2_seri_no TEXT;
    """,
    # 12: çıkış yapılamayan malzeme (açık iş emirlerinin eksik malzemeleri; her yüklemede baştan yazılır),
    #     ekibin "bilginiz var mı?" cevapları ve "iş emri stoğa girmiş ama ERP İmalatta" cevapları
    """
    CREATE TABLE eksik_malzemeler (
        id INTEGER PRIMARY KEY,
        is_emri_no TEXT NOT NULL,
        sira_no INTEGER NOT NULL,     -- iş emrinin kırılımı (0: ana ürün)
        malzeme_kodu TEXT NOT NULL,
        malzeme_adi TEXT,
        envanter_turu TEXT,
        birim TEXT,
        plan_miktar REAL,             -- planlanan takip miktarı
        cikis_miktar REAL,            -- gerçekleşen çıkış; eksik = plan - çıkış
        eldeki REAL,                  -- bütün depolarda
        ana_urun_depo REAL,
        uretim_depo REAL,
        montaj_depo REAL,
        montaj_uretim_depo REAL,
        sevk_depo REAL,
        yukleme_id INTEGER REFERENCES erp_yuklemeler(id)
    );
    CREATE INDEX eksik_malzemeler_is_emri ON eksik_malzemeler (is_emri_no);

    CREATE TABLE eksik_cevaplari (      -- en sonuncusu geçerli; cevaptan sonra yeni eksik gelirse yeniden sorulur
        id INTEGER PRIMARY KEY,
        is_emri_no TEXT NOT NULL,
        cevap TEXT NOT NULL,
        eksikler TEXT NOT NULL,       -- cevap anındaki eksikler (JSON: "sıra|malzeme" → miktar)
        kullanici_id INTEGER REFERENCES kullanicilar(id),
        zaman TEXT NOT NULL
    );
    CREATE INDEX eksik_cevaplari_is_emri ON eksik_cevaplari (is_emri_no);

    CREATE TABLE imalatta_cevaplari (   -- her ürün ve iş emri için ayrı sorulur
        urun_id INTEGER NOT NULL REFERENCES urunler(id),
        is_emri_id INTEGER NOT NULL REFERENCES is_emirleri(id),
        cevap TEXT NOT NULL,
        kullanici_id INTEGER REFERENCES kullanicilar(id),
        zaman TEXT NOT NULL,
        PRIMARY KEY (urun_id, is_emri_id)
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
