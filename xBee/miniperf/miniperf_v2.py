#!/usr/bin/env python3
import argparse
import time
import uuid
import csv
import os
import sys
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice, XBee64BitAddress

# Apenas estas duas variáveis são fixas conforme solicitado:
# BAUD_RATE = 115200
# CSV_FILE = "relatorio.csv"

dev = XBeeDevice("/dev/ttyUSB0", 115200)
dev.open()
print(dev.get_64bit_addr())
dev.close()


SESSION_COUNTER_FILE = "session_counter.txt"

def load_session_counter() -> int:
    if os.path.exists(SESSION_COUNTER_FILE):
        try:
            with open(SESSION_COUNTER_FILE, "r") as f:
                return int(f.read().strip())
        except Exception:
            return 0
    return 0

def save_session_counter(v: int) -> None:
    try:
        with open(SESSION_COUNTER_FILE, "w") as f:
            f.write(str(int(v)))
    except Exception as e:
        print("Erro ao salvar session counter:", e)

# inicializa global (cliente usará e incrementará)
session_counter = load_session_counter()

# ======================
# SERVIDOR
# ======================
def run_server(port, num_pacotes_fallback, BAUD_RATE):
    """
    Servidor: aguarda START, contabiliza DATA (com seq), computa unicos/duplicados no END
    num_pacotes_fallback: usado se cliente NÃO enviar o número esperado no START
    """
    device = XBeeDevice(port, BAUD_RATE)
    device.open()
    print(f"Servidor aguardando mensagens na porta {port}... (baud {BAUD_RATE})")

    session_data = {}  # sessionID (str) -> info dict

    def callback(xbee_message):
        try:
            data = xbee_message.data.decode(errors="ignore")
            remote = xbee_message.remote_device.get_64bit_addr()
            # print(f"[DEBUG] Chegou: {data[:120]} de {remote}")

            parts = data.split(";")
            if len(parts) < 2:
                print(f"[WARN] Mensagem com formato inesperado: {data}")
                return

            kind = parts[0]

            if kind == "START":
                sessionID = parts[1]
                if len(parts) > 2:
                    try:
                        expected = int(parts[2])
                    except Exception:
                        expected = num_pacotes_fallback
                else:
                    expected = num_pacotes_fallback

                session_data[sessionID] = {
                    "enviados_pelo_cliente": expected,   # número que o cliente disse que enviaria
                    "recebidos_total": 0,               # inclui duplicados
                    "unique_seqs": set(),               # seqs únicos recebidos
                    "payload_size": 50,                 # payload fixo
                    "inicio": time.time(),
                    "remote": xbee_message.remote_device
                }
                print(f"Nova sessão: {sessionID}, esperando {expected} pacotes")
                # responde OK para o cliente
                device.send_data(xbee_message.remote_device, "OK")

            elif kind == "DATA":
                # espera: DATA;sessionID;seq_num;payload
                if len(parts) < 3:
                    print(f"[WARN] DATA com formato inválido: {data}")
                    return

                sessionID = parts[1]
                try:
                    seq_num = int(parts[2])
                except Exception:
                    print(f"[{sessionID}] seq inválido em DATA: {parts[2]}")
                    return

                info = session_data.get(sessionID)
                if info is None:
                    print(f"[{sessionID}] Erro: Pacote DATA recebido para sessão desconhecida. Ignorando: {data}")
                    return

                # contabiliza total (inclui duplicados)
                info["recebidos_total"] += 1

                # adiciona ao set de únicos (ignora duplicado para contagem única)
                if seq_num not in info["unique_seqs"]:
                    info["unique_seqs"].add(seq_num)
                    # opcional: log de pacote único
                    # print(f"[{sessionID}] Pacote único {seq_num} recebido. Únicos={len(info['unique_seqs'])}")
                else:
                    # contabilizou como duplicado (já refletido em recebidos_total - len(unique_seqs))
                    # podemos logar duplicado se quiser:
                    # print(f"[{sessionID}] Pacote duplicado {seq_num} recebido.")
                    pass

            elif kind == "END":
                sessionID = parts[1]
                info = session_data.get(sessionID)
                if not info:
                    print(f"[{sessionID}] END para sessão desconhecida. Ignorando.")
                    return

                fim = time.time()
                duracao = fim - info["inicio"] if info["inicio"] else 0.000001

                enviados = info["enviados_pelo_cliente"]
                recebidos_total = info["recebidos_total"]            # inclui duplicados
                unicos = len(info["unique_seqs"])                    # únicos reais
                duplicados = recebidos_total - unicos
                perda_pct = 100 * (1 - (unicos / enviados)) if enviados > 0 else 0.0
                # goodput: apenas dados úteis (únicos) em kb/s
                goodput_kbps = ((unicos * info["payload_size"] * 8) / duracao) / 1000 if duracao > 0 else 0.0

                # FORMATO DO REPORT: mantivemos compatibilidade estendida:
                # REPORT;sessionID;enviados_cliente;unicos_recebidos;recebidos_total;duplicados;perda_pct;goodput_kbps
                report = f"REPORT;{sessionID};{enviados};{unicos};{recebidos_total};{duplicados};{perda_pct:.2f};{goodput_kbps:.2f}"
                device.send_data(info["remote"], report)
                print(f"Relatório enviado: {report}")

                # opcional: salvar local do servidor (não solicitado) OMITIDO; só limpamos a sessão
                del session_data[sessionID]

            else:
                # outros comandos ignorados
                print(f"[DEBUG] Comando desconhecido recebido: {kind}")

        except Exception as e:
            # cuidado: 'remote' e 'data' podem não existir se falhar antes; proteja-se
            try:
                print(f"Erro no callback de {remote} (mensagem: {data}):", e)
            except Exception:
                print("Erro no callback (dados incompletos):", e)

    device.add_data_received_callback(callback)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Servidor encerrado pelo usuário.")
    finally:
        device.close()

