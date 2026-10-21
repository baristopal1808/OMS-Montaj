"""Sipariş talepleri listesinin yüklenmesi, siparişler listesi ve sipariş kartı.

Excel dosyaları test anında uydurma veriyle üretilir; sütun başlıkları ERP'ninkilerle aynıdır.
"""

import io
from datetime import datetime
from pathlib import Path

import openpyxl
import pytest
from PIL import Image

from oms_montaj.erp_okuyucu import OkumaHatasi, rapor_turu, siparis_satirlari, tablo_oku, tarih
from oms_montaj.urun_kurallari import model, renk, satir_turu, seri_nolar, yag

BASLIKLAR = [
    "Ürün Kodu", "Ürün Adı", "Sip.Durumu", "Firma Adı", "Sipariş No", "Sipariş Miktar",
    "Sevk/Kont.Gelen Miktarı", "Satış Birimi", "Uzlaşılan Sevk Tar.", "Açıklama", "İlk Sevk Tarihi",
    "Son Sevk Tarihi", "Sipariş Ürün Genel Durum", "Sip.Sıra No", "Planlama Bilgisi", "Sip.Geliş Tarihi",
    "Sipariş Açıklama", "Bağlı İşemri No", "Sipariş Detay Türü", "Ürün Durumu",
]


def satir(sira, kod, ad, miktar=1, siparis_no="OZ-TS0001", planlama=None, aciklama=None, durum="Onaylı",
          genel="Açık", teslim=datetime(2030, 1, 15), detay="MAKİNA", son_sevk=None, is_emri=None):
    return {
        "Ürün Kodu": kod, "Ürün Adı": ad, "Sip.Durumu": durum, "Firma Adı": "TEST FIRMA",
        "Sipariş No": siparis_no, "Sipariş Miktar": miktar, "Sevk/Kont.Gelen Miktarı": 0, "Satış Birimi": "Adet",
        "Uzlaşılan Sevk Tar.": teslim, "Açıklama": aciklama, "Son Sevk Tarihi": son_sevk,
        "Sipariş Ürün Genel Durum": genel, "Sip.Sıra No": sira, "Planlama Bilgisi": planlama,
        "Sip.Geliş Tarihi": datetime(2029, 12, 1), "Sipariş Açıklama": "TEST NOT", "Bağlı İşemri No": is_emri,
        "Sipariş Detay Türü": detay, "Ürün Durumu": "İmalatta",
    }


def makine_siparisi(**degisen):
    satirlar = [
        satir(1, "SVR-50-NF-BSP", "Vince Asili Vibro Cakici", planlama="OZ-TS0001-VH-01", aciklama="Renk: Standart"),
        satir(2, "PP-536-NF", "Guc Unitesi", planlama="OZ-TS0001-PP-01", aciklama="Yağsız sevk edilecektir.", is_emri=900101),
        satir(3, "KCN-90", "Hidrolik Cene", miktar=2, planlama="OZ-TS0001-HC-01 & OZ-TS0001-HC-02"),
        satir(4, "CB-HS5080-00", "[SVR-50-NF] - H Tipi - Kiris Montaji"),
        satir(5, "OZ00001", "Hortum Seti", miktar=3),
    ]
    for sira, alanlar in degisen.items():
        satirlar[int(sira[1:]) - 1].update(alanlar)
    return satirlar


def excel(satirlar, basliklar=BASLIKLAR, ust_satir=None):
    kitap = openpyxl.Workbook()
    sayfa = kitap.active
    if ust_satir:
        sayfa.append([ust_satir])
    sayfa.append(basliklar)
    for s in satirlar:
        sayfa.append([s.get(b) for b in basliklar])
    tampon = io.BytesIO()
    kitap.save(tampon)
    return tampon.getvalue()


@pytest.fixture
def yukle(gonder):
    def _yukle(veri, ad="siparis talepleri.xlsx"):
        return gonder("/erp-yukleme", dosyalar=(io.BytesIO(veri), ad))

    return _yukle


