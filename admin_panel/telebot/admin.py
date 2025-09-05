from admin_interface.admin import ThemeAdmin
from admin_interface.models import Theme
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.html import format_html
from django.utils import timezone
from admin_panel.telebot.models import Client, VideoGeneration, Payment


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


@admin.register(Payment, site=bot_admin)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "method",
        "status",
        "coins_requested",
        "amount_rub",
        "external_id",
        "created",
        "completed_at",
    )
    list_filter = ("method", "status", "created")
    search_fields = ("client__username", "client__telegram_id", "external_id", "id")
    readonly_fields = ("created", "updated", "completed_at")
    empty_value_display = "-пусто-"
    actions = ["mark_as_paid"]

    def mark_as_paid(self, request, queryset):
        now = timezone.now()
        updated = 0
        for obj in queryset:
            if obj.status != "paid":
                obj.status = "paid"
                if not obj.completed_at:
                    obj.completed_at = now
                obj.save(update_fields=["status", "completed_at"])
                # Начисление монет клиенту (если ещё не было)
                # Проверяем, чтобы не было двойного начисления
                # (можно хранить флаг, но здесь упрощённо — если статус был не paid)
                client = obj.client
                client.balance += obj.coins_requested
                client.save(update_fields=["balance"])
                updated += 1
        self.message_user(request, f"Отмечено оплаченных: {updated}")

    mark_as_paid.short_description = "Отметить выбранные как оплаченные"
