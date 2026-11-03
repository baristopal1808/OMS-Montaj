"""Stoktaki makineler (planın 5. adımı öne alındı; kullanıcı kararları, 02-03/11/2026).

Siparişe bağlanmadan depoda bekleyen makineler, çeneler ve kirişler. Kaynak ERP'nin depo stok raporlarıdır:
sevk deposu ve montaj üretim deposu (montaj deposu stok sayılmaz). Her depo ayrı dosyadır; depo dosyada yazmaz,
dosyanın adından anlaşılır. Raporda seri no yok, yalnızca ürün kodu ve adet var.

Bir ürün kodunun iki depodaki adedinden, açık siparişlerin stoğa girmiş ama sevk edilmemiş aynı kodlu ürünleri
düşülür; kalan kadar "Stok" kartı açılır (kullanıcı: adet kadar kart). Stok kartı bir urunler satırıdır ama
sipariş satırı yoktur (kalem_id boş): ürün kodu, adı ve ailesi kartın kendisinde durur. Numaralarını (motor seri
no, şasi no) ekip girer; ERP'de "stok için" açılıp stoğa girmiş aynı kodlu bir iş emri varsa karta kendiliğinden
bağlanır (motor seri no açıklamasından okunur, teyit bekler). ERP'de bulunamayan makine elle eklenir.

Sevk deposundaki makine test edilmiş sayılır; montaj üretim deposundakinde "Testi yapıldı mı?" sorulur. Stok
kartı siparişe atanınca bilgileri (numaralar, iş emri, notlar, zaman akışı) o siparişin ürün kartına geçer; ürün
test edildiyse Temizlik, edilmediyse Teste hazır aşamasından devam eder (docs/ihtiyaclar.md 3.1). ERP'de stok iş
emri bir siparişe bağlanırsa atama kendiliğinden yapılır.

Depoda adet azalınca (makine sevk edildi ya da başka yere gitti) ekibin bilgi girmediği kartlar kendiliğinden
kalkar; bilgi girilmiş kart kalır ve "depo raporunda görünmüyor" diye işaretlenir, ekip siparişe atar ya da stoktan
çıkarır. Panoda yalnızca makineler (PP, SVR, OVR, OVF, WD) kart olur; çeneler ve kirişler Stok ekranında listelenir.
"""

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .asamalar import ASAMALAR, ileri
from .erp_aktarim import IPTAL, KAPALI, kapali_mi
from .kimlik import ekip_gerekli
from .numaralar import urun_numaralari
from .urun_kurallari import AILE_ADLARI, AILE_SIRASI, AILELER, ANA_URUNLER, SERI_NOSUZ_PARCA, onek, sade
from .veritabani import baglanti

bp = Blueprint("stok", __name__)

DEPOLAR = {"sevk": "Sevk deposu", "montaj_uretim": "Montaj üretim deposu", "montaj": "Montaj deposu"}
STOK_DEPOLARI = ("sevk", "montaj_uretim")  # stok sayılan depolar (kullanıcı, 03/11/2026)
STOK_AILELERI = ("SVR", "OVR", "PP", "OVF", "WD", "Çene", "Kiriş")
TEST_DURUMLARI = {"edildi": "Test edildi", "bekliyor": "Test bekliyor"}
CIKIS_SEBEPLERI = {
    "sevk": "Sevk edildi ya da başka bir yere gitti",
    "yanlis": "Yanlış kart (böyle bir makine yok)",
    "kullanilmayacak": "Kullanılmayacak (hurda, demonte…)",
}
# Alt montaj kodları makine değil: model kodundan sonra "-02-00" gibi ekler (OVR-120-S-02-00, PP-536-07-00,
# WD-28-43-VD-02-02-00) ya da "MONTAJ" (PP-536-POMPA ANA MONTAJI, SCN-350-01-00-MON). WD'nin model kodunda iki sayı var.
MODEL_KODU = re.compile(r"^(?:WD-\d+-\d+|[A-Z]+-\d+[A-Z]?)")
ALT_MONTAJ_EKI = re.compile(r"-\d{2}-\d{2}(?:-|$)")
ALT_MONTAJ_ADI = re.compile(r"MONTAJ|-MON$")


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def depo_bul(dosya_adi):
    """Depo stok raporunun deposu dosyanın adından: 'sevk depo stok raporu.xls' → sevk."""
    ad = sade(Path(dosya_adi or "").stem)
    if "sevk" in ad:
        return "sevk"
    if "uretim" in ad:
        return "montaj_uretim"
    if "montaj" in ad:
        return "montaj"
    return None


