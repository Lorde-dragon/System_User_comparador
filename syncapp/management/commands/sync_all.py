from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import (
    BitrixUser, PontoContact, GesttaUser, DominioAccount, CcontrolWebUser, VisaoLogicaUser,
    SyncRun, SyncDetail
)
from core.services.fetch_bitrix import fetch_bitrix
from core.services.fetch_ponto import fetch_ponto
from core.services.fetch_gestta import fetch_gestta
from core.services.fetch_dominio import fetch_dominio
from core.services.fetch_ccontrolweb import fetch_ccontrolweb
from core.services.fetch_visaologica import fetch_visaologica
import json


class Command(BaseCommand):
    help = "Baixa dados das APIs e grava no banco (ordem: Bitrix, Ponto, Gestta, Dominio, CControlWeb, Visão Lógica)."

    def handle(self, *args, **options):
        run = SyncRun.objects.create(status="running")
        try:
            self.sync_bitrix(run)
            self.sync_ponto(run)
            self.sync_gestta(run)
            self.sync_dominio(run)
            self.sync_ccontrolweb(run)
            self.sync_visaologica(run)
            run.status = "success"
            run.save()
            self.stdout.write(self.style.SUCCESS(f"✅ Sync concluído (run={run.id})"))
        except Exception as e:
            run.status = "error"
            run.mensagem = str(e)
            run.save()
            raise

    def _flush(self, queryset):
        """Limpa a tabela antes de repopular (modo MVP)."""
        deleted, _ = queryset.all().delete()
        return deleted

    # ==================================================
    # BITRIX
    # ==================================================
    @transaction.atomic
    def sync_bitrix(self, run):
        item = SyncDetail.objects.create(run=run, fonte="BITRIX")
        data = fetch_bitrix()
        item.lidos = len(data)
        self._flush(BitrixUser.objects)
        gravados = 0
        for row in data:
            BitrixUser.objects.create(
                status=(row.get("Status") or "").strip() or None,
                nome_user=(row.get("name") or "").strip() or None,
                nome_completo=(row.get("Nome_Completo") or "").strip() or None,
                user_dominio=(row.get("User_Dominio") or "").strip() or None,
                user_local=(row.get("User_Local") or "").strip() or None,
                departamento_principal=(row.get("departamento_principal") or "").strip() or None,
                email=(row.get("email") or "").strip() or None,
                fonte_raw=row,
            )
            gravados += 1
        item.gravados = gravados
        item.save()
        print(f"✔ BITRIX - {gravados} registros gravados")

    # ==================================================
    # PONTO
    # ==================================================
    @transaction.atomic
    def sync_ponto(self, run):
        item = SyncDetail.objects.create(run=run, fonte="PONTO")
        data = fetch_ponto()
        item.lidos = len(data)
        self._flush(PontoContact.objects)
        gravados = 0
        for row in data:
            PontoContact.objects.create(
                nome=row["nome"],
                email=row["email"],
                fonte_raw=row.get("raw", row),
            )
            gravados += 1
        item.gravados = gravados
        item.save()
        print(f"✔ PONTO - {gravados} registros gravados")

    # ==================================================
    # GESTTA
    # ==================================================
    @transaction.atomic
    def sync_gestta(self, run):
        item = SyncDetail.objects.create(run=run, fonte="GESTTA")
        data = fetch_gestta()
        item.lidos = len(data)
        self._flush(GesttaUser.objects)
        gravados = 0
        for row in data:
            GesttaUser.objects.create(
                name=(row.get("name") or "").strip(),
                email=(row.get("email") or "").strip(),
                fonte_raw=row,
            )
            gravados += 1
        item.gravados = gravados
        item.save()
        print(f"✔ GESTTA - {gravados} registros gravados")

    # ==================================================
    # DOMÍNIO
    # ==================================================
    @transaction.atomic
    def sync_dominio(self, run):
        
        # fetch_dominio já executa o upsert no banco e retorna contagens
        res = fetch_dominio()

        # Se fetch_dominio retornou um dict com contagens, só registre e finalize.
        if isinstance(res, dict) and {"lidos", "gravados", "ignorados"} <= set(res.keys()):
            lidos = int(res.get("lidos") or 0)
            gravados = int(res.get("gravados") or 0)
            ignorados = int(res.get("ignorados") or 0)
            print(f"✔ DOMÍNIO - {gravados} registros gravados")
            run.details.create(fonte="DOMINIO", lidos=lidos, gravados=gravados, ignorados=ignorados)
            return

        # (fallback) Se algum dia fetch_dominio voltar a retornar lista de itens,
        # este trecho mantém compatibilidade — mas hoje não deve ser usado.
        data = res
        lidos = gravados = ignorados = 0

        import json
        from core.models import DominioAccount

        for row in data:
            lidos += 1
            if isinstance(row, str):
                try:
                    row = json.loads(row.replace("'", '"'))
                except Exception:
                    ignorados += 1
                    continue

            codigo = row.get("I_SECUSUARIOS")
            nome = (row.get("NOME") or "").strip()
            if not nome or codigo is None:
                ignorados += 1
                continue

            try:
                DominioAccount.objects.update_or_create(
                    id_externo=codigo,
                    defaults={"nome": nome, "fonte_raw": row},
                )
                gravados += 1
            except Exception:
                ignorados += 1

        print(f"✔ DOMÍNIO - {gravados} registros gravados")
        run.details.create(fonte="DOMINIO", lidos=lidos, gravados=gravados, ignorados=ignorados)


    # ==================================================
    # CCONTROL WEB
    # ==================================================
    @transaction.atomic
    def sync_ccontrolweb(self, run):
        item = SyncDetail.objects.create(run=run, fonte="CCONTROLWEB")
        data = fetch_ccontrolweb()
        item.lidos = len(data)

        # Se você quer continuar limpando a tabela antes de repopular:
        self._flush(CcontrolWebUser.objects)

        gravados = 0
        seen = set()  # controla duplicidade dentro do lote

        for row in data:
            # Segurança: ignore itens inválidos
            if not isinstance(row, dict):
                continue

            nome = (row.get("nome_completo") or "").strip()
            email = (row.get("email") or "").strip()

            # Ignore emails vazios
            if not email:
                continue

            # Dedup no mesmo lote (case-insensitive)
            email_key = email.lower()
            if email_key in seen:
                continue
            seen.add(email_key)

            # Upsert por email para maior robustez
            obj, created = CcontrolWebUser.objects.update_or_create(
                email=email,
                defaults={
                    "nome_completo": nome,
                    "fonte_raw": row,
                },
            )
            if created:
                gravados += 1
            else:
                # Se preferir contar atualizações como “gravados” também, troque para: gravados += 1
                pass

        item.gravados = gravados
        item.save()
        print(f"✔ CCONTROLWEB - {gravados} registros gravados")

    # ==================================================
    # Visão Lógica
    # ==================================================
    @transaction.atomic
    def sync_visaologica(self, run):
        item = SyncDetail.objects.create(run=run, fonte="VISAOLOGICA")

        data = fetch_visaologica()
        item.lidos = len(data)

        gravados = 0

        for row in data:
            codigo = str(row.get("CodigoFuncionario", "")).strip()
            if not codigo:
                continue

            VisaoLogicaUser.objects.update_or_create(
                codigo_funcionario=codigo,
                defaults={
                    "nome_funcionario": (row.get("NomeFuncionario") or "").strip(),
                    "dep_funcionario": (row.get("DepFuncionario") or "").strip(),
                    "fonte_raw": row,
                }
            )
            gravados += 1

        item.gravados = gravados
        item.save()

        print(f"✔ VISAOLOGICA - {gravados} registros gravados")


