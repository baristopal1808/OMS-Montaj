# Kaldığımız yer

**23/10/2026, 10:26.** 3. adım sürüyor. İş emirleri, ürün sayfası, makine numaraları, sipariş durumu özeti ve PP'ye takılan kalemlerin montaj durumu yazıldı. Yapay zekâ asistanı denemesi (Claude Haiku 5.5, uydurma veriyle) hazır; kullanıcının API anahtarı alması bekleniyor. Sırada bağlanamayan iş emirlerinin sorulması var.

## Bu oturumda yapılanlar

- 2. adım tamamlandı (siparişler, Özet, sevk edilecek makineler, Sevkiyat, Yedek parça; ayrıntısı `docs/ihtiyaclar.md` Kararlar).
- 3a, ilk yarı (`is_emri_aktarim.py`):
  - Açık ve kapalı iş emirleri (tek dosyada da olur) yüklenir.
  - Siparişe kendiliğinden bağlanır.
  - İş emri açılan ürün "Malzeme hazırlık"a geçer.
  - ERP'nin kapanış notu açıklamadan silinir.
- Ürün sayfası (`urunler.py`): makinenin bilgileri, iş emri (durumuna göre yeşil, sarı ya da soluk kırmızı), kırılımlar.
- Makine numaraları (`numaralar.py`):
  - Motor seri no iş emri açıklamasından okunur (Volvo 4+3+4 ve 4+3+3, CAT).
  - Şasi no ve motor seri no elle ya da "Makine numaraları" şablonuyla girilir.
  - Yalnızca SVR, OVR, PP için.
- Sipariş kartında ve ürün sayfasında "Siparişin durumu" kutusu; durumlar tıklanınca sipariş kartı yalnızca o kalemlerle açılır. Ürünlerin solunda iş emri durumu şeridi.
- PP'ye takılan kalemler (kablosuz kumanda seti, uzaktan erişim modülü): montaj durumu seçilir.
- Göçler 5–8.
- Kullanıcının bir yıllık iş emri listesiyle denendi; 591 sayfa hatasız açılıyor.
- 93 otomatik test geçiyor.

## Sıradaki iş

1. Yapay zekâ asistanı denemesi: `asistan-deneme.bat` ile uydurma veriyle denenir (anahtar gelince). Kullanıcı beğenirse gerçek veriye geçiş ve şirket onayı konuşulur.
2. 3a, ikinci yarı: bağlanamayan iş emirlerinin listesi; hangi siparişe ait olduğunu kullanıcı seçer.
3. 3c: çıkış yapılamayan malzeme, "İş emri tamamlandı ama ERP'de İmalatta" uyarısı, Yapılacaklar listesi.
4. 4. adım: aşama değiştirme, kontrol listeleri, notlar ve zaman akışı, fotoğraf; eksik satır uyarısına "Kontrol ettim, satır silinmiş" düğmesi.
5. ERP'den canlı veri (API, 15 dakikada bir): ERP sorumlusundan adres, belge ve salt okunur erişim gelince.

## Kullanıcıdan beklenenler

- Asistan denemesi için: Anthropic API anahtarı (console.anthropic.com), `OMS Veri\anthropic-anahtar.txt` dosyasına yazılır.
- `baslat.bat`'ı yeniden açıp iş emri Excel'ini bir kez daha yüklemek (açıklamalar temizlenir, motor numaraları yeniden okunur).
- "Makine numaraları" şablonunu doldurup yüklemek (şasi no'lar).
- ERP sorumlusundan: API adresi ve belgesi, salt okunur kullanıcı, hazır görünümlerin adları.
- Sunucu yedeği kullanıcı kararıyla bekliyor; `OMS Veri` şimdilik yalnızca bu bilgisayarda.
