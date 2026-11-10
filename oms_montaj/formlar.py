"""Montaj formları: güç ünitesinin proje takip kartı, test öncesi kontrol formu, test formu ve kurulum formu
(setup list). Uygulama formlara bildiği bilgileri yazar ve PDF'ini çıkarır (kullanıcı kararları, 02/11/2026).

Şablonlar şirketin kendi Excel formlarıdır; gerçek veri sayıldıkları için git'e girmez, veri klasörünün
"formlar" klasöründe durur (alt klasörler serbest). Dosya adından tanınırlar:
- "… PP-536 NF Test Öncesi Kontrol Formu.xlsx": modele (model numarası, NF / VM / OVF, Stage IV / V) özel
- "… NF-VM-3XX-4XX-5XX Güç Ünitesi Test Formu.xlsx": model serisine göre (3XX-4XX-5XX, 7XX, 1XXX)
- "… Güç Ünitesi Kurulum Formu.xlsx": bütün güç üniteleri
Aynı doküman numarasının birden çok revizyonu varsa en yenisi kullanılır. Formu olmayan model için form
basılamaz; kullanıcı formu klasöre ekler.

Bilgiler forma etiketlerinden bulunarak yazılır: "Motor Modeli", "Sipariş Numarası" gibi bir etiketin sağındaki
boş hücreye (iki motorlu formlarda "Motor 1" / "Motor 2" ara etiketlerinin yanındaki hücrelere). Böylece her
form için ayrı ayar gerekmez. Proje takip kartı uygulamanın kendi tasarımıdır (OMS kurumsal görünümü, A4 yatay,
uzaktan okunur); o da Excel olarak hazırlanıp aynı yolla PDF'e çevrilir.

Motor bilgisi (marka, model, güç, çalışma devri) güç ünitesinin ürün koduna göre bir kez girilir ve sonraki
formlarda kendiliğinden gelir. Motor seri no teyit edilmeden form basılmaz. Test yapılacak vibro çakıcı
siparişten gelir (birden çoksa seçilir, yoksa elle yazılır); "-BSP" eki yazılmaz; marka/musteriler.txt'de
"vibro=VH" yazan müşterinin siparişlerinde SVR yerine VH yazılır.

Proje takip kartında siparişteki opsiyonel ekipmanlar (uzaktan erişim modülü, kablosuz kumanda seti) ayrı bir
satırda yazar; sipariş talebinde ayrı kalem oldukları için sahadaki çalışan başka türlü görmüyor (kullanıcı,
10/11/2026). Stoktaki güç ünitesinin de proje takip kartı basılır; sipariş no yerine STOK yazar.

Bakım-onarım için gelen güç ünitesinde (ürün kodu "-MNT" ile biter) dört form da basılır (kullanıcı, 10/11/2026):
şablon, makine modeli ve motor bilgisi makinenin kodundan ("-MNT" atılarak) gelir. Proje takip kartının bandı
kırmızı değil antrasittir, başlığın altında "MAINTENANCE & REPAIR · Bakım-onarım" yazar. Makinenin kendi seri
no'su ERP'de çoğunlukla yoktur; form ekranında yazılır ve makinede saklanır. Opsiyonel ekipman servis talebinde
yazmadığı için stok makinesindeki gibi işaretlenir. Test vibrosu ve yağ son basılan formdan hazır gelir.

PDF'e çevirme: sunucuda LibreOffice (Docker kalıbına kurulur), geliştirme bilgisayarında LibreOffice yoksa
Excel (yönetici izni gerekmiyor). Testlerde PDF_CEVIRICI ayarıyla sahte bir çevirici kullanılır.
"""

import io
from copy import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.drawing.image import Image as ExcelResmi
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils.units import pixels_to_EMU
from openpyxl.worksheet.page import PageMargins
from PIL import Image

from .asamalar import ileri
from .bicim import tarih
from .erp_aktarim import IPTAL
from .form_kurallari import FORM_TURLERI, STOK_FORMLARI, basilan_formlar, forma_tabi_mi, formlu_mu, sinirla
from .kimlik import ekip_gerekli
from .marka import hazir_png, logo_dosyasi, vibro_oneki
from .numaralar import MOTOR_ALANLARI, TEYITSIZ, kayit_numarasi, urun_numaralari
from .urun_kurallari import PP_EKLENTILERI, makine_kodu, motor_sayisi, sade, yag_metni
from .urunler import urun_kaydi
from .veritabani import baglanti
from .zaman_akisi import not_ekle

bp = Blueprint("formlar", __name__)

SABLON_KLASORU = "formlar"
CIKTI_KLASORU = "form-ciktilari"
URUN_TURU = "Güç Ünitesi"
UZAKTAN_ERISIM = "OZ04082"  # uzaktan erişim modülünün ürün kodu (urun_kurallari.PP_EKLENTILERI)
STOK_BASLIGI = "STOK"  # stoktaki makinenin kartında sipariş no'nun yerinde


class FormHatasi(Exception):
    """Kullanıcıya gösterilecek bir sebeple form hazırlanamadı."""


# Şablonlar

@dataclass
class Sablon:
    tur: str
    yol: Path
    dokuman: str = ""
    revizyon: int = 0
    model_no: int | None = None  # test öncesi kontrol formu
    varyantlar: frozenset = field(default_factory=frozenset)
    stage: str | None = None
    seriler: tuple = ()  # test formu: ("3", "4", "5"), ("7",) ya da ("1xxx",)

    @property
    def ad(self):
        return self.yol.stem


VARYANTLAR = {"NF", "VM", "OVF"}


def _sablon_oku(yol):
    ad = sade(yol.stem).replace("_", " ")
    dokuman = re.search(r"fr-mt-(\d+)", ad)
    revizyon = re.search(r"\br(\d+)\b", ad)
    ortak = {"yol": yol, "dokuman": dokuman.group(1) if dokuman else yol.stem,
             "revizyon": int(revizyon.group(1)) if revizyon else 0}
    if "test oncesi" in ad:
        eslesme = re.search(r"pp-(\d+)\s+([a-z/-]+?)(?:\s+stage\s+(iv|v))?\s+test oncesi", ad)
        if not eslesme:
            return None
        varyantlar = frozenset(v.upper() for v in re.split(r"[-/]", eslesme.group(2)) if v)
        return Sablon("test_oncesi", model_no=int(eslesme.group(1)), varyantlar=varyantlar,
                      stage=eslesme.group(3).upper() if eslesme.group(3) else None, **ortak)
    if "test formu" in ad:
        seriler = tuple(re.findall(r"\b(\d)xx\b", ad)) + (("1xxx",) if re.search(r"\b1xxx\b", ad) else ())
        return Sablon("test", seriler=seriler, **ortak) if seriler else None
    if "kurulum" in ad:
        return Sablon("kurulum", **ortak)
    return None


