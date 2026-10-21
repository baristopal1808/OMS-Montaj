# OMS Montaj

OMS Pile Driving Equipment montaj fabrikasının iş takip uygulaması. Bugün Microsoft Teams Planner'da tutulan takibin (sipariş → malzeme hazırlık → montaj → test → sevk) yerine geçecek ve verisini Bilişim ERP'den alacak. Kullanıcı montaj ekibinin lideri.

Eski "PP-Tarafi-Is-Takip-Portali" projesinden tamamen bağımsızdır: o projenin klasörüne ve reposuna dokunulmaz, kodu kopyalanmaz.

Proje geliştirme aşamasında; uygulama planı onaylandı (21/10/2026) ve adım adım kodlanıyor. Plan: @docs/uygulama-plani.md
İhtiyaçlar, açık sorular ve kararlar: @docs/ihtiyaclar.md
Kaldığımız yer: @docs/kaldigimiz-yer.md

## Çalışma şekli

- Kullanıcı yazılımcı değil; montaj ekip lideri ve mühendis. Sade Türkçe yaz; teknik bir terimi ilk kullandığında bir cümleyle tanımla.
- Koda başlamadan önce ihtiyaçlar soru-cevapla netleşir, sonra uygulama planı çıkar ve kullanıcı onaylar. Emin olmadığın her konuda sor.
- Kararlar sohbette bırakılmaz: cevaplanan soru `docs/ihtiyaclar.md` içindeki "Kararlar" tablosuna yazılır.
- Yeni bir bağımlılık eklemeden önce sor. Commit mesajları Türkçe ve kısa olur.
- Commit ve push kullanıcı `/kaydet` yazınca yapılır; komutu yazmak onay sayılır. Bunun dışında önerilir, sormadan yapılmaz.

## Uygulama

- Kod `oms_montaj/` klasöründe: Python 3.12, Flask, SQLite; sunucu olarak Waitress. Kütüphaneler projeye özel `.venv` klasöründe (`kurulum.bat` kurar). Yeni kütüphane eklemeden önce sor.
- Başlatma: `baslat.bat` (port 8090; telefondan açılacak adresi ekrana yazar). Testler: `.venv\Scripts\python -m pytest`.
- Gerçek veri (veritabanı, oturum anahtarı) geliştirmede `OMS Veri/uygulama/` klasöründe; sunucuda `OMS_VERI_KLASORU` ortam değişkeninin gösterdiği klasörde.
- Şema değişikliği `oms_montaj/veritabani.py` içindeki `GOCLER` listesinin sonuna yeni göç olarak eklenir; yayınlanmış göç değiştirilmez.
- Resim dosyaları (.png, .jpg) git'e giremez; simgeler .svg yapılır.

## Oturum düzeni

- Oturum açılınca bir kanca (`.claude/hooks/oturum_acilis.py`) git durumunu bildirir. Kaydedilmemiş değişiklik ya da gönderilmemiş commit varsa ilk mesajında söyle.
- `/devam`: kaldığımız yeri, son kayıtları, son yedeği ve sıradaki işi özetler.
- `/kaydet`: kaldığımız yeri günceller, veri taraması yapar, commit'ler, GitHub'a gönderir ve `OMS Veri/` klasörünü sunucuya yedekler.

## Veri güvenliği (kesin kurallar)

1. Gerçek şirket verisi git'e girmez: Planner dışa aktarımları, ekran görüntüleri, ERP Excel'leri, veritabanı, yedekler. Hepsi `OMS Veri/` klasöründe durur; klasörün tamamını `.gitignore` yok sayar. `git add -f` kullanılmaz.
2. `OMS Veri/` içindeki dosyalar yalnızca kullanıcı istediğinde ya da o anki iş gerektirdiğinde okunur. İçerikleri belgelere, koda ve testlere kopyalanmaz; belgelerde yalnızca sayılar ve yapı anlatılır.
3. Testlerde, örneklerde ve belgelerde yalnızca uydurma veri kullanılır: proje `OZ-TS0001`, motor seri `0000 111 101`, CAT seri `N5F00001`, iş emri `9001xx`, kişi `TEST KULLANICI`, müşteri `TEST FIRMA`. Gerçek proje kodu, seri no, iş emri no, müşteri ya da çalışan adı yazılmaz. Bu yasak git'e giren içerik içindir: uygulama çalışırken gerçek veriden gelen adları (atanan kişi, müşteri) ekranda gösterir.
4. Repo private kalır. `.gitignore` gevşetilmez. `ornek-veri/` içinde yalnızca adı `.gitignore`'da tek tek yazan uydurma dosyalar serbesttir. Kullanıcı gerçek bir dosyayı yanlışlıkla `ornek-veri/` içine koyarsa dosya `OMS Veri/` klasörüne taşınır.
5. ERP'ye yazılmaz; yalnızca okunur (kesinleşmesi bekleniyor: ihtiyaclar.md, soru 12).

## Korumalar

| Koruma | Dosya | Ne yapar |
|---|---|---|
| Yok sayılan dosyalar | `.gitignore` | `OMS Veri/`, Excel, resim, veritabanı ve `.env` dosyalarını git'in dışında tutar |
| Git kapı bekçisi | `.githooks/pre-commit`, `.githooks/commit-msg`, `.githooks/veri_kontrol.py` | Commit'e `OMS Veri/` dosyası, veri dosyası ya da gerçeğe benzeyen değer (proje kodu, seri no, İEN, `OMS Veri/yasakli-kelimeler.txt` içindeki adlar) girerse commit'i durdurur. Python yoksa da durdurur |
| Claude koruması | `.claude/hooks/koruma.py` | `git clean`, `--no-verify`, `OMS Veri`'yi git'e ekleme gibi komutları engeller; `reset --hard`, zorla push, `OMS Veri`'den silme gibi geri alınamaz komutlarda kullanıcıya sorar |
| Veri yedeği | `yedekle.bat`, `araclar/yedekle.py` | `OMS Veri/` klasörünü `yedek-hedefi.txt` dosyasında yazan sunucu klasörüne kopyalar. Hiçbir şey silmez; değişen dosyanın eski hali ayrı klasörde saklanır |

- Git kapı bekçisi her yeni kopyada bir kez `git config core.hooksPath .githooks` komutuyla etkinleşir.
- Uydurma bir değer gerçeğe benzediği için reddedilirse 3. kuraldaki biçimlere çevrilir; korumayı atlamak için bir yol aranmaz.