@pytest.fixture
def ekip(ekle, giris):
    ekle()
    giris()


def sorgu(uygulama, sql, *degerler):
    with uygulama.app_context():
        from oms_montaj.veritabani import baglanti

        return baglanti().execute(sql, degerler).fetchall()


# Kurallar

@pytest.mark.parametrize(
    "kod, detay, beklenen",
    [
        ("SVR-50-NF-BSP", "MAKİNA", ("kart", "SVR")),
        ("KCN-90", "MAKİNA", ("kart", "Çene")),
        ("CB-HS5080-00", "MAKİNA", ("kart", "Kiriş")),
        ("OVR-70-S-HH-BSP", "MAKİNA", ("aksesuar", None)),
        ("PP-536-VM-MNT", "SERVİS", ("servis", "PP")),
        ("OZ00001", "YEDEK P.", ("parca", None)),
        ("HZ0001", "YEDEK P.", ("hizmet", None)),
        ("OZ00002", "MAKİNA", ("aksesuar", None)),
    ],
)
def test_satir_turu(kod, detay, beklenen):
    assert satir_turu(kod, detay) == beklenen


def test_seri_nosuz_ovf_ve_wd_makinenin_parcasidir():
    assert satir_turu("OVF-300-4BF-BSP", "MAKİNA", "OZ-TS0001-OVF-01") == ("kart", "OVF")
    assert satir_turu("OVF-300-BF-LM-B", "MAKİNA", None) == ("aksesuar", None)
    assert satir_turu("WD-28-43-PV", "MAKİNA", "-") == ("aksesuar", None)
    assert satir_turu("SVR-50-NF-BSP", "MAKİNA", None) == ("kart", "SVR")  # yalnızca OVF ve WD


def test_aciklama_ve_planlama_bilgisi_okunur():
    assert model("SVR-120-NF-BSP") == "SVR-NF"
    assert model("OVR-60-SG-01") == "OVR-SG"
    assert model("KCN-90") == "KCN"
    assert renk("Renk: Standart") == "Standart"
    assert renk(None) is None
    assert yag("Yağsız sevk edilecektir.") == ("yagsiz", None)
    assert yag("TEST YAG 46 yağlı sevk")[0] == "yagli"
    assert yag("TEST YAG (ISO VG 68) - Hidrolik Yag")[0] == "yagli"
    assert yag("Renk: Sarı") is None
    assert seri_nolar("OZ-TS0001-HC-01 & OZ-TS0001-HC-02") == ["OZ-TS0001-HC-01", "OZ-TS0001-HC-02"]
    assert seri_nolar("-") == []


# ERP okuyucu

def test_tarih_bicimleri():
    assert tarih(46329) == "2026-11-03"
    assert tarih("03/11/2026") == "2026-11-03"
    assert tarih(datetime(2026, 11, 3, 15, 30)) == "2026-11-03"
    assert tarih("") is None


def test_ustte_baslik_satiri_olan_rapor_okunur(tmp_path):
    yol = tmp_path / "rapor.xlsx"
    yol.write_bytes(excel(makine_siparisi(), ust_satir="TEST RAPORU"))
    basliklar, satirlar = tablo_oku(yol)
    assert rapor_turu(basliklar) == "siparis_talepleri"
    kayitlar = siparis_satirlari(basliklar, satirlar)
    assert len(kayitlar) == 5
    assert kayitlar[1]["bagli_is_emri_no"] == "900101"
    assert kayitlar[0]["teslim_tarihi"] == "2030-01-15"


def test_eksik_sutun_soylenir():
    with pytest.raises(OkumaHatasi, match="Sipariş Miktar"):
        siparis_satirlari(["Sipariş No", "Sip.Sıra No", "Ürün Kodu"], [])


# Yükleme

