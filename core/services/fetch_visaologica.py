import requests
import os
from dotenv import load_dotenv


load_dotenv()

VISAOLOGICA_URL = os.getenv("VISAOLOGICA_URL")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))


def fetch_visaologica():
    if not VISAOLOGICA_URL:
        raise ValueError("VISAOLOGICA_URL não carregada do .env")

    for attempt in range(int(os.getenv("REQUEST_RETRIES", 0)) + 1):
        try:
            r = requests.get(VISAOLOGICA_URL, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            if not isinstance(data, list):
                raise ValueError("Resposta Visão Lógica não é lista")

            return data

        except Exception as e:
            last_err = e

    raise last_err
