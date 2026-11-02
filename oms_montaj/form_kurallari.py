"""Montaj formlarının aşama kuralı (kullanıcı kararları, 02/11/2026).

Güç ünitesinde (PP) dört form basılır: Montaj aşamasında proje takip kartı (eski adıyla proje kodlaması) ve
test öncesi kontrol formu, Teste hazır aşamasında test formu, Temizlik aşamasında kurulum formu (setup list).
Form basılmadan ürün sonraki aşamaya geçmez: proje takip kartı ve test öncesi kontrol formu olmadan "Montaj
tamamlandı"ya, test formu olmadan "Test"e, kurulum formu olmadan "Sevke hazır"a. Kural hem ekibin aşama değişikliğinde hem ERP yüklemesinde
geçerlidir: iş emri ERP'de tamamlansa da ürün Montaj'da bekler; formlar basılınca ERP'nin gösterdiği aşamaya
kendiliğinden geçer. Kural başladığında Montaj tamamlandı ya da daha ileri aşamada olan ürünler muaftır
(urunler.form_muaf). Servis kartları kurala girmez.
"""

from .asamalar import ASAMALAR, SIRA, ileri

FORM_TURLERI = {
    "kodlama": "Proje takip kartı",
    "test_oncesi": "Test öncesi kontrol formu",
    "test": "Test formu",
    "kurulum": "Kurulum formu (setup list)",
}
# Ürün sayfasında aşama kutusundaki çıktı düğmelerinin adları
KISA_ADLAR = {"kodlama": "Proje takip kartı", "test_oncesi": "Test öncesi formu", "test": "Test formu", "kurulum": "Kurulum formu"}
# Formun basıldığı aşama
FORM_ASAMALARI = {"kodlama": "montaj", "test_oncesi": "montaj", "test": "teste_hazir", "kurulum": "temizlik"}
# Aşamaya geçmeden önce basılması gereken formlar, aşama sırasıyla
GECIS_FORMLARI = (
    ("montaj_tamamlandi", ("kodlama", "test_oncesi")),
    ("test", ("test",)),
    ("sevke_hazir", ("kurulum",)),
)
FORMLU_AILELER = ("PP",)


def forma_tabi_mi(urun):
    """urun: aile, tur (sipariş satırının türü) ve form_muaf alanları olan bir satır."""
    return urun["aile"] in FORMLU_AILELER and urun["tur"] == "kart" and not urun["form_muaf"]


def basilan_formlar(vt, urun_idleri=None):
    """{ürün id: {form türü, …}}; urun_idleri verilmezse bütün ürünler."""
    sorgu, degerler = "SELECT DISTINCT urun_id, tur FROM urun_formlari", ()
    if urun_idleri is not None:
        idler = list(urun_idleri)
        if not idler:
            return {}
        sorgu += f" WHERE urun_id IN ({', '.join('?' * len(idler))})"
        degerler = idler
    sonuc = {}
    for r in vt.execute(sorgu, degerler):
        sonuc.setdefault(r["urun_id"], set()).add(r["tur"])
    return sonuc


def eksik_formlar(basilan, hedef):
    """Ürünün hedef aşamaya geçmesi için basılması gereken ama basılmamış formlar, sırasıyla."""
    if hedef == "stokta":
        return []
    return [tur for asama, turler in GECIS_FORMLARI if SIRA[asama] <= SIRA[hedef] for tur in turler if tur not in basilan]


def asama_siniri(basilan):
    """Formlar basılmadığı için ürünün geçemeyeceği ilk aşamadan önceki aşama; sınır yoksa None."""
    for asama, turler in GECIS_FORMLARI:
        if any(tur not in basilan for tur in turler):
            return next(a for a, i in SIRA.items() if i == SIRA[asama] - 1)
    return None


def sinirla(hedef, basilan):
    """ERP'nin gösterdiği aşamayı formların izin verdiği aşamayla sınırlar."""
    sinir = asama_siniri(basilan)
    return sinir if sinir and hedef != "stokta" and SIRA[hedef] > SIRA[sinir] else hedef


def urun_formlari(vt, urun_id):
    """Ürünün basılan formları, yeniden eskiye."""
    return vt.execute(
        "SELECT f.*, k.ad_soyad FROM urun_formlari f LEFT JOIN kullanicilar k ON k.id = f.kullanici_id"
        " WHERE f.urun_id = ? ORDER BY f.id DESC",
        (urun_id,),
    ).fetchall()


def form_durumlari(vt, urun):
    """Ürün sayfasının aşama kutusundaki çıktılar: [{"tur", "ad", "kisa", "asama", "son"}] ve ERP'nin ilerisini
    gösterdiği ama formlar basılmadığı için beklenen aşama (yoksa None)."""
    formlar = urun_formlari(vt, urun["id"])
    durumlar = [{"tur": tur, "ad": ad, "kisa": KISA_ADLAR[tur], "asama": ASAMALAR[FORM_ASAMALARI[tur]],
                 "son": next((f for f in formlar if f["tur"] == tur), None)} for tur, ad in FORM_TURLERI.items()]
    bekleyen = None
    if forma_tabi_mi(urun) and urun["erp_asama"]:
        hedef = ileri(urun["asama"], urun["erp_asama"])
        if hedef != urun["asama"] and sinirla(hedef, {f["tur"] for f in formlar}) != hedef:
            bekleyen = hedef
    return durumlar, bekleyen