def sablonlar():
    """Veri klasöründeki form şablonları: {tür: [Sablon]}; aynı doküman numarasının yalnızca son revizyonu."""
    klasor = Path(current_app.config["VERI_KLASORU"]) / SABLON_KLASORU
    son = {}
    for yol in sorted(klasor.rglob("*.xlsx")) if klasor.is_dir() else []:
        if yol.name.startswith("~$"):  # Excel'in açık dosya için bıraktığı geçici dosya
            continue
        sablon = _sablon_oku(yol)
        if sablon is None:
            continue
        onceki = son.get((sablon.tur, sablon.dokuman))
        if onceki is None or onceki.revizyon < sablon.revizyon:
            son[(sablon.tur, sablon.dokuman)] = sablon
    sonuc = {}
    for sablon in sorted(son.values(), key=lambda s: s.dokuman):
        sonuc.setdefault(sablon.tur, []).append(sablon)
    return sonuc


def pp_modeli(urun_kodu):
    """'PP-551-NF/VM-STAGE V' → (551, {'NF', 'VM'}, 'V'); 'PP-540C-NF-T4' → (540, {'NF'}, None)."""
    kod = (urun_kodu or "").upper()
    eslesme = re.match(r"PP-?(\d+)[A-Z]*", kod)
    if not eslesme:
        return None, frozenset(), None
    kalan = kod[eslesme.end():]
    varyantlar = frozenset(p for p in re.split(r"[-\s/]+", kalan) if p in VARYANTLAR)
    stage = re.search(r"STAGE\s*(IV|V)\b", kalan) or re.search(r"\bS([45])\b", kalan)
    stage = {"4": "IV", "5": "V"}.get(stage.group(1), stage.group(1)) if stage else None
    return int(eslesme.group(1)), varyantlar, stage


