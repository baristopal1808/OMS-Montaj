"""Makine numaraları: vibrohammerın şasi no'su, güç ünitesinin motor seri no'su (iki motorlu güç
ünitesinde iki ayrı numara: motor 1 ve motor 2).

Motor seri no ERP'den okunur: önce makinenin kendi iş emrinin açıklamasından, orada yoksa
kırılımlarınınkinden; makinenin iş emrinde hiç yoksa ve siparişte tek güç ünitesi varsa projenin
motor-pompa hattı (alt montaj) iş emirlerinden. Kırılımlar bazen başka bir güç ünitesinin motorunu da
yazıyor; bu yüzden gereken sayıda numara içeren ilk açıklama alınır. Ekibin ürün sayfasından ya da
"Makine numaraları" şablonuyla girdiği değer ERP'den okunanın önüne geçer; ERP yüklemesi bu değeri
değiştirmez. Şasi no ERP'de yok (Planner notlarında "Şasi No" ve "Şanzıman (Seri) No" olarak
tutuluyordu); yalnızca ekipten gelir.

Numaralar kilitlidir (kullanıcı kararı, 26/10/2026): ERP'den okunan ya da bir kez girilen numara ürün
sayfasında düz yazı olarak görünür; değiştirmek için "Değiştir"e basılır, yeni numara ve sebep yazılır.
Her giriş ve değişiklik (eski, yeni, sebep, kim, ne zaman) numara_degisiklikleri tablosunda saklanır.
Şablon yalnızca boş numaraları doldurur.
"""

import io
from collections import Counter
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from .erp_aktarim import IPTAL
from .urun_kurallari import VIBROHAMMER, motor_sayisi, motor_seri_nolari

# Numarası izlenen makineler; OVF ve WD'de şasi no yok, onlar izlenmez (kullanıcı, 23/10/2026)
NUMARALI_AILELER = ("SVR", "OVR", "PP")
MOTOR_ALANLARI = ("motor_seri_no", "motor2_seri_no")
NUMARA_ADLARI = {"sasi_no": "Şasi no", "motor_seri_no": "Motor seri no", "motor2_seri_no": "Motor 2 seri no"}
KAYNAKLAR = {
    "ekip": "ekip girdi",
    "erp": "ERP iş emri açıklamasından",
    "proje": "projenin motor-pompa hattı iş emrinden",
}


def numara_alanlari(aile, urun_kodu):
    """Makinede izlenen numara alanları: vibrohammerda şasi no; güç ünitesinde motor sayısı kadar motor seri no."""
    if aile in VIBROHAMMER:
        return ("sasi_no",)
    if aile == "PP":
        return MOTOR_ALANLARI[:motor_sayisi(urun_kodu)]
    return ()


def numara_adi(alan, alanlar):
    """İki motorlu güç ünitesinde 'Motor 1 seri no' ve 'Motor 2 seri no'; tek motorluda 'Motor seri no'."""
    if alan == "motor_seri_no" and "motor2_seri_no" in alanlar:
        return "Motor 1 seri no"
    return NUMARA_ADLARI[alan]


def _aciklamalar(vt, is_emri_idleri):
    """Okunma sırasıyla açıklamalar: her iş emrinin önce kendi açıklaması, sonra kırılımlarınınki."""
    metinler = []
    for ie_id in is_emri_idleri:
        metinler += [r[0] for r in vt.execute("SELECT aciklama FROM is_emirleri WHERE id = ?", (ie_id,))]
        metinler += [r[0] for r in vt.execute(
            "SELECT aciklama FROM is_emri_satirlari WHERE is_emri_id = ? ORDER BY sira_no", (ie_id,)
        )]
    return metinler


def motor_listesi(metinler, adet):
    """En çok `adet` motor seri no: `adet` kadar numara içeren ilk açıklamadan; hiçbirinde o kadar yoksa
    bütün açıklamalarda bulunanlardan, yazıldıkları sırayla."""
    bulunan = []
    for metin in metinler:
        nolar = motor_seri_nolari(metin)
        if len(nolar) >= adet:
            return nolar[:adet]
        bulunan += [no for no in nolar if no not in bulunan]
    return bulunan[:adet]