def test_siparis_yuklenir_urun_kartlari_acilir(uygulama, ekip, yukle):
    yanit = yukle(excel(makine_siparisi()))
    assert yanit.status_code == 302
    assert sorgu(uygulama, "SELECT COUNT(*) FROM siparisler")[0][0] == 1
    urunler = sorgu(
        uygulama,
        "SELECT k.urun_kodu, u.seri_no, u.asama FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
        " ORDER BY k.sira_no, u.adet_sira",
    )
    assert [tuple(u) for u in urunler] == [
        ("SVR-50-NF-BSP", "OZ-TS0001-VH-01", "siparis"),
        ("PP-536-NF", "OZ-TS0001-PP-01", "siparis"),
        ("KCN-90", "OZ-TS0001-HC-01", "siparis"),
        ("KCN-90", "OZ-TS0001-HC-02", "siparis"),
        ("CB-HS5080-00", None, "siparis"),
    ]
    yuklenen = list((Path(uygulama.config["VERI_KLASORU"]) / "yuklemeler").iterdir())
    assert len(yuklenen) == 1


def test_ayni_dosya_ikinci_kez_yuklenince_kopya_olusmaz(uygulama, istemci, ekip, yukle):
    yukle(excel(makine_siparisi()))
    yukle(excel(makine_siparisi()))
    assert sorgu(uygulama, "SELECT COUNT(*) FROM urunler")[0][0] == 5
    assert "değişiklik yok" in istemci.get("/erp-yukleme").get_data(as_text=True)


def test_miktar_artinca_yeni_kart_acilir(uygulama, ekip, yukle):
    yukle(excel(makine_siparisi()))
    yukle(excel(makine_siparisi(s3={"Sipariş Miktar": 3})))
    assert sorgu(uygulama, "SELECT COUNT(*) FROM urunler")[0][0] == 6


def test_ilk_kez_kapali_gelen_satir_sevk_edildi_olur_iptal_satira_kart_acilmaz(uygulama, ekip, yukle):
    yukle(excel(makine_siparisi(
        s1={"Sipariş Ürün Genel Durum": "Kapalı", "Sip.Durumu": "Kapalı", "Son Sevk Tarihi": datetime(2029, 12, 20)},
        s3={"Sip.Durumu": "İptal"},
    )))
    asamalar = sorgu(
        uygulama,
        "SELECT k.urun_kodu, u.asama FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id ORDER BY k.sira_no",
    )
    assert dict((a[0], a[1]) for a in asamalar)["SVR-50-NF-BSP"] == "sevk_edildi"
    assert "KCN-90" not in {a[0] for a in asamalar}


def test_izleyici_yukleyemez(ekle, giris, yukle):
    ekle("test.izleyici", rol="izleyici")
    giris("test.izleyici")
    assert yukle(excel(makine_siparisi())).status_code == 403


def test_taninmayan_ve_yanlis_turdeki_dosya(istemci, ekip, yukle):
    yukle(excel([{"A": 1}], basliklar=["A", "B", "C"]), ad="baska.xlsx")
    yukle(b"a;b", ad="liste.csv")
    sayfa = istemci.get("/erp-yukleme").get_data(as_text=True)
    assert "Rapor türü tanınamadı" in sayfa


# Ekranlar

def test_liste_acik_siparisleri_teslim_tarihiyle_gosterir(istemci, ekip, yukle):
    yukle(excel(makine_siparisi() + [
        satir(1, "SVR-50-NF-BSP", "Vince Asili Vibro Cakici", siparis_no="OZ-TS0002",
              genel="Kapalı", durum="Kapalı", son_sevk=datetime(2029, 12, 20)),
        satir(1, "PP-536-NF", "Guc Unitesi", siparis_no="OZ-TS0003", durum="Beklemede", teslim=datetime(2020, 1, 1)),
    ]))
    sayfa = istemci.get("/siparisler").get_data(as_text=True)
    assert "OZ-TS0001" in sayfa and "Teslim 15/01/2030" in sayfa
    assert "OZ-TS0002" not in sayfa
    assert 'class="onay-bekliyor"' in sayfa and "gün geçti" in sayfa
    assert "OZ-TS0002" in istemci.get("/siparisler?durum=kapali").get_data(as_text=True)


