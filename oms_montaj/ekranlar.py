"""Ana ekranlar. Planın 1. adımında yalnızca iskelet: her ekran hangi adımda dolacağını söyler."""

from flask import Blueprint, render_template

bp = Blueprint("ekranlar", __name__)

# uç: (adres, başlık, açıklama, planın hangi adımında dolacağı)
BOS_EKRANLAR = {
    "siparisler": (
        "/",
        "Siparişler",
        "ERP'nin sipariş talepleri listesi yüklenince açık siparişler burada, teslim tarihine göre sıralanır.",
        2,
    ),
    "pano": ("/pano", "Pano", "Ürünler bulundukları aşamanın sütununda görünecek.", 4),
    "stok": ("/stok", "Stok", "Siparişe bağlanmamış ürünler, depoları ve test durumlarıyla burada listelenecek.", 5),
    "yapilacaklar": (
        "/yapilacaklar",
        "Yapılacaklar",
        "Uygulamanın size soracağı her şey burada toplanacak: bağlanamayan iş emirleri, test soruları, sevk onayları.",
        3,
    ),
    "erp_yukleme": ("/erp-yukleme", "ERP yükleme", "ERP'den aldığınız Excel listelerini buradan yükleyeceksiniz.", 2),
    "arsiv": ("/arsiv", "Planner arşivi", "Tamamlanmış Planner kartları burada İEN, seri no ya da sipariş no ile aranacak.", 7),
}


def bos_ekran(baslik, aciklama, adim):
    def gorunum():
        return render_template("bos_ekran.html", baslik=baslik, aciklama=aciklama, adim=adim)

    return gorunum


for _uc, (_adres, _baslik, _aciklama, _adim) in BOS_EKRANLAR.items():
    bp.add_url_rule(_adres, _uc, bos_ekran(_baslik, _aciklama, _adim))


@bp.route("/ayarlar")
def ayarlar():
    return render_template("ayarlar.html")
