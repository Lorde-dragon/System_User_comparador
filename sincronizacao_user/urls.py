from django.urls import path
from . import views

app_name = 'sincronizacao_user'

urlpatterns = [
    path('', views.index, name='index'),
    path('sincronizar-bases/', views.sync_bases, name='sync_bases'),  # NOVO
    path('executar/', views.run_sync, name='run_sync'),
]
