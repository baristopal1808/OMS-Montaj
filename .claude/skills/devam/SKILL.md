---
name: devam
description: Oturum başında kaldığımız yeri özetler - son kayıtlar, kaydedilmemiş değişiklikler, son veri yedeği, sıradaki iş ve kullanıcıdan beklenenler.
---

# /devam

Yeni bir oturumun başında kullanıcıya nerede kaldığımızı anlatır. Hiçbir dosyayı değiştirmez.

1. `docs/kaldigimiz-yer.md` dosyasını oku (CLAUDE.md ile yüklendiyse yeniden okumaya gerek yok).
2. `git log -5 --format="%h %ad %s" --date=format:"%d/%m/%Y %H:%M"`, `git status --short` ve gönderilmemiş commit sayısı için `git rev-list --count @{u}..HEAD` çalıştır (dalın GitHub karşılığı yoksa bunu söyle).
3. `OMS Veri/son-yedek.txt` varsa son yedeğin tarihini oku. Yoksa ya da `yedek-hedefi.txt` tanımlı değilse bunu belirt.
4. Kullanıcıya en fazla 10 satırlık, sade Türkçe bir özet yaz:
   - **Kaldığımız yer:** bir-iki cümle
   - **Kaydedilmemiş iş:** varsa sayı ve "/kaydet ile kaydedebilirsiniz"
   - **Son yedek:** tarih ya da "tanımlı değil"
   - **Sıradaki adım:** kaldığımız yerdeki ilk iş
   - **Sizden beklenen:** varsa
5. Sonunda sıradaki adımla devam edilip edilmeyeceğini sor.
