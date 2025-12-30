from django.db import models

class ColaboradorPonto(models.Model):
    cpf = models.CharField(max_length=20, primary_key=True, verbose_name="CPF")
    nome_completo = models.CharField(max_length=255, verbose_name="Nome Completo")

    class Meta:
        verbose_name = "Colaborador Ponto (Cache)"
        verbose_name_plural = "Colaboradores Ponto (Cache)"

    def __str__(self):
        return f"{self.nome_completo} - {self.cpf}"


class UsuarioBitrix(models.Model):
    id_bitrix = models.IntegerField(primary_key=True, verbose_name="ID Bitrix")
    nome = models.CharField(max_length=255, verbose_name="Nome Bitrix")

    class Meta:
        verbose_name = "Usuário Bitrix (Cache)"
        verbose_name_plural = "Usuários Bitrix (Cache)"

    def __str__(self):
        return f"{self.nome} (ID: {self.id_bitrix})"


class LogAtualizacaoCPF(models.Model):
    id_bitrix = models.IntegerField(verbose_name="ID Bitrix")
    nome = models.CharField(max_length=255, verbose_name="Nome")
    cpf = models.CharField(max_length=20, verbose_name="CPF Atualizado")
    data_atualizacao = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")

    class Meta:
        verbose_name = "Log de Sincronização"
        verbose_name_plural = "Logs de Sincronização"
        ordering = ['-data_atualizacao']

    def __str__(self):
        return f"{self.nome} atualizado em {self.data_atualizacao.strftime('%d/%m/%Y %H:%M')}"

class MatchCPFCheck(models.Model):
    STATUS_OK = "OK"
    STATUS_SEM_MATCH = "SEM_MATCH"
    STATUS_DUPLICADO = "DUPLICADO"

    STATUS_CHOICES = [
        (STATUS_OK, "Coincidente"),
        (STATUS_SEM_MATCH, "Sem match"),
        (STATUS_DUPLICADO, "Duplicado"),
    ]

    id_bitrix = models.IntegerField(primary_key=True, verbose_name="ID Bitrix")
    nome = models.CharField(max_length=255, verbose_name="Nome Bitrix")
    cpf = models.CharField(max_length=20, null=True, blank=True, verbose_name="CPF")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    obs = models.TextField(blank=True)

    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Check Match (Ponto x Bitrix)"
        verbose_name_plural = "Checks Match (Ponto x Bitrix)"
        ordering = ["status", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.id_bitrix}) - {self.status}"

