"""Kontrol listesi (4. adımın 2. parçası; kullanıcı kararları, 20/10/2026 ve 11/11/2026).

Planner'daki kontrol listesinin "yapıldı mı?" soruları ürünün sayfasında işaretlenir. Bilgiler (seri no, motor
seri no, renk, yağ) zaten kendi yerlerinde durur.

Güç ünitesinde (PP; siparişteki yeni makine ve stoktaki makine), çalışma sırasıyla:
- Pompa montajı: ERP'den okunur. İş emrinin pompa montajı kırılımları (adında POMPA ve MONTAJ geçen, motor-pompa
  hattı olmayan) stoğa girince madde kendiliğinden tamamlanmış görünür. Kırılımı olmayan ya da ERP'si geride kalan
  iş emrinde ekip işaretler.
- Opsiyonel ekipmanların montajı (sipariş talebindeki uzaktan erişim modülü, kablosuz kumanda seti): ayrıca
  işaretlenmez; ürün sayfasındaki opsiyonel ekipman bölümünün montaj durumundan gelir.
- Motor açılışı: yapıldığı gün sorulur ve kaydedilir. İki motorlu güç ünitesinde de tek maddedir.
- Motor eksperi: yapılacak mı? Yapılacaksa kartta "Eksper bekleniyor" yazar; yapılınca günü kaydedilir.
- Metal etiket.
Siparişteki güç ünitesinde müşterinin kabin için verdiği seri no da yazılır (bilgi; kurala girmez).

Vibrohammerda (SVR, OVR) metal etiket. Diğer ailelerin ve bakım-onarım kartlarının şablonu ileride (soru 22).

Kural: kontrol listesi tamamlanmadan ürün "Sevke hazır"a (ve "Sevk edildi"ye) geçmez. Motor eksperi kurala
girmez; sonradan da yapılabilir. Kural başladığında Sevke hazır ya da Sevk edildi aşamasındaki ürünler muaftır
(urunler.kontrol_muaf, göç 24); onların listesi de görünür ve işaretlenir.

Her işaret ve geri alma kontrol_isaretleri tablosuna bir satır olarak yazılır (maddenin son satırı geçerli) ve
zaman akışında görünür. Stok makinesi siparişe atanınca işaretleri siparişin ürününe geçer (stok.stoktan_ata).
"""

from datetime import date, datetime

from .asamalar import SIRA
from .bicim import tarih
from .erp_aktarim import IPTAL
from .is_emri_aktarim import kirilim_durumu
from .urun_kurallari import EKLENTI_DURUMLARI, PP_EKLENTILERI, VARSAYILAN_EKLENTI_DURUMU, VIBROHAMMER, pp_eklentisi_mi

MADDELER = {
    "pompa_montaji": "Pompa montajı tamamlandı",
    "motor_acilisi": "Motor açılışı yapıldı",
    "eksper": "Motor eksperi",
    "metal_etiket": "Metal etiket yapıştırıldı",
}
KISA_ADLAR = {"pompa_montaji": "pompa montajı", "motor_acilisi": "motor açılışı", "eksper": "motor eksperi",
              "metal_etiket": "metal etiket"}
KABIN = "kabin_seri_no"
KABIN_ADI = "Müşterinin kabin seri no'su"
ISARETLENEN = ("pompa_montaji", "motor_acilisi", "metal_etiket")  # ekip "yapıldı" diye işaretler
GUNLU = ("motor_acilisi",)  # işaretlerken yapıldığı gün sorulur (eksperde "yapıldı" cevabında da)
EKSPER_DURUMLARI = {"yapilacak": "Eksper bekleniyor", "yapilmayacak": "Eksper yapılmayacak", "yapildi": "Eksper yapıldı"}
YAPILDI = "yapildi"
KURAL_ASAMASI = "sevke_hazir"  # kontrol listesi tamamlanmadan bu aşamaya ve sonrasına geçilmez
ILK_GUN = date(2020, 1, 1)  # yazılan günün alt sınırı (yanlış yıl yazılmasın)


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sablon(urun):
    """Ürünün kontrol listesinin maddeleri, sırasıyla; listesi yoksa boş. "ekipman": siparişteki opsiyonel
    ekipmanların montajı. Bakım-onarım kartında ve stoktan çıkarılan makinede liste yok."""
    if (urun["kalem_id"] is not None and urun["tur"] != "kart") or urun["stok_cikis"]:
        return ()
    if urun["aile"] == "PP":
        return ("pompa_montaji", "ekipman", "motor_acilisi", "eksper", "metal_etiket")
    if urun["aile"] in VIBROHAMMER:
        return ("metal_etiket",)
    return ()


def kabin_alani_var_mi(urun):
    """Müşterinin kabin seri no'su: siparişteki güç ünitesinde."""
    return urun["kalem_id"] is not None and urun["aile"] == "PP" and bool(sablon(urun))


