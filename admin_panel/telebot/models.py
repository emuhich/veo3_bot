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

    class Meta:
        verbose_name = "Генерация видео"
        verbose_name_plural = "Генерации видео"
        ordering = ("-created",)

    def __str__(self):
        return f"VideoGeneration {self.id} for {self.client}"