# Hangi kod stok kartı olur

def kod_turleri(vt):
    """(makine kodları, yarı mamul kodları): siparişte kart satırı ya da iş emrinde son ürün olarak geçenler
    makinedir; iş emrinde yarı mamul olarak geçenler alt montajdır."""
    kart = {r[0].upper() for r in vt.execute("SELECT DISTINCT urun_kodu FROM siparis_kalemleri WHERE tur = 'kart'")}
    kart |= {r[0].upper() for r in vt.execute(
        "SELECT DISTINCT urun_kodu FROM is_emirleri WHERE envanter_tipi = 'Son Ürün' AND urun_kodu IS NOT NULL")}
    yari = {r[0].upper() for r in vt.execute(
        "SELECT DISTINCT urun_kodu FROM is_emirleri WHERE envanter_tipi = 'Yarı Mamul' AND urun_kodu IS NOT NULL")}
    return kart, yari - kart


def stok_ailesi(kod, kart_kodlari=(), yari_kodlar=(), elle=False):
    """Kod stok kartı olacaksa ailesi (PP, SVR, Çene…), olmayacaksa None. Hiç görülmemiş kodda alt montaj
    biçimine bakılır (ALT_MONTAJ_EKI, ALT_MONTAJ_ADI); kiriş kodlarının sonundaki "-00" olağandır.
    elle=True: ekip elle ekliyor; OVF ve WD'nin görülmemiş kodu da kabul edilir."""
    kod = (kod or "").strip().upper()
    aile = AILELER.get(onek(kod))
    # Bakım-onarım (-MNT) ve hortum setleri (-HH) makine değil; seri no'suz OVF ve WD satırı burada da makinedir
    if aile not in STOK_AILELERI or kod.endswith("-MNT") or "-HH" in kod:
        return None
    if kod in kart_kodlari:
        return aile
    if kod in yari_kodlar or ALT_MONTAJ_ADI.search(kod):
        return None
    # OVF ve WD'de makine ile parçası aynı önekle başlar (OVF-300-BF-LM-B, OVF-300-4BF-BSP'nin parçası): yalnızca
    # siparişte makine ya da iş emrinde son ürün olarak görülmüş kod stok kartı olur; öbürleri elle eklenir
    if aile in SERI_NOSUZ_PARCA and not elle:
        return None
    if aile != "Kiriş" and ALT_MONTAJ_EKI.search(MODEL_KODU.sub("", kod)):
        return None
    return aile


def test_durumu(urun):
    """'edildi', 'bekliyor' ya da None (sorulacak). Sevk deposundaki makine test edilmiş sayılır."""
    if urun["test_durumu"]:
        return urun["test_durumu"]
    return "edildi" if urun["depo"] == "sevk" else None


# Depo raporları ve kartların depoyla eşlenmesi

def depo_raporunu_isle(vt, depo, kayitlar, yukleme_id):
    """Bir deponun stok raporunu yazar (o deponun eski satırları silinir): (satır sayısı, makine adedi)."""
    vt.execute("DELETE FROM depo_stoklari WHERE depo = ?", (depo,))
    toplam = Counter()
    for k in kayitlar:
        kod = k["urun_kodu"].strip().upper()
        toplam[kod] += k["miktar"]
        vt.execute(
            "INSERT INTO depo_stoklari (depo, urun_kodu, urun_adi, miktar, yukleme_id) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT (depo, urun_kodu) DO UPDATE SET miktar = miktar + excluded.miktar",
            (depo, kod, k["urun_adi"], k["miktar"], yukleme_id),
        )
    vt.execute(
        "INSERT INTO depo_raporlari (depo, yukleme_id, zaman) VALUES (?, ?, ?)"
        " ON CONFLICT (depo) DO UPDATE SET yukleme_id = excluded.yukleme_id, zaman = excluded.zaman",
        (depo, yukleme_id, _simdi()),
    )
    kart, yari = kod_turleri(vt)
    makine = sum(m for kod, m in toplam.items() if stok_ailesi(kod, kart, yari))
    return len(kayitlar), int(makine)


