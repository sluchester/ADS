#!/usr/bin/env python3
# rx_xbee_rssi.py — RX via digi-xbee com RSSI (ATDB)
from digi.xbee.devices import ZigBeeDevice
import time

def main(port="/dev/ttyUSB0", baud=9600):
    dev = ZigBeeDevice(port, baud)
    try:
        dev.open()
        print(f"RX em {port} @ {baud} usando digi-xbee")
        while True:
            msg = dev.read_data(timeout=10)   # XBeeMessage ou None
            if msg is None:
                continue
            src64 = msg.remote_device.get_64bit_addr()
            data  = msg.data
            try:
                txt = data.decode("utf-8","ignore")
            except:
                txt = ""
            # RSSI do último pacote bom
            db = dev.get_parameter("DB")  # bytes, p.ex. b'\x2C' -> -44 dBm
            rssi = -db[0] if (db and len(db)>=1) else None
            if rssi is not None:
                print(f"[{time.strftime('%H:%M:%S')}] RX de {src64}: '{txt}' | RSSI={rssi} dBm | {data.hex().upper()}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] RX de {src64}: '{txt}' | RSSI=? | {data.hex().upper()}")
    finally:
        try: dev.close()
        except: pass

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=9600)
    a = ap.parse_args()
    main(a.port, a.baud)
