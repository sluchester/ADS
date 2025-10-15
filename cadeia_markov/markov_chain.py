import numpy as np
import pandas as pd
import subprocess
import time
import re
import json
import csv

class MarkovTrafficGenerator:
    def __init__(self, P, server_ip="127.0.0.1", port=5201, seed=None):
        """
        P: matriz de transição (3x3)
        server_ip: endereço do servidor iperf3
        port: porta do iperf3
        """
        self.P = np.array(P)
        self.server_ip = server_ip
        self.port = port
        self.current_state = 0  # Começa no estado 0 (ocioso)
        self.rng = np.random.default_rng(seed)

        # taxas associadas aos estados
        self.rates = {0: 0, 1: 10, 2: 50}  # Mbps
        self.logs = []

    def step(self, epoch_duration=5):
        """Executa um passo da DTMC e gera tráfego correspondente"""
        rate = self.rates[self.current_state]

        bytes_sent = 0
        real_duration = 0.0

        if rate > 0:
            try:
                # Executa iperf3 por epoch_duration segundos
                cmd = [
                    "iperf3",
                    "-c", self.server_ip,
                    "-p", str(self.port),
                    "-u",  # UDP (para controle direto da taxa)
                    "-b", f"{rate}M",
                    "-t", str(epoch_duration),
                    "-J"  # saída JSON
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

                # Converte saída JSON
                data = json.loads(result.stdout)

                # Pega resumo final (end -> sum)
                if "end" in data and "sum" in data["end"]:
                    bytes_sent = data["end"]["sum"].get("bytes", 0)
                    real_duration = data["end"]["sum"].get("seconds", 0.0)

            except Exception as e:
                print(f"Erro ao executar iperf: {e}")

        # Registra os dados do passo
        self.logs.append({
            "state": self.current_state,
            "rate_Mbps": rate,
            "duration_s": real_duration,
            "bytes_sent": bytes_sent,
            "timestamp": time.time()
        })

        # Transição para próximo estado
        self.current_state = self.rng.choice([0, 1, 2], p=self.P[self.current_state])

    def run(self, steps=50, epoch_duration=5):
        for i in range(steps):
            print(f"Step {i+1}/{steps} - Estado {self.current_state}")
            self.step(epoch_duration)
        return self.logs


if __name__ == "__main__":
    # Exemplo de matriz de transição P
    P = [
        [0.7, 0.2, 0.1],  # Estado 0
        [0.3, 0.4, 0.3],  # Estado 1
        [0.2, 0.3, 0.5]   # Estado 2
    ]

    generator = MarkovTrafficGenerator(P, server_ip="127.0.0.1")  # coloque o IP do servidor iperf3
    logs = generator.run(steps=50, epoch_duration=5)

    # Salvar resultados em arquivo CSV
    with open("loopback.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)

    print("Execução finalizada. Resultados salvos em loopback.csv")

    df = pd.read_csv("loopback.csv")
    soma_bytes = df["bytes_sent"].sum()
    print("Soma dos bytes transmitidos:", soma_bytes)