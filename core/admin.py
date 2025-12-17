from django.contrib import admin
from .models import (
    BitrixUser, PontoContact, GesttaUser, DominioAccount, CcontrolWebUser,
    SyncRun, SyncDetail
)

admin.site.register(BitrixUser)
admin.site.register(PontoContact)
admin.site.register(GesttaUser)
admin.site.register(DominioAccount)
admin.site.register(CcontrolWebUser)
admin.site.register(SyncRun)
admin.site.register(SyncDetail)