def _siparisteki_stoklar(vt):
    """Açık siparişlerin stoğa girmiş ama sevk edilmemiş ürünleri, ürün koduna göre: depoda dururlar ve depo
    raporunda sayılırlar. Stoğa girmiş: stoktan atanmış ya da iş emrinden stoğa giren miktar kadar ürün."""
    sayac = Counter()
    kacinci = Counter()
    for u in vt.execute(
        "SELECT k.urun_kodu, k.sevk_miktari, k.erp_durum, k.erp_genel_durum, u.asama, u.stoktan_atama, u.adet_sira,"
        " u.is_emri_id, i.gercek_miktar FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
        " LEFT JOIN is_emirleri i ON i.id = u.is_emri_id WHERE COALESCE(k.erp_durum, '') != ? ORDER BY u.kalem_id, u.adet_sira",
        (IPTAL,),
    ):
        if u["is_emri_id"]:
            kacinci[u["is_emri_id"]] += 1
        if u["asama"] == "sevk_edildi" or kapali_mi(u) or (u["sevk_miktari"] or 0) >= u["adet_sira"]:
            continue
        if u["stoktan_atama"] or (u["is_emri_id"] and kacinci[u["is_emri_id"]] <= (u["gercek_miktar"] or 0)):
            sayac[u["urun_kodu"].upper()] += 1
    return sayac


def bilgi_var_mi(vt, kart):
    """Ekip karta bir bilgi girdi mi (numara, test cevabı, iş emri, not)? Böyle kart kendiliğinden silinmez."""
    if kart["stok_kaynagi"] == "elle" or kart["is_emri_elle"] or kart["test_durumu"]:
        return True
    if any(kart[a] for a in ("motor_seri_no", "motor2_seri_no", "sasi_no")):
        return True
    return vt.execute(
        "SELECT 1 FROM urun_olaylari WHERE urun_id = ? AND kullanici_id IS NOT NULL LIMIT 1", (kart["id"],)
    ).fetchone() is not None


def _kart_ac(vt, kod, adi, aile, depo, kaynak, test=None, kullanici_id=None):
    return vt.execute(
        "INSERT INTO urunler (kalem_id, adet_sira, asama, stok_kodu, stok_adi, stok_aile, stok_kaynagi, depo,"
        " test_durumu, test_degisme, test_degistiren_id) VALUES (NULL, 0, 'stokta', ?, ?, ?, ?, ?, ?, ?, ?)",
        (kod, adi, aile, kaynak, depo, test, _simdi() if test else None, kullanici_id if test else None),
    ).lastrowid


def _karti_sil(vt, urun_id):
    """Ekibin bilgi girmediği stok kartını siler (ERP yüklemesinin olayları dahil)."""
    for tablo in ("urun_olaylari", "numara_degisiklikleri", "imalatta_cevaplari", "urun_formlari"):
        vt.execute(f"DELETE FROM {tablo} WHERE urun_id = ?", (urun_id,))
    vt.execute("DELETE FROM urunler WHERE id = ?", (urun_id,))


def stoklari_esle(vt):
    """Stok kartlarını depo raporlarıyla ve iş emirleriyle eşler; depo, sipariş ve iş emri yüklemelerinden sonra
    çalışır. Ne yapıldığını sayan bir Counter döndürür."""
    sayac = Counter()
    _erpde_atananlar(vt, sayac)
    raporlar = {r["depo"]: r["zaman"] for r in vt.execute("SELECT depo, zaman FROM depo_raporlari")}
    if all(d in raporlar for d in STOK_DEPOLARI):
        _depoyla_esle(vt, sayac, max(raporlar[d] for d in STOK_DEPOLARI))
    _is_emirlerini_bagla(vt, sayac)
    return sayac


