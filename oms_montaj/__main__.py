"""Uygulamayı bu bilgisayarda başlatır: py -m oms_montaj (baslat.bat bunu çalıştırır).

Waitress uygulamayı ağdaki diğer cihazlara da açar. Adresler ekrana yazılır;
telefon aynı şirket ağındaysa ikinci adresle açılır. Port OMS_PORT ortam
değişkeniyle değiştirilebilir.
"""

import os
import socket
import sys

from waitress import serve

from . import uygulama_olustur

VARSAYILAN_PORT = 8090


def ag_adresi():
    """Bu bilgisayarın şirket ağındaki adresi; bulunamazsa None."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as soket:
            # Paket gönderilmez; yalnızca ağa çıkan bağlantının adresi öğrenilir.
            soket.connect(("10.255.255.255", 1))
            return soket.getsockname()[0]
    except OSError:
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    port = int(os.environ.get("OMS_PORT", VARSAYILAN_PORT))
    uygulama = uygulama_olustur()
    print("OMS Montaj çalışıyor. Kapatmak için bu pencereyi kapatın.")
    print(f"  Bu bilgisayarda:         http://localhost:{port}")
    adres = ag_adresi()
    if adres:
        print(f"  Telefonda (şirket ağı):  http://{adres}:{port}")
    print(f"  Veri klasörü: {uygulama.config['VERI_KLASORU']}")
    serve(uygulama, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
