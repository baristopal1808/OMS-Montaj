"""Henüz dolmamış ekranlar ve Ayarlar. Her boş ekran, planın hangi adımında dolacağını söyler."""

from flask import Blueprint, redirect, render_template, url_for

bp = Blueprint("ekranlar", __name__)

# uç: (adres, başlık, açıklama, planın hangi adımında dolacağı)
BOS_EKRANLAR = {
    "arsiv": ("/arsiv", "Planner arşivi", "Tamamlanmış Planner kartları burada İEN, seri no ya da sipariş no ile aranacak.", 7),
}


def bos_ekran(baslik, aciklama, adim):
    def gorunum():
        return render_template("bos_ekran.html", baslik=baslik, aciklama=aciklama, adim=adim)

    return gorunum


for _uc, (_adres, _baslik, _aciklama, _adim) in BOS_EKRANLAR.items():
    bp.add_url_rule(_adres, _uc, bos_ekran(_baslik, _aciklama, _adim))


@bp.route("/pano")
def pano():
    """Pano artık Siparişler ekranıdır (Planner'daki gibi aşama sütunları; 02/11/2026)."""
    return redirect(url_for("siparisler.liste"))


@bp.route("/ayarlar")
def ayarlar():
    return render_template("ayarlar.html")
