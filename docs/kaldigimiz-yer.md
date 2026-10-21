# Kaldığımız yer

**21/10/2026, 11:22.** 1. adım (uygulama iskeleti) tamam; giriş ekranı ve yan menü kullanıcının isteğine göre yeniden tasarlandı. Sırada 2. adım var: ERP sipariş talepleri listesinin yüklenmesi.

## Bu oturumda yapılanlar

- Kalan sorular cevaplandı (13, 14, 36–42); Planner özeti onaylandı.
- Uygulama planı (`docs/uygulama-plani.md`), bağımlılıklar ve WhatsApp ile hata bildiriminde (a) seçeneği onaylandı.
- Atama kuralları ve roller, adlarıyla birlikte `OMS Veri/kurulum/atama-ve-roller.txt` dosyasında. Yasaklı kelimelere üç ad eklendi.
- 1. adım: `oms_montaj/` uygulama iskeleti.
  - Giriş, ilk kurulum, şifre değiştirme.
  - Ekip ve İzleyici rolleri, Ayarlar > Kullanıcılar.
  - Boş ekranlar, Inter yazı tipi.
  - `baslat.bat`, `kurulum.bat`.
- Görünüm, kullanıcının istekleriyle:
  - Giriş ve kurulum ekranı ana portaldaki gibi iki parçalı kart: solda kırmızı panelde beyaz logo, "MONTAJ" ve tanıtım; sağda form.
  - Açılışta logo ortadan ikiye bölünüp açılıyor.
  - Menü solda, koyu yan şerit; telefonda üç çizgili düğmeyle açılan çekmece.
- Logo `OMS Veri/uygulama/marka/oms-logo.png` dosyasında (git'e girmez). Uygulama PNG'nin boş kenarlarını kırpıyor ve yan menüde beyaza çeviriyor.
- 32 otomatik test geçiyor. Ekranlar telefon ve bilgisayar genişliğinde ekran görüntüsüyle denendi.
- Telefondan deneme şimdilik bekliyor: kullanıcının bilgisayarında Windows güvenlik duvarı dışarıdan gelen bağlantıları engelliyor. Acelesi yok; 2. adımdan sonra deneme sürümünü sunucuya erken kurmak düşünülebilir.

## Sıradaki iş

1. 2. adım:
   - "Sipariş talepleri" ve "siparişi tamamlanan sipariş talepleri" Excel'lerinin ERP yükleme ekranından yüklenmesi. Yapıları `docs/ihtiyaclar.md` 2.3'te.
   - Siparişler listesi ve sipariş kartı.
   - Kart kurallarına göre ürün kartlarının oluşması.
   - Seri no, teslim tarihi, renk, yağ, aksesuarlar ve "onay bekliyor" bilgileri.
2. Kullanıcı gerçek listeyi yükleyip dener; düzeltmeler yapılır.
3. 3. adım: iş emirleri.

## Kullanıcıdan beklenenler

- 2. adım bitince gerçek sipariş listesini yükleyip denemek.
- Sunucu yedeği kullanıcı kararıyla ertelendi. `OMS Veri` şimdilik yalnızca bu bilgisayarda; yedek klasörü seçilince `yedek-hedefi.txt` yazılır.
