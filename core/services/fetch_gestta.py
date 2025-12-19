import os
import requests
from dotenv import load_dotenv


load_dotenv()

def fetch_gestta():
    url = os.getenv("GESTTA_URL")
    timeout = int(os.getenv("REQUEST_TIMEOUT", 10))
    for attempt in range(int(os.getenv("REQUEST_RETRIES", 0)) + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise ValueError("Resposta GESTTA não é lista")
            return data
        except Exception as e:
            last_err = e
    raise last_err