def erp_motor_serileri(vt, urun, aile, siparis_id, adet=1):
    """ERP'den okunan motor seri no'ları: ([numara, …], kaynak) ya da ([], None)."""
    if urun["is_emri_id"]:
        if nolar := motor_listesi(_aciklamalar(vt, [urun["is_emri_id"]]), adet):
            return nolar, "erp"
    if aile == "PP":
        guc_unitesi = vt.execute(
            "SELECT COUNT(*) FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
            " WHERE k.siparis_id = ? AND k.aile = 'PP' AND k.tur = 'kart' AND k.erp_durum != ?",
            (siparis_id, IPTAL),
        ).fetchone()[0]
        if guc_unitesi == 1:
            alt = [r[0] for r in vt.execute(
                "SELECT id FROM is_emirleri WHERE siparis_id = ? AND kalem_id IS NULL ORDER BY id", (siparis_id,)
            )]
            if nolar := motor_listesi(_aciklamalar(vt, alt), adet):
                return nolar, "proje"
    return [], None


def urun_numaralari(vt, urun, aile, siparis_id, urun_kodu):
    """Makinenin numaraları, ailesine göre: [(alan, ad, değer, kaynak)]; değer yoksa None.
    Ekibin girdiği numara ERP'den okunanın önüne geçer; boş kalan motor alanları ERP'den okunanlarla
    (ekibin girdiği numaralar dışındakilerle) sırayla doldurulur."""
    alanlar = numara_alanlari(aile, urun_kodu)
    motorlar = [alan for alan in alanlar if alan in MOTOR_ALANLARI]
    erp, erp_kaynagi = erp_motor_serileri(vt, urun, aile, siparis_id, len(motorlar)) if motorlar else ([], None)
    girilen = {urun[alan] for alan in motorlar if urun[alan]}
    okunan = iter([no for no in erp if no not in girilen])
    sonuc = []
    for alan in alanlar:
        if urun[alan]:
            deger, kaynak = urun[alan], "ekip"
        elif alan in motorlar and (deger := next(okunan, None)):
            kaynak = erp_kaynagi
        else:
            deger, kaynak = None, None
        sonuc.append((alan, numara_adi(alan, alanlar), deger, kaynak))
    return sonuc


def numara_yaz(deger, alan):
    """Girilen numarayı düzenler; motor seri no tanınan biçimdeyse '0000 111 101' / 'N5F00001' biçiminde yazılır."""
    deger = " ".join((deger or "").split())
    if alan in MOTOR_ALANLARI and (nolar := motor_seri_nolari(deger)):
        return " / ".join(nolar)
    return deger or None


def numara_degistir(vt, urun_id, alan, eski, yeni, sebep, kullanici_id):
    """Ekibin girdiği numarayı yazar ve değişiklik geçmişine ekler (eski: o an görünen numara, ERP'den
    okunan da olabilir; ilk girişte boş)."""
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    vt.execute(
        f"UPDATE urunler SET {alan} = ?, numara_degisme = ?, numara_degistiren_id = ? WHERE id = ?",
        (yeni, zaman, kullanici_id, urun_id),
    )
    vt.execute(
        "INSERT INTO numara_degisiklikleri (urun_id, alan, eski, yeni, sebep, kullanici_id, zaman)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (urun_id, alan, eski, yeni, sebep, kullanici_id, zaman),
    )


def numara_gecmisi(vt, urun_id):
    """Makinenin numara değişiklikleri, yeniden eskiye."""
    return vt.execute(
        "SELECT d.*, k.ad_soyad FROM numara_degisiklikleri d LEFT JOIN kullanicilar k ON k.id = d.kullanici_id"
        " WHERE d.urun_id = ? ORDER BY d.id DESC",
        (urun_id,),
    ).fetchall()


# "Makine numaraları" şablonu: uygulama doldurur, ekip şasi ve motor seri no'larını ekleyip geri yükler.
SABLON_BASLIKLARI = (
    "Kart No", "Sipariş No", "Müşteri", "Ürün Kodu", "Ürün Adı", "Seri No", "Şasi No", "Motor Seri No",
    "Motor 2 Seri No", "ERP'den okunan motor seri no", "ERP'den okunan motor 2 seri no",
)
SABLON_ACIKLAMASI = (
    "Şasi No ve Motor Seri No sütunlarını doldurup dosyayı ERP yükleme ekranından yükleyin.",
    "Şablon yalnızca boş numaraları doldurur: numarası olan (ekibin girdiği ya da ERP'den okunan) makinede numara"
    " kilitlidir ve değiştirilmez. Değiştirmek için makinenin sayfasında \"Değiştir\" kullanılır; sebep yazılır.",
    "Motor Seri No, ERP'den okunamadıysa doldurulur (ERP'den okunanı \"ERP'den okunan motor seri no\" sütununda görürsünüz).",
    "İki motorlu güç ünitelerinde (PP-1072, PP-1536 gibi model numarası 1000 ve üstü) birinci motor Motor Seri No,"
    " ikinci motor Motor 2 Seri No sütununa yazılır. Tek motorlu makinelerde Motor 2 Seri No boş kalır.",
    "Kart No sütununu değiştirmeyin: satır makineyle bu numarayla eşleşir.",
)


