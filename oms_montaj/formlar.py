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
from .form_kurallari import FORM_TURLERI, basilan_formlar, forma_tabi_mi, sinirla
from .kimlik import ekip_gerekli
from .marka import hazir_png, logo_dosyasi, vibro_oneki
from .numaralar import MOTOR_ALANLARI, TEYITSIZ, urun_numaralari
from .urun_kurallari import motor_sayisi, sade, yag_metni
from .urunler import urun_kaydi
from .veritabani import baglanti

bp = Blueprint("formlar", __name__)

SABLON_KLASORU = "formlar"
CIKTI_KLASORU = "form-ciktilari"
URUN_TURU = "Güç Ünitesi"


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


def uzaktan_erisim_var_mi(vt, urun):
    return vt.execute(
        "SELECT 1 FROM siparis_kalemleri WHERE siparis_id = ? AND urun_kodu = 'OZ04082' AND COALESCE(erp_durum, '') != ?",
        (urun["siparis_id"], IPTAL),
    ).fetchone() is not None


def motor_serileri(vt, urun):
    """(motor seri no'ları, teyit bekleyen ya da girilmemiş numaraların adları)."""
    numaralar = [n for n in urun_numaralari(vt, urun, urun["aile"], urun["siparis_id"], urun["urun_kodu"])
                 if n[0] in MOTOR_ALANLARI]
    eksik = [ad for _, ad, deger, kaynak in numaralar if not deger or kaynak in TEYITSIZ]
    return [deger for _, _, deger, _ in numaralar], eksik


def is_emri_no(vt, urun):
    ie = vt.execute("SELECT is_emri_no FROM is_emirleri WHERE id = ?", (urun["is_emri_id"],)).fetchone() if urun["is_emri_id"] else None
    return ie[0] if ie else ""


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
# basılır (kullanıcı kararı, 02/11/2026); sunucuda yerini ölçüleri aynı Liberation Sans alır.

KIRMIZI, KOYU, SOLUK, CIZGI = "C41E24", "16181D", "5B6170", "D9DCE3"
YAZI_TIPI = "Arial"


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


