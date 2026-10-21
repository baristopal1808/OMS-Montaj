"""Menü ve düğmelerde kullanılan çizgi simgeler (24x24, yazı rengini alır).

Şablonlarda {{ simge('pano') }} olarak kullanılır.
"""

from markupsafe import Markup

YOLLAR = {
    "siparisler": '<rect x="8" y="2" width="8" height="4" rx="1"/>'
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'
    '<path d="M12 11h4M12 16h4M8 11h.01M8 16h.01"/>',
    "pano": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 7v7M12 7v3M16 7v9"/>',
    "stok": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    "yapilacaklar": '<path d="m9 11 3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    "erp_yukleme": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>',
    "arsiv": '<rect x="2" y="3" width="20" height="5" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8M10 12h4"/>',
    "ayarlar": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "anahtar": '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6M15.5 7.5l3 3L22 7l-3-3"/>',
    "cikis": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
}


def simge(ad):
    return Markup(
        '<svg class="simge" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"'
        f' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{YOLLAR[ad]}</svg>'
    )
