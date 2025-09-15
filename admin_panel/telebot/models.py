import uuid

from django.db import models


class CreatedModel(models.Model):
    """Абстрактная модель. Добавляет дату создания."""

    created = models.DateTimeField("Дата создания", auto_now_add=True)
    updated = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")

    class Meta:
        abstract = True


class Client(CreatedModel):
    username = models.CharField(
        max_length=50,
        help_text="Username клиента",
        verbose_name="Username",
        blank=True,
        null=True,
    )
    telegram_id = models.BigIntegerField(
        help_text="Telegram ID пользователя", verbose_name="Telegram ID"
    )
    name = models.CharField(
        max_length=255, verbose_name="Имя в Telegram", help_text="Имя в Telegram"
    )
    url = models.CharField(max_length=255, verbose_name="Ссылка на пользователя")
    balance = models.IntegerField(
        default=0, verbose_name="Баланс", help_text="Баланс клиента"
    )
    free_chat_daily_limit = models.IntegerField(default=10, verbose_name="Лимит бесплатных ChatGPT сообщений в день")
    free_chat_used_today = models.IntegerField(default=0, verbose_name="Использовано сегодня (ChatGPT)")
    free_chat_last_reset = models.DateField(null=True, blank=True, verbose_name="Дата последнего сброса лимита")
    referral_code = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Реферальный код"
    )
    referral_earnings = models.IntegerField(
        default=0,
        verbose_name="Заработано на рефералах"
    )

    def ensure_referral_code(self):
        if not self.referral_code:
            while True:
                code = uuid.uuid4().hex[:8]
                if not Client.objects.filter(referral_code=code).exists():
                    self.referral_code = code
                    self.save(update_fields=["referral_code"])
                    break

    def ensure_free_chat_quota(self, today):
        # Сброс лимита если день сменился
        if self.free_chat_last_reset != today:
            self.free_chat_used_today = 0
            self.free_chat_last_reset = today

    def has_free_chat_quota(self):
        return self.free_chat_used_today < self.free_chat_daily_limit

    def inc_free_chat_usage(self):
        self.free_chat_used_today += 1

    class Meta:
        verbose_name = "Клиенты телеграмм бота"
        verbose_name_plural = "Клиенты телеграмм бота"
        ordering = ("-created",)

    def __str__(self):
        return "{} ({})".format(self.username, self.telegram_id)


class VideoGeneration(CreatedModel):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="video_generation",
        verbose_name="Клиент",
    )
    task_id = models.CharField(
        max_length=255,
        verbose_name="File ID видео",
        help_text="File ID сгенерированного видео",
    )
    status = models.CharField(
        max_length=50,
        verbose_name="Статус",
        help_text="Статус генерации видео",
        choices=[
            ("in_progress", "В процессе"),
            ("completed", "Завершено"),
            ("failed", "Не удалось"),
        ],
        default="in_progress",
    )
    message_id = models.BigIntegerField(
        verbose_name="Message ID",
        help_text="ID сообщения с видео в телеграм",
        null=True,
        blank=True,
    )
    result_url = models.URLField(
        verbose_name="Ссылка на видео",
        help_text="Ссылка на сгенерированное видео",
        null=True,
        blank=True,
    )
    failed_message = models.TextField(
        verbose_name="Сообщение об ошибке",
        help_text="Сообщение об ошибке при генерации видео",
        null=True,
        blank=True,
    )
    coins_charged = models.IntegerField(
        default=0,
        verbose_name="Списано монет",
        help_text="Сколько монет списано за это видео"
    )

    class Meta:
        verbose_name = "Генерация видео"
        verbose_name_plural = "Генерации видео"
        ordering = ("-created",)

    def __str__(self):
        return f"VideoGeneration {self.id} for {self.client}"


class Payment(CreatedModel):
    METHOD_CHOICES = [
        ("yookassa", "YooKassa"),
        ("cryptobot", "CryptoBot"),
        ("stars", "Telegram Stars"),
    ]
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("paid", "Оплачен"),
        ("failed", "Ошибка"),
        ("canceled", "Отменён"),
        ("expired", "Просрочен"),
    ]
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Клиент",
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    coins_requested = models.IntegerField(verbose_name="Монет запрошено")
    amount_rub = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Сумма в рублях")
    external_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="ID во внешней системе")
    external_payload = models.JSONField(blank=True, null=True)
    check_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на оплату")
    comment = models.CharField(max_length=255, blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ("-created",)

    def __str__(self):
        return f"Payment {self.id} {self.method} {self.status}"

    def mark_paid(self, dt):
        self.status = "paid"
        self.completed_at = dt
        self.save()

    def mark_failed(self, msg=None):
        self.status = "failed"
        if msg and not self.comment:
            self.comment = msg
        self.save()


class Referral(CreatedModel):
    inviter = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="referrals_made",
        verbose_name="Пригласивший"
    )
    invited = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="referral_origin",
        verbose_name="Приглашённый"
    )
    reward_coins = models.IntegerField(default=0, verbose_name="Монет начислено пригласившему")
    invited_bonus = models.IntegerField(default=0, verbose_name="Бонус приглашённому")

    class Meta:
        verbose_name = "Реферал"
        verbose_name_plural = "Рефералы"
        ordering = ("-created",)

    def __str__(self):
        return f"Referral {self.id}: {self.inviter_id} -> {self.invited_id}"


class Mailing(models.Model):
    CHOICES = (
        ("no_media", 'Без медиа'),
        ("photo", 'Фото'),
        ("video", 'Видео'),
        ("document", 'Документ'),
    )
    media_type = models.CharField(
        max_length=50,
        help_text='Тип медиа',
        verbose_name='Тип медиа',
        choices=CHOICES
    )
    text = models.TextField(
        max_length=4096,
        help_text='Текст рассылки',
        verbose_name='Текст',
        blank=True,
        null=True,
    )
    file_id = models.CharField(
        max_length=255,
        help_text='File ID медиа рассылки',
        verbose_name='File ID',
        blank=True,
        null=True,
    )
    date_malling = models.DateTimeField(
        help_text='Дата рассылки',
        verbose_name='Дата',
    )
    is_sent = models.BooleanField(
        help_text='Статус отправки',
        verbose_name='Статус отправки',
        default=False
    )

    class Meta:
        verbose_name = 'Рассылки'
        verbose_name_plural = 'Рассылки'

    def __str__(self):
        return str(self.pk)
