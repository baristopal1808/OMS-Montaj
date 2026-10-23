"""Makine numaraları: vibrohammerın şasi no'su, güç ünitesinin motor seri no'su.

Motor seri no ERP'den okunur: önce makinenin kendi iş emrinin ve kırılımlarının açıklamasından;
orada yoksa ve siparişte tek güç ünitesi varsa projenin motor-pompa hattı (alt montaj) iş
emirlerinden. Ekibin ürün sayfasından ya da "Makine numaraları" şablonuyla girdiği değer ERP'den
okunanın önüne geçer; ERP yüklemesi bu değeri değiştirmez. Şasi no ERP'de yok (Planner notlarında
"Şasi No" ve "Şanzıman (Seri) No" olarak tutuluyordu); yalnızca ekipten gelir.
"""

import io
from collections import Counter
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font

from .erp_aktarim import IPTAL
from .urun_kurallari import ANA_URUNLER, motor_seri_nolari

# Hangi makinede hangi numara alanı var
NUMARA_ALANLARI = {
    "SVR": ("sasi_no",),
    "OVR": ("sasi_no",),
    "PP": ("motor_seri_no",),
    "OVF": ("sasi_no", "motor_seri_no"),
    "WD": ("sasi_no", "motor_seri_no"),
}
NUMARA_ADLARI = {"sasi_no": "Şasi no", "motor_seri_no": "Motor seri no"}
KAYNAKLAR = {
    "ekip": "ekip girdi",
    "erp": "ERP iş emri açıklamasından",
    "proje": "projenin motor-pompa hattı iş emrinden",
}


def _aciklamalar(vt, is_emri_idleri):
    idler = list(is_emri_idleri)
    if not idler:
        return []
    yer = ", ".join("?" * len(idler))
    return [r[0] for r in vt.execute(
        f"SELECT aciklama FROM is_emirleri WHERE id IN ({yer})"
        f" UNION ALL SELECT aciklama FROM is_emri_satirlari WHERE is_emri_id IN ({yer})",
        (*idler, *idler),
    )]


def erp_motor_serisi(vt, urun, aile, siparis_id):
    """ERP'den okunan motor seri no: (değer, kaynak) ya da (None, None)."""
    if urun["is_emri_id"]:
        if nolar := motor_seri_nolari(*_aciklamalar(vt, [urun["is_emri_id"]])):
            return " / ".join(nolar), "erp"
    if aile == "PP":
        guc_unitesi = vt.execute(
            "SELECT COUNT(*) FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
            " WHERE k.siparis_id = ? AND k.aile = 'PP' AND k.tur = 'kart' AND k.erp_durum != ?",
            (siparis_id, IPTAL),
        ).fetchone()[0]
        if guc_unitesi == 1:
            alt = [r[0] for r in vt.execute(
                "SELECT id FROM is_emirleri WHERE siparis_id = ? AND kalem_id IS NULL", (siparis_id,)
            )]
            if nolar := motor_seri_nolari(*_aciklamalar(vt, alt)):
                return " / ".join(nolar), "proje"
    return None, None


def urun_numaralari(vt, urun, aile, siparis_id):
    """Makinenin numaraları, ailesine göre: [(alan, ad, değer, kaynak)]; değer yoksa None."""
    sonuc = []
    for alan in NUMARA_ALANLARI.get(aile, ()):
        if urun[alan]:
            deger, kaynak = urun[alan], "ekip"
        elif alan == "motor_seri_no":
            deger, kaynak = erp_motor_serisi(vt, urun, aile, siparis_id)
        else:
            deger, kaynak = None, None
        sonuc.append((alan, NUMARA_ADLARI[alan], deger, kaynak))
    return sonuc


def numara_yaz(deger, alan):
    """Girilen numarayı düzenler; motor seri no tanınan biçimdeyse '0000 111 101' / 'N5F00001' biçiminde yazılır."""
    deger = " ".join((deger or "").split())
    if alan == "motor_seri_no" and (nolar := motor_seri_nolari(deger)):
        return " / ".join(nolar)
    return deger or None