def uygun_sablonlar(tur, urun_kodu, butun=None):
    """Ürüne uyan şablonlar (genellikle bir tane; Stage belirsizse birden çok)."""
    butun = sablonlar() if butun is None else butun
    adaylar = butun.get(tur, [])
    if tur == "kurulum":
        return adaylar
    no, varyantlar, stage = pp_modeli(urun_kodu)
    if no is None:
        return []
    if tur == "test":
        seri = "1xxx" if no >= 1000 else str(no // 100)
        return [s for s in adaylar if seri in s.seriler]
    uyan = [s for s in adaylar if s.model_no == no and s.varyantlar == varyantlar]
    if stage and any(s.stage for s in uyan):
        uyan = [s for s in uyan if s.stage == stage]
    return uyan


# Ürünün bilgileri

def motor_bilgisi(vt, urun_kodu):
    return vt.execute("SELECT * FROM motor_bilgileri WHERE urun_kodu = ?", (urun_kodu,)).fetchone()


def _sayi(deger):
    return f"{deger:g}".replace(".", ",") if isinstance(deger, float) else str(deger)


def motor_metinleri(motor):
    """Forma yazılan motor bilgileri: model ('VOLVO TAD1643VE'), güç ('450 kW / 603 HP'), devir ('1800 rpm')."""
    if not motor:
        return {}
    guc = " / ".join(p for p in (f"{_sayi(motor['guc_kw'])} kW" if motor["guc_kw"] else "",
                                 f"{_sayi(motor['guc_hp'])} HP" if motor["guc_hp"] else "") if p)
    return {"motor_modeli": " ".join(p for p in ((motor["marka"] or "").upper(), motor["model"]) if p),
            "motor_gucu": guc, "devir": f"{motor['devir']} rpm" if motor["devir"] else ""}


def vibro_adi(urun_kodu, onek=None):
    """'SVR-120-NF-BSP' → 'SVR-120-NF'; müşterinin vibro öneki VH ise 'VH-120-NF'."""
    ad = re.sub(r"-BSP$", "", (urun_kodu or "").upper())
    return re.sub(r"^SVR\b", onek, ad) if onek else ad


def vibro_adaylari(vt, urun):
    """Siparişteki vibro çakıcılar: [{"ad", "seri_no", "urun_kodu"}]."""
    onek = vibro_oneki(urun["siparis_no"])
    return [
        {"ad": vibro_adi(r["urun_kodu"], onek), "seri_no": r["seri_no"] or "", "urun_kodu": r["urun_kodu"]}
        for r in vt.execute(
            "SELECT u.seri_no, k.urun_kodu FROM urunler u JOIN siparis_kalemleri k ON k.id = u.kalem_id"
            " WHERE k.siparis_id = ? AND k.aile IN ('SVR', 'OVR') AND k.tur = 'kart' AND COALESCE(k.erp_durum, '') != ?"
            " ORDER BY k.sira_no, u.adet_sira",
            (urun["siparis_id"], IPTAL),
        )
    ]


def ekipman_kodlari(vt, urun):
    """Siparişteki opsiyonel ekipmanların (urun_kurallari.PP_EKLENTILERI) kodları, sipariş talebindeki sırayla.
    Stok makinesinde sipariş talebi yok, bakıma gelen makinenin ekipmanı servis talebinde yazmaz: ekibin proje takip
    kartı ekranında işaretledikleri (10/11/2026). Bakımda henüz işaretlenmediyse servis talebindeki ekipman gelir."""
    elle = urun["elle_ekipman"]
    if not urun["siparis_id"] or (urun["tur"] == "servis" and elle is not None):
        return [kod for kod in PP_EKLENTILERI if kod in (elle or "").split(",")]
    kodlar = []
    for r in vt.execute(
        "SELECT UPPER(urun_kodu) FROM siparis_kalemleri WHERE siparis_id = ? AND COALESCE(erp_durum, '') != ? ORDER BY sira_no",
        (urun["siparis_id"], IPTAL),
    ):
        if r[0] in PP_EKLENTILERI and r[0] not in kodlar:
            kodlar.append(r[0])
    return kodlar


def motor_serileri(vt, urun):
    """(motor seri no'ları, teyit bekleyen ya da girilmemiş numaraların adları)."""
    numaralar = [n for n in urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"])
                 if n[0] in MOTOR_ALANLARI]
    eksik = [ad for _, ad, deger, kaynak in numaralar if not deger or kaynak in TEYITSIZ]
    return [deger for _, _, deger, _ in numaralar], eksik


def kayit_bilgisi(vt, urun):
    """Makinenin iş emri ya da stok giriş no'su (numaralar.kayit_numarasi): ERP iş emri, yoksa ekibin yazdığı numara
    (yüklenen listelerde olmayan iş emri ya da ERP'ye geçmeden önce stoğa alınan makinenin stok giriş no'su)."""
    ie = vt.execute("SELECT is_emri_no FROM is_emirleri WHERE id = ?", (urun["is_emri_id"],)).fetchone() if urun["is_emri_id"] else None
    return kayit_numarasi(urun, ie[0] if ie else None)


def kayit_alanlari(kayit):
    """Forma yazılan numara: Excel formlarının "iş emri numarası" hücresine iş emri no (stok giriş no'sunda "Stok giriş
    no …"); proje takip kartında satırın etiketi numaranın türüne göre İŞ EMRİ NO ya da STOK GİRİŞ NO olur."""
    if kayit is None:
        return {"is_emri_no": "", "kayit_no": "", "kayit_turu": "is_emri"}
    excel = kayit["no"] if kayit["tur"] == "is_emri" else f"{kayit['ad']} {kayit['no']}"
    return {"is_emri_no": excel, "kayit_no": kayit["no"], "kayit_turu": kayit["tur"]}


# Excel şablonuna yazma

ETIKETLER = (
    (r"motor modeli", "motor_modeli"),
    (r"motor gucu", "motor_gucu"),
    (r"motor seri numarasi", "motor_seri"),
    (r"motor calisma devri", "devir"),
    (r"siparis numarasi", "siparis_no"),
    (r"is emri numarasi", "is_emri_no"),
    (r"test yapil(?:acak|an) vibro", "vibro"),
    (r"vibro cakici seri numarasi", "vibro_seri"),
    (r"makine modeli", "makine_modeli"),
    (r"form verilis tarihi", "tarih"),
    (r"urun turu", "urun_turu"),
    (r"uzaktan erisim var mi", "uzaktan_erisim"),
    (r"motor sayisi", "motor_sayisi"),
)
YAZI_TIPI_DEGISIMI = {"Exo 2": "Arial"}
ARA_ETIKET = re.compile(r"^motor\s*[12]\b")  # iki motorlu formlarda "Motor 1 (F10'lu)" / "Motor 2"
MOTOR_ANAHTARLARI = {"motor_modeli", "motor_gucu", "motor_seri", "devir"}  # iki motorlu formda iki hücresi olabilir


def _bolgeler(sayfa):
    """Her hücrenin ait olduğu bölge (birleşik aralık ya da tek hücre): {(satır, sütun): (r1, c1, r2, c2)}."""
    bolge = {}
    for aralik in sayfa.merged_cells.ranges:
        kutu = (aralik.min_row, aralik.min_col, aralik.max_row, aralik.max_col)
        for satir in range(aralik.min_row, aralik.max_row + 1):
            for sutun in range(aralik.min_col, aralik.max_col + 1):
                bolge[(satir, sutun)] = kutu
    return bolge


def _bos(deger):
    return deger is None or not str(deger).strip()


def yazilacak_yerler(sayfa):
    """Etiketlerin sağındaki boş hücreler: {anahtar: [(etiket hücresi, [yazılacak hücreler])]}. Etiketin hemen
    sağındaki boş bölge yazılacak yerdir. Motor bilgilerinde ondan sonrakiler de sayılır: bir ara etiketten
    ("Motor 2") sonra gelen ya da etiketle aynı yükseklikte birleşik kutu olan (iki motorlu formda motor 1 ve
    motor 2 sütunları). Dolu bir hücreye gelince durulur; şablonda zaten yazılı değer (bazı formlarda motor
    modeli) değiştirilmez."""
    bolge = _bolgeler(sayfa)
    yerler = {}
    for satir in sayfa.iter_rows():
        for hucre in satir:
            if not isinstance(hucre.value, str):
                continue
            metin = sade(hucre.value)
            anahtar = next((a for desen, a in ETIKETLER if re.match(desen, metin)), None)
            if anahtar is None:
                continue
            r1, _, r2, c2 = bolge.get((hucre.row, hucre.column), (hucre.row, hucre.column, hucre.row, hucre.column))
            bos, ara_etiketten_sonra = [], True
            sutun = c2 + 1
            while sutun <= sayfa.max_column:
                b1, bc1, b2, bc2 = bolge.get((r1, sutun), (r1, sutun, r1, sutun))
                if b1 != r1:
                    break
                deger = sayfa.cell(b1, bc1).value
                if _bos(deger):
                    kutu = b2 == r2 and (bc2 > bc1 or b2 > b1)  # etiketle aynı yükseklikte birleşik kutu
                    if bos and anahtar not in MOTOR_ANAHTARLARI or not (ara_etiketten_sonra or kutu):
                        break
                    bos.append(sayfa.cell(b1, bc1))
                    ara_etiketten_sonra = False
                elif ARA_ETIKET.match(sade(deger)):
                    ara_etiketten_sonra = True
                else:
                    break
                sutun = bc2 + 1
            yerler.setdefault(anahtar, []).append((hucre, bos))
    return yerler


def _yaz(hucre, deger):
    hucre.value = deger
    if "\n" in deger:
        hizalama = hucre.alignment
        hucre.alignment = Alignment(horizontal=hizalama.horizontal, vertical=hizalama.vertical or "center", wrap_text=True)


def sablonu_doldur(yol, degerler):
    """Şablonu açar, bilgileri yazar ve kitabı döndürür. Liste değerler (motor seri no'ları) sırayla hücrelere
    dağıtılır; hücre yetmezse sonuncusunda alt alta yazılır. Etiketin sağında boş hücre yoksa (form veriliş
    tarihi bazı formlarda böyle) değer etiketin sonuna eklenir."""
    kitap = load_workbook(yol)
    for fazla in kitap.worksheets[1:]:
        kitap.remove(fazla)
    sayfa = kitap.worksheets[0]
    for anahtar, yerler in yazilacak_yerler(sayfa).items():
        deger = degerler.get(anahtar)
        if not deger:
            continue
        for etiket, bos in yerler:
            liste = deger if isinstance(deger, list) else None
            if not bos:
                if anahtar == "tarih":
                    etiket.value = f"{etiket.value.rstrip()} {deger}"
                continue
            if liste is None:
                for hucre in bos:
                    _yaz(hucre, str(deger))
            else:
                for i, hucre in enumerate(bos):
                    parca = liste[i:] if i == len(bos) - 1 else liste[i:i + 1]
                    if parca:
                        _yaz(hucre, "\n".join(parca))
    # Şablonlar Exo 2 yazı tipiyle kayıtlı ama satır yükseklikleri Exo 2 olmayan bilgisayarda Excel'in yerine
    # koyduğu Arial'a göre ayarlanmış; Exo 2 ile iki satırlık etiketler satıra sığmıyor. Form bugün göründüğü gibi
    # (Arial) basılır; sunucuda Arial'ın yerini ölçüleri aynı Liberation Sans alır.
    for satir in sayfa.iter_rows():
        for hucre in satir:
            if hucre.has_style and hucre.font.name in YAZI_TIPI_DEGISIMI:
                yeni = copy(hucre.font)
                yeni.name = YAZI_TIPI_DEGISIMI[hucre.font.name]
                hucre.font = yeni
    # Sayfa ayarı olmayan formlar (bazılarında yok) A4 yatay, tek sayfa basılır
    if sayfa.page_setup.orientation is None:
        sayfa.page_setup.orientation = "landscape"
        sayfa.page_setup.paperSize = sayfa.PAPERSIZE_A4
        sayfa.sheet_properties.pageSetUpPr.fitToPage = True
        sayfa.page_setup.fitToWidth = sayfa.page_setup.fitToHeight = 1
    return kitap


# Proje takip kartı (eski adıyla proje kodlaması): OMS kurumsal görünümü, A4 yatay, uzaktan okunur. Arial ile
# basılır (kullanıcı kararı, 02/11/2026); sunucuda yerini ölçüleri aynı Liberation Sans alır. Sayfa tek sayfaya
# sığdırılır; satır yükseklikleri yazılara göre hesaplanır.
# İki dilli (kullanıcı, 10/11/2026): başlık, kırmızı etiketler ve sabit değerler (yağsız/yağlı sevk, belirtilmedi,
# stok, opsiyonel ekipman adları) üstte İngilizce, altta küçük Türkçe. Model kodları, numaralar ve yağın modeli
# çevrilmez. Sığmayan değer küçülür; birden çok test vibrosu yazılmışsa ("SVR-25-NF/OVF-300-4-BF") alt alta basılır.

KIRMIZI, KOYU, SOLUK, CIZGI = "C41E24", "16181D", "5B6170", "D9DCE3"
ANTRASIT = "383E42"  # bakım-onarım kartının bandı (RAL 7016 antrasit gri; kullanıcı, 10/11/2026)
YAZI_TIPI = "Arial"
KART_BASLIGI = ("PROJECT TRACKING CARD", "Proje takip kartı · Montaj fabrikası")
BAKIM_IBARESI = ("MAINTENANCE & REPAIR", "Bakım-onarım")  # bakım kartında başlığın altında
KART_ETIKETLERI = {  # İngilizcede satır sonları, etiket sütununa sığsın diye
    "guc": ("POWER PACK", "Güç ünitesi"),
    "vibro": ("TEST VIBRO\nHAMMER", "Test vibrosu"),
    "motor": ("ENGINE\nSERIAL NO", "Motor seri no"),
    "is_emri": ("WORK\nORDER NO", "İş emri no"),
    "stok_giris": ("STOCK\nENTRY NO", "Stok giriş no"),
    "yag": ("OIL", "Yağ"),
    "ekipman": ("OPTIONAL\nEQUIPMENT", "Opsiyonel ekipman"),
}
# Yağ: "Yağsız", "YAĞSIZ SEVK", "yağsız sevk edilecektir"… aynı anlamda (sade yazımla eşleşir)
KART_DEGERLERI = {"yagsiz": ("Without oil", "Yağsız sevk"), "yagli": ("With oil", "Yağlı sevk")}
YAG_SABITI = re.compile(r"(yagsiz|yagli)(?: sevk\w*(?: edilecek\w*)?)?")
BELIRTILMEDI = ("Not specified", "Belirtilmedi")
STOK_IKI_DILLI = ("STOCK", "Stok")
EKIPMAN_INGILIZCE = {"OZ04082": "Remote Access Module", "OZ04314": "Wireless Remote Control Set"}
# Birden çok test vibrosu: model kodundan önceki ayraç (/ , ; + & "ve" ya da boşluk). "NF/VM" gibi kodun kendi
# eğik çizgisi bölünmez; ayraçtan sonra yeni bir model kodu ("OVF-300") başlamalı.
VIBRO_AYRACI = re.compile(r"\s*(?:[/,;+&]|\bve\b)\s*(?=[A-Za-z]{2,4}-\d)|\s+(?=[A-Za-z]{2,4}-\d)", re.IGNORECASE)
SUTUNLAR = {"A": 33, "B": 78, "C": 41}  # A: etiketler; B-C: değerler (C: seri no "OZ-…-PP-01" tek satıra sığsın)
SATIR_ARALIGI = 1.2  # Arial'in satır yüksekliği, yazı boyunun katı
ETIKET_BOYU, ETIKET_ALT_BOYU = 24, 16
# Kalın Arial'de harflerin yaklaşık genişliği (yazı boyunun katı); sığdırma hesabı için
_GENISLIKLER = {**dict.fromkeys("0123456789", .556), "-": .333, "/": .278, " ": .278, ".": .278, ",": .278,
                "·": .278, "(": .333, ")": .333, "×": .584}


def yazi_genisligi(metin, boy):
    """Kalın Arial yazının yaklaşık genişliği (punto)."""
    return boy * sum(_GENISLIKLER.get(h, .72 if h.isupper() else .3 if h in "iljtfIı" else .6) for h in metin)


def _deger_genisligi():
    """Birleşik B-C değer hücresinin yazı sığan genişliği (punto): sütun genişliği n karakter ≈ 7n + 5 piksel."""
    return sum(SUTUNLAR[s] * 7 + 5 for s in "BC") * 0.75 - 12


def sigan_boy(satirlar, boy, en_kucuk=20):
    """Satırların en uzunu değer hücresine sığacak yazı boyu (en çok boy)."""
    en_uzun = max((yazi_genisligi(s, 1) for s in satirlar if s), default=0)
    if not en_uzun:
        return boy
    return max(en_kucuk, min(boy, int(_deger_genisligi() / en_uzun)))


def vibro_satirlari(vibro):
    """Test vibrosu kartta: tek satıra sığıyorsa olduğu gibi; sığmıyorsa ve birden çok vibro yazılmışsa alt alta."""
    vibro = " ".join((vibro or "").split())
    if not vibro or yazi_genisligi(vibro, 52) <= _deger_genisligi():
        return [vibro] if vibro else []
    return [p for p in VIBRO_AYRACI.split(vibro) if p] or [vibro]


def yag_iki_dilli(yag):
    """Yağ: (İngilizce, Türkçe). "Yağsız sevk" ve "Yağlı sevk" (ya da yalnızca "Yağsız") iki dilli; boşsa
    "Belirtilmedi"; yağın modeli olduğu gibi (Türkçesi None)."""
    yag = " ".join((yag or "").split())
    if not yag:
        return BELIRTILMEDI
    sabit = YAG_SABITI.fullmatch(sade(yag))
    return KART_DEGERLERI[sabit.group(1)] if sabit else (yag, None)


def _yuksek(boylar, en_az=0):
    """Satırları alt alta yazılan hücrenin yüksekliği (punto)."""
    return max(en_az, round(sum(boylar) * SATIR_ARALIGI + 6))


def _beyaz_logo():
    """OMS logosunun kenarları kırpılmış, beyaza boyanmış PNG'si (kırmızı bandın üstüne); logo yoksa None."""
    dosya = logo_dosyasi()
    if dosya is None or dosya.suffix.lower() != ".png":
        return None
    with Image.open(io.BytesIO(hazir_png(str(dosya), dosya.stat().st_mtime))) as acilan:
        resim = acilan.convert("RGBA")
    beyaz = Image.new("RGBA", resim.size, (255, 255, 255, 255))
    beyaz.putalpha(resim.getchannel("A"))
    tampon = io.BytesIO()
    beyaz.save(tampon, "PNG")
    tampon.seek(0)
    return tampon


def _yazi(boy, renk=KOYU, kalin=True):
    return InlineFont(rFont=YAZI_TIPI, sz=boy, b=kalin, color=renk)


def iki_dilli(ingilizce, turkce, boy, alt_boy, renk=KOYU, alt_renk=SOLUK):
    """Üstte İngilizce, altında küçük Türkçe (Türkçe yoksa yalnızca üstteki)."""
    if not turkce:
        return CellRichText(TextBlock(_yazi(boy, renk), ingilizce))
    return CellRichText(TextBlock(_yazi(boy, renk), ingilizce), TextBlock(_yazi(alt_boy, alt_renk, kalin=False), "\n" + turkce))


def kodlama_kitabi(b):
    """Proje takip kartının Excel kitabı. b: forma yazılan bilgiler (ekipman: ürün kodları; bakim: bakım-onarım
    için gelen makine)."""
    kitap = Workbook()
    s = kitap.active
    s.title = "Proje takip kartı"
    s.sheet_view.showGridLines = False
    s.page_setup.orientation = "landscape"
    s.page_setup.paperSize = s.PAPERSIZE_A4
    s.sheet_properties.pageSetUpPr.fitToPage = True
    s.page_setup.fitToWidth = s.page_setup.fitToHeight = 1
    s.print_options.horizontalCentered = True
    s.page_margins = PageMargins(left=0.4, right=0.4, top=0.4, bottom=0.4, header=0, footer=0)
    for sutun, genislik in SUTUNLAR.items():
        s.column_dimensions[sutun].width = genislik

    def font(boy, renk=KOYU, kalin=True):
        return Font(name=YAZI_TIPI, size=boy, bold=kalin, color=renk)

    bakim = bool(b.get("bakim"))
    bant = PatternFill("solid", fgColor=ANTRASIT if bakim else KIRMIZI)
    ince = Side(style="thin", color=CIZGI)
    kalin = Side(style="thick", color=KOYU)

    # Bant (bakım-onarımda antrasit): solda logo, sağda başlık (üstte İngilizce, altta Türkçe); bakımda başlığın
    # altında MAINTENANCE & REPAIR · Bakım-onarım
    bant_satirlari = {1: 46, 2: 24, **({3: 34} if bakim else {})}
    for satir, yukseklik in bant_satirlari.items():
        s.row_dimensions[satir].height = yukseklik
        for sutun in "ABC":
            s[f"{sutun}{satir}"].fill = bant
    s["C1"] = KART_BASLIGI[0]
    s["C1"].font = font(28, "FFFFFF")
    s["C1"].alignment = Alignment(horizontal="right", vertical="bottom")
    s["C2"] = KART_BASLIGI[1]
    s["C2"].font = font(13, "FFFFFF", kalin=False)
    s["C2"].alignment = Alignment(horizontal="right", vertical="top")
    if bakim:
        s["C3"] = CellRichText(TextBlock(_yazi(22, "FFFFFF"), BAKIM_IBARESI[0]),
                               TextBlock(_yazi(15, "FFFFFF", kalin=False), " · " + BAKIM_IBARESI[1]))
        s["C3"].alignment = Alignment(horizontal="right", vertical="center")
    logo = _beyaz_logo()
    if logo:
        resim = ExcelResmi(logo)
        yukseklik = 60  # piksel; bandın ortasında (punto ≈ 4/3 piksel)
        ust = round((sum(bant_satirlari.values()) * 4 / 3 - yukseklik) / 2)
        genislik = round(resim.width * yukseklik / resim.height)
        resim.anchor = OneCellAnchor(_from=AnchorMarker(col=0, colOff=pixels_to_EMU(16), row=0, rowOff=pixels_to_EMU(ust)),
                                     ext=XDRPositiveSize2D(pixels_to_EMU(genislik), pixels_to_EMU(yukseklik)))
        s.add_image(resim)
    else:
        s["A1"] = "OMS"
        s["A1"].font = font(28, "FFFFFF")
        s.merge_cells(f"A1:A{len(bant_satirlari)}")
        s["A1"].alignment = Alignment(vertical="center")
    bas = len(bant_satirlari) + 2  # sipariş no satırı; üstünde ince bir boşluk
    s.row_dimensions[bas - 1].height = 6

    # Sipariş no (en büyük yazı; stok makinesinde STOCK, altında Stok) ve sağında güç ünitesinin seri no'su
    s.merge_cells(f"A{bas}:B{bas}")
    if b["siparis_no"] == STOK_BASLIGI:
        s[f"A{bas}"] = iki_dilli(*STOK_IKI_DILLI, 84, 30)
        s.row_dimensions[bas].height = _yuksek([84, 30])
    else:
        s[f"A{bas}"] = b["siparis_no"]
        s[f"A{bas}"].font = font(84)
        s.row_dimensions[bas].height = 100
    s[f"A{bas}"].alignment = Alignment(vertical="center", wrap_text=True)
    s[f"C{bas}"] = b.get("seri_no") or ""
    s[f"C{bas}"].font = font(24, SOLUK)
    s[f"C{bas}"].alignment = Alignment(horizontal="right", vertical="bottom", wrap_text=True)
    for sutun in "ABC":
        s[f"{sutun}{bas}"].border = Border(bottom=kalin)

    motorlar = b.get("motor_seri") or []
    ikili = len(motorlar) > 1
    model = b.get("motor_model_kisa") or ""
    ekipman = [kod for kod in (b.get("ekipman") or []) if kod in PP_EKLENTILERI]

    def tek_dilli(anahtar, satirlar, boy):
        """Çevrilmeyen değer (model kodu, numara): sığmazsa küçülür; birden çok satırsa alt alta."""
        satirlar = satirlar or ["—"]
        boy = sigan_boy(satirlar, boy)
        return (anahtar, "\n".join(satirlar), boy, [boy] * len(satirlar), False)

    # (etiket, değer, düz değerin yazı boyu, değerin satır boyları, değer küçülerek tek satıra sığsın mı)
    satirlar = []
    guc = (CellRichText(TextBlock(_yazi(52), b["makine_modeli"]),
                        TextBlock(_yazi(42, SOLUK), f" · {model}{' (×2)' if ikili else ''}")) if model else b["makine_modeli"])
    satirlar.append(("guc", guc, 52, [52], True))
    vibrolar = vibro_satirlari(b.get("vibro"))
    satirlar.append(tek_dilli("vibro", vibrolar, 42 if len(vibrolar) > 1 else 52))
    satirlar.append(tek_dilli("motor", [
        f"{i} · {b.get('motor_marka', '')} {no}".replace("  ", " ") if ikili else f"{b.get('motor_marka', '')} {no}".strip()
        for i, no in enumerate(motorlar, 1)], 42 if ikili else 52))
    satirlar.append(tek_dilli(b.get("kayit_turu") if b.get("kayit_turu") in KART_ETIKETLERI else "is_emri",
                              [b.get("kayit_no") or b.get("is_emri_no") or "—"], 52))
    ingilizce, turkce = yag_iki_dilli(b.get("yag"))
    yag_boyu = sigan_boy([ingilizce], 36)
    satirlar.append(("yag", iki_dilli(ingilizce, turkce, yag_boyu, 22), yag_boyu, [yag_boyu] + ([22] if turkce else []), False))
    # Siparişte (stok makinesinde ekibin işaretlediği) uzaktan erişim modülü ve kablosuz kumanda seti, alt alta
    if ekipman:
        # Satır sonu, bittiği satırın yazı boyunu alır: Türkçe satırın sonundaki satır sonu küçük yazıyla (yoksa
        # Türkçe satır büyük yazı kadar yükselir)
        bloklar = []
        for i, kod in enumerate(ekipman):
            bloklar += [TextBlock(_yazi(32), EKIPMAN_INGILIZCE[kod]),
                        TextBlock(_yazi(20, SOLUK, kalin=False), "\n" + PP_EKLENTILERI[kod] + ("\n" if i < len(ekipman) - 1 else ""))]
        satirlar.append(("ekipman", CellRichText(*bloklar), 32, [32, 20] * len(ekipman), False))

    son = bas + len(satirlar)
    for i, (anahtar, deger, boy, boylar, kucul) in enumerate(satirlar, start=bas + 1):
        ingilizce, turkce = KART_ETIKETLERI[anahtar]
        etiket_boylari = [ETIKET_BOYU] * (ingilizce.count("\n") + 1) + [ETIKET_ALT_BOYU]
        s.row_dimensions[i].height = max(_yuksek(etiket_boylari), _yuksek(boylar, 60 if anahtar in ("yag", "ekipman") else 72))
        s[f"A{i}"] = iki_dilli(ingilizce, turkce, ETIKET_BOYU, ETIKET_ALT_BOYU, KIRMIZI, KIRMIZI)
        s[f"A{i}"].alignment = Alignment(vertical="center", wrap_text=True)
        s.merge_cells(f"B{i}:C{i}")
        s[f"B{i}"] = deger
        s[f"B{i}"].font = font(boy)
        # Güç ünitesi satırı uzun motor modelinde taşmasın diye satıra sığacak kadar küçülür
        s[f"B{i}"].alignment = Alignment(vertical="center", wrap_text=not kucul, shrink_to_fit=kucul)
        if i < son:
            for sutun in "ABC":
                s[f"{sutun}{i}"].border = Border(bottom=ince)
    alt = son + 1
    s.row_dimensions[alt].height = _yuksek([13, 11])
    s[f"A{alt}"] = CellRichText(TextBlock(_yazi(13, SOLUK, kalin=False), f"Issue date: {b.get('tarih', '')}"),
                                TextBlock(_yazi(11, SOLUK, kalin=False), "\nForm veriliş tarihi"))
    s[f"A{alt}"].alignment = Alignment(vertical="bottom", wrap_text=True)
    s[f"C{alt}"] = "OMS Montaj"
    s[f"C{alt}"].font = font(13, SOLUK, kalin=False)
    s[f"C{alt}"].alignment = Alignment(horizontal="right", vertical="bottom")
    for sutun in "ABC":
        s[f"{sutun}{alt}"].border = Border(top=ince)
    s.print_area = f"A1:C{alt}"
    return kitap


# PDF'e çevirme

_KILIT = threading.Lock()  # Excel ve LibreOffice aynı anda tek dosya çevirir
EXCEL_BETIGI = r"""
$ErrorActionPreference = 'Stop'
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
    $kitap = $excel.Workbooks.Open($env:OMS_GIRDI, 0, $true)
    try { $kitap.ExportAsFixedFormat(0, $env:OMS_CIKTI) } finally { $kitap.Close($false) }
} finally {
    $excel.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
}
"""


def _libreoffice():
    for aday in (os.environ.get("OMS_SOFFICE"), shutil.which("soffice"), shutil.which("libreoffice"),
                 r"C:\Program Files\LibreOffice\program\soffice.exe"):
        if aday and Path(aday).is_file():
            return aday
    return None


def pdf_cevir(girdi, cikti):
    """Excel dosyasını PDF'e çevirir: LibreOffice, yoksa (Windows'ta) Excel."""
    cevirici = current_app.config.get("PDF_CEVIRICI")
    if cevirici:
        return cevirici(girdi, cikti)
    with _KILIT:
        soffice = _libreoffice()
        if soffice:
            with tempfile.TemporaryDirectory() as gecici:
                sonuc = subprocess.run([soffice, "--headless", "--norestore", "--convert-to", "pdf", "--outdir", gecici, str(girdi)],
                                       capture_output=True, timeout=180)
                uretilen = Path(gecici) / (Path(girdi).stem + ".pdf")
                if sonuc.returncode or not uretilen.is_file():
                    raise FormHatasi("LibreOffice formu PDF'e çeviremedi.")
                shutil.move(uretilen, cikti)
            return
        if os.name != "nt":
            raise FormHatasi("PDF'e çevirecek program yok: sunucuya LibreOffice kurulmalı.")
        ortam = {**os.environ, "OMS_GIRDI": str(Path(girdi).resolve()), "OMS_CIKTI": str(Path(cikti).resolve())}
        try:
            sonuc = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", EXCEL_BETIGI],
                                   env=ortam, capture_output=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as hata:
            raise FormHatasi("Excel formu PDF'e çeviremedi.") from hata
        if sonuc.returncode or not Path(cikti).is_file():
            raise FormHatasi("Excel formu PDF'e çeviremedi. Bu bilgisayarda Excel ya da LibreOffice kurulu olmalı.")


# Formun hazırlanması

def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def form_hazirla(vt, urun, tur, b, sablon, kullanici_id):
    """Formu hazırlar, PDF'ini veri klasörüne yazar ve kaydeder; formların izin verdiği ölçüde ürünü ERP'nin
    gösterdiği aşamaya ilerletir (stok kartında aşama değişmez). Kaydın id'sini döndürür."""
    stokta = urun["kalem_id"] is None
    veri = Path(current_app.config["VERI_KLASORU"])
    klasor = veri / CIKTI_KLASORU / str(urun["id"])
    klasor.mkdir(parents=True, exist_ok=True)
    ad = f"{tur}-{datetime.now():%Y%m%d-%H%M%S}"
    kitap = kodlama_kitabi(b) if tur == "kodlama" else sablonu_doldur(sablon.yol, b)
    excel_yolu, pdf_yolu = klasor / f"{ad}.xlsx", klasor / f"{ad}.pdf"
    kitap.save(excel_yolu)
    pdf_cevir(excel_yolu, pdf_yolu)
    cur = vt.execute(
        "INSERT INTO urun_formlari (urun_id, tur, sablon, bilgiler, dosya, kullanici_id, zaman, stokta) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (urun["id"], tur, sablon.yol.name if sablon else None, json.dumps(b, ensure_ascii=False),
         pdf_yolu.relative_to(veri).as_posix(), kullanici_id, _simdi(), int(stokta)),
    )
    if not stokta and forma_tabi_mi(urun) and urun["erp_asama"]:
        yeni = ileri(urun["asama"], sinirla(urun["erp_asama"], basilan_formlar(vt, [urun["id"]]).get(urun["id"], set())))
        if yeni != urun["asama"]:
            vt.execute("UPDATE urunler SET asama = ? WHERE id = ?", (yeni, urun["id"]))
            vt.execute(
                "INSERT INTO urun_olaylari (urun_id, tur, zaman, eski_asama, yeni_asama, metin) VALUES (?, 'asama', ?, ?, ?, ?)",
                (urun["id"], _simdi(), urun["asama"], yeni, "Formlar basıldı; ürün ERP'nin gösterdiği aşamaya geçti."),
            )
    return cur.lastrowid


