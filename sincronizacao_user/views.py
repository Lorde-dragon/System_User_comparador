from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import LogAtualizacaoCPF, ColaboradorPonto, UsuarioBitrix, MatchCPFCheck
from .services import (
    sync_colaboradores_ponto,
    sync_usuarios_bitrix,
    atualizar_cpfs_no_bitrix,
    gerar_checks_match_persistidos,
    enviar_cpfs_ok_do_check
)


def index(request):
    stats = gerar_checks_match_persistidos()

    checks = MatchCPFCheck.objects.all()
    logs = LogAtualizacaoCPF.objects.all().order_by('-data_atualizacao')[:50]

    return render(request, "sincronizacao_user/index.html", {
        "logs": logs,
        "titulo": "Sincronização de Usuários",
        "checks": checks,
        "stats": stats
    })



@require_POST
def sync_bases(request):
    """
    Botão:
    - Atualiza bases locais (Ponto e Bitrix)
    - NÃO envia Bitrix
    - Checagem será gerada automaticamente na tela (ou após sync)
    """
    try:
        msg_ponto = sync_colaboradores_ponto()
        msg_bitrix = sync_usuarios_bitrix()

        messages.success(request, f"{msg_ponto} {msg_bitrix}")
        return redirect("sincronizacao_user:index")

    except Exception as e:
        messages.error(request, f"Ocorreu um erro ao atualizar bases: {str(e)}")
        return redirect('sincronizacao_user:index')

@require_POST
def run_sync(request):
    """
    Botão 2:
    - Envia CPFs ao Bitrix utilizando a tabela MatchCPFCheck
    - NÃO recalcula match aqui
    - NÃO atualiza bases locais
    """
    try:
        # opcional: garantir que a tabela está atualizada antes do envio
        gerar_checks_match_persistidos()

        resultado = enviar_cpfs_ok_do_check()

        if resultado["atualizados"] > 0:
            messages.success(request, f"Sucesso! {resultado['atualizados']} usuários tiveram CPFs atualizados no Bitrix.")
        else:
            messages.warning(request, "Nenhum CPF precisou ser atualizado nesta rodada.")

        if resultado["erros"] > 0:
            messages.error(request, f"Atenção: {resultado['erros']} erros ocorreram durante o envio ao Bitrix.")

    except Exception as e:
        messages.error(request, f"Ocorreu um erro durante a atualização no Bitrix: {str(e)}")

    return redirect('sincronizacao_user:index')