def numaralari_kaydet(vt, urun_id, degerler, kullanici_id):
    """Ekibin girdiği numaraları yazar; boş değer ekibin girdiğini siler (ERP'den okunan yeniden görünür)."""
    vt.execute(
        f"UPDATE urunler SET {', '.join(f'{alan} = ?' for alan in degerler)},"
        " numara_degisme = ?, numara_degistiren_id = ? WHERE id = ?",
        (*degerler.values(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), kullanici_id, urun_id),
    )


# "Makine numaraları" şablonu: uygulama doldurur, ekip şasi ve motor seri no'larını ekleyip geri yükler.
SABLON_BASLIKLARI = (
    "Kart No", "Sipariş No", "Müşteri", "Ürün Kodu", "Ürün Adı", "Seri No", "Şasi No", "Motor Seri No",
    "ERP'den okunan motor seri no",
)
SABLON_ACIKLAMASI = (
    "Şasi No ve Motor Seri No sütunlarını doldurup dosyayı ERP yükleme ekranından yükleyin.",
    "Boş bırakılan hücre değiştirilmez; bir numarayı silmek için makinenin sayfasını kullanın.",
    "Motor Seri No yalnızca ERP'den okunan numara yanlış ya da eksikse doldurulur; doldurulan, ERP'den okunanın önüne geçer.",
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
        "SELECT u.id, u.seri_no, u.sasi_no, u.motor_seri_no, u.is_emri_id, k.urun_kodu, k.urun_adi, k.aile,"
        " k.siparis_id, s.siparis_no, s.musteri FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
        " JOIN siparisler s ON s.id = k.siparis_id"
        f" WHERE k.tur = 'kart' AND k.erp_durum != ? AND k.aile IN ({', '.join('?' * len(ANA_URUNLER))})"
        " ORDER BY s.talep_tarihi DESC, s.siparis_no, k.sira_no, u.adet_sira",
        (IPTAL, *ANA_URUNLER),
    ).fetchall():
        erp = erp_motor_serisi(vt, u, u["aile"], u["siparis_id"])[0] if "motor_seri_no" in NUMARA_ALANLARI[u["aile"]] else None
        sayfa.append([u["id"], u["siparis_no"], u["musteri"], u["urun_kodu"], u["urun_adi"], u["seri_no"],
                      u["sasi_no"], u["motor_seri_no"], erp])
    for sutun, genislik in zip("ABCDEFGHI", (9, 13, 28, 22, 30, 22, 18, 18, 26)):
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
            "SELECT u.id, u.sasi_no, u.motor_seri_no, k.urun_kodu, s.siparis_no FROM urunler u"
            " JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id WHERE u.id = ?",
            (urun_id,),
        ).fetchone()
        # Kart no başka bir makineyi gösteriyorsa (başka bir kurulumun şablonu) satır yazılmaz.
        if urun is None or any(kayit[a] and kayit[a] != urun[a] for a in ("siparis_no", "urun_kodu")):
            sayac["eslesmeyen"] += 1
            continue
        degisen = {}
        for alan in ("sasi_no", "motor_seri_no"):
            yeni = numara_yaz(kayit[alan], alan)
            if yeni and yeni != urun[alan]:
                degisen[alan] = yeni
        if degisen:
            numaralari_kaydet(vt, urun_id, degisen, kullanici_id)
            sayac["guncellenen"] += 1
    return sayac


def numara_ozeti(sayac):
    parcalar = [f"{sayac['satir']} satır okundu", f"{sayac['guncellenen']} makinenin numarası güncellendi"]
    if sayac["eslesmeyen"]:
        parcalar.append(f"{sayac['eslesmeyen']} satır hiçbir makineyle eşleşmedi (Kart No değişmiş olabilir)")
    return "; ".join(parcalar) + "."
