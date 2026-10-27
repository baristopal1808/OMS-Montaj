"""Yapay zekâ asistanı (deneme): ekip uygulamaya Türkçe soru sorar ("OZ-… siparişinin özeti, motor
seri no'su ne, montaj bitti mi?"). Her ekranın sağ altındaki sohbet kutusundan kullanılır
(_asistan_kutusu.html); soru sayfa yenilenmeden gönderilir, cevap JSON olarak döner.

Asistan Claude Haiku 5.5 ile çalışır ve veritabanını yalnızca bu dosyadaki araçlarla okur; cevap
tahminden değil kayıtlardan gelir, hiçbir şey yazmaz. Aynı konuşmadaki son KONUSMA_HAFIZASI soru ve
cevabı hatırlar ("Yeni konuşma" ile sıfırlanır). Her soru, cevabı ve yaklaşık maliyeti kaydedilir;
kutuda bu ayın toplamı görünür.

Yalnızca OMS_ASISTAN=1 ortam değişkeniyle açılır: baslat.bat gerçek veriyle (kullanıcı onayladı,
23/10/2026; sorulan siparişin bilgileri cevap için Anthropic'e gider), asistan-deneme.bat uydurma
veriyle ayrı bir kopyada. API anahtarı OMS_ANAHTAR_DOSYASI'nın gösterdiği dosyadan (geliştirmede
"OMS Veri\\anthropic-anahtar.txt") ya da ANTHROPIC_API_KEY ortam değişkeninden gelir; git'e girmez.
"""

import json
import os
from datetime import date, datetime

import anthropic
from anthropic import beta_tool
from flask import Blueprint, abort, current_app, g, get_template_attribute, jsonify, request, session

from .asamalar import ASAMALAR
from .erp_aktarim import IPTAL
from .is_emri_aktarim import is_emri_durumu
from .makineler import sevk_edilecek_makineler
from .numaralar import KAYNAKLAR, urun_numaralari
from .siparisler import (
    DURUMLAR, TIPLER, URUN_DURUMLARI, ozetle, siparis_durum_ozeti, teslim_bilgisi, urun_is_emri_sinifi,
)
from .urun_kurallari import EKLENTI_DURUMLARI, VARSAYILAN_EKLENTI_DURUMU, pp_eklentisi_mi, renk, yag
from .veritabani import baglanti

bp = Blueprint("asistan", __name__)

MODEL = "claude-haiku-5-5"
# Claude Haiku 5.5 fiyatı (100 bin token'a kadar istek), 1 milyon token başına dolar
GIRIS_FIYATI, CIKIS_FIYATI = 0.10, 0.50
EN_COK_ADIM = 6  # bir soruda en çok kaç kez araç çağrılabilir
KONUSMA_HAFIZASI = 3  # devam sorularında hatırlanan önceki soru-cevap sayısı
SISTEM = """Sen OMS Pile Driving Equipment montaj fabrikasının iş takip uygulamasının asistanısın. \
Montaj ekibinin sorularını Türkçe, kısa ve net cevapla.

- Bilgiyi yalnızca araçlardan al. Araçların vermediği bir şeyi tahmin etme; bulamadıysan bunu söyle.
- Sipariş numaraları "OZ-" ile başlar (örnek: OZ-TS0001). Kullanıcı numarayı eksik yazarsa önce siparis_ara ile ara.
- Terimler: iş emri (ERP'de ürünün üretim emri), kırılım (iş emrinin alt montajı), aşama (uygulamadaki \
montaj aşaması: Sipariş, Malzeme hazırlık, Montaj, Montaj tamamlandı, Teste hazır, Test, Temizlik, Sevke hazır, \
Sevk edildi, Stokta), planlama birimi ürün \
üretim durumu (ERP'deki "Ürün Durumu": İmalatta, Montajda, Hazır, Sevke Hazır).
- Motor seri no ve şasi no'yu söylerken kaynağını da belirt (ekip girdi ya da ERP iş emri açıklamasından).
- "Montaj tamamlandı mı" sorusunda iş emrinin ERP'de tamamlanıp tamamlanmadığına ve ürünün aşamasına bak.
- Cevabı kısa maddelerle ver; tablo kullanma."""


