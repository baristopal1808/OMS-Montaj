"""Ekranda gösterim biçimleri; şablonlarda süzgeç olarak kullanılır: {{ tarih | tarih }}."""

import re
from datetime import date, datetime

from markupsafe import Markup, escape


def tarih(deger):
    """'2026-11-03' ya da tarih nesnesi → '03/11/2026'."""
    if not deger:
        return ""
    if isinstance(deger, str):
        try:
            deger = date.fromisoformat(deger[:10])
        except ValueError:
            return deger
    return deger.strftime("%d/%m/%Y")


def zaman(deger):
    """'2026-10-21 11:40:05' → '21/10/2026 11:40'."""
    if not deger:
        return ""
    try:
        return datetime.fromisoformat(str(deger)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return str(deger)


def sayi(deger):
    """1.0 → '1', 2.5 → '2,5'."""
    if deger is None:
        return ""
    if float(deger).is_integer():
        return str(int(deger))
    return f"{deger:g}".replace(".", ",")


def asistan_metni(metin):
    """Asistan cevabındaki basit Markdown: **kalın**, "- " ile başlayan maddeler, # başlıklar; gerisi paragraf.
    Metin önce HTML'den arındırılır, yalnızca bu birkaç biçim etikete çevrilir."""
    html, liste = [], False
    for satir in str(escape(metin or "")).split("\n"):
        satir = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", satir)
        madde = re.match(r"\s*[-•*]\s+(.*)", satir)
        if madde:
            html.append(("" if liste else "<ul>") + f"<li>{madde.group(1)}</li>")
            liste = True
            continue
        if liste:
            html.append("</ul>")
            liste = False
        baslik = re.match(r"\s*#{1,6}\s+(.*)", satir)
        if baslik:
            html.append(f"<p><strong>{baslik.group(1)}</strong></p>")
        elif satir.strip():
            html.append(f"<p>{satir}</p>")
    if liste:
        html.append("</ul>")
    return Markup("".join(html))


SUZGECLER = {"tarih": tarih, "zaman": zaman, "sayi": sayi, "asistan_metni": asistan_metni}
