from django.contrib import admin
from .models import (
    ColaboradorPonto, UsuarioBitrix, LogAtualizacaoCPF
)

admin.site.register(ColaboradorPonto)
admin.site.register(UsuarioBitrix)
admin.site.register(LogAtualizacaoCPF)