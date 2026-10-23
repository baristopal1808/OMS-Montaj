# Kaldığımız yer

**23/10/2026, 08:33.** 3. adımın ilk parçaları yazıldı: iş emirleri yükleniyor ve siparişe bağlanıyor; her makinenin kendi sayfası, motor seri no ve şasi no var. Sırada bağlanamayan iş emirlerinin kullanıcıya sorulması.

## Bu oturumda yapılanlar

- 2. adım tamamlandı (siparişler, Özet, sevk edilecek makineler, Sevkiyat, Yedek parça; ayrıntısı `docs/ihtiyaclar.md` Kararlar).
  - Onay bekleyen siparişler ayrı sütunda; sevk edilecek sayılara girmez.
  - Sipariş talebi revizyonları kartta görünür.
  - Seri no'suz OVF ve WD satırları makine sayılmaz.
  - Müşteri rengi ve logosu; diğer siparişlerde OMS logosu ve kırmızısı.
- 3a, ilk yarı (`is_emri_aktarim.py`):
  - Açık ve kapalı iş emirleri (tek dosyada da olur) yüklenir.
  - Siparişe kendiliğinden bağlanır: ERP bağlantısı, açıklamadaki proje kodu, alt montaj, stok.
  - İş emri açılan ürün "Malzeme hazırlık"a geçer.
  - Kırılımlar iki listeden birleşir.
- Ürün sayfası (`urunler.py`, 3b öne alındı): makinenin bilgileri, iş emri, kırılımlar (tamamlanan ve bekleyen). Ürüne tıklayınca bu sayfa, siparişe tıklayınca bütün kalemler açılır.
- Makine numaraları (`numaralar.py`):
  - Motor seri no iş emri açıklamalarından okunur.
  - Şasi no ve motor seri no ürün sayfasından elle girilir.
  - Toplu giriş için "Makine numaraları" şablonu (ERP yükleme ekranından indirilir, doldurulup yüklenir).
- Göçler 5–7: revizyonlar, iş emirleri, makine numaraları.
- Kullanıcının bir yıllık iş emri listesiyle denendi: 719 iş emri, 277'si sipariş satırına bağlandı. Bütün sayfalar hatasız açıldı.
- 89 otomatik test geçiyor.

## Sıradaki iş

1. 3a, ikinci yarı: bağlanamayan iş emirlerinin listesi; hangi siparişe ait olduğunu kullanıcı seçer (önce açık olanlar).
2. 3c: çıkış yapılamayan malzeme, "İş emri tamamlandı ama ERP'de İmalatta" uyarısı, Yapılacaklar listesi.
3. 4. adım: aşama değiştirme, kontrol listeleri, notlar ve zaman akışı, fotoğraf; eksik satır uyarısına "Kontrol ettim, satır silinmiş" düğmesi.

## Kullanıcıdan beklenenler

- `baslat.bat`'ı yeniden açıp bir yıllık iş emri Excel'ini bir kez daha yüklemek (kırılım açıklamalarındaki motor numaraları için).
- "Makine numaraları" şablonunu indirip şasi no'ları (Planner'daki "Şasi No" ve "Şanzıman (Seri) No") doldurup yüklemek.
- OVF ve WD'de şasi no mu, motor seri no mu, ikisi mi gerekli?
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
