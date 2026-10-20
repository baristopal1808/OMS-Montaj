# Kaldığımız yer

**20/10/2026, 18:04.** İhtiyaç sorularının büyük kısmı cevaplandı ve ERP örnek dosyaları incelendi; geçmiş veri soruları (13, 14) cevap bekliyor. Uygulama kodu yok.

## Bu oturumda yapılanlar

- İlk kayıt yapıldı ve GitHub'a ilk kez gönderildi.
- `docs/ihtiyaclar.md` içindeki soruların çoğu cevaplandı; kararlar 5. bölümdeki tabloda. Öne çıkanlar:
  - Bütün ürün grupları, alt montajlar (DKM, BGM, motor-pompa hattı), kirişler, yedek parça ve servis takip edilir. Her fiziksel ürünün ayrı kartı olur.
  - Sipariş kartı ana kalemdir: içinde ürünler bölüm bölüm görünür. Ana ekran siparişler listesi; ayrıca aşama sütunlu bir Pano olur.
  - Etiketler, aşamalar ve kontrol listesi şablonları Ayarlar'dan yönetilir. Aşama listesi 3.1'de; denemelerde kesinleşir.
  - Bağlantısı ERP'de görünmeyen stok ürünleri kullanıcıya sorularak bağlanır.
  - Seri no'lar ve çene no uygulamada tutulur. Sipariş seri no'ları ERP'de "Planlama Bilgisi" sütununda var.
  - ERP'ye yazılmaz. Veriler toplu Excel listeleriyle yüklenir (3.2).
  - Herkes kendi kullanıcı adıyla girer; deneme süresince yetki ayrımı yok. Telefonda rahat kullanılır, karta fotoğraf eklenir. Yazı tipi Inter, yazılar çok küçük değil.
- Sipariş talebi görüntüleri ve ERP örnek Excel'leri `OMS Veri/erp/` klasörüne kondu ve incelendi. Yapıları `docs/ihtiyaclar.md` 2.2 ve 2.3'te; gerçek değer yazılmadı.

## Sıradaki iş

1. Soru 13 (geçmiş Planner kartlarının aktarımı, a–d) ve soru 14 (kart sohbetleri) cevaplanır.
2. Kullanıcı 2. bölümdeki Planner özetini onaylar.
3. Uygulama planı çıkarılır ve kullanıcıya onaya sunulur. Planda yeni bağımlılıklar (Excel okuma kütüphaneleri, Inter yazı tipi dosyası) ayrıca onaya sunulur.
4. Onaydan sonra geliştirme başlar.

Sonraya bırakılanlar: vibrohammer ve diğer ailelerin kontrol listesi şablonları (soru 22), servis takibinin ayrıntısı (soru 26, denemelerde), e-posta bildirimleri (denemelerden sonra).

## Kullanıcıdan beklenenler

- Soru 13 ve 14'ün cevapları.
- 2. bölümdeki Planner özetinin onayı.
- Sunucu yedeği kullanıcı kararıyla ertelendi. `OMS Veri` şimdilik yalnızca bu bilgisayarda; yedek klasörü seçilince `yedek-hedefi.txt` yazılır.
