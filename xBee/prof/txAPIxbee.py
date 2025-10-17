#!/usr/bin/env python3
from digi.xbee.devices import ZigBeeDevice, RemoteZigBeeDevice, XBee64BitAddress

def main(port="/dev/ttyUSB0", baud=9600, dst64="0013A20040B9701C", msg="Alo mundo"):
    dev = ZigBeeDevice(port, baud)
    try:
        dev.open()
        remote = RemoteZigBeeDevice(dev, XBee64BitAddress.from_hex_string(dst64))
        dev.send_data(remote, msg)
        print("Enviado para", dst64)
    finally:
        try: dev.close()
        except: pass

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--dst64", required=True, help="Ex.: 13A20040B9719C")
    ap.add_argument("--msg", default="Alo mundo")
    a = ap.parse_args()
    main(a.port, a.baud, a.dst64, a.msg)