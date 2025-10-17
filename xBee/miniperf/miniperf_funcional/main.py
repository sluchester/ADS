# main.py
import argparse
import sys
from server import run_server
from client import run_client

def main():
    parser = argparse.ArgumentParser(description="miniperf XBee modular")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", help="Porta serial do XBee servidor")
    group.add_argument("-c", "--client", help="Porta serial do XBee cliente")

    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--csv", default="relatorio.csv")
    parser.add_argument("--remote", help="Endereço 64-bit do XBee remoto")
    parser.add_argument("-n", "--num", type=int, default=100)
    parser.add_argument("-t", "--time", type=int, default=10)
    parser.add_argument("--rate", type=int, help="Pacotes por segundo")
    args = parser.parse_args()

    if args.server:
        run_server(args.server, args.num, args.baud)
    elif args.client:
        if not args.remote:
            print("Cliente precisa do endereço remoto (--remote)")
            sys.exit(1)
        run_client(args.client, args.remote, args.num, args.time, args.rate, args.baud, args.csv)

if __name__ == "__main__":
    main()