def test_liste_suzgecleri_ve_arama(istemci, ekip, yukle):
    yukle(excel(makine_siparisi() + [satir(1, "PP-536-NF", "Guc Unitesi", siparis_no="OZ-TS0003")]))
    vibro = istemci.get("/siparisler?aile=vibrohammer").get_data(as_text=True)
    assert "OZ-TS0001" in vibro and "OZ-TS0003" not in vibro
    bulunan = istemci.get("/siparisler?ara=HC-02").get_data(as_text=True)
    assert "OZ-TS0001" in bulunan and "OZ-TS0003" not in bulunan


def test_siparis_karti_bolumleri_gosterir(istemci, ekip, yukle):
    yukle(excel(makine_siparisi()))
    sayfa = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    for beklenen in ("SVR · Vinç asılı vibro çakıcı", "OZ-TS0001-VH-01", "Renk: Standart", "Yağsız sevk",
                     "OZ-TS0001-HC-02", "Kiriş", "Aksesuarlar", "Hortum Seti", "İş emri 900101",
                     "Planlama birimi ürün üretim durumu", "TEST NOT", "TEST FIRMA"):
        assert beklenen in sayfa, beklenen


def test_atlanan_satir_numaralari_bildirilir(istemci, ekip, yukle):
    satirlar = makine_siparisi()
    del satirlar[3]  # 4. satır listede yok
    yukle(excel(satirlar))
    assert "1 siparişte toplam 1 satır listede yok" in istemci.get("/erp-yukleme").get_data(as_text=True)
    assert "Siparişin 4. satırı yüklenen ERP listesinde yok" in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)


def test_yag_bilgisi_olmayan_pp_icin_uyari(istemci, ekip, yukle):
    yukle(excel(makine_siparisi(s2={"Açıklama": None})))
    assert "Yağ bilgisi yok" in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)


def gecikmis_ve_ileri_siparis():
    return makine_siparisi() + [
        satir(1, "PP-536-NF", "Guc Unitesi", siparis_no="OZ-TS0003", teslim=datetime(2020, 1, 1)),
    ]


def onay_bekleyen_siparis():
    return [satir(1, "PP-536-NF", "Guc Unitesi", siparis_no="OZ-TS0004", durum="Beklemede", teslim=datetime(2020, 1, 1))]


def test_acik_siparisler_teslim_sutunlarinda(istemci, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis() + onay_bekleyen_siparis()))
    sayfa = istemci.get("/siparisler").get_data(as_text=True)
    gecikenler, planlanan, onay = (sayfa.index(ad) for ad in ("Gecikenler", "Planlananlar", "Onay bekleyen projeler"))
    # Onay bekleyen sipariş teslimi geçmiş olsa da gecikenlerde değil, en sağdaki sütunda durur.
    assert gecikenler < sayfa.index("OZ-TS0003") < planlanan < sayfa.index("OZ-TS0001") < onay < sayfa.index("OZ-TS0004")
    assert 'href="/siparisler/OZ-TS0001#aile-SVR"' in sayfa
    yalniz_onay = istemci.get("/siparisler?durum=onay_bekliyor").get_data(as_text=True)
    assert "OZ-TS0004" in yalniz_onay and "Gecikenler" not in yalniz_onay and "OZ-TS0001" not in yalniz_onay


def test_onay_bekleyenler_sevk_edileceklere_girmez(istemci, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis() + onay_bekleyen_siparis()))
    makineler = istemci.get("/makineler").get_data(as_text=True)
    assert "OZ-TS0003" in makineler and "OZ-TS0004" not in makineler
    ozet = istemci.get("/").get_data(as_text=True)
    assert '<span class="gosterge-deger">3</span>' in ozet  # sevk edilecek makine: onay bekleyen PP sayılmaz
    assert "sipariş · 1 makine" in ozet  # teslimi geçen: onay bekleyen sayılmaz