def asistan_acik():
    return bool(current_app.config.get("ASISTAN_ACIK"))


def api_anahtari():
    """Anahtar dosyasındaki (Not Defteri'nin eklediği BOM'u da atarak) ya da ortam değişkenindeki anahtar."""
    dosya = os.environ.get("OMS_ANAHTAR_DOSYASI")
    if dosya and os.path.isfile(dosya):
        with open(dosya, encoding="utf-8-sig") as f:
            return f.read().strip()
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def _json(veri):
    return json.dumps(veri, ensure_ascii=False, default=str)


# Araçlar: yalnızca okur. Her biri JSON metni döndürür.

def siparis_ara(metin: str) -> str:
    """Siparişleri sipariş no, müşteri, ürün kodu, seri no ya da iş emri no ile arar; en çok 15 sonuç.

    Args:
        metin: Aranacak metin; örnek: "OZ-TS0001", "TS0001", "SVR-50", "TEST FIRMA".
    """
    vt = baglanti()
    desen = f"%{metin.strip()}%"
    sonuc = []
    for s in vt.execute(
        "SELECT DISTINCT s.* FROM siparisler s"
        " LEFT JOIN siparis_kalemleri k ON k.siparis_id = s.id LEFT JOIN urunler u ON u.kalem_id = k.id"
        " WHERE s.siparis_no LIKE ? OR s.musteri LIKE ? OR k.urun_kodu LIKE ? OR k.urun_adi LIKE ?"
        " OR k.bagli_is_emri_no LIKE ? OR u.seri_no LIKE ? ORDER BY s.siparis_no DESC LIMIT 15",
        (desen,) * 6,
    ).fetchall():
        kalemler = vt.execute("SELECT * FROM siparis_kalemleri WHERE siparis_id = ?", (s["id"],)).fetchall()
        o = ozetle(s, kalemler)
        sonuc.append({"siparis_no": s["siparis_no"], "musteri": s["musteri"], "tip": TIPLER.get(s["tip"], s["tip"]),
                      "durum": DURUMLAR[o["durum"]], "teslim_tarihi": o["teslim"],
                      "urunler": ", ".join(f"{adet} {aile}" for aile, adet in o["urunler"])})
    return _json(sonuc or {"bulunamadi": f'"{metin}" ile eşleşen sipariş yok.'})


