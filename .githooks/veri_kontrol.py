"""Gerçek şirket verisinin git'e girmesini engeller.

.githooks/pre-commit her commit'ten önce bunu çalıştırır: commit'e girecek
dosyaların adına ve eklenen satırlara bakar. .githooks/commit-msg commit
mesajını tarar (--mesaj DOSYA). --tum ile commit'e girebilecek bütün dosyalar
(izlenen ve yeni) baştan sona taranır; /kaydet bunu commit'ten önce çalıştırır.

Bulgu varsa listeyi yazar ve 1 ile çıkar; git commit'i durdurur.
"""

import re
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VERI_KLASORU = "OMS Veri/"
IZINLI_KLASORLER = ("ornek-veri/",)
VERI_UZANTILARI = {
    ".xlsx", ".xls", ".xlsm", ".csv", ".db", ".sqlite", ".sqlite3", ".bak",
    ".png", ".jpg", ".jpeg", ".heic", ".webp", ".pdf", ".docx",
}
# Müşteri ve çalışan adları gibi gerçek değerler; dosyanın kendisi git'e girmez.
YASAKLI_KELIMELER = KOK / "OMS Veri" / "yasakli-kelimeler.txt"

# (ad, gerçeğe benzeyen değer, izinli uydurma biçim). Uydurma biçimler
# CLAUDE.md'de: proje OZ-TS0001, seri 0000 111 101, CAT N5F00001, iş emri 9001xx.
DESENLER = [
    ("proje kodu", re.compile(r"\bOZ-[A-Z]{2}\d{4}\b"), re.compile(r"^OZ-TS")),
    ("motor seri no", re.compile(r"\b\d{4}\s\d{3}\s{1,2}\d{3,4}\b"), re.compile(r"^0000\s")),
    ("CAT seri no", re.compile(r"\b(?:N5F|N5H|WRH)\d{4,6}\b"), re.compile(r"^(?:N5F|N5H|WRH)0000")),
    ("iş emri no", re.compile(r"\b[İI]EN\s*:?\s*\d{4,}"), re.compile(r"9001\d*$")),
]
UYDURMA_BICIMLER = "proje OZ-TS0001, seri 0000 111 101, CAT N5F00001, iş emri 9001xx"

TURKCE = str.maketrans("çğıöşüÇĞİIÖŞÜ", "cgiosuCGIIOSU")


def sade(metin):
    """Büyük-küçük harf ve Türkçe karakter farkını kaldırır."""
    return metin.translate(TURKCE).lower()


def git(*args):
    sonuc = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args], cwd=KOK, capture_output=True, check=True
    )
    return sonuc.stdout.decode("utf-8", "replace")


def yasakli_kelimeler():
    if not YASAKLI_KELIMELER.exists():
        return []
    kelimeler = []
    for satir in YASAKLI_KELIMELER.read_text(encoding="utf-8-sig").splitlines():
        satir = satir.strip()
        if satir and not satir.startswith("#"):
            kelimeler.append((satir, re.compile(r"\b" + re.escape(sade(satir)) + r"\b")))
    return kelimeler


def satiri_tara(satir, kelimeler):
    bulgular = []
    for ad, desen, izinli in DESENLER:
        for eslesme in desen.finditer(satir):
            if not izinli.search(eslesme.group()):
                bulgular.append(f"{ad}: {eslesme.group()}")
    sade_satir = sade(satir)
    for kelime, desen in kelimeler:
        if desen.search(sade_satir):
            bulgular.append(f"yasaklı kelime: {kelime}")
    return bulgular


def yolu_denetle(yol):
    dosya = Path(yol)
    if yol.startswith(VERI_KLASORU):
        return "OMS Veri klasöründen dosya"
    if dosya.name == ".env":
        return "gizli ayar dosyası (.env)"
    if dosya.suffix.lower() in VERI_UZANTILARI and not yol.startswith(IZINLI_KLASORLER):
        return f"veri taşıyabilecek dosya türü ({dosya.suffix.lower()})"
    return None


def sahnedeki_yollar():
    cikti = git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR")
    return [y for y in cikti.split("\0") if y]


def sahnedeki_satirlar():
    """Commit'e girecek eklenen satırlar: (yol, satır no, metin)."""
    fark = git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR")
    yol, no, baslikta = None, 0, False
    for satir in fark.splitlines():
        if satir.startswith("diff --git "):
            yol, baslikta = None, True
        elif baslikta and satir.startswith("+++ "):
            yol = satir[6:] if satir.startswith("+++ b/") else None
        elif satir.startswith("@@"):
            baslikta = False
            eslesme = re.search(r"\+(\d+)", satir)
            no = int(eslesme.group(1)) if eslesme else 0
        elif not baslikta and yol and satir.startswith("+"):
            yield yol, no, satir[1:]
            no += 1


def tum_yollar():
    cikti = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return [y for y in cikti.split("\0") if y]


def tum_satirlar(yollar):
    for yol in yollar:
        dosya = KOK / yol
        if not dosya.is_file():
            continue
        veri = dosya.read_bytes()
        if b"\0" in veri:
            continue
        for no, satir in enumerate(veri.decode("utf-8", "replace").splitlines(), 1):
            yield yol, no, satir


def main(argv):
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")
    kelimeler = yasakli_kelimeler()
    bulgular = []

    if argv[:1] == ["--mesaj"]:
        metin = Path(argv[1]).read_text(encoding="utf-8", errors="replace")
        for no, satir in enumerate(metin.splitlines(), 1):
            if not satir.startswith("#"):
                bulgular += [f"commit mesajı, satır {no}: {b}" for b in satiri_tara(satir, kelimeler)]
    else:
        tum = argv[:1] == ["--tum"]
        yollar = tum_yollar() if tum else sahnedeki_yollar()
        for yol in yollar:
            neden = yolu_denetle(yol)
            if neden:
                bulgular.append(f"{yol}: {neden}")
        satirlar = tum_satirlar(yollar) if tum else sahnedeki_satirlar()
        for yol, no, satir in satirlar:
            bulgular += [f"{yol}:{no}: {b}" for b in satiri_tara(satir, kelimeler)]
        if tum and not bulgular:
            print(f"Veri taraması temiz ({len(yollar)} dosya).")

    if not bulgular:
        return 0
    print("Gerçek veri olabilecek içerik bulundu, commit'e girmemeli:", file=sys.stderr)
    for bulgu in bulgular:
        print(f"  - {bulgu}", file=sys.stderr)
    print(f"Uydurma biçimler: {UYDURMA_BICIMLER}.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
