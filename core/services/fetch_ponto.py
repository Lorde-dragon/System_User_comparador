import os
import requests
from dotenv import load_dotenv


load_dotenv()

def fetch_ponto():
    url = os.getenv("PONTO_URL")
    token = os.getenv("PONTO_TOKEN")

    if not url or not token:
        raise RuntimeError("PONTO_URL ou PONTO_TOKEN não definidos no .env")

    headers = {
        "Authentication": f"{token}",
        "Accept": "application/json"
    }

    timeout = int(os.getenv("REQUEST_TIMEOUT", 10))
    retries = int(os.getenv("REQUEST_RETRIES", 0))

    last_err = None

    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()

            data = r.json()
            if not isinstance(data, list):
                raise ValueError("Resposta Ponto não é lista")

            norm = []
            for item in data:
                if not isinstance(item, dict):
                    continue

                j = item.get("json")
                if not isinstance(j, dict):
                    continue

                nome = (j.get("nome") or "").strip()
                email = (j.get("email") or "").strip()

                if nome or email:
                    norm.append({
                        "nome": nome,
                        "email": email,
                        "raw": item
                    })

            return norm

        except Exception as e:
            last_err = e

    raise last_err
