"""Ürünün zaman akışı: kartın başından geçen her şey, yeniden eskiye (Planner'daki görev sohbetinin karşılığı).

Saklananlar (urun_olaylari): ekibin notları ve aşama değişiklikleri (ekip ya da ERP yüklemesi). Ekip aşamayı
ileri de geri de alabilir; değişikliğin yanına isteğe bağlı bir not yazılır. Notu yazan kişi sonradan
düzeltebilir: önceki hâli not_duzeltmeleri tablosunda saklanır, not silinmez (kullanıcı kararları, 02/11/2026).

Hesaplananlar (saklanmaz, her açılışta ERP verisinden ve uygulamanın öbür kayıtlarından okunur; böylece geçmişi
de ERP'deki tarihleriyle görünür): sipariş talebinin onayı, iş emrinin açılışı, ilk stok girişi ve tamamlanması,
sipariş talebi revizyonları, ERP'deki sevk, makine numarası girişleri ve teyitleri, eksik malzeme ve "İmalatta"
cevapları, yarı mamullerin "Hazır" işaretleri, opsiyonel ekipmanın montaj durumu ve basılan montaj formları.
"""

from collections import defaultdict
from datetime import datetime

from .asamalar import ASAMALAR
from .bicim import tarih
from .erp_aktarim import REVIZYON_ADLARI
from .form_kurallari import FORM_TURLERI
from .is_emri_aktarim import KAPALI
from .numaralar import TEYIT
from .urun_kurallari import EKLENTI_DURUMLARI, VARSAYILAN_EKLENTI_DURUMU, pp_eklentisi_mi
from .uyarilar import EKSIK_CEVAPLARI, IMALATTA_CEVAPLARI

ERP = "ERP"


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def asama_degistir(vt, urun_id, eski, yeni, metin, kullanici_id):
    vt.execute("UPDATE urunler SET asama = ? WHERE id = ?", (yeni, urun_id))
    vt.execute(
        "INSERT INTO urun_olaylari (urun_id, tur, zaman, kullanici_id, eski_asama, yeni_asama, metin)"
        " VALUES (?, 'asama', ?, ?, ?, ?, ?)",
        (urun_id, _simdi(), kullanici_id, eski, yeni, metin),
    )


def not_ekle(vt, urun_id, metin, kullanici_id):
    vt.execute(
        "INSERT INTO urun_olaylari (urun_id, tur, zaman, kullanici_id, metin) VALUES (?, 'not', ?, ?, ?)",
        (urun_id, _simdi(), kullanici_id, metin),
    )


def not_duzelt(vt, olay, metin):
    """Notu (ya da aşama değişikliğinin notunu) düzeltir; önceki hâli saklanır."""
    zaman = _simdi()
    vt.execute("INSERT INTO not_duzeltmeleri (olay_id, eski_metin, zaman) VALUES (?, ?, ?)", (olay["id"], olay["metin"], zaman))
    vt.execute("UPDATE urun_olaylari SET metin = ?, duzeltme = ? WHERE id = ?", (metin, zaman, olay["id"]))


def _oge(zaman, tur, baslik, kim=ERP, metin=None, olay=None):
    """Akışın bir satırı. zaman: 'YYYY-AA-GG' (ERP'nin günlük tarihleri) ya da 'YYYY-AA-GG SS:DD:ss'."""
    return {"zaman": zaman, "gun": len(zaman) == 10, "tur": tur, "baslik": baslik, "kim": kim, "metin": metin,
            "olay": olay, "onceki": [], "form": None}


