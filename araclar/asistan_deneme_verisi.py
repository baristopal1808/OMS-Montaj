"""Yapay zekâ asistanı denemesi için uydurma veri: OMS_VERI_KLASORU klasöründeki (asistan-deneme.bat
"OMS Veri\\asistan-deneme" verir) veritabanına uydurma siparişler ve iş emirleri yükler. Klasörde
sipariş varsa dokunmaz. Gerçek veritabanına dokunmaz; değerler CLAUDE.md'deki uydurma biçimlerdedir.

Kullanım: .venv\\Scripts\\python araclar\\asistan_deneme_verisi.py
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from oms_montaj import uygulama_olustur  # noqa: E402
from oms_montaj.erp_aktarim import siparisleri_isle  # noqa: E402
from oms_montaj.erp_okuyucu import IS_EMRI_SUTUNLARI, SIPARIS_SUTUNLARI  # noqa: E402
from oms_montaj.is_emri_aktarim import is_emirlerini_bagla, is_emirlerini_isle  # noqa: E402
from oms_montaj.veritabani import baglanti  # noqa: E402

BUGUN = date.today()


def gun(fark):
    return (BUGUN + timedelta(days=fark)).isoformat()


def satir(no, sira, kod, ad, miktar=1, seri=None, aciklama=None, durum="Onaylı", genel="Açık", teslim=20,
          urun_durumu="İmalatta", son_sevk=None, detay="MAKİNA"):
    kayit = dict.fromkeys(SIPARIS_SUTUNLARI)
    kayit.update(
        siparis_no=no, sira_no=sira, urun_kodu=kod, urun_adi=ad, miktar=miktar, sevk_miktari=miktar if son_sevk else 0,
        birim="Adet", aciklama=aciklama, planlama_bilgisi=seri, erp_durum=durum, erp_genel_durum=genel,
        erp_urun_durumu=urun_durumu, detay_turu=detay, musteri="TEST FIRMA", teslim_tarihi=gun(teslim),
        talep_tarihi=gun(-60), son_sevk_tarihi=son_sevk, ilk_sevk_tarihi=son_sevk, siparis_aciklama="TEST NOT",
    )
    return kayit


def is_emri(no, sira, kod, ad, durum="Açık", plan=1, gercek=0, aciklama=None, siparis=None, acilis=-20,
            giris=None, envanter="Son Ürün"):
    """giris: ilk stok girişinin bugünden kaç gün önce olduğu (negatif); kapalı iş emri o gün kapanmış sayılır."""
    kayit = dict.fromkeys(IS_EMRI_SUTUNLARI)
    kayit.update(
        is_emri_no=str(no), sira_no=sira, urun_kodu=kod, urun_adi=ad, durum=durum, kaynak_tipi="Montaj",
        envanter_tipi=envanter, plan_miktar=plan, gercek_miktar=gercek, kalan_miktar=plan - gercek,
        acilis_tarihi=gun(acilis), baslama_tarihi=gun(acilis), tahmini_bitis=gun(acilis + 30),
        kapatma_tarihi=gun(giris) if durum == "Kapalı" and giris is not None else None,
        ilk_stok_giris=gun(giris) if giris is not None else None,
        aciklama=aciklama, erp_siparis=siparis,
    )
    return kayit


SIPARISLER = [
    # Montajı süren sipariş: SVR'nin iş emri tamamlandı, PP açık, çeneler yarıda, kiriş başlamadı
    satir("OZ-TS0001", 1, "SVR-50-NF-BSP", "Vince Asili Vibro Cakici", seri="OZ-TS0001-VH-01", aciklama="Renk: Standart"),
    satir("OZ-TS0001", 2, "PP-536-NF", "Guc Unitesi", seri="OZ-TS0001-PP-01", aciklama="Yağsız sevk edilecektir."),
    satir("OZ-TS0001", 3, "KCN-90", "Hidrolik Cene", miktar=2, seri="OZ-TS0001-HC-01 & OZ-TS0001-HC-02"),
    satir("OZ-TS0001", 4, "CB-HS5080-00", "[SVR-50-NF] - H Tipi - Kiris Montaji"),
    satir("OZ-TS0001", 5, "OZ04314", "PP Kablosuz Kumanda Seti"),
    # Teslimi geçmiş sipariş
    satir("OZ-TS0002", 1, "OVR-70-S-CV", "Ekskavatore Monteli Vibro Cakici", seri="OZ-TS0002-VH-01", teslim=-5,
          urun_durumu="Montajda"),
    satir("OZ-TS0002", 2, "SCN-75", "Hidrolik Cene", seri="OZ-TS0002-HC-01", teslim=-5),
    # Güç ünitesi siparişi: iş emri ERP'de tamamlandı, motor CAT
    satir("OZ-TS0003", 1, "PP-768-NF", "Guc Unitesi", seri="OZ-TS0003-PP-01", teslim=40,
          aciklama="TEST YAG 46 yağlı sevk", urun_durumu="Hazır"),
    satir("OZ-TS0003", 2, "OZ04082", "Uzaktan Erisim Modulu", teslim=40),
    # Onay bekleyen sipariş
    satir("OZ-TS0004", 1, "SVR-82-NF-BSP", "Vince Asili Vibro Cakici", seri="OZ-TS0004-VH-01", durum="Beklemede", teslim=70),
    # Sevk edilmiş sipariş
    satir("OZ-TS0005", 1, "PP-536-NF", "Guc Unitesi", seri="OZ-TS0005-PP-01", durum="Kapalı", genel="Kapalı",
          teslim=-30, son_sevk=gun(-25), urun_durumu="Sevke Hazır"),
]

IS_EMIRLERI = [
    is_emri(900101, 0, "SVR-50-NF-BSP", "Vince Asili Vibro Cakici", durum="Kapalı", gercek=1, giris=-3,
            siparis="SS-SA1-OZ-TS0001-1-", aciklama="OZ-TS0001 projesi için üretilecektir."),
    is_emri(900102, 0, "PP-536-NF", "Guc Unitesi", siparis="SS-SA1-OZ-TS0001-2-",
            aciklama="OZ-TS0001 - 0000 111 1011 - TEST FIRMA"),
    is_emri(900102, 25, "CP0001", "PP Yag Tanki Montaji", durum="Kapalı", gercek=1, envanter="Yarı Mamul"),
    is_emri(900102, 26, "CP0002", "PP Sogutma Modulu Montaji", envanter="Yarı Mamul"),
    is_emri(900103, 0, "KCN-90", "Hidrolik Cene", plan=2, gercek=1, aciklama="OZ-TS0001 projesi için üretilecektir.",
            giris=-2),
    is_emri(900104, 0, "CP0003", "Disli Kutusu Montaji", envanter="Yarı Mamul", aciklama="OZ-TS0001 projesi için"),
    is_emri(900105, 0, "OVR-70-S-CV", "Ekskavatore Monteli Vibro Cakici", acilis=-40,
            aciklama="OZ-TS0002 projesi için üretilecektir."),
    is_emri(900106, 0, "PP-768-NF", "Guc Unitesi", durum="Kapalı", gercek=1, giris=-1, acilis=-30,
            aciklama="OZ-TS0003-PP-01 / N5F00001 / STANDART / YAGLI SEVK"),
    is_emri(900107, 0, "OVR-70-S-CV", "Ekskavatore Monteli Vibro Cakici", aciklama="Stok için üretilecektir."),
]


def main():
    uygulama = uygulama_olustur()
    klasor = uygulama.config["VERI_KLASORU"]
    if Path(klasor).resolve() == (Path(__file__).resolve().parent.parent / "OMS Veri" / "uygulama").resolve():
        sys.exit("Bu araç gerçek veri klasörüne uydurma veri yazmaz; OMS_VERI_KLASORU ayrı bir klasörü göstermeli.")
    with uygulama.app_context():
        vt = baglanti()
        if vt.execute("SELECT 1 FROM siparisler LIMIT 1").fetchone():
            print(f"Deneme verisi zaten var: {klasor}")
            return
        with vt:
            yukleme = vt.execute(
                "INSERT INTO erp_yuklemeler (dosya_adi, kayit_adi, tur) VALUES ('uydurma veri', 'uydurma', 'siparis_talepleri')"
            ).lastrowid
            siparisleri_isle(vt, SIPARISLER, yukleme)
            is_emirlerini_isle(vt, IS_EMIRLERI, yukleme)
            is_emirlerini_bagla(vt)
            vt.execute("UPDATE siparis_kalemleri SET montaj_durumu = 'talep_acildi' WHERE urun_kodu = 'OZ04314'")
            vt.execute("UPDATE urunler SET sasi_no = 'TEST-SASI-001' WHERE seri_no = 'OZ-TS0001-VH-01'")
        print(f"Uydurma deneme verisi yüklendi: {klasor}")


if __name__ == "__main__":
    os.environ.setdefault("OMS_VERI_KLASORU", str(Path(__file__).resolve().parent.parent / "OMS Veri" / "asistan-deneme"))
    main()
