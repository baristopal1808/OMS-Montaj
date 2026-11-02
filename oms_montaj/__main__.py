"""Uygulamayı bu bilgisayarda başlatır: py -m oms_montaj (baslat.bat bunu çalıştırır).

Waitress uygulamayı ağdaki diğer cihazlara da açar. Adresler ekrana yazılır;
telefon aynı şirket ağındaysa ikinci adresle açılır. Port OMS_PORT ortam
değişkeniyle değiştirilebilir.

Uygulama zaten açıksa ikinci kez açılmaz: Windows aynı portu iki programın dinlemesine izin veriyor ve
tarayıcı bazen eski sürüme bağlanıyordu (02/11/2026).
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


def acik_mi(port):
    """Bu bilgisayarda portu dinleyen bir program (uygulamanın açık bir kopyası) var mı?"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    port = int(os.environ.get("OMS_PORT", VARSAYILAN_PORT))
    if acik_mi(port):
        print(f"OMS Montaj zaten açık (http://localhost:{port}). İkinci kez açılmadı.")
        print("Yeni sürümü açmak için önce açık olan OMS Montaj penceresini kapatın, sonra baslat.bat'ı yeniden çalıştırın.")
        sys.exit(1)
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
