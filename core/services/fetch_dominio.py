import requests
from core.models import DominioAccount


def fetch_dominio():
    """
    Faz a coleta e atualização dos dados da API do Domínio.
    Usa o campo I_SECUSUARIOS como chave única (id_externo).
    Garante que apenas registros válidos sejam salvos e
    trata automaticamente erros e respostas vazias.
    """
    url = "http://ti-system:5006/api/jdash/user_dominio"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        raise Exception(f"Erro ao conectar à API do Domínio: {e}")

    try:
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("A resposta da API não é uma lista válida.")
    except Exception as e:
        raise Exception(f"Erro ao decodificar JSON: {e}")

    lidos = 0
    gravados = 0
    ignorados = 0

    for item in data:
        # Ignora registros nulos, vazios ou inválidos
        if not item or not isinstance(item, dict):
            ignorados += 1
            continue

        codigo = item.get("I_SECUSUARIOS")
        nome = item.get("NOME")

        if codigo is None or not nome:
            ignorados += 1
            continue

        try:
            DominioAccount.objects.update_or_create(
                id_externo=codigo,
                defaults={
                    "nome": nome.strip(),
                    "fonte_raw": item,
                },
            )
            gravados += 1
        except Exception as e:
            ignorados += 1
            print(f"⚠️ Erro ao salvar registro {codigo} - {nome}: {e}")

        lidos += 1

    print(f"✅ Domínio sincronizado — lidos: {lidos}, gravados: {gravados}, ignorados: {ignorados}")

    return {
        "lidos": lidos,
        "gravados": gravados,
        "ignorados": ignorados,
    }
