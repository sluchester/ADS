import serial
import time

def send_at_command(ser, command):
    """Envia um comando AT e retorna a resposta"""
    ser.write((command + "\r").encode('utf-8'))
    time.sleep(0.1)
    resposta = ser.readline().decode('utf-8').strip()
    return resposta

def main():
    ser = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate=9600,
        timeout=1
    )

    if ser.is_open:
        print(f"Conectado ao XBee em {ser.port}")

    try:
        # Entrar no modo de comando
        time.sleep(1)
        ser.write(b"+++")
        time.sleep(1)
        resposta = ser.read(10).decode('utf-8').strip()
        if "OK" not in resposta:
            print("Falha ao entrar no modo de comando. Resposta:", resposta)
            return
        print("Entrou no modo de comando AT.")

        # Coletar informações
        sh = send_at_command(ser, "ATSH")
        sl = send_at_command(ser, "ATSL")
        dh = send_at_command(ser, "ATDH")
        dl = send_at_command(ser, "ATDL")
        pan_id = send_at_command(ser, "ATID")

        # Mostrar resultados
        print("\n--- Diagnóstico do XBee ---")
        print(f"Endereço do Nó (SH+SL): {sh}{sl}")
        print(f"Endereço de Destino (DH+DL): {dh}{dl}")
        print(f"PAN ID: {pan_id}")

        # Sair do modo de comando
        send_at_command(ser, "ATCN")

    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário.")
    finally:
        ser.close()
        print("Conexão fechada.")

if __name__ == "__main__":
    main()