def test_ozet_sayilari_ve_grafikleri(istemci, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis()))
    sayfa = istemci.get("/").get_data(as_text=True)
    assert '<span class="gosterge-deger">2</span>' in sayfa  # açık sipariş
    assert '<span class="gosterge-deger">3</span>' in sayfa  # sevk edilecek makine: SVR + PP + PP; çene, kiriş sayılmaz
    assert "sipariş · 1 makine" in sayfa  # teslimi geçen
    assert 'href="/makineler?aile=PP"' in sayfa and 'aile=Çene' not in sayfa
    assert 'href="/siparisler?teslim=gecikti"' in sayfa and 'href="/makineler?bas=' in sayfa
    assert 'href="/makineler?planlama=' in sayfa and 'href="/makineler?teslim=gecikti"' in sayfa
    assert "İmalatta" in sayfa and "Haftalık teslim takvimi" in sayfa
    tablo = sayfa[sayfa.index('<table class="tablo">'):]
    assert "OZ-TS0003" in tablo and "OZ-TS0001" not in tablo


def test_teslim_suzgeci_tek_sutunu_gosterir(istemci, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis()))
    sayfa = istemci.get("/siparisler?teslim=gecikti").get_data(as_text=True)
    assert "OZ-TS0003" in sayfa and "OZ-TS0001" not in sayfa
    assert 'Yalnızca "Gecikenler" gösteriliyor' in sayfa


def test_takvimden_gelen_tarih_araligi(istemci, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis()))
    sayfa = istemci.get("/siparisler?bas=2030-01-14&bit=2030-01-20").get_data(as_text=True)
    assert "OZ-TS0001" in sayfa and "OZ-TS0003" not in sayfa
    assert "Makine teslimi 14/01/2030–20/01/2030 arasında olan siparişler" in sayfa


def yedek_parca_siparisi(**degisen):
    return [satir(1, "OZ00001", "TEST PARCA", miktar=32, siparis_no="OZ-TS0004", detay="YEDEK P.", **degisen),
            satir(2, "HZ0001", "Nakliye", siparis_no="OZ-TS0004", detay="YEDEK P.", **degisen)]


def test_yedek_parca_kendi_ekraninda(istemci, ekip, yukle):
    yukle(excel(makine_siparisi() + yedek_parca_siparisi()))
    ekran = istemci.get("/yedek-parca").get_data(as_text=True)
    assert "OZ-TS0004" in ekran and "OZ-TS0001" not in ekran
    assert "OZ-TS0004" not in istemci.get("/siparisler").get_data(as_text=True)
    assert "OZ-TS0004" in istemci.get("/siparisler?tip=yedek_parca").get_data(as_text=True)


def test_sevkiyat_ceyrege_gore(istemci, ekip, yukle):
    bugun = datetime.now()
    kapali = {"genel": "Kapalı", "durum": "Kapalı", "son_sevk": bugun}
    yukle(excel(makine_siparisi(s1={
        "Sipariş Ürün Genel Durum": "Kapalı", "Sip.Durumu": "Kapalı", "Son Sevk Tarihi": bugun,
    }) + yedek_parca_siparisi(**kapali)))
    ceyrek = f"{bugun.year}-{(bugun.month - 1) // 3 + 1}"
    sayfa = istemci.get("/sevkiyat").get_data(as_text=True)
    assert f'href="/sevkiyat?ceyrek={ceyrek}" class="etkin"' in sayfa
    assert "OZ-TS0001" in sayfa and 'href="/siparisler/OZ-TS0001#aile-SVR"' in sayfa
    yedek = sayfa[sayfa.index("Yedek parça sevkiyatı"):]
    assert "OZ-TS0004" in yedek and "32 adet" in yedek
    assert "Bu çeyrekte sevk edilen makine yok" in istemci.get("/sevkiyat?ceyrek=2020-1").get_data(as_text=True)
    ozet = istemci.get("/").get_data(as_text=True)
    sevk_kutusu = ozet[ozet.index('class="gosterge" href="/sevkiyat"'):]
    assert '<span class="gosterge-deger">1</span>' in sevk_kutusu[:400]


