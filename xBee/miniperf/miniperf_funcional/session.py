# session.py
import os
from utils import SESSION_COUNTER_FILE

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