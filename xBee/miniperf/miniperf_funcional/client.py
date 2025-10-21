# client.py
import csv
import time
import sys
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice, XBee64BitAddress
from session import load_session_counter, save_session_counter
from utils import CSV_FILE, BAUD_RATE

def run_client(port, remote_addr, num_pacotes, max_tempo, packets_per_second, baud_rate=BAUD_RATE, csv_file=CSV_FILE):
    session_counter = load_session_counter() + 1
    save_session_counter(session_counter)
    sessionID = str(session_counter)
    print(f"Iniciando sessão #{sessionID}")

    device = XBeeDevice(port, baud_rate)
    device.open()
    remote = RemoteXBeeDevice(device, XBee64BitAddress.from_hex_string(remote_addr))

    ok_received = False
    report_str = None

    def client_callback(msg):
        nonlocal ok_received, report_str
        data = msg.data.decode(errors="ignore")
        if data == "OK":
            ok_received = True
        elif data.startswith("REPORT"):
            report_str = data

    device.add_data_received_callback(client_callback)

    start_msg = f"START;{sessionID};{num_pacotes}"
    device.send_data(remote, start_msg)
    print("START enviado, aguardando OK...")

    wait_until = time.time() + 5
    while not ok_received and time.time() < wait_until:
        time.sleep(0.1)

    if not ok_received:
        print("Servidor não respondeu OK. Abortando.")
        device.close()
        return

    payload = "X" * 50
    seq = 0
    enviados = 0
    inicio = time.time()
    interval = 1.0 / packets_per_second if packets_per_second else 0

    next_send = time.time()
    while enviados < num_pacotes:
        seq += 1
        msg = f"DATA;{sessionID};{seq};{payload}"
        device.send_data(remote, msg)
        enviados += 1

        next_send += interval
        delay = next_send - time.time()
        if delay > 0:
            time.sleep(delay)


    device.send_data(remote, f"END;{sessionID}")
    print(f"Enviados {enviados} pacotes. Aguardando REPORT...")

    timeout = time.time() + 10
    while report_str is None and time.time() < timeout:
        time.sleep(0.1)

    if report_str:
        print("Relatório recebido:", report_str)
        parts = report_str.split(";")
        if len(parts) == 8:
            _, sid, enviados_cli, unicos, total, duplicados, perda, goodput = parts
            write_header = not os.path.exists(csv_file)
            with open(csv_file, "a", newline="") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["SessionID", "EnviadosCliente", "UnicosRecebidos",
                                     "TotalRecebidos", "Duplicados", "Perda(%)", "Goodput(kbps)"])
                writer.writerow([sid, enviados_cli, unicos, total, duplicados, perda, goodput])
            print(f"Relatório salvo em {csv_file}")
    else:
        print("Timeout aguardando REPORT.")

    device.close()
    sys.exit(0)