from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LiveconfigsConfig(AppConfig):
    name = "admin_panel.liveconfigs"
    verbose_name = _("Liveconfigs")
