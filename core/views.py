from django.shortcuts import render, redirect
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Q, Count
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import (
    BitrixUser, PontoContact, GesttaUser, DominioAccount, CcontrolWebUser, VisaoLogicaUser, SyncRun, SyncDetail
)
import subprocess
import sys
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import Lower

def login_redirect(request):
    # apenas para garantir rota /login do urls global usa auth view
    return redirect("login")

def _cmp_equal(a: str|None, b: str|None) -> bool:
    """Comparação EXATA, sensível a caixa e acento. Apenas strip de borda."""
    if a is None or b is None:
        return False
    return a.strip() == b.strip()

def _bitrix_email(u: BitrixUser) -> str|None:
    # se Bitrix não fornece email, permanece None
    return (u.email or None)

def _validacoes(u: BitrixUser):
    #Retorna dict com status de cada fonte e motivo se falha.
    result = {
        "ponto": (False, "sem verificação"),
        "gestta": (False, "sem verificação"),
        "dominio": (False, "sem verificação"),
        "web": (False, "sem verificação"),
        "visao": (False, "sem verificação"),
    }

    email_b = _bitrix_email(u)

    # Ponto: validação apenas pelo nome
    if not u.nome_completo:
        result["ponto"] = (False, "BITRIX sem nome para conciliar")
    else:
        qs = PontoContact.objects.filter(nome=u.nome_completo)
        count = qs.count()
        if count == 1:
            result["ponto"] = (True, "")
        elif count == 0:
            result["ponto"] = (False, "Ponto: nenhum registro com esse nome")
        else:
            result["ponto"] = (False, f"Ponto: duplicidade ({count} registros com mesmo nome)")

    # GESTTA: apenas e-mail
    if email_b is None:
        result["gestta"] = (False, "BITRIX sem e-mail")
    else:
        result["gestta"] = (GesttaUser.objects.filter(email=email_b).exists(), "Gestta: e-mail não encontrado" if not GesttaUser.objects.filter(email=email_b).exists() else "")

    # DOMÍNIO: user_dominio deve existir em DominioAccount.nome
    if not u.user_dominio:
        result["dominio"] = (False, "BITRIX sem User_Dominio")
    else:
        result["dominio"] = (DominioAccount.objects.filter(nome=u.user_dominio).exists(), "Domínio: user não encontrado" if not DominioAccount.objects.filter(nome=u.user_dominio).exists() else "")

    # CCONTROLWEB: e-mail
    if email_b is None:
        result["web"] = (False, "BITRIX sem e-mail")
    else:
        result["web"] = (CcontrolWebUser.objects.filter(email=email_b).exists(), "Web: e-mail não encontrado" if not CcontrolWebUser.objects.filter(email=email_b).exists() else "")

    # Visão Lógica: nome deve existir em VisaoLogicaUser.nome_funcionario
    if not u.user_local:
        result["visao"] = (False, "BITRIX sem nome para conciliar")
    else:
        exists = VisaoLogicaUser.objects.filter(nome_funcionario=u.user_local).exists()
        result["visao"] = (exists, "Visão Lógica: nome não encontrado" if not exists else "")

    return result

@login_required
def dashboard(request):
    # filtros
    status = request.GET.get("status", "Ativo")  # padrão Ativo
    dept = request.GET.get("departamento") or ""
    q = request.GET.get("q") or ""
    divergencias = request.GET.get("div")  # "ponto|gestta|dominio|web|visao" opcional

    users = BitrixUser.objects.all()

    if status in ("Ativo", "Inativo"):
        users = users.filter(status=status)

    if dept:
        users = users.filter(departamento_principal=dept)

    if q:
        # busca "contém" mantendo sensibilidade — Django é case-sensitive em SQLite? Depende.
        # Para MVP, usa icontains? NÃO. Precisamos sensível; então usamos contains puro.
        users = users.filter(
            Q(nome_user__contains=q) |
            Q(nome_completo__contains=q) |
            Q(user_dominio__contains=q) |
            Q(user_local__contains=q) |
            Q(email__contains=q)
        )

    # montar lista com validações (ineficiente para milhões, ok para MVP)
    rows = []
    total = users.count()
    for u in users:
        v = _validacoes(u)
        if divergencias:
            chave = divergencias.lower()
            if chave in v and v[chave][0] is True:
                # pediu ver só divergências dessa fonte, mas está ok => pula
                continue
        rows.append((u, v))

    # dados para filtros de departamento
    departamentos = (
        BitrixUser.objects.exclude(departamento_principal__isnull=True)
        .exclude(departamento_principal__exact="")
        .values_list("departamento_principal", flat=True)
        .distinct()
        .order_by("departamento_principal")
    )

    # contadores de divergências por fonte
    cont = {"ponto":0,"gestta":0,"dominio":0,"web":0,"visao":0}
    for u in BitrixUser.objects.filter(status="Ativo"):
        v = _validacoes(u)
        for k in cont.keys():
            if not v[k][0]:
                cont[k]+=1

    context = {
        "rows": rows,
        "total": total,
        "status_sel": status,
        "dept_sel": dept,
        "q": q,
        "departamentos": departamentos,
        "div_sel": divergencias or "",
        "sync_last": SyncRun.objects.order_by("-created_at").first(),
        "cont_div": cont,
        "fontes": ["ponto", "gestta", "dominio", "web", "visao"],  # para exibição dinâmica
    }

    return render(request, "core/dashboard.html", context)

@user_passes_test(lambda u: u.is_staff)
@staff_member_required
def sync_manual(request):
    if request.method == "POST":
        try:
            # roda no mesmo processo python
            exitcode = subprocess.call([sys.executable, "manage.py", "sync_all"])
            if exitcode == 0:
                messages.success(request, "Atualização concluída com sucesso.")
            else:
                messages.error(request, f"Erro ao atualizar (exitcode={exitcode}).")
        except Exception as e:
            messages.error(request, f"Erro ao atualizar: {e}")
        return redirect("sync_manual")

    itens = SyncDetail.objects.select_related("run").order_by("-created_at")[:50]
    run = SyncRun.objects.order_by("-created_at").first()
    return render(request, "core/sync_manual.html", {"itens": itens, "run": run})


# @user_passes_test(lambda u: u.is_staff)  # só staff/admin
# def register_user(request):
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         is_staff = request.POST.get('is_staff') == 'on'
        
#         if User.objects.filter(username=username).exists():
#             messages.error(request, "Usuário já existe!")
#         else:
#             user = User.objects.create_user(username=username, password=password, is_staff=is_staff)
#             messages.success(request, f"Usuário {username} criado com sucesso!")

#     return render(request, 'core/register_user.html')