def siparis_bilgisi(siparis_no: str) -> str:
    """Bir siparişin bütün bilgisi: müşteri, durum, teslim tarihi, ürünler (seri no, aşama, iş emri ve
    durumu, motor seri no, şasi no), güç ünitesinin opsiyonel ekipmanları (kablosuz kumanda, uzaktan erişim
    modülü) ve montaj durumları, alt montajlar ve siparişin durum özeti.

    Args:
        siparis_no: Tam sipariş numarası; örnek: "OZ-TS0001".
    """
    vt = baglanti()
    s = vt.execute("SELECT * FROM siparisler WHERE siparis_no = ?", (siparis_no.strip().upper(),)).fetchone()
    if s is None:
        return _json({"bulunamadi": f"{siparis_no} numaralı sipariş yok. siparis_ara ile aramayı dene."})
    kalemler = vt.execute("SELECT * FROM siparis_kalemleri WHERE siparis_id = ? ORDER BY sira_no", (s["id"],)).fetchall()
    o = ozetle(s, kalemler)
    is_emirleri = {ie["id"]: ie for ie in vt.execute("SELECT * FROM is_emirleri WHERE siparis_id = ?", (s["id"],))}
    urunler, eklentiler, diger = [], [], []
    for k in kalemler:
        if k["tur"] == "hizmet" or k["erp_durum"] == IPTAL:
            continue
        if pp_eklentisi_mi(k["urun_kodu"], s["tip"]):
            eklentiler.append({"urun": f'{k["urun_kodu"]} {k["urun_adi"]}',
                               "montaj_durumu": EKLENTI_DURUMLARI[k["montaj_durumu"] or VARSAYILAN_EKLENTI_DURUMU]})
            continue
        kartlar = vt.execute("SELECT * FROM urunler WHERE kalem_id = ? ORDER BY adet_sira", (k["id"],)).fetchall()
        if not kartlar:
            diger.append(f'{k["urun_kodu"]} {k["urun_adi"]} ({k["miktar"]:g} {k["birim"] or ""})'.strip())
            continue
        for u in kartlar:
            ie = is_emirleri.get(u["is_emri_id"])
            urunler.append({
                "urun_kodu": k["urun_kodu"], "urun_adi": k["urun_adi"], "aile": k["aile"], "seri_no": u["seri_no"],
                "adet": f'{u["adet_sira"]}/{k["miktar"]:g}', "asama": ASAMALAR[u["asama"]],
                "is_emri": {"no": ie["is_emri_no"], "durum": is_emri_durumu(ie)[0], "acilis": ie["acilis_tarihi"],
                            "tahmini_bitis": ie["tahmini_bitis"], "kapanis": ie["kapatma_tarihi"],
                            "stoga_giren": ie["gercek_miktar"], "planlanan": ie["plan_miktar"]} if ie else None,
                "is_emri_durumu": URUN_DURUMLARI[urun_is_emri_sinifi(u["asama"], k, ie)],
                "planlama_birimi_urun_durumu": k["erp_urun_durumu"],
                "numaralar": {ad: (f"{deger} ({KAYNAKLAR[kaynak]})" if deger else "girilmedi")
                              for _, ad, deger, kaynak in urun_numaralari(vt, u, k["aile"], s["id"], k["urun_kodu"])},
                "renk": renk(k["aciklama"]),
                "yag": (yag(k["aciklama"]) or ("bilgi yok",))[0] if k["aile"] == "PP" else None,
            })
    alt = [{"is_emri": ie["is_emri_no"], "urun": f'{ie["urun_kodu"]} {ie["urun_adi"] or ""}'.strip(),
            "durum": is_emri_durumu(ie)[0]} for ie in is_emirleri.values() if not ie["kalem_id"]]
    durum = siparis_durum_ozeti(vt, s)
    return _json({
        "siparis_no": s["siparis_no"], "musteri": s["musteri"], "tip": TIPLER.get(s["tip"], s["tip"]),
        "durum": DURUMLAR[o["durum"]], "talep_tarihi": s["talep_tarihi"], "teslim_tarihi": o["teslim"],
        "teslime_kalan": (teslim_bilgisi(o["teslim"]) or ("",))[0] if o["durum"] == "acik" else None,
        "son_sevk": o["son_sevk"], "notu": s["notu"],
        "durum_ozeti": {ad: adet for _, ad, adet in durum["urunler"]},
        "urunler": urunler, "opsiyonel_ekipmanlar": eklentiler, "diger_kalemler": diger,
        "alt_montaj_is_emirleri": alt,
    })


def makine_ara(metin: str) -> str:
    """Makineyi seri no, şasi no ya da motor seri no ile arar (motor seri no ERP iş emri açıklamalarında da
    aranır); makinenin siparişini ve durumunu döndürür. En çok 10 sonuç.

    Args:
        metin: Seri no, şasi no ya da motor seri no'nun tamamı ya da bir parçası; örnek: "OZ-TS0001-PP-01", "0000 111".
    """
    vt = baglanti()
    desen = f"%{' '.join(metin.split())}%"
    sonuc = []
    for u in vt.execute(
        "SELECT DISTINCT u.*, k.urun_kodu, k.urun_adi, k.aile, k.siparis_id, s.siparis_no, s.musteri"
        " FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id JOIN siparisler s ON s.id = k.siparis_id"
        " LEFT JOIN is_emirleri i ON i.id = u.is_emri_id LEFT JOIN is_emri_satirlari r ON r.is_emri_id = i.id"
        " WHERE u.seri_no LIKE ? OR u.sasi_no LIKE ? OR u.motor_seri_no LIKE ? OR u.motor2_seri_no LIKE ?"
        " OR i.aciklama LIKE ? OR r.aciklama LIKE ? LIMIT 10",
        (desen,) * 6,
    ).fetchall():
        sonuc.append({
            "siparis_no": u["siparis_no"], "musteri": u["musteri"], "urun": f'{u["urun_kodu"]} {u["urun_adi"]}',
            "seri_no": u["seri_no"], "asama": ASAMALAR[u["asama"]],
            "numaralar": {ad: (f"{deger} ({KAYNAKLAR[kaynak]})" if deger else "girilmedi")
                          for _, ad, deger, kaynak in urun_numaralari(vt, u, u["aile"], u["siparis_id"], u["urun_kodu"])},
        })
    return _json(sonuc or {"bulunamadi": f'"{metin}" ile eşleşen makine yok.'})


