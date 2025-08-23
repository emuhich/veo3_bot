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

    class Meta:
        verbose_name = "Клиенты телеграмм бота"
        verbose_name_plural = "Клиенты телеграмм бота"
        ordering = ("-created",)

    def __str__(self):
        return "{} ({})".format(self.username, self.telegram_id)