# Ekranlar

def _urun(vt, urun_id, tur):
    """Formu basılacak güç ünitesi (bakım-onarım için gelen de); stoktaki güç ünitesinde yalnızca proje takip kartı."""
    urun = urun_kaydi(vt, urun_id)
    if urun is None or not formlu_mu(urun):
        abort(404)
    if tur not in (STOK_FORMLARI if urun["kalem_id"] is None else FORM_TURLERI):
        abort(404)
    return urun


def _sayi_oku(metin):
    metin = (metin or "").strip().replace(",", ".")
    if not metin:
        return None
    try:
        return float(metin)
    except ValueError:
        raise FormHatasi(f"\"{metin}\" sayı değil.") from None


def _motor_kaydet(vt, urun_kodu, form):
    model = (form.get("motor_model") or "").strip()
    if not model:
        raise FormHatasi("Motor modelini yazın.")
    kw, hp = _sayi_oku(form.get("guc_kw")), _sayi_oku(form.get("guc_hp"))
    if kw and not hp:
        hp = round(kw * 1.341)
    devir = _sayi_oku(form.get("devir"))
    vt.execute(
        "INSERT INTO motor_bilgileri (urun_kodu, marka, model, guc_kw, guc_hp, devir, kullanici_id, zaman)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (urun_kodu) DO UPDATE SET marka = excluded.marka,"
        " model = excluded.model, guc_kw = excluded.guc_kw, guc_hp = excluded.guc_hp, devir = excluded.devir,"
        " kullanici_id = excluded.kullanici_id, zaman = excluded.zaman",
        (urun_kodu, (form.get("motor_marka") or "").strip() or None, model, kw, hp,
         int(devir) if devir else None, g.kullanici["id"], _simdi()),
    )


