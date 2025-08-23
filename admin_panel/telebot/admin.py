from admin_interface.admin import ThemeAdmin
from admin_interface.models import Theme
from django.contrib import admin
from django.contrib.admin import AdminSite


class BotAdminSite(AdminSite):
    site_title = "Управление ботом"
    site_header = "Управление ботом"
    index_title = ""


bot_admin = BotAdminSite()


@admin.register(Theme, site=bot_admin)
class AdminTheme(ThemeAdmin):
    pass
