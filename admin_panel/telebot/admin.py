from admin_interface.admin import ThemeAdmin
from admin_interface.models import Theme
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html

from admin_panel.telebot.models import Client, VideoGeneration


class BotAdminSite(AdminSite):
    site_title = "Управление ботом"
    site_header = "Управление ботом"
    index_title = ""


bot_admin = BotAdminSite()


@admin.register(Theme, site=bot_admin)
class AdminTheme(ThemeAdmin):
    pass


@admin.register(Client, site=bot_admin)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "user_link",
        "username",
        "telegram_id",
        "balance",
    )
    list_display_links = ("pk", "username")
    empty_value_display = "-пусто-"
    search_fields = ("username", "telegram_id")

    def user_link(self, obj: Client):
        if obj.username and obj.name:
            return format_html(
                '<a href="https://t.me/{}">{}</a>', obj.username, obj.name
            )
        else:
            return obj.url

    user_link.short_description = "Ссылка"


@admin.register(VideoGeneration, site=bot_admin)
class VideoGenerationAdmin(admin.ModelAdmin):
    list_display = ("pk", "client", "task_id", "status", "created")
    list_display_links = ("pk", "task_id")
    list_filter = ("status",)
    search_fields = ("client__username", "client__telegram_id", "task_id")
    empty_value_display = "-пусто-"
    readonly_fields = ("created", "updated")