def kodlama_kitabi(b):
    """Proje takip kartının Excel kitabı. b: forma yazılan bilgiler."""
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
    s.column_dimensions["A"].width = 30
    s.column_dimensions["B"].width = 86
    s.column_dimensions["C"].width = 36

    def font(boy, renk=KOYU, kalin=True):
        return Font(name=YAZI_TIPI, size=boy, bold=kalin, color=renk)

    kirmizi = PatternFill("solid", fgColor=KIRMIZI)
    ince = Side(style="thin", color=CIZGI)
    kalin = Side(style="thick", color=KOYU)

    # Kırmızı bant: solda logo, sağda başlık
    s.row_dimensions[1].height = 44
    s.row_dimensions[2].height = 22
    for satir in (1, 2):
        for sutun in "ABC":
            s[f"{sutun}{satir}"].fill = kirmizi
    s["C1"] = "PROJE TAKİP KARTI"
    s["C1"].font = font(24, "FFFFFF")
    s["C1"].alignment = Alignment(horizontal="right", vertical="bottom")
    s["C2"] = "MONTAJ FABRİKASI"
    s["C2"].font = font(11, "FFFFFF", kalin=False)
    s["C2"].alignment = Alignment(horizontal="right", vertical="top")
    logo = _beyaz_logo()
    if logo:
        resim = ExcelResmi(logo)
        yukseklik = 56  # piksel; bandın (44 + 22 punto ≈ 88 piksel) ortasında
        genislik = round(resim.width * yukseklik / resim.height)
        resim.anchor = OneCellAnchor(_from=AnchorMarker(col=0, colOff=pixels_to_EMU(16), row=0, rowOff=pixels_to_EMU(16)),
                                     ext=XDRPositiveSize2D(pixels_to_EMU(genislik), pixels_to_EMU(yukseklik)))
        s.add_image(resim)
    else:
        s["A1"] = "OMS"
        s["A1"].font = font(28, "FFFFFF")
        s.merge_cells("A1:A2")
        s["A1"].alignment = Alignment(vertical="center")
    s.row_dimensions[3].height = 6

    # Sipariş no (en büyük yazı) ve sağında güç ünitesinin seri no'su
    s.row_dimensions[4].height = 104
    s.merge_cells("A4:B4")
    s["A4"] = b["siparis_no"]
    s["A4"].font = font(84)
    s["A4"].alignment = Alignment(vertical="center")
    s["C4"] = b.get("seri_no") or ""
    s["C4"].font = font(20, SOLUK)
    s["C4"].alignment = Alignment(horizontal="right", vertical="bottom", wrap_text=True)
    for sutun in "ABC":
        s[f"{sutun}4"].border = Border(bottom=kalin)

    motorlar = b.get("motor_seri") or []
    ikili = len(motorlar) > 1
    model = b.get("motor_model_kisa") or ""
    satirlar = [
        ("GÜÇ ÜNİTESİ", CellRichText(TextBlock(InlineFont(rFont=YAZI_TIPI, sz=48, b=True, color=KOYU), b["makine_modeli"]),
                                     TextBlock(InlineFont(rFont=YAZI_TIPI, sz=38, b=True, color=SOLUK),
                                               f" · {model}{' (×2)' if ikili else ''}")) if model else b["makine_modeli"]),
        ("TEST VİBROSU", b.get("vibro") or "—"),
        ("MOTOR SERİ NO", "\n".join(
            f"{i} · {b.get('motor_marka', '')} {no}".replace("  ", " ") if ikili else f"{b.get('motor_marka', '')} {no}".strip()
            for i, no in enumerate(motorlar, 1)) or "—"),
        ("İŞ EMRİ NO", b.get("is_emri_no") or "—"),
        ("YAĞ", b.get("yag") or "Belirtilmedi"),
    ]
    son = 4 + len(satirlar)
    for i, (etiket, deger) in enumerate(satirlar, start=5):
        iki_satir = ikili and etiket == "MOTOR SERİ NO"
        yag_satiri = etiket == "YAĞ"
        s.row_dimensions[i].height = 118 if iki_satir else 58 if yag_satiri else 74
        s[f"A{i}"] = etiket
        s[f"A{i}"].font = font(15, KIRMIZI)
        s[f"A{i}"].alignment = Alignment(vertical="center")
        s.merge_cells(f"B{i}:C{i}")
        s[f"B{i}"] = deger
        s[f"B{i}"].font = font(38 if iki_satir else 28 if yag_satiri else 48)
        # Güç ünitesi satırı uzun motor modelinde taşmasın diye satıra sığacak kadar küçülür
        s[f"B{i}"].alignment = Alignment(vertical="center", wrap_text=iki_satir or yag_satiri,
                                         shrink_to_fit=etiket == "GÜÇ ÜNİTESİ")
        if i < son:
            for sutun in "ABC":
                s[f"{sutun}{i}"].border = Border(bottom=ince)
    alt = son + 1
    s.row_dimensions[alt].height = 24
    s[f"A{alt}"] = f"Form veriliş tarihi: {b.get('tarih', '')}"
    s[f"A{alt}"].font = font(11, SOLUK, kalin=False)
    s[f"A{alt}"].alignment = Alignment(vertical="bottom")
    s[f"C{alt}"] = "OMS Montaj"
    s[f"C{alt}"].font = font(11, SOLUK, kalin=False)
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
    gösterdiği aşamaya ilerletir. Kaydın id'sini döndürür."""
    veri = Path(current_app.config["VERI_KLASORU"])
    klasor = veri / CIKTI_KLASORU / str(urun["id"])
    klasor.mkdir(parents=True, exist_ok=True)
    ad = f"{tur}-{datetime.now():%Y%m%d-%H%M%S}"
    kitap = kodlama_kitabi(b) if tur == "kodlama" else sablonu_doldur(sablon.yol, b)
    excel_yolu, pdf_yolu = klasor / f"{ad}.xlsx", klasor / f"{ad}.pdf"
    kitap.save(excel_yolu)
    pdf_cevir(excel_yolu, pdf_yolu)
    cur = vt.execute(
        "INSERT INTO urun_formlari (urun_id, tur, sablon, bilgiler, dosya, kullanici_id, zaman) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (urun["id"], tur, sablon.yol.name if sablon else None, json.dumps(b, ensure_ascii=False),
         pdf_yolu.relative_to(veri).as_posix(), kullanici_id, _simdi()),
    )
    if forma_tabi_mi(urun) and urun["erp_asama"]:
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
    urun = urun_kaydi(vt, urun_id)
    if urun is None or tur not in FORM_TURLERI or urun["aile"] != "PP" or urun["tur"] != "kart":
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
    motor = motor_bilgisi(vt, urun["urun_kodu"])
    seriler, teyitsiz = motor_serileri(vt, urun)
    vibrolar = vibro_adaylari(vt, urun)
    adaylar = [] if tur == "kodlama" else uygun_sablonlar(tur, urun["urun_kodu"])
    bugun = date.today().isoformat()

    if request.method == "POST":
        if g.kullanici["rol"] != "ekip":
            abort(403)
        try:
            if request.form.get("motor_model") is not None:
                with vt:
                    _motor_kaydet(vt, urun["urun_kodu"], request.form)
                motor = motor_bilgisi(vt, urun["urun_kodu"])
                if request.form.get("islem") == "motor":
                    flash(f"{urun['urun_kodu']} için motor bilgisi kaydedildi; sonraki formlarda kendiliğinden gelir.")
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
                b = {
                    "siparis_no": urun["siparis_no"], "seri_no": urun["seri_no"] or "", "makine_modeli": urun["urun_kodu"],
                    "is_emri_no": is_emri_no(vt, urun), "motor_seri": seriler, "motor_marka": (motor["marka"] or "").upper(),
                    "motor_model_kisa": motor["model"], **motorlar,
                    "vibro": (request.form.get("vibro") or "").strip(), "vibro_seri": (request.form.get("vibro_seri") or "").strip(),
                    "tarih": tarih(form_tarihi), "urun_turu": URUN_TURU, "yag": (request.form.get("yag") or "").strip(),
                    "uzaktan_erisim": "Var" if uzaktan_erisim_var_mi(vt, urun) else "Yok",
                    "motor_sayisi": str(motor_sayisi(urun["urun_kodu"])),
                }
                form_id = form_hazirla(vt, urun, tur, b, sablon, g.kullanici["id"])
        except FormHatasi as hata:
            flash(f"Form hazırlanmadı: {hata}")
            return redirect(url_for(".form", urun_id=urun_id, tur=tur))
        return redirect(url_for("urunler.sayfa", urun_id=urun_id, form=form_id) + "#asama")

    return render_template(
        "form.html", urun=urun, tur=tur, tur_adi=FORM_TURLERI[tur], motor=motor, motor_metni=motor_metinleri(motor),
        seriler=seriler, teyitsiz=teyitsiz, vibrolar=vibrolar, adaylar=adaylar, bugun=bugun, ie_no=is_emri_no(vt, urun),
        yag_onerisi=yag_metni(urun["aciklama"]), oneri=_motor_onerisi(vt, urun["urun_kodu"]) if not motor else None,
    )


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
    ad = f"{FORM_TURLERI[kayit['tur']]} {urun['siparis_no']} {urun['urun_kodu']}.pdf".replace("/", "-")
    return send_file(yol, mimetype="application/pdf", download_name=ad)