def kurala_tabi_mi(urun):
    return bool(sablon(urun)) and not urun["kontrol_muaf"]


def gun(metin):
    """Formdan gelen gün (YYYY-AA-GG); geçersizse ya da bugünden ileriyse None."""
    try:
        d = date.fromisoformat((metin or "").strip())
    except ValueError:
        return None
    return d.isoformat() if ILK_GUN <= d <= date.today() else None


def _yer(sayi):
    return ", ".join("?" * sayi)


def son_isaretler(vt, urun_idleri):
    """{ürün id: {madde: satır}}: her maddenin son işareti (kimin işaretlediğiyle); geri alınan madde yok sayılır."""
    idler = list(dict.fromkeys(urun_idleri))
    if not idler:
        return {}
    sonuc = {}
    for r in vt.execute(
        "SELECT k.*, u.ad_soyad FROM kontrol_isaretleri k LEFT JOIN kullanicilar u ON u.id = k.kullanici_id"
        f" WHERE k.id IN (SELECT MAX(id) FROM kontrol_isaretleri WHERE urun_id IN ({_yer(len(idler))})"
        " GROUP BY urun_id, madde)",
        idler,
    ):
        if r["deger"] is not None:
            sonuc.setdefault(r["urun_id"], {})[r["madde"]] = r
    return sonuc


def pompa_kirilimi_mi(ad):
    ad = (ad or "").upper()
    return "POMPA" in ad and "MONTAJ" in ad and "MOTOR" not in ad


def pompa_kirilimlari(vt, is_emri_idleri):
    """{iş emri id: (stoğa giren, toplam)}: iş emrinin pompa montajı kırılımları."""
    idler = [i for i in dict.fromkeys(is_emri_idleri) if i]
    if not idler:
        return {}
    sonuc = {}
    for s in vt.execute(
        f"SELECT * FROM is_emri_satirlari WHERE is_emri_id IN ({_yer(len(idler))}) ORDER BY is_emri_id, sira_no", idler,
    ):
        if pompa_kirilimi_mi(s["urun_adi"]):
            giren, toplam = sonuc.get(s["is_emri_id"], (0, 0))
            sonuc[s["is_emri_id"]] = (giren + (kirilim_durumu(s)[1] == "kapali"), toplam + 1)
    return sonuc


def _ekipmanlar(vt, siparis_idleri):
    """{sipariş id: [kalem]}: siparişin opsiyonel ekipmanları (iptal edilmemiş), sipariş talebindeki sırayla."""
    idler = [i for i in dict.fromkeys(siparis_idleri) if i]
    if not idler:
        return {}
    sonuc = {}
    for k in vt.execute(
        "SELECT k.id, k.siparis_id, k.urun_kodu, k.urun_adi, k.montaj_durumu, s.tip FROM siparis_kalemleri k"
        f" JOIN siparisler s ON s.id = k.siparis_id WHERE k.siparis_id IN ({_yer(len(idler))})"
        " AND COALESCE(k.erp_durum, '') != ? ORDER BY k.siparis_id, k.sira_no",
        [*idler, IPTAL],
    ):
        if pp_eklentisi_mi(k["urun_kodu"], k["tip"]):
            sonuc.setdefault(k["siparis_id"], []).append(k)
    return sonuc


def kontrol_listeleri(vt, urunler):
    """{ürün id: [madde]}: kontrol listesi olan ürünlerin listesi. urunler: urunler satırları (aile, kalem_id, tur,
    stok_cikis, is_emri_id ve sipariş ürününde siparis_id alanlarıyla). Madde: {"madde", "ad", "tamam", "zorunlu",
    "isaret" (son işaret ya da None), "erp" ((stoğa giren, toplam) pompa kırılımı ya da None), "durum" (eksperin
    cevabı ya da opsiyonel ekipmanın montaj durumu), "kalem" (opsiyonel ekipmanın sipariş satırı)}."""
    urunler = [u for u in urunler if sablon(u)]
    if not urunler:
        return {}
    isaretler = son_isaretler(vt, [u["id"] for u in urunler])
    pompa = pompa_kirilimlari(vt, [u["is_emri_id"] for u in urunler if u["aile"] == "PP"])
    ekipman = _ekipmanlar(vt, [u["siparis_id"] for u in urunler if u["kalem_id"] is not None and u["aile"] == "PP"])
    sonuc = {}
    for u in urunler:
        isaret = isaretler.get(u["id"], {})
        liste = []
        for madde in sablon(u):
            if madde == "ekipman":
                for k in ekipman.get(u["siparis_id"], []) if u["kalem_id"] is not None else []:
                    ad = PP_EKLENTILERI.get((k["urun_kodu"] or "").upper(), k["urun_adi"])
                    durum = k["montaj_durumu"] or VARSAYILAN_EKLENTI_DURUMU
                    liste.append({"madde": "ekipman", "ad": f"{ad} montajı", "tamam": durum == "montaj_edildi",
                                  "zorunlu": True, "isaret": None, "erp": None, "durum": EKLENTI_DURUMLARI[durum],
                                  "kalem": k})
                continue
            m = {"madde": madde, "ad": MADDELER[madde], "isaret": isaret.get(madde), "zorunlu": madde != "eksper",
                 "erp": None, "durum": None, "kalem": None}
            if madde == "eksper":
                m["durum"] = m["isaret"]["deger"] if m["isaret"] else None
                m["tamam"] = m["durum"] in (YAPILDI, "yapilmayacak")
            else:
                m["tamam"] = m["isaret"] is not None
            if madde == "pompa_montaji" and u["is_emri_id"] in pompa:
                m["erp"] = pompa[u["is_emri_id"]]
                m["tamam"] = m["tamam"] or m["erp"][0] == m["erp"][1]
            liste.append(m)
        sonuc[u["id"]] = liste
    return sonuc


