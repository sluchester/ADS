#!/usr/bin/env python3
import argparse
import csv
import json
import os
import subprocess
import time
from datetime import datetime
import numpy as np

class MarkovTrafficGenerator:
    def __init__(self, P, server_ip='127.0.0.1', port=5201, seed=None,
                 out_file='traffic_log.csv', run_id=None, append=True):
        self.P = np.array(P)
        self.server_ip = server_ip
        self.port = port
        self.current_state = 0 # começa ocioso
        self.rng = np.random.default_rng(seed)
        self.rates = {0: 0, 1: 10, 2: 50}  # # taxa de cada estado em Mbps
        self.out_file = out_file
        self.append = append
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.fieldnames = [
            'run_id', 'step', 'state', 'rate_Mbps',
            'iperf_returncode', 'iperf_stderr', 'iperf_stdout_snippet',
            'duration_s', 'bytes_sent', 'achieved_Mbps',
            'wall_start', 'wall_end', 'wall_duration'
        ]
        if not self.append and os.path.isfile(self.out_file):
            os.remove(self.out_file)

    def _write_row(self, row):
        file_exists = os.path.isfile(self.out_file)
        with open(self.out_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def _parse_iperf_json(self, stdout):
        # retorna (bytes_sent, seconds) com fallback 0
        if not stdout:
            return 0, 0.0
        try:
            data = json.loads(stdout)
            end = data.get('end', {})
            # Para UDP iperf3 pode usar 'sum_sent' ou 'sum', tente várias chaves
            s = {}
            if isinstance(end, dict):
                if 'sum_sent' in end:
                    s = end['sum_sent']
                elif 'sum' in end:
                    s = end['sum']
                else:
                    # procura um dict interno
                    for v in end.values():
                        if isinstance(v, dict):
                            s = v
                            break
            bytes_sent = s.get('bytes', s.get('bytes_sent', 0))
            seconds = s.get('seconds', s.get('duration', 0.0))
            return int(bytes_sent or 0), float(seconds or 0.0)
        except Exception:
            # fallback regex se JSON falhar
            import re
            m = re.search(r'"bytes"\s*:\s*(\d+)', stdout)
            m2 = re.search(r'"seconds"\s*:\s*([0-9.]+)', stdout)
            bytes_sent = int(m.group(1)) if m else 0
            seconds = float(m2.group(1)) if m2 else 0.0
            return bytes_sent, seconds

    def step(self, step_idx, epoch_duration=5, timeout_margin=10):
        rate = self.rates.get(self.current_state, 0)
        wall_start = time.time()
        bytes_sent = 0
        real_duration = 0.0
        returncode = None
        stderr = ""
        stdout_snippet = ""

        if rate > 0:
            cmd = [
                "iperf3",
                "-c", self.server_ip,
                "-p", str(self.port),
                "-u",
                "-b", f"{rate}M",
                "-t", str(epoch_duration),
                "-J"
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=epoch_duration + timeout_margin)
                returncode = proc.returncode
                stderr = (proc.stderr or "")[:1000]  # corta para log
                stdout_snippet = (proc.stdout or "")[:2000]
                bytes_sent, real_duration = self._parse_iperf_json(proc.stdout)
            except subprocess.TimeoutExpired as e:
                stderr = f"timeout: {e}"
                returncode = -1
            except Exception as e:
                stderr = f"exception: {e}"
                returncode = -2
        else:
            # estado ocioso -> simula a espera de epoch_duration
            # opcional: se quiser que o script espere mesmo em idle, descomente:
            # time.sleep(epoch_duration)
            real_duration = 0.0
            bytes_sent = 0

        wall_end = time.time()
        wall_duration = wall_end - wall_start

        achieved_mbps = (bytes_sent * 8 / real_duration / 1e6) if real_duration > 0 else 0.0

        row = {
            'run_id': self.run_id,
            'step': step_idx,
            'state': self.current_state,
            'rate_Mbps': rate,
            'iperf_returncode': returncode,
            'iperf_stderr': stderr,
            'iperf_stdout_snippet': stdout_snippet,
            'duration_s': real_duration,
            'bytes_sent': bytes_sent,
            'achieved_Mbps': achieved_mbps,
            'wall_start': wall_start,
            'wall_end': wall_end,
            'wall_duration': wall_duration
        }

        self._write_row(row)

        # transição
        self.current_state = int(self.rng.choice([0, 1, 2], p=self.P[self.current_state]))
        return row

    def run(self, steps=50, epoch_duration=5):
        run_wall_start = time.time()
        rows = []
        for i in range(steps):
            print(f"Step {i+1}/{steps}  state={self.current_state}")
            r = self.step(i+1, epoch_duration=epoch_duration)
            rows.append(r)
        run_wall_end = time.time()
        total_bytes = sum(r['bytes_sent'] for r in rows)
        total_wall = run_wall_end - run_wall_start
        overall_mbps = total_bytes * 8 / total_wall / 1e6 if total_wall > 0 else 0.0

        print("=== Resultado ===")
        print(f"Total bytes: {total_bytes}")
        print(f"Total wall time: {total_wall:.3f} s")
        print(f"Throughput medida (total_bytes / wall_time): {overall_mbps:.3f} Mbps")

        # estimativas teóricas
        rates = np.array([self.rates[0], self.rates[1], self.rates[2]])
        # distribuição estacionária
        w, v = np.linalg.eig(self.P.T)
        idx = next(i for i, val in enumerate(w) if abs(val - 1) < 1e-8)
        v1 = np.real(v[:, idx])
        pi = v1 / v1.sum()
        stationary_mbps = float(pi.dot(rates))
        print(f"Est. estacionária (pi): {pi}")
        print(f"Taxa média teórica (estacionária): {stationary_mbps:.3f} Mbps")

        # média finita iniciando em estado 0 (por comparação)
        cur = np.array([1.0, 0.0, 0.0])
        avg_list = []
        for _ in range(steps):
            avg_list.append(cur.dot(rates))
            cur = cur.dot(self.P)
        finite_avg = sum(avg_list) / steps
        print(f"Taxa média teórica (50 passos iniciando em 0): {finite_avg:.3f} Mbps")

        return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-ip', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5201)
    parser.add_argument('--steps', type=int, default=50)
    parser.add_argument('--epoch', type=int, default=5)
    parser.add_argument('--outfile', default='traffic_log_debug.csv')
    parser.add_argument('--no-append', action='store_true')
    args = parser.parse_args()

    P = [[0.7,0.2,0.1],[0.3,0.4,0.3],[0.2,0.3,0.5]]
    gen = MarkovTrafficGenerator(P, server_ip=args.server_ip, port=args.port,
                                 out_file=args.outfile, append=not args.no_append)
    gen.run(steps=args.steps, epoch_duration=args.epoch)

if __name__ == '__main__':
    main()