def sablon(vt):
    """Bütün makinelerin (iptal edilmemiş satırlardaki) satır satır yer aldığı şablon (.xlsx içeriği)."""
    kitap = Workbook()
    sayfa = kitap.active
    sayfa.title = "Makine numaraları"
    sayfa.append(SABLON_BASLIKLARI)
    for hucre in sayfa[1]:
        hucre.font = Font(bold=True)
    for u in vt.execute(
        "SELECT u.id, u.seri_no, u.sasi_no, u.motor_seri_no, u.motor2_seri_no, u.is_emri_id, k.urun_kodu,"
        " k.urun_adi, k.aile, k.siparis_id, s.siparis_no, s.musteri"
        " FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id"
        f" WHERE k.tur = 'kart' AND k.erp_durum != ? AND k.aile IN ({', '.join('?' * len(NUMARALI_AILELER))})"
        " ORDER BY s.talep_tarihi DESC, s.siparis_no, k.sira_no, u.adet_sira",
        (IPTAL, *NUMARALI_AILELER),
    ).fetchall():
        motorlar = [a for a in numara_alanlari(u["aile"], u["urun_kodu"]) if a in MOTOR_ALANLARI]
        erp = erp_motor_serileri(vt, u, u["aile"], u["siparis_id"], len(motorlar))[0] if motorlar else []
        sayfa.append([u["id"], u["siparis_no"], u["musteri"], u["urun_kodu"], u["urun_adi"], u["seri_no"],
                      u["sasi_no"], u["motor_seri_no"], u["motor2_seri_no"], *(erp + [None, None])[:2]])
    for sutun, genislik in zip("ABCDEFGHIJK", (9, 13, 28, 22, 30, 22, 18, 18, 18, 26, 26)):
        sayfa.column_dimensions[sutun].width = genislik
    sayfa.freeze_panes = "A2"
    bilgi = kitap.create_sheet("Nasıl doldurulur")
    for satir in SABLON_ACIKLAMASI:
        bilgi.append([satir])
    bilgi.column_dimensions["A"].width = 110
    tampon = io.BytesIO()
    kitap.save(tampon)
    return tampon.getvalue()


def numaralari_isle(vt, kayitlar, kullanici_id):
    """Doldurulmuş şablonu işler; ne yapıldığını sayan bir Counter döndürür."""
    sayac = Counter(satir=len(kayitlar))
    for kayit in kayitlar:
        try:
            urun_id = int(float(kayit["kart_no"]))
        except ValueError:
            sayac["eslesmeyen"] += 1
            continue
        urun = vt.execute(
            "SELECT u.*, k.urun_kodu, k.aile, k.siparis_id, s.siparis_no FROM urunler u"
            " JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id WHERE u.id = ?",
            (urun_id,),
        ).fetchone()
        # Kart no başka bir makineyi gösteriyorsa (başka bir kurulumun şablonu) satır yazılmaz.
        if urun is None or any(kayit[a] and kayit[a] != urun[a] for a in ("siparis_no", "urun_kodu")):
            sayac["eslesmeyen"] += 1
            continue
        # Yalnızca makinede izlenen ve boş olan alanlar yazılır; numarası olan alan kilitlidir.
        guncellendi = kilitli = False
        for alan, _, deger, _ in urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"]):
            yeni = numara_yaz(kayit.get(alan), alan)
            if not yeni or yeni == deger:
                continue
            if deger:
                kilitli = True
                continue
            numara_degistir(vt, urun_id, alan, None, yeni, None, kullanici_id)
            guncellendi = True
        sayac["guncellenen"] += guncellendi
        sayac["kilitli"] += kilitli
    return sayac


def numara_ozeti(sayac):
    parcalar = [f"{sayac['satir']} satır okundu", f"{sayac['guncellenen']} makinenin boş numarası dolduruldu"]
    if sayac["kilitli"]:
        parcalar.append(f"{sayac['kilitli']} makinede numara zaten vardı, kilitli olduğu için değiştirilmedi"
                        " (değiştirmek için makinenin sayfasında \"Değiştir\")")
    if sayac["eslesmeyen"]:
        parcalar.append(f"{sayac['eslesmeyen']} satır hiçbir makineyle eşleşmedi (Kart No değişmiş olabilir)")
    return "; ".join(parcalar) + "."