def sevk_edilecek_makineler_listesi(sadece_gecikenler: bool = False) -> str:
    """Sevk edilecek (açık siparişlerdeki, sevk edilmemiş) makineler: sipariş, ürün, teslim tarihi, aşama, iş emri
    durumu ve planlama birimi ürün durumu. Onay bekleyen siparişler sayılmaz.

    Args:
        sadece_gecikenler: True ise yalnızca teslim tarihi geçmiş makineler.
    """
    bugun = date.today().isoformat()
    sonuc = []
    for m in sevk_edilecek_makineler(baglanti()):
        if sadece_gecikenler and not (m["teslim_tarihi"] and m["teslim_tarihi"] < bugun):
            continue
        ie = {"durum": m["ie_durum"], "gercek_miktar": m["ie_gercek"]} if m["is_emri_no"] else None
        sonuc.append({"siparis_no": m["siparis_no"], "musteri": m["musteri"], "urun": m["urun_kodu"],
                      "seri_no": m["seri_no"], "teslim_tarihi": m["teslim_tarihi"], "asama": ASAMALAR[m["asama"]],
                      "is_emri": f'{m["is_emri_no"]} ({is_emri_durumu(ie)[0]})' if ie else "açılmadı",
                      "planlama_birimi_urun_durumu": m["erp_urun_durumu"]})
    return _json({"makine_sayisi": len(sonuc), "makineler": sonuc})


ARACLAR = [beta_tool(arac) for arac in (siparis_ara, siparis_bilgisi, makine_ara, sevk_edilecek_makineler_listesi)]


def sor(soru, gecmis=()):
    """Soruyu Claude'a sorar; gecmis: aynı konuşmanın önceki (soru, cevap) çiftleri.
    {"cevap", "araclar", "giris", "cikis", "maliyet"} ya da {"hata"} döndürür."""
    anahtar = api_anahtari()
    if not anahtar:
        return {"hata": 'API anahtarı tanımlı değil. Anahtarı "OMS Veri\\anthropic-anahtar.txt" dosyasına yazıp '
                        "asistan-deneme.bat ile yeniden açın."}
    istemci = anthropic.Anthropic(api_key=anahtar, max_retries=2, timeout=60)
    giris = cikis = 0
    kullanilan, son = [], None
    try:
        runner = istemci.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=4096,
            system=SISTEM,
            tools=ARACLAR,
            messages=[
                *({"role": rol, "content": metin} for onceki, cevap in gecmis
                  for rol, metin in (("user", onceki), ("assistant", cevap))),
                {"role": "user", "content": soru},
            ],
            output_config={"effort": "medium"},
            max_iterations=EN_COK_ADIM,
        )
        for mesaj in runner:
            son = mesaj
            giris += mesaj.usage.input_tokens + (mesaj.usage.cache_read_input_tokens or 0)
            cikis += mesaj.usage.output_tokens
            kullanilan += [b.name for b in mesaj.content if b.type == "tool_use"]
    except anthropic.AuthenticationError:
        return {"hata": "API anahtarı geçersiz. Anahtarı kontrol edin."}
    except anthropic.PermissionDeniedError:
        return {"hata": "API anahtarının bu işleme izni yok."}
    except anthropic.RateLimitError:
        return {"hata": "Kısa sürede çok soru soruldu; bir dakika bekleyip yeniden deneyin."}
    except anthropic.BadRequestError as hata:
        if "credit" in str(hata).lower():
            return {"hata": "Anthropic hesabında bakiye yok; console.anthropic.com'dan bakiye yükleyin."}
        return {"hata": f"İstek reddedildi: {hata.message}"}
    except anthropic.APIConnectionError:
        return {"hata": "Anthropic'e ulaşılamadı. Bilgisayarın internete çıkabildiğini kontrol edin."}
    except anthropic.APIStatusError as hata:
        return {"hata": f"Anthropic hata verdi ({hata.status_code}); biraz sonra yeniden deneyin."}
    if son is None:
        return {"hata": "Cevap alınamadı."}
    if son.stop_reason == "refusal":
        cevap = "Asistan bu soruyu cevaplamadı. Soruyu farklı sorarak yeniden deneyin."
    else:
        cevap = "\n".join(b.text for b in son.content if b.type == "text").strip() or "Cevap boş geldi."
    return {
        "cevap": cevap,
        "araclar": kullanilan,
        "giris": giris,
        "cikis": cikis,
        "maliyet": (giris * GIRIS_FIYATI + cikis * CIKIS_FIYATI) / 1_000_000,
    }


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _son_soru_id(vt):
    return vt.execute("SELECT COALESCE(MAX(id), 0) FROM asistan_sorulari").fetchone()[0]