def _depoyla_esle(vt, sayac, rapor_zamani):
    kart_kodlari, yari = kod_turleri(vt)
    adet = defaultdict(Counter)
    adlar = {}
    for r in vt.execute("SELECT * FROM depo_stoklari WHERE depo IN (?, ?)", STOK_DEPOLARI):
        if aile := stok_ailesi(r["urun_kodu"], kart_kodlari, yari):
            adet[r["urun_kodu"]][r["depo"]] += r["miktar"]
            adlar[r["urun_kodu"]] = (r["urun_adi"], aile)
    siparisteki = _siparisteki_stoklar(vt)
    kartlar = defaultdict(list)
    cikanlar = Counter()  # son rapordan sonra ekibin stoktan çıkardıkları: rapor yenilenene kadar sayılır
    for k in vt.execute("SELECT * FROM urunler WHERE kalem_id IS NULL ORDER BY id"):
        if k["stok_cikis"] is None:
            kartlar[k["stok_kodu"].upper()].append(k)
        elif k["stok_cikis"] > rapor_zamani and k["depo"] in STOK_DEPOLARI:
            cikanlar[(k["stok_kodu"].upper(), k["depo"])] += 1
    bugun = date.today().isoformat()

    for kod in sorted(set(adet) | set(kartlar)):
        s, m = int(adet[kod]["sevk"]), int(adet[kod]["montaj_uretim"])
        o = siparisteki.get(kod, 0)
        # Siparişlerin ürünleri önce montaj üretim deposundan düşülür (test edilip sevk deposuna geçmemiş olabilirler)
        yer = {"montaj_uretim": max(0, m - o), "sevk": max(0, s - max(0, o - m))}
        for d in STOK_DEPOLARI:
            yer[d] = max(0, yer[d] - cikanlar[(kod, d)])
        liste = kartlar.get(kod, [])
        elle = [k for k in liste if k["stok_kaynagi"] == "elle"]
        oto = [k for k in liste if k["stok_kaynagi"] != "elle"]
        # Elle eklenen kart, yazılan deposunun adedinden düşer; depoda adet kalmadıysa işaretlenir
        for k in elle:
            if k["depo"] in yer:
                if yer[k["depo"]] > 0:
                    yer[k["depo"]] -= 1
                    _depoda_yok(vt, k, None)
                else:
                    sayac["depoda_yok"] += _depoda_yok(vt, k, bugun)
        # Kalan otomatik kartlar: önce bilgi girilmiş, sonra test edilmiş, sonra eski olanlar
        bilgili = {k["id"]: bilgi_var_mi(vt, k) for k in oto}
        oto.sort(key=lambda k: (not bilgili[k["id"]], test_durumu(k) != "edildi", k["id"]))
        toplam = yer["sevk"] + yer["montaj_uretim"]
        for k in oto[toplam:]:
            if bilgili[k["id"]]:
                sayac["depoda_yok"] += _depoda_yok(vt, k, bugun)
            else:
                _karti_sil(vt, k["id"])
                sayac["kalkan"] += 1
        # Depolar: kart bulunduğu depoda yer varsa orada kalır; yoksa test edilmiş olan önce sevk deposuna
        tasinacak = []
        for k in oto[:toplam]:
            if yer.get(k["depo"], 0) > 0:
                yer[k["depo"]] -= 1
                _depoda_yok(vt, k, None)
            else:
                tasinacak.append(k)
        for k in sorted(tasinacak, key=lambda k: (test_durumu(k) != "edildi", k["id"])):
            d = "sevk" if yer["sevk"] > 0 else "montaj_uretim"
            yer[d] -= 1
            vt.execute("UPDATE urunler SET depo = ?, depoda_yok = NULL WHERE id = ?", (d, k["id"]))
        for d in STOK_DEPOLARI:
            for _ in range(yer[d]):
                adi, aile = adlar[kod]
                _kart_ac(vt, kod, adi, aile, d, "depo")
                sayac["yeni"] += 1


def _depoda_yok(vt, kart, gun):
    """Kartın "depo raporunda görünmüyor" işaretini koyar (gun) ya da kaldırır (None); yeni konduysa 1."""
    if bool(kart["depoda_yok"]) == bool(gun):
        return 0
    vt.execute("UPDATE urunler SET depoda_yok = ? WHERE id = ?", (gun, kart["id"]))
    return 1 if gun else 0


def _is_emirlerini_bagla(vt, sayac):
    """ERP'de stok için açılıp stoğa girmiş iş emirlerini, aynı kodlu ve iş emri olmayan stok kartlarına bağlar
    (yeni stok girişi önce). Ekibin iş emrini girdiği ya da kaldırdığı karta dokunulmaz."""
    tutulan = Counter(r[0] for r in vt.execute("SELECT is_emri_id FROM urunler WHERE is_emri_id IS NOT NULL"))
    bos = defaultdict(list)
    for k in vt.execute(
        "SELECT id, stok_kodu FROM urunler WHERE kalem_id IS NULL AND stok_cikis IS NULL AND is_emri_id IS NULL"
        " AND is_emri_elle = 0 ORDER BY id"
    ):
        bos[k["stok_kodu"].upper()].append(k["id"])
    if not bos:
        return
    for ie in vt.execute(
        "SELECT id, urun_kodu, gercek_miktar FROM is_emirleri WHERE baglanti IN ('stok', 'kullanici_stok')"
        " AND envanter_tipi = 'Son Ürün' AND COALESCE(gercek_miktar, 0) > 0"
        " ORDER BY COALESCE(son_stok_giris, kapatma_tarihi, acilis_tarihi) DESC, id DESC"
    ).fetchall():
        kod = (ie["urun_kodu"] or "").upper()
        serbest = int(ie["gercek_miktar"]) - tutulan[ie["id"]]
        while serbest > 0 and bos.get(kod):
            vt.execute("UPDATE urunler SET is_emri_id = ? WHERE id = ?", (ie["id"], bos[kod].pop(0)))
            serbest -= 1
            sayac["is_emri"] += 1


