import requests
from django.conf import settings

def fetch_bitrix():
    url = settings.BITRIX_URL
    timeout = settings.REQUEST_TIMEOUT
    for attempt in range(settings.REQUEST_RETRIES + 1):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise ValueError("Resposta BITRIX não é lista")
            return data
        except Exception as e:
            last_err = e
    raise last_err
