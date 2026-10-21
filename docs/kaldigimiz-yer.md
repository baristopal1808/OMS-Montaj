# Kaldığımız yer

**21/10/2026, 10:54.** İhtiyaçlar netleşti, uygulama planı onaylandı ve geliştirmenin 1. adımı (iskelet) yazıldı. Sırada giriş ekranına logo eklemek ve kullanıcının denemesi var.

## Bu oturumda yapılanlar

- Kalan sorular cevaplandı (13, 14, 36–42); Planner özeti (ihtiyaclar.md, 2. bölüm) onaylandı.
- Uygulama planı yazıldı ve onaylandı: `docs/uygulama-plani.md`. Bağımlılıklar ve WhatsApp ile hata bildiriminde (a) seçeneği onaylandı.
- Atama kuralları ve roller, adlarıyla birlikte `OMS Veri/kurulum/atama-ve-roller.txt` dosyasına yazıldı. Belgelerde yalnızca görevler geçiyor.
- Yasaklı kelimeler listesine üç ad eklendi (genel müdür ve sipariş formlarındaki iki kişi).
- 1. adım: `oms_montaj/` uygulama iskeleti.
  - Giriş, ilk kurulum, şifre değiştirme.
  - Ekip ve İzleyici rolleri, Ayarlar > Kullanıcılar.
  - Boş ekranlar, Inter yazı tipi.
  - `baslat.bat`, `kurulum.bat`.
  - 26 otomatik test geçiyor. Telefon genişliğinde ekran görüntüsüyle denendi.

## Sıradaki iş

1. Giriş ve kurulum ekranına OMS logosu, altında "MONTAJ" yazısı ve açılışta yazının ikiye bölünüp yukarı ve aşağı açıldığı bir canlandırma. Kullanıcı siyah logoyu gönderecek.
2. Kullanıcıya bilgisayarda ve telefonda nasıl deneyeceği adım adım anlatılır. Telefondan açılmıyorsa sebebi bulunur: güvenlik duvarı ya da Wi-Fi ağının ayrı olması.
3. Kullanıcı 1. adımı dener; düzeltmeler yapılır.
4. 2. adım: ERP sipariş talepleri listesinin yüklenmesi, siparişler listesi ve sipariş kartı.

## Kullanıcıdan beklenenler

- Siyah OMS logosu (tercihen .svg).
- 1. adımın denenmesi.
- Sunucu yedeği kullanıcı kararıyla ertelendi. `OMS Veri` şimdilik yalnızca bu bilgisayarda; yedek klasörü seçilince `yedek-hedefi.txt` yazılır.
