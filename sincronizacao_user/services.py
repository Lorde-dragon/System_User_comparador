import os
import pyodbc
import requests
from django.db import transaction
from .models import ColaboradorPonto, UsuarioBitrix, LogAtualizacaoCPF, MatchCPFCheck


# ======================================================
# CONFIGURAÇÕES
# ======================================================

def get_mysql_connection():
    """
    Retorna uma conexão válida com o banco MySQL via ODBC.
    Usa as variáveis de ambiente definidas no .env.
    """
    db_host = os.getenv("DB_HOST_dj")
    db_port = os.getenv("DB_PORT_dj")
    db_user = os.getenv("DB_USER_dj")
    db_password = os.getenv("DB_PASSWORD_dj")
    db_name = os.getenv("DB_NAME_dj")

    connection_string = (
        "DRIVER={MySQL ODBC 8.1 Unicode Driver};"
        f"SERVER={db_host};"
        f"PORT={db_port};"
        f"DATABASE={db_name};"
        f"UID={db_user};"
        f"PWD={db_password};"
    )

    return pyodbc.connect(connection_string)


# ======================================================
# 1. SINCRONIZAR PONTO (MySQL -> Django Model)
# ======================================================

def sync_colaboradores_ponto():
    """Busca dados no MySQL e atualiza a tabela local ColaboradorPonto."""
    conn = get_mysql_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                CONCAT_WS(' ', firstname, lastname) AS nome_completo,
                cpf
            FROM 
                ccontroll_db_api.coalize_colaboradores
            WHERE
                status <> 99
        """)

        colaboradores = cursor.fetchall()

        count = 0
        for row in colaboradores:
            nome_completo = row[0]
            cpf = row[1]

            if not cpf:
                continue

            ColaboradorPonto.objects.update_or_create(
                cpf=cpf,
                defaults={'nome_completo': nome_completo}
            )
            count += 1

        return f"{count} colaboradores do Ponto sincronizados."

    finally:
        cursor.close()
        conn.close()


# ======================================================
# 2. SINCRONIZAR BITRIX (MySQL -> Django Model)
# ======================================================

def sync_usuarios_bitrix():
    """Busca dados no MySQL e atualiza a tabela local UsuarioBitrix."""
    conn = get_mysql_connection()
    cursor = conn.cursor()

    try:
        ids_ignorados = (
            11, 1, 10525, 9649, 16, 16019, 1476, 13861, 20377,
            3279, 21583, 5983, 6, 1388, 4841, 6093, 8951, 922, 9
        )
        ids_str = ",".join(map(str, ids_ignorados))

        query = f"""
            SELECT 
                ID,
                NAME
            FROM 
                ccontroll_db_api.core_usuarios_bitrix
            WHERE
                ID NOT IN ({ids_str})
            AND
                STATUS <> 0
        """

        cursor.execute(query)
        usuarios = cursor.fetchall()

        count = 0
        for row in usuarios:
            id_bitrix = row[0]
            nome = row[1]

            UsuarioBitrix.objects.update_or_create(
                id_bitrix=id_bitrix,
                defaults={'nome': nome}
            )
            count += 1

        return f"{count} usuários do Bitrix sincronizados."

    finally:
        cursor.close()
        conn.close()




@transaction.atomic
def gerar_checks_match_persistidos():
    """
    Gera e salva (persistido) os checks do match EXATO por nome.
    A tabela MatchCPFCheck vira a fonte para exibição e envio.
    """

    # Mapa: nome_completo -> lista de cpfs (para detectar duplicados)
    ponto_map = {}
    for c in ColaboradorPonto.objects.exclude(cpf__isnull=True).exclude(cpf="").only("nome_completo", "cpf"):
        ponto_map.setdefault(c.nome_completo, []).append(c.cpf)

    ok = sem_match = duplicado = 0

    # Vamos montar lista para bulk_create/update
    checks_to_upsert = []

    for u in UsuarioBitrix.objects.all().only("id_bitrix", "nome"):
        cpfs = ponto_map.get(u.nome)

        if not cpfs:
            status = MatchCPFCheck.STATUS_SEM_MATCH
            cpf = None
            obs = "Nome não encontrado no Ponto"
            sem_match += 1

        elif len(cpfs) > 1:
            status = MatchCPFCheck.STATUS_DUPLICADO
            cpf = None
            obs = f"{len(cpfs)} CPFs no Ponto para o mesmo nome"
            duplicado += 1

        else:
            status = MatchCPFCheck.STATUS_OK
            cpf = cpfs[0]
            obs = "Pronto para atualizar no Bitrix"
            ok += 1

        checks_to_upsert.append(MatchCPFCheck(
            id_bitrix=u.id_bitrix,
            nome=u.nome,
            cpf=cpf,
            status=status,
            obs=obs
        ))

    # ✅ UPSERT PROFISSIONAL
    # Requer Django 4.1+ (bulk_create com update_conflicts)
    MatchCPFCheck.objects.bulk_create(
        checks_to_upsert,
        update_conflicts=True,
        unique_fields=["id_bitrix"],
        update_fields=["nome", "cpf", "status", "obs", "atualizado_em"]
    )

    return {
        "total_bitrix": UsuarioBitrix.objects.count(),
        "total_ponto": ColaboradorPonto.objects.count(),
        "ok": ok,
        "sem_match": sem_match,
        "duplicado": duplicado,
        "problemas": sem_match + duplicado,
    }



# ======================================================
# 3. WEBHOOK BITRIX
# ======================================================

def enviar_cpf_bitrix(id_usuario, cpf):
    """Envia o CPF para o Bitrix via Webhook."""
    webhook_url = os.getenv("WEBHOOK_URL", "")

    if not webhook_url:
        print("AVISO: WEBHOOK_URL não configurado.")
        return False

    url = f"{webhook_url}user.update.json"

    payload = {
        "ID": int(id_usuario),
        "UF_USR_1766407282224": str(cpf)
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"Erro ao enviar webhook para ID {id_usuario}: {e}")
        return False


# ======================================================
# 4A. SINCRONIZAÇÃO COMPLETA (ATUALIZA BASE + ENVIA BITRIX)
# ======================================================

def executar_sincronizacao_completa():
    """
    Orquestra todo o processo:
    1. Atualiza cache do Ponto.
    2. Atualiza cache do Bitrix.
    3. Compara nomes e envia atualizações.
    """
    msg_ponto = sync_colaboradores_ponto()
    msg_bitrix = sync_usuarios_bitrix()

    usuarios_bitrix = UsuarioBitrix.objects.all()
    atualizados_count = 0

    for u_bitrix in usuarios_bitrix:
        try:
            colab_ponto = ColaboradorPonto.objects.get(nome_completo=u_bitrix.nome)
            cpf = colab_ponto.cpf

            if cpf:
                sucesso = enviar_cpf_bitrix(u_bitrix.id_bitrix, cpf)

                if sucesso:
                    LogAtualizacaoCPF.objects.create(
                        id_bitrix=u_bitrix.id_bitrix,
                        nome=u_bitrix.nome,
                        cpf=cpf
                    )
                    atualizados_count += 1

        except ColaboradorPonto.DoesNotExist:
            continue
        except ColaboradorPonto.MultipleObjectsReturned:
            print(f"AVISO: Múltiplos registros encontrados para {u_bitrix.nome}. Pulando.")
            continue

    return {
        "ponto_msg": msg_ponto,
        "bitrix_msg": msg_bitrix,
        "atualizados": atualizados_count
    }


# ======================================================
# 4B. SOMENTE ATUALIZAR BITRIX (SEM ATUALIZAR BASE LOCAL)
# ======================================================

def atualizar_cpfs_no_bitrix():
    """
    Atualiza CPFs no Bitrix com match EXATO e ÚNICO.
    Não sincroniza bases locais.
    """

    # Mapa nome -> lista de CPFs (para detectar duplicados)
    ponto_map = {}
    for c in ColaboradorPonto.objects.exclude(cpf__isnull=True).exclude(cpf=""):
        ponto_map.setdefault(c.nome_completo, []).append(c.cpf)

    atualizados = 0
    sem_match = 0
    duplicados = 0
    erros = 0

    for u in UsuarioBitrix.objects.all():
        cpfs = ponto_map.get(u.nome)

        if not cpfs:
            sem_match += 1
            continue

        if len(cpfs) > 1:
            duplicados += 1
            continue

        cpf = cpfs[0]

        sucesso = enviar_cpf_bitrix(u.id_bitrix, cpf)
        if sucesso:
            LogAtualizacaoCPF.objects.create(
                id_bitrix=u.id_bitrix,
                nome=u.nome,
                cpf=cpf
            )
            atualizados += 1
        else:
            erros += 1

    return {
        "atualizados": atualizados,
        "sem_match": sem_match,
        "duplicados": duplicados,
        "erros": erros,
    }

def enviar_cpfs_ok_do_check():
    """
    Envia ao Bitrix apenas os registros que estão com status OK na tabela MatchCPFCheck.
    Assim, o envio fica consistente com a checagem exibida na tela.
    """
    qs = (
        MatchCPFCheck.objects
        .filter(status=MatchCPFCheck.STATUS_OK)
        .exclude(cpf__isnull=True)
        .exclude(cpf="")
    )

    atualizados = 0
    erros = 0

    for item in qs:
        sucesso = enviar_cpf_bitrix(item.id_bitrix, item.cpf)

        if sucesso:
            LogAtualizacaoCPF.objects.create(
                id_bitrix=item.id_bitrix,
                nome=item.nome,
                cpf=item.cpf
            )
            atualizados += 1
        else:
            erros += 1

    return {"atualizados": atualizados, "erros": erros}
