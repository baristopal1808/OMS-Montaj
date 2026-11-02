# Kaldığımız yer

**02/11/2026, 14:40.** 4. adımın ilk parçası (aşama, notlar, zaman akışı) ve güç ünitesinin montaj çıktıları (proje takip kartı, test öncesi kontrol, test ve kurulum formu) yapıldı; kullanıcının denemesini bekliyor. Sırada Siparişler ekranındaki güncelleme var (kullanıcı anlatacak).

## Bu oturumda yapılanlar

- Yarı mamuller:
  - Montajda yapılanlar artık "imalattan bekleniyor" sayılmıyor. Durum ERP'den okunuyor: üreten kırılım, stok girişi, depodaki miktar. Ekip "Hazır" işaretleyebiliyor.
  - Rotaya göre ayrım: rotası olan "İmalattan bekleniyor", rotası olmayan "Montajı bekliyor" (göç 15). Rota, çıkış yapılamayan malzeme raporu yeniden yüklenince görünür.
- Motor seri no teyidi: ERP'den okunan numarada "!" görünüyor; kutucuk işaretlenip teyit edilince nihai numara oluyor.
- 4. adım, 1. parça:
  - Aşama ileri ve geri alınabiliyor; geri alırken sebep zorunlu.
  - Notlar yazılıyor; yazan düzeltebiliyor, not silinmiyor.
  - Zaman akışında ERP geçmişi de var. Ürün sayfasında notlar ve akış sağ sütunda (göç 14).
  - Sipariş kartında "Kontrol ettim, satır silinmiş" düğmesi var.
- Montaj çıktıları (güç ünitesi):
  - Aşama kutusunun sağ altındaki düğmelerle çıkarılıyor; alınmamış gri, alınmış yeşil.
  - Şablonlar `OMS Veri/uygulama/formlar/` klasöründe; uygulama dosya adından tanıyor, bilgileri etiketlerin yanına yazıyor.
  - PDF'i Excel çıkarıyor (sunucuda LibreOffice olacak).
  - Proje takip kartı uygulamanın kendi tasarımı: Arial, A4 yatay, yağ satırı var.
  - Motor bilgisi ürün koduna göre bir kez giriliyor. Motor seri no teyit edilmeden çıktı alınmıyor.
  - Çıktı alınmadan ürün sonraki aşamaya geçmiyor (ERP yüklemesinde de). Kural başladığında Montaj tamamlandı ya da ilerisindeki ürünler muaf.
- Uygulama artık iki kez açılmıyor (bilgisayarda eski ve yeni sürüm aynı anda açıktı).
- 132 otomatik test geçiyor; gerçek verinin kopyasında 1.468 sayfa (form ekranları dahil) hatasız açılıyor.

## Sıradaki iş

1. Siparişler ekranında güncelleme: kullanıcı ne istediğini anlatacak.
2. Kullanıcının denemesi: `baslat.bat` tek kopya açılmalı. Çıktı düğmeleri, ilk proje takip kartı (motor bilgisi girişi), test öncesi formu ve aşama kuralı denenir. Çıkış yapılamayan malzeme raporu yeniden yüklenir, rota ayrımı görülür.
3. 4. adımın kalan parçaları, her biri önce sorularla: (2) kontrol listesi ve PP şablonu, (3) fotoğraf, (4) atama ve etiketler, (5) pano.
4. SVR ve OVR formları (test formu ve montaj öncesi kalite kontrol formları): kullanıcı hazır olunca.
5. Yapılacaklar'ın sadeleştirilmesi: kullanıcıya hâlâ karışık geliyor; ayrı bir çalışma yapılacak.
6. ERP'den canlı veri (API, 15 dakikada bir): ERP sorumlusundan adres, belge ve salt okunur erişim gelince.

## Kullanıcıdan beklenenler

- Yeni ekranları denemek; proje takip kartının son hâlini onaylamak (örnekler `OMS Veri/taslaklar/`).
- PP-908'in test öncesi kontrol formunu ve 9XX test formunu hazırlanınca `OMS Veri/uygulama/formlar/` klasörüne koymak; o zamana kadar PP-908'de çıktı alınamaz.
- ERP'deki hatalı ve boş yarı mamul rotalarını güncellemek.
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar; iki motorlu PP'lerde ikinci motor).
- Asistan: Anthropic'in iade cevabı gelince denemeye karar vermek.
- ERP sorumlusundan: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