@bp.route("/urun/<int:urun_id>/form/<tur>", methods=["GET", "POST"])
def form(urun_id, tur):
    vt = baglanti()
    urun = _urun(vt, urun_id, tur)
    stokta = urun["kalem_id"] is None
    bakim = urun["tur"] == "servis"  # bakım-onarım için gelen güç ünitesi
    kod = makine_kodu(urun["urun_kodu"])  # bakımda "-MNT"siz: şablon ve motor bilgisi bununla bulunur
    motor = motor_bilgisi(vt, kod)
    seriler, teyitsiz = motor_serileri(vt, urun)
    vibrolar = vibro_adaylari(vt, urun)
    ekipman = ekipman_kodlari(vt, urun)
    adaylar = [] if tur == "kodlama" else uygun_sablonlar(tur, kod)
    bugun = date.today().isoformat()

    if request.method == "POST":
        if g.kullanici["rol"] != "ekip":
            abort(403)
        try:
            if request.form.get("motor_model") is not None:
                with vt:
                    _motor_kaydet(vt, kod, request.form)
                motor = motor_bilgisi(vt, kod)
                if request.form.get("islem") == "motor":
                    flash(f"{kod} için motor bilgisi kaydedildi; sonraki formlarda kendiliğinden gelir.")
                    return redirect(url_for(".form", urun_id=urun_id, tur=tur))
            with vt:
                if teyitsiz:
                    raise FormHatasi(f"Önce {', '.join(ad.lower() for ad in teyitsiz)} girilip teyit edilmeli (Makine numaraları).")
                if not motor:
                    raise FormHatasi("Motor bilgisini girin.")
                sablon = None
                if tur != "kodlama":
                    sablon = next((s for s in adaylar if s.yol.name == request.form.get("sablon")), None)
                    if sablon is None:
                        raise FormHatasi("Bu model için form bulunamadı." if not adaylar else "Formu seçin.")
                try:
                    form_tarihi = date.fromisoformat(request.form.get("tarih") or bugun)
                except ValueError:
                    raise FormHatasi("Form veriliş tarihi geçersiz.") from None
                motorlar = motor_metinleri(motor)
                seri_no = urun["seri_no"] or ""
                if tur == "kodlama" and (stokta or bakim):
                    # Stok ve bakım makinesinin opsiyonel ekipmanı: ekip işaretler, sonraki basımlarda işaretli gelir
                    secilen = request.form.getlist("ekipman")
                    ekipman = [e for e in PP_EKLENTILERI if e in secilen]
                    vt.execute("UPDATE urunler SET elle_ekipman = ? WHERE id = ?", (",".join(ekipman), urun_id))
                if tur == "kodlama" and bakim:
                    # Bakıma gelen makinenin kendi seri no'su: ERP'de çoğunlukla yok, ekip yazar; makinede saklanır
                    seri_no = " ".join((request.form.get("seri_no") or "").split())
                    if seri_no != (urun["seri_no"] or ""):
                        vt.execute("UPDATE urunler SET seri_no = ? WHERE id = ?", (seri_no or None, urun_id))
                        not_ekle(vt, urun_id, f"Makinenin seri no'su girildi: {seri_no}." if seri_no
                                 else "Makinenin seri no'su kaldırıldı.", g.kullanici["id"])
                b = {
                    "siparis_no": urun["siparis_no"] or STOK_BASLIGI, "seri_no": seri_no, "makine_modeli": kod, "bakim": bakim,
                    **kayit_alanlari(kayit_bilgisi(vt, urun)), "motor_seri": seriler, "motor_marka": (motor["marka"] or "").upper(),
                    "motor_model_kisa": motor["model"], **motorlar,
                    "vibro": (request.form.get("vibro") or "").strip(), "vibro_seri": (request.form.get("vibro_seri") or "").strip(),
                    "tarih": tarih(form_tarihi), "urun_turu": URUN_TURU, "yag": (request.form.get("yag") or "").strip(),
                    "uzaktan_erisim": "Var" if UZAKTAN_ERISIM in ekipman else "Yok",
                    "motor_sayisi": str(motor_sayisi(urun["urun_kodu"])), "ekipman": ekipman,
                }
                form_id = form_hazirla(vt, urun, tur, b, sablon, g.kullanici["id"])
        except FormHatasi as hata:
            flash(f"Form hazırlanmadı: {hata}")
            return redirect(url_for(".form", urun_id=urun_id, tur=tur))
        return redirect(url_for("urunler.sayfa", urun_id=urun_id, form=form_id) + ("#stok" if stokta else "#asama"))

    return render_template(
        "form.html", urun=urun, tur=tur, tur_adi=FORM_TURLERI[tur], motor=motor, motor_metni=motor_metinleri(motor),
        seriler=seriler, teyitsiz=teyitsiz, vibrolar=vibrolar, adaylar=adaylar, bugun=bugun, kayit=kayit_bilgisi(vt, urun),
        yag_onerisi=yag_metni(urun["aciklama"]), oneri=_motor_onerisi(vt, kod) if not motor else None,
        stokta=stokta, bakim=bakim, makine_kodu=kod, ekipman=ekipman, PP_EKLENTILERI=PP_EKLENTILERI,
        STOK_BASLIGI=STOK_BASLIGI, onceki=onceki_bilgiler(vt, urun, tur),
    )