def _erpde_atananlar(vt, sayac):
    """İş emri ERP'de bir siparişe bağlanmış (planlama stok makinesini siparişe vermiş) stok kartları o siparişin
    ürün kartına kendiliğinden atanır."""
    for kart in vt.execute(
        "SELECT * FROM urunler WHERE kalem_id IS NULL AND stok_cikis IS NULL AND is_emri_id IS NOT NULL"
    ).fetchall():
        hedef = vt.execute(
            "SELECT * FROM urunler WHERE is_emri_id = ? AND kalem_id IS NOT NULL AND stoktan_atama IS NULL"
            " ORDER BY adet_sira LIMIT 1",
            (kart["is_emri_id"],),
        ).fetchone()
        if hedef:
            stoktan_ata(vt, kart, hedef, None)
            sayac["erpde_atanan"] += 1


def stok_ozeti(depo, satir_sayisi, makine):
    return f"{DEPOLAR[depo]}: {satir_sayisi} malzemenin stoğu var; {makine} adet makine, çene ya da kiriş."


def esleme_ozeti(sayac):
    """Stok kartlarının eşlenmesinin bir cümlelik özeti (boş olabilir)."""
    parcalar = []
    if sayac["yeni"]:
        parcalar.append(f"{sayac['yeni']} yeni stok kartı açıldı")
    if sayac["kalkan"]:
        parcalar.append(f"{sayac['kalkan']} stok kartı depoda kalmadığı için kalktı")
    if sayac["depoda_yok"]:
        parcalar.append(f"{sayac['depoda_yok']} stok kartı depo raporunda görünmüyor (Stok ekranında)")
    if sayac["is_emri"]:
        parcalar.append(f"{sayac['is_emri']} stok kartına ERP'deki stok iş emri bağlandı")
    if sayac["erpde_atanan"]:
        parcalar.append(f"{sayac['erpde_atanan']} stok makinesi ERP'de siparişe bağlandığı için o siparişe atandı")
    return ("Stok: " + ", ".join(parcalar) + ".") if parcalar else ""


# Siparişe atama

def stoktan_ata(vt, stok, hedef, kullanici_id):
    """Stok kartını siparişin ürün kartına atar: numaralar, iş emri, test durumu, notlar ve zaman akışı hedefe
    geçer, stok kartı silinir. Ürün test edildiyse Temizlik, edilmediyse Teste hazır aşamasından devam eder.
    kullanici_id boşsa atamayı ERP yaptı (stok iş emri siparişe bağlandı)."""
    test = test_durumu(stok)
    yeni = ileri(hedef["asama"], "temizlik" if test == "edildi" else "teste_hazir")
    for tablo in ("urun_olaylari", "numara_degisiklikleri", "urun_formlari"):
        vt.execute(f"UPDATE {tablo} SET urun_id = ? WHERE urun_id = ?", (hedef["id"], stok["id"]))
    vt.execute("UPDATE OR IGNORE imalatta_cevaplari SET urun_id = ? WHERE urun_id = ?", (hedef["id"], stok["id"]))
    vt.execute("DELETE FROM imalatta_cevaplari WHERE urun_id = ?", (stok["id"],))
    zaman = _simdi()
    vt.execute(
        "UPDATE urunler SET is_emri_id = COALESCE(?, is_emri_id), motor_seri_no = COALESCE(?, motor_seri_no),"
        " motor2_seri_no = COALESCE(?, motor2_seri_no), sasi_no = COALESCE(?, sasi_no),"
        " numara_degisme = COALESCE(?, numara_degisme), numara_degistiren_id = COALESCE(?, numara_degistiren_id),"
        " stok_kodu = ?, stok_adi = ?, stok_aile = ?, stok_kaynagi = ?, depo = ?, test_durumu = ?, test_degisme = ?,"
        " test_degistiren_id = ?, is_emri_elle = ?, stoktan_atama = ?, stoktan_atayan_id = ?, asama = ?,"
        " erp_asama = 'montaj_tamamlandi' WHERE id = ?",
        (stok["is_emri_id"], stok["motor_seri_no"], stok["motor2_seri_no"], stok["sasi_no"], stok["numara_degisme"],
         stok["numara_degistiren_id"], stok["stok_kodu"], stok["stok_adi"], stok["stok_aile"], stok["stok_kaynagi"],
         stok["depo"], test, stok["test_degisme"], stok["test_degistiren_id"], stok["is_emri_elle"], zaman,
         kullanici_id, yeni, hedef["id"]),
    )
    nereden = ", ".join(p for p in (DEPOLAR.get(stok["depo"]), TEST_DURUMLARI.get(test, "testi bilinmiyor").lower()) if p)
    metin = (f"Stoktan bu siparişe atandı ({nereden})." if kullanici_id else
             f"ERP'de stok iş emri bu siparişe bağlandı; stok kartı bu karta taşındı ({nereden}).")
    vt.execute(
        "INSERT INTO urun_olaylari (urun_id, tur, zaman, kullanici_id, eski_asama, yeni_asama, metin)"
        " VALUES (?, 'asama', ?, ?, 'stokta', ?, ?)",
        (hedef["id"], zaman, kullanici_id, yeni, metin),
    )
    vt.execute("DELETE FROM urunler WHERE id = ?", (stok["id"],))
    return yeni


