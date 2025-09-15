from admin_interface.admin import ThemeAdmin
from admin_interface.models import Theme
from django.contrib import admin
from django.contrib.admin import AdminSite, ModelAdmin
from django.utils.html import format_html
from django.utils import timezone
from django.db import transaction

from admin_panel.telebot.forms import MailingForm
from admin_panel.telebot.models import Client, VideoGeneration, Payment, Referral, Mailing


class BotAdminSite(AdminSite):
    site_title = "Управление ботом"
    site_header = "Управление ботом"
    index_title = ""


bot_admin = BotAdminSite()


@admin.register(Theme, site=bot_admin)
class AdminTheme(ThemeAdmin):
    pass


class ReferralInline(admin.TabularInline):
    model = Referral
    fk_name = "inviter"
    extra = 0
    verbose_name = "Реферал"
    verbose_name_plural = "Рефералы"
    readonly_fields = ("invited", "reward_coins", "invited_bonus", "created")
    can_delete = False
    show_change_link = True


@admin.register(Client, site=bot_admin)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "user_link",
        "username",
        "telegram_id",
        "balance",
        "referral_code",
        "referral_earnings",
        "free_chat_used_today",
        "created",
    )
    list_display_links = ("pk", "username")
    list_editable = ("balance",)
    empty_value_display = "-пусто-"
    search_fields = (
        "username",
        "telegram_id",
        "referral_code",
        "name",
    )
    list_filter = (
        "created",
        "free_chat_last_reset",
    )
    date_hierarchy = "created"
    readonly_fields = ("created", "updated")
    inlines = (ReferralInline,)
    actions = ("generate_ref_codes", "reset_free_chat_quota")

    def user_link(self, obj: Client):
        if obj.username and obj.name:
            return format_html('<a href="https://t.me/{}">{}</a>', obj.username, obj.name)
        return obj.url

    user_link.short_description = "Ссылка"

    def generate_ref_codes(self, request, queryset):
        generated = 0
        for obj in queryset:
            if not obj.referral_code:
                obj.ensure_referral_code()
                generated += 1
        self.message_user(request, f"Сгенерировано кодов: {generated}")

    generate_ref_codes.short_description = "Сгенерировать реф.коды"

    def reset_free_chat_quota(self, request, queryset):
        updated = queryset.update(free_chat_used_today=0)
        self.message_user(request, f"Сброшено лимитов: {updated}")

    reset_free_chat_quota.short_description = "Сбросить дневной лимит ChatGPT"


class ChargedFilter(admin.SimpleListFilter):
    title = "Списание монет"
    parameter_name = "charged"

    def lookups(self, request, model_admin):
        return (
            ("charged", "> 0"),
            ("zero", "= 0"),
        )

    def queryset(self, request, queryset):
        if self.value() == "charged":
            return queryset.filter(coins_charged__gt=0)
        if self.value() == "zero":
            return queryset.filter(coins_charged=0)
        return queryset


@admin.register(VideoGeneration, site=bot_admin)
class VideoGenerationAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "client",
        "task_id",
        "status",
        "coins_charged",
        "created",
    )
    list_display_links = ("pk", "task_id")
    list_filter = ("status", ChargedFilter, "created")
    search_fields = (
        "client__username",
        "client__telegram_id",
        "task_id",
    )
    empty_value_display = "-пусто-"
    readonly_fields = ("created", "updated")
    actions = ("refund_failed",)
    list_select_related = ("client",)
    date_hierarchy = "created"

    def refund_failed(self, request, queryset):
        refunded = 0
        for vg in queryset.select_related("client"):
            if vg.status == "failed" and vg.coins_charged > 0:
                with transaction.atomic():
                    client = vg.client
                    client.balance += vg.coins_charged
                    client.save(update_fields=["balance"])
                    vg.coins_charged = 0
                    vg.save(update_fields=["coins_charged"])
                    refunded += 1
        self.message_user(request, f"Возвращено монет по задачам: {refunded}")

    refund_failed.short_description = "Вернуть монеты за failed"


class HasExternalIDFilter(admin.SimpleListFilter):
    title = "Есть external ID"
    parameter_name = "has_ext"

    def lookups(self, request, model_admin):
        return (("yes", "Да"), ("no", "Нет"))

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(external_id__isnull=True).exclude(external_id__exact="")
        if self.value() == "no":
            return queryset.filter(external_id__isnull=True) | queryset.filter(external_id__exact="")
        return queryset


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
    list_filter = ("method", "status", HasExternalIDFilter, "created")
    search_fields = (
        "client__username",
        "client__telegram_id",
        "external_id",
        "id",
        "comment",
    )
    readonly_fields = ("created", "updated", "completed_at")
    empty_value_display = "-пусто-"
    actions = ["mark_as_paid"]
    date_hierarchy = "created"
    list_select_related = ("client",)

    def mark_as_paid(self, request, queryset):
        now = timezone.now()
        updated = 0
        for obj in queryset.select_related("client"):
            if obj.status != "paid":
                obj.status = "paid"
                if not obj.completed_at:
                    obj.completed_at = now
                obj.save(update_fields=["status", "completed_at"])
                client = obj.client
                client.balance += obj.coins_requested
                client.save(update_fields=["balance"])
                updated += 1
        self.message_user(request, f"Отмечено оплаченных: {updated}")

    mark_as_paid.short_description = "Отметить выбранные как оплаченные"


@admin.register(Referral, site=bot_admin)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "inviter",
        "invited",
        "reward_coins",
        "invited_bonus",
        "created",
    )
    list_filter = ("created",)
    search_fields = (
        "inviter__username",
        "inviter__telegram_id",
        "invited__username",
        "invited__telegram_id",
    )
    readonly_fields = ("created", "updated")
    list_select_related = ("inviter", "invited")
    date_hierarchy = "created"
    empty_value_display = "-пусто-"


@admin.register(Mailing, site=bot_admin)
class MailingAdmin(ModelAdmin):
    add_form_template = 'tgbot/form_mailing.html'
    list_display = (
        'pk',
        'media_type',
        'text',
        'file_id',
        'date_malling',
        'is_sent',
    )

    list_display_links = ('pk',)
    empty_value_display = '-пусто-'

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['form'] = MailingForm()
        return super().add_view(request, form_url, extra_context)

    class Meta:
        verbose_name_plural = 'Рассылка'
