"""Motor açılışı için WhatsApp'tan haber verme (kullanıcı, 19/11/2026).

Güç ünitesinin motor açılışı kabin testinden sonra yapılır. Kabin testi tamamlanınca (ürün Test'ten Temizlik'e ya da
daha ileri geçince) açılır bir pencere "Motor açılışı gerekli" der ve hazır bir WhatsApp mesajı önerir; ekip
"WhatsApp'ta aç"a basar, WhatsApp mesaj yazılmış olarak açılır, ekip yalnızca "Gönder"e basar. Mesaj yalnızca
Volvo motorlu kabinlerde önerilir (kullanıcı seçti); CAT motorlu kabinde pencere yalnızca açılışın yapılıp
yapılmadığını sorar. Pencere kapatılsa da düğme ürün sayfasındaki kontrol listesinde durur.

Mesajın gideceği kişinin hitabı (örneğin "Ad Bey"), telefon numarası ve mesaj metni Ayarlar > Motor açılışı
ekranından girilir; gerçek veri olduğu için koda ve git'e girmez, veritabanında (ayarlar tablosu) durur. Mesaj
metninde {hitap} kişinin hitabıyla, {motor} motor seri no'larıyla değiştirilir; iki motorlu güç ünitesinde
"motorumuzun" yerine "motorlarımızın" yazılır.

"WhatsApp'ta aç"a basılınca zaman akışına "Motor açılışı için WhatsApp'tan haber verildi" yazılır (mesajın
gerçekten gönderilip gönderilmediğini uygulama bilemez; WhatsApp'ı açtığını kaydeder).
"""

import re
from datetime import date, datetime
from urllib.parse import quote

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, session, url_for

from .kimlik import ekip_gerekli
from .kontrol_listesi import ACILIS_HABERI, isaretle, kontrol_listeleri, test_bitti_mi
from .numaralar import MOTOR_ALANLARI, urun_numaralari
from .urun_kurallari import makine_kodu
from .veritabani import baglanti

bp = Blueprint("motor_acilisi", __name__)

HITAP, TELEFON, MESAJ = "acilis_hitap", "acilis_telefon", "acilis_mesaj"
VARSAYILAN_MESAJ = ("Merhaba {hitap}, {motor} seri numaralı motorumuzun bulunduğu kabin testi tamamlandı. "
                    "Motor açılışı gereklidir. Ne zaman müsaitsiniz?")
OTURUM_ANAHTARI = "motor_acilisi_sor"  # aşama değişince bir sonraki sayfada açılacak pencerenin ürünü


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ayarlar(vt):
    """{hitap, telefon, mesaj}: Ayarlar'dan girilen değerler; mesaj girilmemişse varsayılan metin."""
    degerler = {r["anahtar"]: r["deger"] for r in vt.execute(
        "SELECT anahtar, deger FROM ayarlar WHERE anahtar IN (?, ?, ?)", (HITAP, TELEFON, MESAJ))}
    return {"hitap": degerler.get(HITAP) or "", "telefon": degerler.get(TELEFON) or "",
            "mesaj": degerler.get(MESAJ) or VARSAYILAN_MESAJ}


def telefon_duzelt(metin):
    """WhatsApp'ın istediği biçim: yalnızca rakamlar, ülke koduyla (Türkiye 90). '0532 111 22 33' → '905321112233'.
    Geçersizse None."""
    rakamlar = re.sub(r"\D", "", metin or "")
    if rakamlar.startswith("00"):
        rakamlar = rakamlar[2:]
    if len(rakamlar) == 11 and rakamlar.startswith("0"):
        rakamlar = "90" + rakamlar[1:]
    elif len(rakamlar) == 10 and rakamlar.startswith("5"):
        rakamlar = "90" + rakamlar
    return rakamlar if 10 <= len(rakamlar) <= 15 else None


def motor_nolari(vt, urun):
    """Güç ünitesinin motor seri no'ları (ekibin girdiği ya da ERP'den okunan), sırasıyla."""
    return [deger for alan, _, deger, _ in urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"])
            if alan in MOTOR_ALANLARI and deger]


def volvo_mu(vt, urun, nolar=None):
    """Motor Volvo mu: Ayarlar'da girilen motor markasından (formlardaki motor bilgisi), marka girilmemişse motor
    seri no'sundan (CAT numaralarında harf var: N5F00001; Volvo'nunkiler yalnızca rakam). Bilinmiyorsa Volvo
    sayılır (güç ünitelerinin çoğu Volvo motorlu)."""
    motor = vt.execute("SELECT marka FROM motor_bilgileri WHERE urun_kodu = ?", (makine_kodu(urun["urun_kodu"]),)).fetchone()
    marka = ((motor["marka"] if motor else "") or "").upper()
    if "CAT" in marka:
        return False
    if "VOLVO" in marka:
        return True
    nolar = motor_nolari(vt, urun) if nolar is None else nolar
    return not any(re.search(r"[A-Za-z]", no) for no in nolar)


def mesaj_metni(sablon, hitap, nolar):
    """Hazır mesaj: {hitap} ve {motor} yerine konur; iki motorda "motorumuzun" → "motorlarımızın"."""
    motor = " ve ".join(nolar) if nolar else "(motor seri no girilmedi)"
    metin = sablon.replace("{hitap}", hitap.strip() or "").replace("{motor}", motor)
    if len(nolar) > 1:
        metin = metin.replace("motorumuzun", "motorlarımızın")
    return re.sub(r"\s+([,.])", r"\1", re.sub(r" {2,}", " ", metin)).strip()


