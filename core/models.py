from django.db import models

# ======================================================
# 🔹 MODELO BASE COM TIMESTAMP
# ======================================================
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ======================================================
# 🔹 MODELOS DAS FONTES
# ======================================================
class BitrixUser(TimeStampedModel):
    status = models.CharField(max_length=30, null=True, blank=True)
    nome_user = models.CharField(max_length=255, null=True, blank=True)
    nome_completo = models.CharField(max_length=255, null=True, blank=True)
    user_dominio = models.CharField(max_length=255, null=True, blank=True)
    user_local = models.CharField(max_length=255, null=True, blank=True)
    departamento_principal = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    fonte_raw = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["nome_user"]),
            models.Index(fields=["nome_completo"]),
            models.Index(fields=["user_dominio"]),
            models.Index(fields=["user_local"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.nome_user or "(sem nome)"

    
class PontoContact(TimeStampedModel):
    nome = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    fonte_raw = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("nome", "email")]
        indexes = [models.Index(fields=["nome"]), models.Index(fields=["email"])]

    def __str__(self):
        return f"{self.nome} <{self.email}>"


class GesttaUser(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    fonte_raw = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name} <{self.email}>"


class DominioAccount(TimeStampedModel):
    id_externo = models.IntegerField(unique=True, null=False, blank=False)
    nome = models.CharField(max_length=255)
    fonte_raw = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.id_externo} - {self.nome}"


class CcontrolWebUser(TimeStampedModel):
    nome_completo = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    fonte_raw = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.nome_completo} <{self.email}>"


# ======================================================
# 🔹 MODELOS DE SINCRONIZAÇÃO (LOG DE EXECUÇÃO)
# ======================================================
class SyncRun(TimeStampedModel):
    STATUS_CHOICES = (
        ("running", "running"),
        ("success", "success"),
        ("error", "error"),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="running")
    mensagem = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Execução {self.id} - {self.status} ({self.created_at:%d/%m/%Y %H:%M})"


class SyncDetail(TimeStampedModel):
    """
    Registra o resultado da sincronização por fonte
    (ex: BITRIX, Ponto, GESTTA, DOMINIO, CCONTROLWEB)
    """
    FONTE_CHOICES = (
        ("BITRIX", "BITRIX"),
        ("Ponto", "Ponto"),
        ("GESTTA", "GESTTA"),
        ("DOMINIO", "DOMINIO"),
        ("CCONTROLWEB", "CCONTROLWEB"),
    )
    run = models.ForeignKey(SyncRun, related_name="details", on_delete=models.CASCADE)
    fonte = models.CharField(max_length=20, choices=FONTE_CHOICES)
    lidos = models.IntegerField(default=0)
    gravados = models.IntegerField(default=0)
    ignorados = models.IntegerField(default=0)
    mensagem_erro = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.run_id} - {self.fonte}: {self.gravados}/{self.lidos}"