def test_son_listede_olmayan_acik_siparis_gizlenir_ve_geri_gelir(istemci, uygulama, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis()))
    yanit = yukle(excel(makine_siparisi()))  # OZ-TS0003 bu listede yok
    assert yanit.status_code == 302
    assert "1 açık sipariş yüklenen listede yok" in istemci.get("/erp-yukleme").get_data(as_text=True)
    assert "OZ-TS0003" not in istemci.get("/siparisler").get_data(as_text=True)
    assert "OZ-TS0003" in istemci.get("/siparisler?durum=listede_yok").get_data(as_text=True)
    assert sorgu(uygulama, "SELECT COUNT(*) FROM siparisler")[0][0] == 2  # silinmedi
    yukle(excel(gecikmis_ve_ileri_siparis()))
    assert "OZ-TS0003" in istemci.get("/siparisler").get_data(as_text=True)


def test_ayni_satirin_iptal_kaydi_gecerli_kaydi_ezmez(uygulama, ekip, yukle):
    satirlar = makine_siparisi()
    satirlar.append(satir(1, "SVR-50-NF-BSP", "Vince Asili Vibro Cakici", durum="İptal", genel="İptal"))
    yukle(excel(satirlar))
    assert sorgu(uygulama, "SELECT erp_durum FROM siparis_kalemleri WHERE sira_no = 1")[0][0] == "Onaylı"
    assert sorgu(uygulama, "SELECT COUNT(*) FROM urunler")[0][0] == 5


def duzeltilmis_siparis():
    """Yanlış girilip "Yanlış" notuyla iptal edilen satırlar, geçerli satırlarla aynı numarayı taşıyor."""
    yanlis = {"durum": "İptal", "genel": "İptal"}
    return [
        satir(1, "SVR-50-NF-BSP", "Vince Asili Vibro Cakici", planlama="OZ-TS0001-VH-01"),
        {**satir(1, "SVR-50-NF-BSP", "Vince Asili Vibro Cakici", **yanlis), "Sipariş Açıklama": "Yanlış"},
        {**satir(2, "PP-536-NF", "Guc Unitesi", **yanlis), "Sipariş Açıklama": "Yanlış"},
        satir(3, "PP-536-NF", "Guc Unitesi", planlama="OZ-TS0001-PP-01", aciklama="Yağsız sevk edilecektir."),
        {**satir(3, "SCN-165", "Hidrolik Cene", **yanlis), "Sipariş Açıklama": "Yanlış"},
        satir(4, "SCN-165-T", "Hidrolik Cene", planlama="OZ-TS0001-HC-01"),
    ]


def test_yanlis_girilip_iptal_edilen_satirlar_siparisi_bozmaz(istemci, uygulama, ekip, yukle):
    # Önce eski sürümün bıraktığı yanlış durum: 1. ve 3. satırların yalnızca iptal kaydı
    satirlar = duzeltilmis_siparis()
    yukle(excel([satirlar[1], satirlar[2], satirlar[4], satirlar[5]]))
    yukle(excel(satirlar))
    kalemler = sorgu(uygulama, "SELECT sira_no, urun_kodu, erp_durum FROM siparis_kalemleri ORDER BY sira_no")
    assert [tuple(k) for k in kalemler] == [
        (1, "SVR-50-NF-BSP", "Onaylı"), (2, "PP-536-NF", "İptal"), (3, "PP-536-NF", "Onaylı"), (4, "SCN-165-T", "Onaylı"),
    ]
    assert sorgu(uygulama, "SELECT notu FROM siparisler")[0][0] == "TEST NOT"
    sayfa = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    bolumler, iptaller = sayfa.split("İptal edilen satırlar")
    assert "OZ-TS0001-PP-01" in bolumler and "Yağsız sevk" in bolumler
    assert "2. satır" in iptaller and "ERP açıklaması: Yanlış" in iptaller
    assert "Not:</strong> Yanlış" not in sayfa


