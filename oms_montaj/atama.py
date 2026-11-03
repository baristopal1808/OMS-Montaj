"""Kartlara atanan kişiler. Şimdilik varsayılan atama (kullanıcı kararları, 21/10/2026 ve 02/11/2026): güç
ünitesi (PP) ve yarı mamulleri ekip liderine; vibro (SVR, OVR), çene, kiriş, OVF, WD, servis ve yedek parça
montaj ekibindeki iki kişiye. Kişiler Ayarlar > Kullanıcılar ekranında bir kez seçilir (varsayilan_atamalar
tablosu). Kartta baş harfleri görünür; tıklanınca pano o kişinin kartlarına süzülür. Kart kart değiştirmek
4. adımın atama parçasında gelir. Adlar git'e girmez; veritabanında durur.
"""

ATAMA_GRUPLARI = {
    "pp": "Güç ünitesi (PP) ve yarı mamulleri",
    "diger": "Vibro (SVR, OVR), çene, kiriş, OVF, WD, servis ve yedek parça",
}


# Fotoğrafı olmayan kişinin baş harflerinin zemini; kişi kendi rengini seçebilir (kullanicilar.renk)
KISI_RENKLERI = ("#2a78d6", "#1baf7a", "#6250d6", "#eb6834", "#e87ba4", "#0e7490")


def kisi_rengi(kullanici):
    return kullanici["renk"] or KISI_RENKLERI[kullanici["id"] % len(KISI_RENKLERI)]


def kisi(kullanici):
    """Kartlarda ve menüde gösterilen kişi: {"id", "ad", "harf", "renk", "fotograf"}."""
    return {"id": kullanici["id"], "ad": kullanici["ad_soyad"], "harf": bas_harfleri(kullanici["ad_soyad"]),
            "renk": kisi_rengi(kullanici), "fotograf": kullanici["fotograf"]}


def atama_grubu(aile):
    return "pp" if aile == "PP" else "diger"


def varsayilan_atananlar(vt):
    """{grup: [kullanıcı satırı (id, ad_soyad, renk, fotograf)]}; yalnızca etkin hesaplar, ada göre."""
    sonuc = {grup: [] for grup in ATAMA_GRUPLARI}
    for r in vt.execute(
        "SELECT a.grup, k.id, k.ad_soyad, k.renk, k.fotograf FROM varsayilan_atamalar a"
        " JOIN kullanicilar k ON k.id = a.kullanici_id WHERE k.aktif = 1 ORDER BY k.ad_soyad COLLATE NOCASE"
    ):
        sonuc.setdefault(r["grup"], []).append(r)
    return sonuc


def varsayilan_atamayi_kaydet(vt, secimler):
    """secimler: {grup: [kullanıcı id]}"""
    vt.execute("DELETE FROM varsayilan_atamalar")
    vt.executemany(
        "INSERT INTO varsayilan_atamalar (grup, kullanici_id) VALUES (?, ?)",
        [(grup, kid) for grup, idler in secimler.items() if grup in ATAMA_GRUPLARI for kid in idler],
    )


def bas_harfleri(ad_soyad):
    """'TEST KULLANICI' → 'TK'; tek kelimeyse ilk iki harf."""
    kelimeler = (ad_soyad or "").split()
    if not kelimeler:
        return "?"
    if len(kelimeler) == 1:
        return kelimeler[0][:2].upper()
    return (kelimeler[0][0] + kelimeler[-1][0]).upper()