def akis(vt, urun, numara_adlari):
    """Ürünün zaman akışı, yeniden eskiye. urun: urunler.urun_kaydi satırı; numara_adlari: alan → ad."""
    ogeler = []

    # Ekibin notları ve aşama değişiklikleri (ERP yüklemesinin değişikliklerinde kişi yok)
    olaylar = vt.execute(
        "SELECT o.*, k.ad_soyad FROM urun_olaylari o LEFT JOIN kullanicilar k ON k.id = o.kullanici_id"
        " WHERE o.urun_id = ? ORDER BY o.id",
        (urun["id"],),
    ).fetchall()
    onceki = defaultdict(list)
    if olaylar:
        for d in vt.execute(
            f"SELECT * FROM not_duzeltmeleri WHERE olay_id IN ({', '.join('?' * len(olaylar))}) ORDER BY id DESC",
            [o["id"] for o in olaylar],
        ):
            onceki[d["olay_id"]].append(d)
    for o in olaylar:
        if o["tur"] == "asama":
            baslik = f"Aşama: {ASAMALAR.get(o['eski_asama'], o['eski_asama'])} → {ASAMALAR.get(o['yeni_asama'], o['yeni_asama'])}"
            oge = _oge(o["zaman"], "asama", baslik, o["ad_soyad"] or "ERP yüklemesi", o["metin"], o)
        else:
            oge = _oge(o["zaman"], "not", "Not", o["ad_soyad"] or "", o["metin"], o)
        oge["onceki"] = onceki[o["id"]]
        ogeler.append(oge)

    # Sipariş talebi ve revizyonları (satırın ve siparişin kendisinin), ERP'deki sevk
    talep = vt.execute("SELECT talep_tarihi FROM siparisler WHERE id = ?", (urun["siparis_id"],)).fetchone()[0]
    if talep:
        ogeler.append(_oge(talep, "erp", "Sipariş talebi onaylandı"))
    for r in vt.execute(
        "SELECT r.*, y.zaman FROM siparis_revizyonlari r JOIN erp_yuklemeler y ON y.id = r.yukleme_id"
        " WHERE r.siparis_id = ? AND (r.sira_no = ? OR r.sira_no IS NULL) ORDER BY r.id",
        (urun["siparis_id"], urun["sira_no"]),
    ):
        ad = REVIZYON_ADLARI.get(r["alan"], r["alan"])
        if r["alan"] in ("yeni_satir", "iptal", "iptal_kalkti"):
            ogeler.append(_oge(r["zaman"], "erp", f"Sipariş talebi revize edildi: {ad.lower()}"))
        else:
            eski, yeni = (tarih(r["eski"]), tarih(r["yeni"])) if r["alan"] == "teslim_tarihi" else (r["eski"], r["yeni"])
            ogeler.append(_oge(r["zaman"], "erp", f"Sipariş talebi revize edildi: {ad.lower()}", metin=f"{eski or '—'} → {yeni or '—'}"))
    if urun["son_sevk_tarihi"]:
        ogeler.append(_oge(urun["son_sevk_tarihi"], "erp", "ERP'de sevk edildi"))

    # İş emri: açılış, ilk stok girişi, tamamlanma; eksik malzeme cevapları ve yarı mamul işaretleri
    ie = vt.execute("SELECT * FROM is_emirleri WHERE id = ?", (urun["is_emri_id"],)).fetchone() if urun["is_emri_id"] else None
    if ie:
        no = ie["is_emri_no"]
        if ie["acilis_tarihi"]:
            ogeler.append(_oge(ie["acilis_tarihi"], "erp", f"İş emri {no} açıldı"))
        tamamlandi = ie["durum"] == KAPALI and ie["gercek_miktar"]
        if ie["ilk_stok_giris"] and not (tamamlandi and (ie["plan_miktar"] or 1) <= 1):
            ogeler.append(_oge(ie["ilk_stok_giris"], "erp", f"İş emri {no}: ilk stok girişi"))
        if tamamlandi and ie["kapatma_tarihi"]:
            ogeler.append(_oge(ie["kapatma_tarihi"], "erp", f"İş emri {no} ERP'de tamamlandı",
                               metin=f"{ie['gercek_miktar']:g}/{(ie['plan_miktar'] or 0):g} stoğa girdi"))
        for c in vt.execute(
            "SELECT c.*, k.ad_soyad FROM eksik_cevaplari c LEFT JOIN kullanicilar k ON k.id = c.kullanici_id"
            " WHERE c.is_emri_no = ? ORDER BY c.id",
            (no,),
        ):
            ogeler.append(_oge(c["zaman"], "cevap", f"Eksik malzeme: {EKSIK_CEVAPLARI.get(c['cevap'], c['cevap'])}",
                               c["ad_soyad"] or ""))
        for i in vt.execute(
            "SELECT y.zaman, k.ad_soyad, COUNT(*) AS adet FROM gelen_yari_mamuller y"
            " LEFT JOIN kullanicilar k ON k.id = y.kullanici_id WHERE y.is_emri_no = ? GROUP BY y.zaman, y.kullanici_id",
            (no,),
        ):
            ogeler.append(_oge(i["zaman"], "cevap", f"{i['adet']} yarı mamul \"Hazır\" işaretlendi", i["ad_soyad"] or ""))
    for c in vt.execute(
        "SELECT c.*, k.ad_soyad, i.is_emri_no FROM imalatta_cevaplari c LEFT JOIN kullanicilar k ON k.id = c.kullanici_id"
        " LEFT JOIN is_emirleri i ON i.id = c.is_emri_id WHERE c.urun_id = ?",
        (urun["id"],),
    ):
        ogeler.append(_oge(c["zaman"], "cevap", f"ERP'de \"İmalatta\" uyarısı: {IMALATTA_CEVAPLARI.get(c['cevap'], c['cevap'])}",
                           c["ad_soyad"] or ""))

    # Makine numaraları: giriş, değişiklik (sebebiyle) ve teyit
    for d in vt.execute(
        "SELECT d.*, k.ad_soyad FROM numara_degisiklikleri d LEFT JOIN kullanicilar k ON k.id = d.kullanici_id"
        " WHERE d.urun_id = ? ORDER BY d.id",
        (urun["id"],),
    ):
        ad = numara_adlari.get(d["alan"], d["alan"])
        if d["sebep"] == TEYIT:
            oge = _oge(d["zaman"], "numara", f"{ad} teyit edildi: {d['yeni']}", d["ad_soyad"] or "")
        elif d["eski"]:
            oge = _oge(d["zaman"], "numara", f"{ad} değiştirildi: {d['eski']} → {d['yeni']}", d["ad_soyad"] or "", d["sebep"])
        else:
            oge = _oge(d["zaman"], "numara", f"{ad} girildi: {d['yeni']}", d["ad_soyad"] or "")
        ogeler.append(oge)

    # Güç ünitesinin opsiyonel ekipmanları: montaj durumunun son değişikliği
    if urun["aile"] == "PP":
        for k in vt.execute(
            "SELECT k.urun_kodu, k.montaj_durumu, k.montaj_degisme, u.ad_soyad FROM siparis_kalemleri k"
            " LEFT JOIN kullanicilar u ON u.id = k.montaj_degistiren_id WHERE k.siparis_id = ? AND k.montaj_degisme IS NOT NULL",
            (urun["siparis_id"],),
        ):
            if pp_eklentisi_mi(k["urun_kodu"], urun["tip"]):
                durum = EKLENTI_DURUMLARI[k["montaj_durumu"] or VARSAYILAN_EKLENTI_DURUMU]
                ogeler.append(_oge(k["montaj_degisme"], "cevap", f"Opsiyonel ekipman {k['urun_kodu']}: {durum}", k["ad_soyad"] or ""))

    # Basılan montaj formları (PDF'iyle)
    for f in vt.execute(
        "SELECT f.id, f.tur, f.zaman, k.ad_soyad FROM urun_formlari f LEFT JOIN kullanicilar k ON k.id = f.kullanici_id"
        " WHERE f.urun_id = ? ORDER BY f.id",
        (urun["id"],),
    ):
        oge = _oge(f["zaman"], "form", f"{FORM_TURLERI.get(f['tur'], f['tur'])} basıldı", f["ad_soyad"] or "")
        oge["form"] = f["id"]
        ogeler.append(oge)

    # Yeniden eskiye; aynı anda olanlarda sonra kaydedilen üstte (sıralama kararlıdır)
    ogeler.reverse()
    ogeler.sort(key=lambda o: o["zaman"], reverse=True)
    return ogeler