def test_dis_tedarik_kalemde_erp_durumu_gosterilmez(istemci, ekip, yukle):
    yukle(excel(makine_siparisi()))
    sayfa = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    aksesuar = sayfa[sayfa.index("Aksesuarlar ve diğer kalemler"):]
    assert "Dış tedarik" in aksesuar and "Planlama birimi ürün üretim durumu" not in aksesuar
    assert "Planlama birimi ürün üretim durumu" in sayfa[:sayfa.index("Aksesuarlar ve diğer kalemler")]


def test_ozet_satirlari_tiklanir_ve_kutucuklar_renkli(istemci, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis()))
    sayfa = istemci.get("/").get_data(as_text=True)
    assert 'data-adres="/siparisler/OZ-TS0003"' in sayfa
    assert 'class="sk-urun renkli" style="--renk: #1baf7a"' in sayfa  # PP her yerde aynı renk


def test_seri_nosuz_ovf_parcasi_makine_sayilmaz(istemci, ekip, yukle):
    yukle(excel([
        satir(1, "OVF-300-4BF-BSP", "Zemin Iyilestirme", planlama="OZ-TS0001-OVF-01"),
        satir(2, "OVF-300-BF-LM-B", "TEST PARCA", miktar=2),
    ]))
    assert "1 makine · 1 proje" in istemci.get("/makineler").get_data(as_text=True)
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    diger = kart[kart.index("Aksesuarlar ve diğer kalemler"):]
    assert "OVF-300-BF-LM-B" in diger and "OVF-300-4BF-BSP" not in diger


def test_revizyonlar_sipariste_gorunur(istemci, ekip, yukle):
    yukle(excel(makine_siparisi()))
    yukle(excel(makine_siparisi()))  # aynı liste: revizyon yok
    assert "Revize" not in istemci.get("/siparisler").get_data(as_text=True)
    assert "revizyonlar" not in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)

    degisen = makine_siparisi(s1={"Uzlaşılan Sevk Tar.": datetime(2030, 2, 1)}, s2={"Açıklama": "TEST YAG 46 yağlı sevk"})
    degisen[3]["Sip.Durumu"] = "İptal"
    degisen[0]["Sipariş Açıklama"] = degisen[1]["Sipariş Açıklama"] = degisen[2]["Sipariş Açıklama"] = "TEST NOT 2"
    degisen[4]["Sipariş Açıklama"] = "TEST NOT 2"
    degisen.append(satir(6, "OZ00002", "Kablosuz Kumanda Seti"))
    degisen[5]["Sipariş Açıklama"] = "TEST NOT 2"
    yukle(excel(degisen))
    assert "1 siparişte revizyon var" in istemci.get("/erp-yukleme").get_data(as_text=True)
    assert 'class="etiket revize"' in istemci.get("/siparisler").get_data(as_text=True)
    kart = istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    bolum = kart[kart.index('id="revizyonlar"'):]
    for beklenen in ("Teslim tarihi", "15/01/2030", "01/02/2030", "Açıklama", "Yağsız sevk edilecektir.",
                     "TEST YAG 46 yağlı sevk", "Yeni satır eklendi", "OZ00002 · 1 Adet", "Satır iptal edildi",
                     "Sipariş notu", "TEST NOT 2"):
        assert beklenen in bolum, beklenen
    assert "Revize edildi" in kart[:kart.index('id="revizyonlar"')]