def onceki_bilgiler(vt, urun, tur):
    """Makinenin son basılan formunda elle yazılanlar (test vibrosu, yağ): yeniden basarken ya da sonraki formda
    hazır gelir (stok ve bakım makinesinde siparişte vibro yok). Önce aynı form, yoksa son basılan herhangi bir form;
    stoktayken basılanlar yalnızca stok kartında."""
    son = vt.execute(
        "SELECT bilgiler FROM urun_formlari WHERE urun_id = ? AND stokta = ? ORDER BY tur = ? DESC, id DESC LIMIT 1",
        (urun["id"], int(urun["kalem_id"] is None), tur),
    ).fetchone()
    return json.loads(son[0]) if son else {}


def _motor_onerisi(vt, urun_kodu):
    """Aynı model numarasının başka bir kodu için girilmiş motor bilgisi (öneri olarak)."""
    no = pp_modeli(urun_kodu)[0]
    if no is None:
        return None
    return next((m for m in vt.execute("SELECT * FROM motor_bilgileri ORDER BY zaman DESC")
                 if pp_modeli(m["urun_kodu"])[0] == no), None)


@bp.route("/urun/<int:urun_id>/form-dosyasi/<int:form_id>")
def dosya(urun_id, form_id):
    vt = baglanti()
    kayit = vt.execute("SELECT * FROM urun_formlari WHERE id = ? AND urun_id = ?", (form_id, urun_id)).fetchone()
    veri = Path(current_app.config["VERI_KLASORU"]).resolve()
    yol = (veri / kayit["dosya"]).resolve() if kayit and kayit["dosya"] else None
    if yol is None or veri not in yol.parents or not yol.is_file():
        abort(404)
    urun = urun_kaydi(vt, urun_id)
    ad = f"{FORM_TURLERI[kayit['tur']]} {urun['siparis_no'] or 'Stok'} {urun['urun_kodu']}.pdf".replace("/", "-")
    return send_file(yol, mimetype="application/pdf", download_name=ad)
