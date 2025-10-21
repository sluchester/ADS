Para baixar o pacote queueing para cadeias de Markov, executar direto no terminal do projeto, dentro do octave (no caso, estou usando VS com extensão do Octave):

- [Site para baixar os arquivos e também para ](https://www.moreno.marzolla.name/software/queueing/)
- pkg install -local "https://github.com/mmarzolla/queueing/releases/download/1.2.8/queueing-1.2.8.tar.gz"

(mbits transmitidos * 8) / 5

8 porque 1 byte são 8 bits

5 porque o tempo de sessão é de aprox. 5s

para saber o total transmitido, seria a soma do número total de bits transmitidos * 8/ tempo total (50 sessões * 5 segundos por cada sessão)


## Ambiente venv no windows

Para executar o ambiente venv no windows é um pouco mais chato que no linux.

Comando de criação inicial do venv é igual ao linux:
```cmd
python -m venv .venv
```

Se você tentou executar pelo mesmo comando que o linux, tentou pegar o código da internet e também não funcionou, eis aqui o passo a passo:
- Usando o terminal do vs code, verifique no canto superior direito se está usando o PowerShell (pois este comando foi testado apenas usando o PowerShell)
- Digite a tecla windows no seu pc, abra o PowerShell no modo ADMINISTRADOR  e digite o seguinte comando: 
```cmd
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
- Se aparecer uma mensagem de confirmação digite "s" OU "y" (se seu SO estiver em inglês)
- Após isso, dê um reload no VS Code e digite:
```cmd
.\venv\Scripts\Activate.ps1
```