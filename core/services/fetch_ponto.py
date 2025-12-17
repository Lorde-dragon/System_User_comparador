import requests
from django.conf import settings

def fetch_ponto():
    url = settings.PONTO_URL
    headers = {"Authentication": settings.PONTO_TOKEN, "Accept": "application/json"}
    timeout = settings.REQUEST_TIMEOUT
    for attempt in range(settings.REQUEST_RETRIES + 1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                raise ValueError("Resposta Ponto não é lista")
            # normaliza para uma lista de dicts simples {nome, email}
            norm = []
            for item in data:
                j = item.get("json") if isinstance(item, dict) else None
                if not j:  # ignora itens ruins
                    continue
                nome = (j.get("nome") or "").strip()
                email = (j.get("email") or "").strip()
                if nome or email:
                    norm.append({"nome": nome, "email": email, "raw": item})
            return norm
        except Exception as e:
            last_err = e
    raise last_err
