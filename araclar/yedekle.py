"""OMS Veri klasörünü sunucudaki yedek klasörüne kopyalar.

Hedef, proje kökündeki yedek-hedefi.txt dosyasının ilk satırıdır (git'e girmez).
Dosyalar <hedef>/OMS Veri altına gider. Hiçbir şey silinmez:
- yerelde silinen dosya yedekte kalır;
- değişen bir dosyanın yedekteki eski hali, üzerine yazılmadan önce
  <hedef>/OMS Veri - eski surumler/<tarih-saat>/ altına taşınır;
- yedekteki dosya yereldekinden yeniyse dokunulmaz, uyarı verilir.
Bitince OMS Veri/son-yedek.txt dosyasına tarih ve özet yazılır.

Kullanım: py -3 -I araclar/yedekle.py [--kaynak KLASÖR] [--hedef KLASÖR]
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
SON_YEDEK = "son-yedek.txt"
# Ağ sürücüleri dosya saatini yuvarlayabilir; bu kadar saniyelik fark "aynı" sayılır.
SAAT_PAYI = 2


def hedefi_oku():
    dosya = KOK / "yedek-hedefi.txt"
    if not dosya.exists():
        return None
    for satir in dosya.read_text(encoding="utf-8-sig").splitlines():
        satir = satir.strip().strip('"')
        if satir and not satir.startswith("#"):
            return Path(satir)
    return None


def yedekle(kaynak, hedef):
    yedek = hedef / "OMS Veri"
    eski = hedef / "OMS Veri - eski surumler" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    sayac = {"yeni": 0, "güncellendi": 0, "aynı": 0}
    yedekte_yeni, hatalar = [], []

    for dosya in sorted(kaynak.rglob("*")):
        if not dosya.is_file() or dosya.name.startswith("~$") or dosya.name == SON_YEDEK:
            continue
        goreli = dosya.relative_to(kaynak)
        hedef_dosya = yedek / goreli
        try:
            if hedef_dosya.exists():
                k, h = dosya.stat(), hedef_dosya.stat()
                if h.st_mtime > k.st_mtime + SAAT_PAYI:
                    yedekte_yeni.append(str(goreli))
                    continue
                if abs(k.st_mtime - h.st_mtime) <= SAAT_PAYI and k.st_size == h.st_size:
                    sayac["aynı"] += 1
                    continue
                (eski / goreli).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(hedef_dosya, eski / goreli)
                sayac["güncellendi"] += 1
            else:
                sayac["yeni"] += 1
            hedef_dosya.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dosya, hedef_dosya)
        except OSError as hata:
            hatalar.append(f"{goreli}: {hata}")
    return sayac, yedekte_yeni, hatalar


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    ayrac = argparse.ArgumentParser(description="OMS Veri klasörünü yedekler.")
    ayrac.add_argument("--kaynak", type=Path, default=KOK / "OMS Veri")
    ayrac.add_argument("--hedef", type=Path)
    args = ayrac.parse_args(argv)
    kaynak, hedef = args.kaynak, args.hedef or hedefi_oku()

    if hedef is None:
        print("Yedek hedefi tanımlı değil. Proje klasöründe yedek-hedefi.txt dosyasını açıp "
              "ilk satırına sunucudaki klasörün yolunu yazın.")
        return 1
    if not kaynak.is_dir():
        print(f"Yedeklenecek klasör bulunamadı: {kaynak}")
        return 1
    if not hedef.is_dir():
        print(f"Yedek klasörüne ulaşılamıyor: {hedef}")
        return 1
    if hedef.resolve().is_relative_to(kaynak.resolve()):
        print("Yedek klasörü, yedeklenen klasörün içinde olamaz.")
        return 1

    sayac, yedekte_yeni, hatalar = yedekle(kaynak, hedef)
    ozet = ", ".join(f"{adet} {ad}" for ad, adet in sayac.items())
    zaman = datetime.now().strftime("%d/%m/%Y %H:%M")
    print(f"Yedek: {ozet}. Hedef: {hedef}")
    if sayac["güncellendi"]:
        print("Güncellenen dosyaların önceki halleri 'OMS Veri - eski surumler' klasöründe.")
    for goreli in yedekte_yeni:
        print(f"Uyarı: yedekteki dosya yereldekinden yeni, dokunulmadı: {goreli}")
    for hata in hatalar:
        print(f"Hata: {hata}")
    if hatalar:
        return 1
    (kaynak / SON_YEDEK).write_text(f"{zaman} · {hedef} · {ozet}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
