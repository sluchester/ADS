import serial

def main():
    # Configuração da porta serial (ajuste a baudrate se necessário)
    ser = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate=9600,
        timeout=1   # tempo de espera para leitura (em segundos)
    )

    if ser.is_open:
        print(f"Escutando XBee na porta {ser.port}...")

    try:
        while True:
            # Lê dados da serial
            dados = ser.readline().decode('utf-8', errors='ignore').strip()
            if dados:
                print("Recebido:", dados)

    except KeyboardInterrupt:
        print("\nEncerrando leitura.")
    finally:
        ser.close()
        print("Conexão fechada.")

if __name__ == "__main__":
    main()