def konusma(vt):
    """Bu kullanıcının şu anki konuşması (sorular eskiden yeniye). Konuşma oturum açılınca ya da "Yeni
    konuşma"yla başlar; sınır, o anki son sorunun kayıt numarasıdır."""
    if "asistan_sinir" not in session:
        session["asistan_sinir"] = _son_soru_id(vt)
    return vt.execute(
        "SELECT * FROM asistan_sorulari WHERE kullanici_id = ? AND id > ? ORDER BY id",
        (g.kullanici["id"], session["asistan_sinir"]),
    ).fetchall()


def ay_ozeti(vt):
    """Bu ay cevaplanan soru sayısı ve yaklaşık toplam maliyet (dolar)."""
    return tuple(vt.execute(
        "SELECT COUNT(*), COALESCE(SUM(maliyet), 0) FROM asistan_sorulari WHERE zaman >= ? AND hata IS NULL",
        (f"{date.today():%Y-%m}-01",),
    ).fetchone())


def ilk_ad(ad_soyad):
    """Karşılamada kullanılan ad: 'TEST KULLANICI' → 'TEST'. Hitap (Bey, Hanım) eklenmez; kişinin nasıl
    hitap edilmek istediği bilinmiyor."""
    return (ad_soyad or "").split()[0] if (ad_soyad or "").strip() else ""


@bp.app_context_processor
def sablon_degiskenleri():
    """Sohbet kutusu her sayfada çizilir; konuşma ve ay özeti yalnızca kutu açıksa okunur."""
    return {
        "asistan_konusmasi": lambda: konusma(baglanti()),
        "asistan_ay_ozeti": lambda: ay_ozeti(baglanti()),
        "asistan_anahtar_var": lambda: bool(api_anahtari()),
        "ilk_ad": ilk_ad,
    }


@bp.route("/asistan/sor", methods=["POST"])
def sor_gorunumu():
    """Sohbet kutusunun sorusu: cevabın HTML'i ve bu ayın özeti JSON olarak döner."""
    if not asistan_acik():
        abort(404)
    vt = baglanti()
    soru = (request.form.get("soru") or "").strip()[:1000]
    if not soru:
        abort(400)
    gecmis = [(s["soru"], s["cevap"]) for s in konusma(vt) if s["cevap"]][-KONUSMA_HAFIZASI:]
    sonuc = sor(soru, gecmis)
    with vt:
        kayit_id = vt.execute(
            "INSERT INTO asistan_sorulari (kullanici_id, zaman, soru, cevap, hata, araclar, giris, cikis, maliyet)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (g.kullanici["id"], _simdi(), soru, sonuc.get("cevap"), sonuc.get("hata"),
             ", ".join(sonuc.get("araclar", [])), sonuc.get("giris"), sonuc.get("cikis"), sonuc.get("maliyet")),
        ).lastrowid
    kayit = vt.execute("SELECT * FROM asistan_sorulari WHERE id = ?", (kayit_id,)).fetchone()
    sayi, toplam = ay_ozeti(vt)
    return jsonify(
        cevap=str(get_template_attribute("_asistan_kutusu.html", "cevap_balonu")(kayit)),
        ozet=f"bu ay {sayi} soru · ≈ {toplam:.3f} $",
    )


@bp.route("/asistan/yeni", methods=["POST"])
def yeni_konusma():
    if not asistan_acik():
        abort(404)
    session["asistan_sinir"] = _son_soru_id(baglanti())
    return jsonify(tamam=True)
