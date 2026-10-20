---
name: kaydet
description: Çalışmayı kaydeder - kaldığımız yeri günceller, gerçek veri taraması yapar, commit'ler, GitHub'a gönderir ve OMS Veri klasörünü sunucuya yedekler. Yalnızca kullanıcı /kaydet yazınca çalışır.
disable-model-invocation: true
---

# /kaydet

Kullanıcının `/kaydet` yazması commit ve push için onaydır; ayrıca sorma. Bir adım başarısız olursa dur, nedenini sade Türkçeyle söyle ve sonraki adımlara geçme. Tek istisna 7. adımdır: yedek, commit ya da push başarısız olsa da denenir.

1. **Durum.** `git status --short` ve `git log -1 --oneline` çalıştır. Değişiklik de gönderilmemiş commit de yoksa "Kaydedilecek yeni bir şey yok" de ve yalnızca 7. adımı yap.

2. **Kaldığımız yer.** `docs/kaldigimiz-yer.md` dosyasını bu oturuma göre güncelle:
   - en üstte tarih ve saat (GG/AA/YYYY, Europe/Istanbul) ve tek cümlelik durum
   - "Bu oturumda yapılanlar": kısa maddeler
   - "Sıradaki iş": numaralı, ilk madde bir sonraki oturumun ilk işi
   - "Kullanıcıdan beklenenler": cevap bekleyen soru ve dosyalar

   Dosya bir günlük değildir; yalnızca şu anki durumu anlatır (eski oturumlar git geçmişinde durur). Gerçek proje kodu, seri no, iş emri no, müşteri ya da çalışan adı yazma.

3. **Veri taraması.** `py -3 -I .githooks/veri_kontrol.py --tum` çalıştır. Bulgu varsa dur: bulguları göster, düzeltmeyi öner, commit'leme.

4. **Sahneye al.** `git add -A`, sonra `git status --short`. Listede `OMS Veri/` altından bir dosya ya da beklenmeyen bir veri dosyası (Excel, resim, veritabanı) varsa dur ve kullanıcıya göster.

5. **Commit.** Ne yapıldığını anlatan kısa, Türkçe bir mesajla commit'le. pre-commit kancası yeniden tarar; reddederse dur. `--no-verify` hiçbir koşulda kullanılmaz.

6. **GitHub'a gönder.** `git push`. Dalın GitHub'da karşılığı yoksa `git push -u origin <dal>`. Ağ ya da giriş hatası olursa nedenini söyle; commit bilgisayarda durduğu için kayıp yoktur, bir sonraki `/kaydet` yeniden dener.

7. **Veri yedeği.** Proje kökünde `yedek-hedefi.txt` varsa `py -3 -I araclar/yedekle.py` çalıştır ve sonucunu al. Dosya yoksa yedeğin tanımlı olmadığını bir cümleyle hatırlat. Sunucuya ulaşılamazsa uyar; commit ve push bundan etkilenmez.

8. **Rapor.** Kullanıcıya 3-5 satır yaz: commit (kısa kod ve mesaj), GitHub'a gönderildi mi, yedek sonucu, kaldığımız yerdeki sıradaki iş.
