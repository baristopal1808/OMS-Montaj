# Kaldığımız yer

**21/10/2026, 15:27.** 2. adım (siparişler) bitti ve kullanıcının istekleriyle genişledi: Özet ana ekranı, teslim sütunları, Sevkiyat ve Yedek parça ekranları. Sırada küçük düzeltmeler ve 3. adım (iş emirleri) var.

## Bu oturumda yapılanlar

- 2. adım: ERP yükleme ekranı, sipariş talepleri listesinin işlenmesi, sipariş kartları.
  - ERP okuyucu (`erp_okuyucu.py`): .xls/.xlsx.
  - Eşleştirici (`erp_aktarim.py`).
  - Ürün kuralları (`urun_kurallari.py`).
- Siparişler ekranı: açık siparişler üç teslim sütununda (Gecikenler, 14 gün içinde, Daha sonra).
  - Süzgeçler ve arama var.
  - Ürün kutucuğu sipariş kartında o ailenin bölümüne gider.
- Özet (ana ekran):
  - Tıklanır sayı kutuları.
  - Makinelerin aileye ve planlama durumuna göre pastaları.
  - Tıklanır haftalık teslim takvimi.
  - Teslimi geçen ve yaklaşan siparişler tablosu.
  - Bilgisayarda kaydırmadan sığar.
  - Pasta renkleri renk körlüğü denetiminden geçti.
- Sevkiyat: çeyrek dönemlere göre sevk edilen makineler, yedek parça sevkiyatı ayrı açılır bölümde.
- Yedek parça ekranı: yedek parça siparişleri tablo olarak.
- Kurallar:
  - En son yüklenen ERP listesi gerçeği gösterir. Listede olmayan açık siparişler gizlenir, silinmez.
  - Aynı satırın iptal ve geçerli kaydı varsa geçerli olan alınır.
  - İptal edilen satırlar kartta ayrı bölümde durur.
- Görünüm: giriş ekranı, logo, yan menü, sayfa geçiş animasyonu, renkli dosya bırakma alanı.
- Süzgeçsiz sipariş listesi (`OMS Veri/erp/`) denendi: 236 sipariş; satın alınan kalemler artık listede.
- 68 otomatik test geçiyor.

## Sıradaki iş

1. Kullanıcının son istekleri:
   - OZ kodlu (dış tedarik) kalemlerde ERP "Ürün Durumu" gösterilmez.
   - Sipariş kutucukları aile rengiyle renklenir.
   - Özet tablosunda satırın tamamı tıklanır.
2. 3. adım, yavaş yavaş:
   - Açık ve kapalı iş emirlerinin yüklenmesi ve siparişe bağlanması.
   - Ürüne tıklayınca ürün sayfası: iş emri durumu, kırılımlar (tamamlanan ve bekleyen), eksik malzeme.
   - Ardından test → motor açılışı → eksper → metal etiket sırası (4. adımla birlikte).

## Kullanıcıdan beklenenler

- Yeni sürümle `baslat.bat`'ı yeniden açıp süzgeçsiz listeyi yeniden yüklemek (iptal satırı düzeltmesi için).
- Sunucu yedeği kullanıcı kararıyla ertelendi. `OMS Veri` şimdilik yalnızca bu bilgisayarda; yedek klasörü seçilince `yedek-hedefi.txt` yazılır.
