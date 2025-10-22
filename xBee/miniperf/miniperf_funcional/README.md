## Como rodar?

No servidor, rodar:
```cmd
python3 main.py -s /dev/ttyUSB0 --baud 115200
```

No cliente, rodar:
```cmd
python3 main.py -c /dev/ttyUSB1 --baud 115200 --csv teste.csv --remote 0013A20041FBCD12 -n 100 -t 10 --rate 10
```