def atanabilecekler(vt, kod):
    """Stok kartının atanabileceği sipariş ürünleri: aynı ürün kodlu, açık siparişte, iş emri açılmamış ve
    stoktan atanmamış ürünler (teslim tarihi yakın olan önce)."""
    return vt.execute(
        "SELECT u.id, u.seri_no, u.adet_sira, k.miktar, k.teslim_tarihi, k.erp_durum, s.siparis_no, s.musteri"
        " FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id"
        " WHERE UPPER(k.urun_kodu) = ? AND u.is_emri_id IS NULL AND u.stoktan_atama IS NULL AND u.asama = 'siparis'"
        " AND COALESCE(k.erp_durum, '') NOT IN (?, ?) AND COALESCE(k.erp_genel_durum, '') != ? AND s.erp_listede = 1"
        " ORDER BY k.teslim_tarihi IS NULL, k.teslim_tarihi, s.siparis_no, u.adet_sira",
        ((kod or "").upper(), IPTAL, KAPALI, KAPALI),
    ).fetchall()


def stok_kartlari(vt, kod=None):
    """Stoktaki kartlar (stoktan çıkarılmamış), iş emri numarasıyla."""
    kosul, degerler = ("AND UPPER(u.stok_kodu) = ?", ((kod or "").upper(),)) if kod else ("", ())
    return vt.execute(
        "SELECT u.*, u.stok_kodu AS urun_kodu, u.stok_adi AS urun_adi, u.stok_aile AS aile, i.is_emri_no"
        " FROM urunler u LEFT JOIN is_emirleri i ON i.id = u.is_emri_id"
        f" WHERE u.kalem_id IS NULL AND u.stok_cikis IS NULL {kosul} ORDER BY u.stok_kodu, u.id",
        degerler,
    ).fetchall()


def stok_sayilari(vt):
    """Ürün koduna göre stoktaki kart sayısı (sipariş kartında ve panoda "Stokta var")."""
    return Counter(r[0].upper() for r in vt.execute(
        "SELECT stok_kodu FROM urunler WHERE kalem_id IS NULL AND stok_cikis IS NULL"))


# Ekranlar

@bp.app_context_processor
def sablon_degiskenleri():
    return {"DEPOLAR": DEPOLAR, "TEST_DURUMLARI": TEST_DURUMLARI, "stok_test_durumu": test_durumu}