def whatsapp_adresleri(telefon, metin):
    """(uygulama, web): bilgisayarda kurulu WhatsApp'ı (telefonda da uygulamayı) mesaj yazılmış olarak açan adres ve
    WhatsApp Web adresi."""
    sorgu = f"phone={telefon}&text={quote(metin, safe='')}"
    return f"whatsapp://send?{sorgu}", f"https://web.whatsapp.com/send?{sorgu}"


def bildirim(vt, urun):
    """Ürünün motor açılışı bilgisi (pencere ve kontrol listesi için) ya da None (güç ünitesi değilse, kontrol
    listesi yoksa ya da açılış yapıldıysa): {urun_id, urun_kodu, siparis_no, sirada (test bitmedi), haber (son haber
    kaydı), volvo, telefon_var, hitap, metin, uygulama, web}."""
    if urun["aile"] != "PP":
        return None
    madde = next((m for m in kontrol_listeleri(vt, [urun]).get(urun["id"], []) if m["madde"] == "motor_acilisi"), None)
    if madde is None or madde["tamam"]:
        return None
    nolar = motor_nolari(vt, urun)
    ayar = ayarlar(vt)
    volvo = volvo_mu(vt, urun, nolar)
    metin = mesaj_metni(ayar["mesaj"], ayar["hitap"], nolar)
    uygulama, web = whatsapp_adresleri(ayar["telefon"], metin) if ayar["telefon"] else (None, None)
    return {"urun_id": urun["id"], "urun_kodu": urun["urun_kodu"], "siparis_no": urun["siparis_no"],
            "sirada": madde["sirada"], "haber": madde["haber"], "volvo": volvo, "telefon_var": bool(ayar["telefon"]),
            "hitap": ayar["hitap"], "metin": metin, "uygulama": uygulama, "web": web}


def asama_sonrasi(urun, eski, yeni):
    """Aşama değişince: kabin testi bu değişiklikle tamamlandıysa (eskiden test bitmemişti, şimdi bitti) bir sonraki
    sayfada motor açılışı penceresi açılsın."""
    if urun["aile"] == "PP" and not test_bitti_mi(dict(urun, asama=eski)) and test_bitti_mi(dict(urun, asama=yeni)):
        session[OTURUM_ANAHTARI] = urun["id"]


@bp.app_context_processor
def sablon_degiskenleri():
    def pencere():
        """Bu sayfada açılacak motor açılışı penceresinin bilgisi (bir kez gösterilir) ya da None."""
        urun_id = session.pop(OTURUM_ANAHTARI, None)
        if not urun_id or not g.get("kullanici"):
            return None
        from .urunler import urun_kaydi  # döngüsel içe aktarmayı önler

        vt = baglanti()
        urun = urun_kaydi(vt, urun_id)
        return bildirim(vt, urun) if urun else None

    return {"motor_acilisi_penceresi": pencere, "bugun_tarihi": lambda: date.today().isoformat()}


@bp.route("/urun/<int:urun_id>/acilis-haberi", methods=["POST"])
@ekip_gerekli
def haber(urun_id):
    """WhatsApp açıldı: zaman akışına "Motor açılışı için WhatsApp'tan haber verildi" yazılır."""
    from .urunler import urun_kaydi

    vt = baglanti()
    urun = urun_kaydi(vt, urun_id)
    if urun is None or bildirim(vt, urun) is None:
        abort(404)
    with vt:
        isaretle(vt, urun_id, ACILIS_HABERI, "whatsapp", None, g.kullanici["id"])
    return jsonify(tamam=True)


@bp.route("/ayarlar/motor-acilisi", methods=["GET", "POST"])
def ayar_ekrani():
    """Motor açılışı için haber verilecek kişinin hitabı, telefon numarası ve mesaj metni. Yalnızca ekip değiştirir."""
    vt = baglanti()
    if request.method == "POST":
        if g.kullanici["rol"] != "ekip":
            abort(403)
        hitap = " ".join((request.form.get("hitap") or "").split())
        telefon_metni = (request.form.get("telefon") or "").strip()
        telefon = telefon_duzelt(telefon_metni) if telefon_metni else ""
        mesaj = (request.form.get("mesaj") or "").strip()
        if telefon is None:
            flash("Telefon numarası anlaşılamadı; ülke koduyla yazın (örneğin 90 5xx xxx xx xx). Hiçbir şey kaydedilmedi.")
            return redirect(url_for(".ayar_ekrani"))
        if mesaj and "{motor}" not in mesaj:
            flash("Mesaj metninde {motor} geçmeli (motor seri no'nun yazılacağı yer). Hiçbir şey kaydedilmedi.")
            return redirect(url_for(".ayar_ekrani"))
        with vt:
            for anahtar, deger in ((HITAP, hitap), (TELEFON, telefon), (MESAJ, "" if mesaj == VARSAYILAN_MESAJ else mesaj)):
                vt.execute(
                    "INSERT INTO ayarlar (anahtar, deger, zaman, kullanici_id) VALUES (?, ?, ?, ?)"
                    " ON CONFLICT (anahtar) DO UPDATE SET deger = excluded.deger, zaman = excluded.zaman,"
                    " kullanici_id = excluded.kullanici_id",
                    (anahtar, deger or None, _simdi(), g.kullanici["id"]),
                )
        flash("Motor açılışı ayarları kaydedildi.")
        return redirect(url_for(".ayar_ekrani"))
    ayar = ayarlar(vt)
    ornek = mesaj_metni(ayar["mesaj"], ayar["hitap"] or "{hitap}", ["0000 111 101"])
    return render_template("motor_acilisi_ayari.html", ayar=ayar, ornek=ornek, VARSAYILAN_MESAJ=VARSAYILAN_MESAJ)