def test_raporda_olmayan_sutun_revizyon_sayilmaz(istemci, ekip, yukle):
    yukle(excel(makine_siparisi()))
    yukle(excel(makine_siparisi(), basliklar=[b for b in BASLIKLAR if b not in ("Açıklama", "Planlama Bilgisi")]))
    assert "revizyonlar" not in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)


def test_makineler_sayfasi_suzgecleri(istemci, ekip, yukle):
    yukle(excel(gecikmis_ve_ileri_siparis()))
    tumu = istemci.get("/makineler").get_data(as_text=True)
    assert "3 makine · 2 proje" in tumu  # çene ve kiriş sayılmaz
    assert "OZ-TS0001-VH-01" in tumu and "OZ-TS0001-HC-01" not in tumu
    gecikmis = istemci.get("/makineler?teslim=gecikti").get_data(as_text=True)
    assert "OZ-TS0003" in gecikmis and "OZ-TS0001" not in gecikmis
    hafta = istemci.get("/makineler?bas=2030-01-14&bit=2030-01-20").get_data(as_text=True)
    assert "OZ-TS0001" in hafta and "OZ-TS0003" not in hafta
    assert "OZ-TS0003" in istemci.get("/makineler?aile=PP").get_data(as_text=True)
    assert "Bu seçime uyan makine yok" in istemci.get("/makineler?planlama=Montajda").get_data(as_text=True)
    imalatta = istemci.get("/makineler?planlama=İmalatta").get_data(as_text=True)
    assert "3 makine" in imalatta and 'class="etkin" aria-current="page">\n    İmalatta' in imalatta


def test_musteriye_ozel_renk_ve_logo(istemci, uygulama, ekip, yukle):
    marka = Path(uygulama.config["VERI_KLASORU"]) / "marka"
    (marka / "musteriler.txt").write_text("# deneme\nTS0;#0e518d\n", encoding="utf-8")
    resim = Image.new("RGBA", (40, 20), (0, 0, 0, 255))
    resim.save(marka / "musteri-TS0.png")
    yukle(excel(makine_siparisi()))
    liste = istemci.get("/siparisler").get_data(as_text=True)
    assert "musterili" in liste and "--musteri-renk: #0e518d" in liste and "/marka/musteri/TS0?s=" in liste
    assert "musterili" in istemci.get("/siparisler/OZ-TS0001").get_data(as_text=True)
    assert istemci.get("/marka/musteri/TS0").mimetype == "image/png"
    assert istemci.get("/marka/musteri/XX9").status_code == 404
    # Logo dosyasının adı ayar satırına yazılabilir; klasör adı yazılamaz.
    (marka / "musteri-TS0.png").rename(marka / "test-firma-logo.png")
    (marka / "musteriler.txt").write_text("TS0;#0e518d;test-firma-logo.png\n", encoding="utf-8")
    assert istemci.get("/marka/musteri/TS0").mimetype == "image/png"
    (marka / "musteriler.txt").write_text("TS0;#0e518d;../test-firma-logo.png\n", encoding="utf-8")
    assert istemci.get("/marka/musteri/TS0").status_code == 404
    assert "--musteri-renk: #0e518d" in istemci.get("/siparisler").get_data(as_text=True)
    # Dosyada olmayan müşteriler: OMS logosu ve OMS kırmızısı; "*" satırı rengi değiştirir.
    resim.save(marka / "oms-logo.png")
    (marka / "musteriler.txt").write_text("XX9;#0e518d\n", encoding="utf-8")
    liste = istemci.get("/siparisler").get_data(as_text=True)
    assert "--musteri-renk: #c41e24" in liste and "/marka/logo?s=" in liste
    (marka / "musteriler.txt").write_text("XX9;#0e518d\n*;#16181d\n", encoding="utf-8")
    assert "--musteri-renk: #16181d" in istemci.get("/siparisler").get_data(as_text=True)


def test_bilinmeyen_siparis_404(istemci, ekip):
    assert istemci.get("/siparisler/OZ-TS9999").status_code == 404
