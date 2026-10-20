"""Claude'un veri kaybettirebilecek komutlarını durdurur (PreToolUse kancası).

Bash ve PowerShell araçlarına giden her komuta bakar:
- ENGELLE: hiç çalıştırılmaz (git clean, --no-verify, OMS Veri'yi git'e ekleme ...).
- SOR: kullanıcı onaylamadan çalışmaz (reset --hard, zorla push, OMS Veri'den silme ...).
Komut bunlardan birine uymazsa kanca hiçbir şey yazmaz; normal izin akışı sürer.
"""

import json
import re
import sys

# Komut parçası: aynı komut içinde kalır, ; && || | ya da satır sonunda biter.
P = r"[^\n;&|]*"
VERI = r"OMS\\?\sVeri"

ENGELLE = [
    (rf"\bgit\b{P}\bclean\b",
     "git clean, git'in yok saydığı dosyaları (OMS Veri dahil) silebilir."),
    (r"--no-verify\b",
     "--no-verify gerçek veri korumasını (pre-commit) atlar."),
    (rf"\bgit\b{P}\bcommit\b{P}\s-n\b",
     "git commit -n gerçek veri korumasını (pre-commit) atlar."),
    (rf"\bgit\b{P}\badd\b{P}(?:\s-f\b|\s--force\b)",
     "git add -f .gitignore'u aşar; gerçek veri git'e girebilir."),
    (rf"\bgit\b{P}\b(?:add|commit|stage)\b{P}{VERI}",
     "OMS Veri klasörü git'e eklenmez."),
    (r"core\.hooksPath",
     "Koruma kancalarının yeri değiştirilmez."),
]

SOR = [
    (rf"\bgit\b{P}\breset\b{P}--hard\b",
     "git reset --hard kaydedilmemiş değişiklikleri siler."),
    (rf"\bgit\b{P}\bpush\b{P}(?:\s-f\b|--force)",
     "Zorla gönderme GitHub'daki geçmişi silebilir."),
    (rf"\bgit\b{P}\bcheckout\b{P}(?:\s--\s|\s\.(?:\s|$))",
     "Dosyalardaki kaydedilmemiş değişiklikler geri alınır."),
    (rf"\bgit\b{P}\brestore\b(?!{P}--staged)",
     "Dosyalardaki kaydedilmemiş değişiklikler geri alınır."),
    (rf"\bgit\b{P}\bbranch\b{P}\s-D\b",
     "Birleştirilmemiş dal silinir."),
    (rf"\bgit\b{P}\bstash\b{P}\b(?:drop|clear)\b",
     "Saklanan değişiklikler silinir."),
    (rf"\bgit\b{P}\brm\b",
     "git rm dosyayı diskten de siler."),
    (rf"\bgit\b{P}\b(?:rebase|filter-branch|filter-repo)\b",
     "Kayıt geçmişi yeniden yazılır."),
    (rf"(?i)(?:\brm\b|\brmdir\b|\brd\b|\bdel\b|\berase\b|remove-item|\bri\b|clear-content){P}{VERI}",
     "OMS Veri klasöründeki gerçek veriler silinir."),
]


def karar(tur, neden):
    cikti = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": tur,
            "permissionDecisionReason": f"Proje koruması: {neden}",
        }
    }
    print(json.dumps(cikti, ensure_ascii=True))


def main():
    try:
        girdi = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        komut = girdi.get("tool_input", {}).get("command", "")
    except (ValueError, AttributeError):
        return 0
    for liste, tur in ((ENGELLE, "deny"), (SOR, "ask")):
        for desen, neden in liste:
            if re.search(desen, komut):
                karar(tur, neden)
                return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
