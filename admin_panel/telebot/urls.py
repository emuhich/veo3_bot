from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path('mailing', views.mailing, name='mailing'),
]