# ======================
# CLIENTE
# ======================
def run_client(port, remote_addr, num_pacotes, max_tempo, packets_per_second, BAUD_RATE, CSV_FILE):
    """
    Cliente: incrementa contador de session (persistente), envia START,
    envia DATA numerados, envia END, aguarda REPORT e salva CSV (CSV_FILE).
    """
    global session_counter
    session_counter += 1
    try:
        save_session_counter(session_counter)
    except Exception as e:
        print("Aviso: não foi possível persistir session counter:", e)

    sessionID = str(session_counter)
    print(f"Iniciando sessão #{sessionID}")

    device = XBeeDevice(port, BAUD_RATE)
    device.open()
    # cria remote após open (boa prática)
    remote = RemoteXBeeDevice(device, XBee64BitAddress.from_hex_string(remote_addr))

    ok_received = False
    report_str = None

    def client_callback(xbee_msg):
        nonlocal ok_received, report_str
        try:
            d = xbee_msg.data.decode(errors="ignore")
        except Exception:
            return
        # print(f"[DEBUG client] recebido: {d}")
        if d == "OK":
            ok_received = True
        elif d.startswith("REPORT"):
            report_str = d

    device.add_data_received_callback(client_callback)

    # envia START;sessionID;num_pacotes
    start_msg = f"START;{sessionID};{num_pacotes}"
    device.send_data(remote, start_msg)
    print("START enviado, aguardando OK...")

    # aguarda OK com timeout
    wait_until = time.time() + 5
    while not ok_received and time.time() < wait_until:
        time.sleep(0.05)

    if not ok_received:
        print("Servidor não respondeu OK. Abortando.")
        device.close()
        return

    print("Servidor respondeu OK. Iniciando envio de pacotes...")

    payload = "X" * 50  # payload fixo 50 bytes
    seq = 0
    enviados = 0
    inicio = time.time()

    if packets_per_second and packets_per_second > 0:
        interval = 1.0 / packets_per_second
        next_send = time.time() + interval
    else:
        interval = 0
        next_send = 0

    while enviados < num_pacotes and (time.time() - inicio) < max_tempo:
        seq += 1
        # DATA;sessionID;seq;payload
        msg = f"DATA;{sessionID};{seq};{payload}"
        device.send_data(remote, msg)
        enviados += 1

        if interval > 0:
            now = time.time()
            if now < next_send:
                time.sleep(next_send - now)
            next_send += interval

    # envia END
    device.send_data(remote, f"END;{sessionID}")
    print(f"Envio concluído: {enviados} pacotes enviados. Aguardando relatório...")

    # aguarda REPORT
    timeout = time.time() + 10
    while report_str is None and time.time() < timeout:
        time.sleep(0.1)

    if report_str:
        print("Relatório recebido:", report_str)
        parts = report_str.split(";")
        # esperamos 8 campos: REPORT;sid;enviados;unicos;recebidos_total;duplicados;perda;goodput
        if len(parts) == 8:
            _, sid, enviados_cli, unicos_str, recebidos_total_str, duplicados_str, perda_str, goodput_str = parts
            # salva no CSV (arquivo fixo CSV_FILE)
            write_header = not os.path.exists(CSV_FILE)
            try:
                with open(CSV_FILE, "a", newline="") as f:
                    writer = csv.writer(f)
                    if write_header:
                        writer.writerow(["SessionID", "EnviadosCliente", "UnicosRecebidos",
                                         "TotalRecebidos", "Duplicados", "Perda(%)", "Goodput(kbps)"])
                    writer.writerow([sid, enviados_cli, unicos_str, recebidos_total_str, duplicados_str, perda_str, goodput_str])
                print(f"Relatório salvo em {CSV_FILE}")
            except Exception as e:
                print("Erro ao salvar CSV:", e)
        else:
            print("Formato de REPORT inesperado. Salvando linha bruta no CSV.")
            try:
                with open(CSV_FILE, "a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([report_str])
            except Exception as e:
                print("Erro ao salvar CSV (formato inesperado):", e)
    else:
        print("Não recebeu REPORT dentro do timeout.")

    device.close()
    sys.exit(0)

# ======================
# MAIN
# ======================
# Exemplo de modificação sugerida
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="miniperf XBee (numeração + duplicados)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", help="Porta serial do XBee para rodar servidor (ex: /dev/ttyUSB0)")
    group.add_argument("-c", "--client", help="Porta serial do XBee para rodar cliente (ex: /dev/ttyUSB1)")
    
    # Argumentos adicionados
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate da porta serial (padrão: 115200)")
    parser.add_argument("--csv", default="relatorio.csv", help="Nome do arquivo CSV para salvar o relatório (padrão: relatorio.csv)")

    parser.add_argument("--remote", help="Endereço 64-bit do XBee remoto (necessário no modo client)")
    parser.add_argument("-n", "--num", type=int, default=100, help="Número de pacotes a enviar (cliente)")
    parser.add_argument("-t", "--time", type=int, default=10, help="Tempo máximo de envio em segundos (cliente)")
    parser.add_argument("--rate", type=int, help="Pacotes por segundo (cliente). Se omitido, envia o mais rápido possível.")
    args = parser.parse_args()

    # É preciso passar os novos argumentos para as funções
    if args.server:
        # A função run_server precisa ser ajustada para receber 'args.baud'
        run_server(args.server, args.num, args.baud)
    elif args.client:
        if not args.remote:
            print("Cliente precisa do endereço remoto do servidor (--remote)")
            sys.exit(1)
        # A função run_client precisa ser ajustada para receber 'args.baud' e 'args.csv'
        run_client(args.client, args.remote, args.num, args.time, args.rate, args.baud, args.csv)