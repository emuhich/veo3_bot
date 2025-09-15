from datetime import datetime

import pytz
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

from admin_panel.telebot.models import Client, Mailing


class AsyncDatabaseOperations:
    @staticmethod
    @sync_to_async
    def create_object(model, **kwargs):
        """
        Создает объект модели с заданными параметрами
        """
        return model.objects.create(**kwargs)

    @staticmethod
    @sync_to_async
    def get_object_or_none(model, **kwargs):
        """
        Возвращает объект модели, соответствующий заданным параметрам, или None, если такого объекта не существует
        """
        return model.objects.filter(**kwargs).first()

    @staticmethod
    @sync_to_async
    def get_all_objects(model):
        """
        Возвращает все объекты заданной модели
        """
        return model.objects.all()

    @staticmethod
    @sync_to_async
    def delete_object(model, **kwargs):
        """
        Удаляет объект модели, соответствующий заданным параметрам
        """
        obj = model.objects.filter(**kwargs).first()
        if obj:
            obj.delete()

    @staticmethod
    @sync_to_async
    def get_objects_filter(model, **kwargs):
        """
        Возвращает объекты модели, соответствующий заданным параметрам
        """
        return model.objects.filter(**kwargs)


# Создание объекта
# user = await AsyncDatabaseOperations.create_object(User, username='test', password='test')
#
# # Получение объекта или None
# user = await AsyncDatabaseOperations.get_object_or_none(User, username='test')
#
# # Получение всех объектов
# all_users = await AsyncDatabaseOperations.get_all_objects(User)


@sync_to_async()
def select_client(telegram_id):
    """
    Возвращает пользователя по телеграм ID
    """
    return Client.objects.filter(telegram_id=telegram_id).first()


@sync_to_async()
def create_client(username, telegram_id, url, name):
    """
    Создает пользователя
    """
    Client.objects.create(
        telegram_id=telegram_id, username=username, url=url, name=name
    )


@sync_to_async()
def create_super_user(username, password):
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, password=password)


@sync_to_async()
def get_all_malling():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    return Mailing.objects.filter(is_sent=False, date_malling__lte=now)


@sync_to_async()
def get_all_users():
    return Client.objects.all()
