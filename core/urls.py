from django.urls import path
from django.contrib.auth.decorators import login_required, user_passes_test
from . import views

is_staff_required = user_passes_test(lambda u: u.is_staff)

app_name = "core"

urlpatterns = [
    path("", login_required(views.dashboard), name="dashboard"),
    path("sync/", is_staff_required(views.sync_manual), name="sync_manual"),
]
 