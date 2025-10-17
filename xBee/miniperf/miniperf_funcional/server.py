# server.py
import time
from digi.xbee.devices import XBeeDevice
from utils import BAUD_RATE

def run_server(port, num_pacotes_fallback, baud_rate=BAUD_RATE):
    device = XBeeDevice(port, baud_rate)
    device.open()
    print(f"Servidor aguardando mensagens na porta {port}... (baud {baud_rate})")

    session_data = {}

    def callback(xbee_message):
        try:
            data = xbee_message.data.decode(errors="ignore")
            remote = xbee_message.remote_device.get_64bit_addr()
            parts = data.split(";")
            if len(parts) < 2:
                print(f"[WARN] Mensagem inválida: {data}")
                return

            kind = parts[0]

            if kind == "START":
                sessionID = parts[1]
                expected = int(parts[2]) if len(parts) > 2 else num_pacotes_fallback
                session_data[sessionID] = {
                    "enviados_pelo_cliente": expected,
                    "recebidos_total": 0,
                    "unique_seqs": set(),
                    "payload_size": 50,
                    "inicio": time.time(),
                    "remote": xbee_message.remote_device
                }
                print(f"Nova sessão: {sessionID}, esperando {expected} pacotes")
                device.send_data(xbee_message.remote_device, "OK")

            elif kind == "DATA":
                if len(parts) < 3:
                    return
                sessionID, seq_num = parts[1], int(parts[2])
                info = session_data.get(sessionID)
                if info is None:
                    print(f"[{sessionID}] DATA para sessão desconhecida.")
                    return

                info["recebidos_total"] += 1
                info["unique_seqs"].add(seq_num)

            elif kind == "END":
                sessionID = parts[1]
                info = session_data.get(sessionID)
                if not info:
                    return

                fim = time.time()
                duracao = fim - info["inicio"]
                enviados = info["enviados_pelo_cliente"]
                unicos = len(info["unique_seqs"])
                duplicados = info["recebidos_total"] - unicos
                perda_pct = 100 * (1 - (unicos / enviados)) if enviados > 0 else 0
                goodput_kbps = ((unicos * info["payload_size"] * 8) / duracao) / 1000 if duracao > 0 else 0

                report = f"REPORT;{sessionID};{enviados};{unicos};{info['recebidos_total']};{duplicados};{perda_pct:.2f};{goodput_kbps:.2f}"
                device.send_data(info["remote"], report)
                print(f"Relatório enviado: {report}")
                del session_data[sessionID]

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