@bp.route("/stok")
def liste():
    vt = baglanti()
    kartlar = stok_kartlari(vt)
    bekleyen = {}
    for kod in {k["urun_kodu"].upper() for k in kartlar}:
        bekleyen[kod] = atanabilecekler(vt, kod)
    gruplar = defaultdict(list)
    for k in kartlar:
        gruplar[k["aile"]].append(k)
    raporlar = {r["depo"]: r for r in vt.execute(
        "SELECT r.depo, r.zaman, y.dosya_adi FROM depo_raporlari r JOIN erp_yuklemeler y ON y.id = r.yukleme_id")}
    kart_kodlari, yari = kod_turleri(vt)
    kodlar = sorted({k for k in kart_kodlari if stok_ailesi(k, kart_kodlari, yari)})
    cikanlar = vt.execute(
        "SELECT u.*, k.ad_soyad FROM urunler u LEFT JOIN kullanicilar k ON k.id = u.stok_cikaran_id"
        " WHERE u.kalem_id IS NULL AND u.stok_cikis IS NOT NULL ORDER BY u.stok_cikis DESC LIMIT 20"
    ).fetchall()
    return render_template(
        "stok.html",
        makineler=[(aile, gruplar[aile]) for aile in AILE_SIRASI if aile in ANA_URUNLER and gruplar.get(aile)],
        yardimcilar=[(aile, gruplar[aile]) for aile in AILE_SIRASI if aile not in ANA_URUNLER and gruplar.get(aile)],
        toplam=len(kartlar),
        bekleyen=bekleyen,
        numaralar={k["id"]: [(ad, deger, kaynak) for _, ad, deger, kaynak in urun_numaralari(vt, k, k["aile"], None, k["urun_kodu"])]
                   for k in kartlar},
        raporlar=raporlar,
        kodlar=kodlar,
        cikanlar=cikanlar,
        AILE_ADLARI=AILE_ADLARI,
        STOK_DEPOLARI=STOK_DEPOLARI,
        CIKIS_SEBEPLERI=CIKIS_SEBEPLERI,
    )


def _stok_karti(vt, urun_id):
    kart = vt.execute("SELECT * FROM urunler WHERE id = ? AND kalem_id IS NULL AND stok_cikis IS NULL", (urun_id,)).fetchone()
    if kart is None:
        abort(404)
    return kart


def _geri(urun_id, capa=""):
    return redirect(url_for("urunler.sayfa", urun_id=urun_id) + capa)


@bp.route("/stok/ekle", methods=["POST"])
@ekip_gerekli
def ekle():
    """Depo raporunda olmayan (ya da ERP'de bulunamayan) bir stok makinesini elle ekler."""
    vt = baglanti()
    kod = " ".join((request.form.get("urun_kodu") or "").split()).upper()
    depo = request.form.get("depo") or None
    test = request.form.get("test") or None
    if depo not in (None, *STOK_DEPOLARI) or test not in (None, *TEST_DURUMLARI):
        abort(400)
    aile = stok_ailesi(kod, *kod_turleri(vt), elle=True)
    if not kod:
        flash("Ürün kodunu yazın.")
        return redirect(url_for(".liste") + "#ekle")
    if aile is None:
        flash(f"{kod}: makine, çene ya da kiriş kodu olarak tanınmadı (SVR, OVR, PP, OVF, WD, SCN, KCN, ACN, CB ile"
              " başlamalı; alt montaj kodları stok kartı olmaz).")
        return redirect(url_for(".liste") + "#ekle")
    adi = next((r[0] for r in vt.execute(
        "SELECT urun_adi FROM depo_stoklari WHERE urun_kodu = ? AND urun_adi IS NOT NULL UNION ALL"
        " SELECT urun_adi FROM siparis_kalemleri WHERE UPPER(urun_kodu) = ? AND urun_adi IS NOT NULL UNION ALL"
        " SELECT urun_adi FROM is_emirleri WHERE UPPER(urun_kodu) = ? AND urun_adi IS NOT NULL LIMIT 1",
        (kod, kod, kod))), None)
    with vt:
        urun_id = _kart_ac(vt, kod, adi, aile, depo, "elle", test, g.kullanici["id"])
        vt.execute(
            "INSERT INTO urun_olaylari (urun_id, tur, zaman, kullanici_id, metin) VALUES (?, 'not', ?, ?, ?)",
            (urun_id, _simdi(), g.kullanici["id"], "Stok makinesi elle eklendi."
             + (f" Depo: {DEPOLAR[depo]}." if depo else "")),
        )
    flash(f"{kod} stok kartı eklendi. Numaralarını ve biliniyorsa iş emrini girin.")
    return _geri(urun_id, "#stok")


@bp.route("/stok/<int:urun_id>/test", methods=["POST"])
@ekip_gerekli
def test(urun_id):
    vt = baglanti()
    kart = _stok_karti(vt, urun_id)
    durum = request.form.get("test")
    if durum not in TEST_DURUMLARI:
        abort(400)
    with vt:
        vt.execute("UPDATE urunler SET test_durumu = ?, test_degisme = ?, test_degistiren_id = ? WHERE id = ?",
                   (durum, _simdi(), g.kullanici["id"], kart["id"]))
    flash(f"{kart['stok_kodu']}: {TEST_DURUMLARI[durum].lower()} olarak kaydedildi.")
    return _geri(urun_id, "#stok")


