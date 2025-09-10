# TODO
# numeração por pacotes
# verificar a vazão (goodput)
# forçar o numero de pacotes por segundo mesmo (50 pacotes por segundo)
# perda de pacotes no relatorio -> já tem


import argparse
import time
import uuid
import csv
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice, XBee64BitAddress

# ======================
# SERVIDOR
# ======================
def run_server(port, baudrate, num_pacotes, tempo):
    device = XBeeDevice(port, baudrate)
    device.open()
    print(f"Servidor aguardando mensagens na porta {port}...")

    session_data = {}

    def callback(xbee_message):
        try:
            data = xbee_message.data.decode(errors="ignore")
            remote = xbee_message.remote_device.get_64bit_addr()
            print(f"[DEBUG] Chegou: {data[:60]}... de {remote}")

            parts = data.split(";")
            kind = parts[0]

            if kind == "START":
                sessionID = parts[1]
                session_data[sessionID] = {
                    "enviados": num_pacotes,
                    "recebidos": 0,
                    "payload_size": 50,   # payload fixo
                    "inicio": time.time(),
                    "remote": xbee_message.remote_device
                }
                print(f"Nova sessão: {sessionID}, esperando {num_pacotes} pacotes")
                device.send_data(xbee_message.remote_device, "OK")

            elif kind == "DATA":
                sessionID = parts[1]
                if sessionID in session_data:
                    session_data[sessionID]["recebidos"] += 1

            elif kind == "END":
                sessionID = parts[1]
                if sessionID in session_data:
                    info = session_data[sessionID]
                    fim = time.time()
                    tempo_total = fim - info["inicio"]
                    enviados = info["enviados"]
                    recebidos = info["recebidos"]
                    perda = 100 * (1 - recebidos / enviados) if enviados > 0 else 0
                    goodput = (recebidos * info["payload_size"] * 8) / tempo_total / 1000
                    report = f"REPORT;{sessionID};{enviados};{recebidos};{perda:.2f};{goodput:.2f}"
                    device.send_data(info["remote"], report)
                    print(f"Relatório enviado: {report}")

        except Exception as e:
            print("Erro no callback:", e)

    device.add_data_received_callback(callback)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Servidor encerrado.")
    finally:
        device.close()

# ======================
# CLIENTE
# ======================
def run_client(port, baudrate, remote_addr, num_pacotes, tempo, csv_file):
    device = XBeeDevice(port, baudrate)
    remote = RemoteXBeeDevice(device, XBee64BitAddress.from_hex_string(remote_addr))
    device.open()
    time.sleep(2)

    sessionID = str(uuid.uuid4())[:8]
    ok_received = False
    report = None

    def client_callback(xbee_msg):
        nonlocal ok_received, report
        data = xbee_msg.data.decode(errors="ignore")
        print(f"[DEBUG] Cliente recebeu: {data}")
        if data == "OK":
            ok_received = True
        elif data.startswith("REPORT"):
            report = data

    device.add_data_received_callback(client_callback)

    # Inicia sessão
    start_msg = f"START;{sessionID}"
    device.send_data(remote, start_msg)
    print("Mensagem START enviada, aguardando OK...")

    timeout = time.time() + 5
    while not ok_received and time.time() < timeout:
        time.sleep(0.2)

    if not ok_received:
        print("Servidor não respondeu OK. Abortando.")
        device.close()
        return

    print("Servidor respondeu OK. Iniciando envio de pacotes...")
    payload = "X" * 50  # sempre 50 bytes fixos
    inicio = time.time()
    enviados = 0
    while enviados < num_pacotes and (time.time() - inicio) < tempo:
        msg = f"DATA;{sessionID};{payload}"
        device.send_data(remote, msg)
        enviados += 1

    # Finaliza sessão
    device.send_data(remote, f"END;{sessionID}")

    # Aguarda relatório
    timeout = time.time() + 10
    while report is None and time.time() < timeout:
        time.sleep(0.2)

    if report:
        print("Relatório recebido:", report)
        _, sid, enviados, recebidos, perda, goodput = report.split(";")
        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([sid, enviados, recebidos, perda, goodput])
        print(f"Relatório salvo em {csv_file}")
    else:
        print("Não recebeu relatório do servidor.")

    device.close()

# ======================
# MAIN
# ======================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XBee API mode - goodput e perda")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", help="Porta serial XBee servidor")
    group.add_argument("-c", "--client", help="Porta serial XBee cliente")
    parser.add_argument("-b", "--baudrate", type=int, default=9600)
    parser.add_argument("--remote", help="Endereço remoto XBee (cliente)")
    parser.add_argument("-n", "--num", type=int, default=100, help="Número de pacotes")
    parser.add_argument("-t", "--time", type=int, default=10, help="Tempo máximo (s)")
    parser.add_argument("--csv", default="resultados.csv", help="Arquivo CSV de saída (cliente)")
    args = parser.parse_args()

    if args.server:
        run_server(args.server, args.baudrate, args.num, args.time)
    elif args.client:
        if not args.remote:
            print("Cliente precisa do endereço remoto do servidor (--remote)")
        else:
            run_client(args.client, args.baudrate, args.remote, args.num, args.time, args.csv)