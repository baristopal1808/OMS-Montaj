"""Oturum açılınca git durumunu Claude'a bildirir (SessionStart kancası).

Kaydedilmemiş değişiklik ya da GitHub'a gönderilmemiş kayıt varsa kullanıcıya da
kısa bir uyarı gösterir. Kaldığımız yer docs/kaldigimiz-yer.md'dedir; CLAUDE.md
onu zaten yükler.
"""

import json
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]


def git(*args):
    sonuc = subprocess.run(
        ["git", "-c", "core.quotepath=false", *args], cwd=KOK, capture_output=True
    )
    return sonuc.returncode, sonuc.stdout.decode("utf-8", "replace").strip()


def main():
    _, dal = git("branch", "--show-current")
    kod, son_kayitlar = git("log", "-3", "--format=%h %ad %s", "--date=format:%d/%m/%Y %H:%M")
    kayit_var = kod == 0 and bool(son_kayitlar)
    _, durum = git("status", "--porcelain")
    degisenler = [s for s in durum.splitlines() if s.strip()]
    kod, ileride = git("rev-list", "--count", "@{u}..HEAD")
    gonderilmemis = int(ileride) if kod == 0 and ileride.isdigit() else None

    satirlar = [f"OMS Montaj git durumu (dal: {dal or '-'})"]
    satirlar.append("Son kayıtlar:\n" + son_kayitlar if kayit_var else "Henüz hiç commit yok.")
    if degisenler:
        satirlar.append(f"Kaydedilmemiş {len(degisenler)} değişiklik:")
        satirlar += [f"  {s}" for s in degisenler[:15]]
        if len(degisenler) > 15:
            satirlar.append(f"  ... ve {len(degisenler) - 15} dosya daha")
    else:
        satirlar.append("Kaydedilmemiş değişiklik yok.")
    if gonderilmemis is None and kayit_var:
        satirlar.append("Bu dal GitHub'a hiç gönderilmemiş.")
    elif gonderilmemis:
        satirlar.append(f"GitHub'a gönderilmemiş {gonderilmemis} commit var.")

    uyarilar = []
    if degisenler:
        uyarilar.append(f"kaydedilmemiş {len(degisenler)} değişiklik")
    if gonderilmemis or (gonderilmemis is None and kayit_var):
        uyarilar.append("GitHub'a gönderilmemiş kayıt")

    cikti = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(satirlar),
        }
    }
    if uyarilar:
        cikti["systemMessage"] = "OMS Montaj: " + " ve ".join(uyarilar) + " var. Kaydetmek için /kaydet yazın."
    print(json.dumps(cikti, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
