"""Ekranda gösterim biçimleri; şablonlarda süzgeç olarak kullanılır: {{ tarih | tarih }}."""

from datetime import date, datetime


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


SUZGECLER = {"tarih": tarih, "zaman": zaman, "sayi": sayi}