@bp.route("/stok/<int:urun_id>/is-emri", methods=["POST"])
@ekip_gerekli
def is_emri(urun_id):
    """Stok kartının iş emrini girer, değiştirir ya da kaldırır (iş emri listelerinde olmalı)."""
    vt = baglanti()
    kart = _stok_karti(vt, urun_id)
    no = "".join((request.form.get("is_emri_no") or "").split())
    ie = None
    if no:
        ie = vt.execute("SELECT id, urun_kodu FROM is_emirleri WHERE is_emri_no = ?", (no,)).fetchone()
        if ie is None:
            flash(f"İş emri {no} yüklenen iş emri listelerinde yok; numarayı kontrol edin.")
            return _geri(urun_id, "#stok")
        if (ie["urun_kodu"] or "").upper() != kart["stok_kodu"].upper():
            flash(f"İş emri {no} başka bir ürünün ({ie['urun_kodu']}); bu kartın ürünü {kart['stok_kodu']}.")
            return _geri(urun_id, "#stok")
        sahibi = vt.execute("SELECT id FROM urunler WHERE is_emri_id = ? AND id != ?", (ie["id"], urun_id)).fetchone()
        if sahibi:
            flash(f"İş emri {no} başka bir kartta kayıtlı.")
            return _geri(urun_id, "#stok")
    with vt:
        vt.execute("UPDATE urunler SET is_emri_id = ?, is_emri_elle = 1 WHERE id = ?", (ie["id"] if ie else None, urun_id))
        vt.execute(
            "INSERT INTO urun_olaylari (urun_id, tur, zaman, kullanici_id, metin) VALUES (?, 'not', ?, ?, ?)",
            (urun_id, _simdi(), g.kullanici["id"], f"İş emri girildi: {no}." if ie else "İş emri kaldırıldı."),
        )
    flash(f"İş emri {no} kaydedildi." if ie else "İş emri kaldırıldı.")
    return _geri(urun_id, "#stok")


@bp.route("/stok/<int:urun_id>/ata", methods=["POST"])
@ekip_gerekli
def ata(urun_id):
    """Stok kartını bir siparişin ürün kartına atar; atanan ürünün sayfasına gider."""
    vt = baglanti()
    kart = _stok_karti(vt, urun_id)
    hedef_id = request.form.get("hedef", type=int)
    if hedef_id not in {u["id"] for u in atanabilecekler(vt, kart["stok_kodu"])}:
        flash("Bu stok makinesi seçilen ürüne atanamaz (iş emri açılmış, başka bir stok makinesi atanmış ya da"
              " ürün kodu farklı).")
        return redirect(request.referrer or url_for(".liste"))
    hedef = vt.execute("SELECT * FROM urunler WHERE id = ?", (hedef_id,)).fetchone()
    siparis = vt.execute(
        "SELECT s.siparis_no FROM siparis_kalemleri k JOIN siparisler s ON s.id = k.siparis_id WHERE k.id = ?",
        (hedef["kalem_id"],),
    ).fetchone()[0]
    with vt:
        asama = stoktan_ata(vt, kart, hedef, g.kullanici["id"])
    flash(f"{kart['stok_kodu']} stoktan {siparis} siparişine atandı; \"{ASAMALAR[asama]}\" aşamasından devam ediyor.")
    return _geri(hedef_id, "#asama")


@bp.route("/stok/<int:urun_id>/cikar", methods=["POST"])
@ekip_gerekli
def cikar(urun_id):
    """Stok kartını stoktan çıkarır (silinmez; Stok ekranında "stoktan çıkarılanlar"da görünür)."""
    vt = baglanti()
    kart = _stok_karti(vt, urun_id)
    sebep = request.form.get("sebep")
    if sebep not in CIKIS_SEBEPLERI:
        flash("Stoktan çıkarma sebebini seçin.")
        return _geri(urun_id, "#stok")
    aciklama = " ".join((request.form.get("aciklama") or "").split())
    metin = CIKIS_SEBEPLERI[sebep] + (f": {aciklama}" if aciklama else "")
    with vt:
        vt.execute("UPDATE urunler SET stok_cikis = ?, stok_cikis_sebep = ?, stok_cikaran_id = ? WHERE id = ?",
                   (_simdi(), metin, g.kullanici["id"], urun_id))
    flash(f"{kart['stok_kodu']} stoktan çıkarıldı ({metin}). Depo raporu yenilenene kadar bu adet için yeni kart açılmaz.")
    return redirect(url_for(".liste"))