def eksik_maddeler(liste):
    """Kurala giren (motor eksperi dışındaki) ama tamamlanmamış maddeler."""
    return [m for m in liste or () if m["zorunlu"] and not m["tamam"]]


def eksik_metni(eksikler):
    """'motor açılışı, metal etiket, Kablosuz Kumanda Seti montajı'"""
    return ", ".join(m["ad"] if m["madde"] == "ekipman" else KISA_ADLAR[m["madde"]] for m in eksikler)


def gecis_engeli(vt, urun, hedef):
    """Ürün hedef aşamaya kontrol listesi yüzünden geçemiyorsa eksik maddeler; geçebiliyorsa boş liste. Kural
    Sevke hazır'a ve sonrasına ileri geçişte geçerlidir; geri alırken sorulmaz."""
    if not kurala_tabi_mi(urun) or SIRA[hedef] < SIRA[KURAL_ASAMASI] or SIRA[hedef] <= SIRA[urun["asama"]]:
        return []
    return eksik_maddeler(kontrol_listeleri(vt, [urun]).get(urun["id"]))


def ozet(liste):
    """Panodaki kartın satırı: (tamamlanan, kurala giren madde sayısı) ve eksper bekleniyor mu."""
    zorunlu = [m for m in liste if m["zorunlu"]]
    eksper = any(m["madde"] == "eksper" and m["durum"] == "yapilacak" for m in liste)
    return sum(m["tamam"] for m in zorunlu), len(zorunlu), eksper


def isaretle(vt, urun_id, madde, deger, gun_, kullanici_id):
    """Bir işaret ya da geri alma (deger None) yazar."""
    vt.execute(
        "INSERT INTO kontrol_isaretleri (urun_id, madde, deger, tarih, zaman, kullanici_id) VALUES (?, ?, ?, ?, ?, ?)",
        (urun_id, madde, deger, gun_, _simdi(), kullanici_id),
    )


def akis_kayitlari(vt, urun_id):
    """Zaman akışı için kontrol listesi kayıtları: [(zaman, başlık, kim, metin)], eskiden yeniye."""
    kayitlar, onceki = [], {}
    for r in vt.execute(
        "SELECT k.*, u.ad_soyad FROM kontrol_isaretleri k LEFT JOIN kullanicilar u ON u.id = k.kullanici_id"
        " WHERE k.urun_id = ? ORDER BY k.id",
        (urun_id,),
    ):
        madde, deger, eski = r["madde"], r["deger"], onceki.get(r["madde"])
        metin = f"Yapıldığı gün: {tarih(r['tarih'])}" if r["tarih"] else None
        if madde == KABIN:
            baslik = (f"{KABIN_ADI} silindi (önceki: {eski})" if deger is None else
                      f"{KABIN_ADI} değiştirildi: {eski} → {deger}" if eski else f"{KABIN_ADI} girildi: {deger}")
        elif madde == "eksper":
            baslik = {"yapilacak": "Motor eksperi yapılacak (eksper bekleniyor)", "yapilmayacak": "Motor eksperi yapılmayacak",
                      YAPILDI: "Motor eksperi yapıldı"}.get(deger, "Kontrol listesi: motor eksperinin cevabı geri alındı")
        elif deger is None:
            baslik = f"Kontrol listesi: {KISA_ADLAR.get(madde, madde)} işareti geri alındı"
        else:
            baslik = f"Kontrol listesi: {MADDELER.get(madde, madde).lower()}"
        kayitlar.append((r["zaman"], baslik, r["ad_soyad"] or "", metin))
        onceki[madde] = deger
    return kayitlar
