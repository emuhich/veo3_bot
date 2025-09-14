import datetime as dt
import json
import logging
import time

from django.core import exceptions

from admin_panel.liveconfigs.models.models import ConfigRow
from admin_panel.liveconfigs.signals import config_row_update_signal

logger = logging.getLogger()

DESCRIPTION_SUFFIX = "_DESCRIPTION"
TAGS_SUFFIX = "_TAGS"
VALIDATORS_SUFFIX = "_VALIDATORS"
CHOICES_SUFFIX = "_CHOICES"

CACHE_TTL = 60 * 10  # 10 mins


class ConfigRowDescriptor:
    """Кеширующий дескриптор для работы с конфигами"""

    def __init__(self, config_name, default_value, description=None, topic=None, tags=None):
        self.config_name = config_name
        self.default_value = default_value
        self.last_value = default_value
        self.next_check = None
        self.description = description
        self.tags = tags
        self.topic = topic

    def formatted_value(self):
        if isinstance(self.default_value, dt.date):
            self.last_value = dt.date.fromisoformat(self.last_value)
        elif isinstance(self.default_value, dt.time):
            self.last_value = dt.time.fromisoformat(self.last_value)
        elif isinstance(self.default_value, dt.datetime):
            self.last_value = dt.datetime.fromisoformat(self.last_value)

    def __get__(self, obj, klass=None):
        now = time.time()
        if not self.next_check or now > self.next_check:
            dt_now = dt.datetime.now(tz=dt.timezone.utc)
            try:
                logger.info("accessing db to grab config %s", self.config_name)
                db_row = ConfigRow.objects.get(name=self.config_name)
                update_fields = {}
                if db_row.description != self.description:
                    update_fields["description"] = self.description
                if db_row.tags != self.tags:
                    update_fields["tags"] = self.tags
                if db_row.topic != self.topic:
                    update_fields["topic"] = self.topic
                if db_row.last_read is None or (db_row.last_read < dt_now - dt.timedelta(days=1)):
                    update_fields["last_read"] = dt_now
                if update_fields:
                    config_row_update_signal.send(
                        sender=None, config_name=self.config_name, update_fields=update_fields
                    )
                self.last_value = db_row.value
                self.formatted_value()
            except exceptions.ObjectDoesNotExist:
                logger.warning(
                    "no config %s in db, using default value %s",
                    self.config_name,
                    self.default_value,
                )
                self.last_value = self.default_value
                self.formatted_value()
                update_fields = {
                    "name": self.config_name,
                    "value": self.last_value,
                    "description": self.description,
                    "tags": self.tags,
                    "topic": self.topic,
                    "last_read": dt_now,
                    "last_set": dt_now,
                }
                config_row_update_signal.send(
                    sender=None, config_name=self.config_name, update_fields=update_fields
                )

        self.next_check = now + CACHE_TTL
        return self.last_value


class ConfigMeta(type):
    """Metaclass for configs. Replaces all attributes with descriptors"""

    def __new__(cls, name, bases, dct):
        prefix = dct.get("__prefix__", "")
        if prefix and not prefix.endswith("_"):
            prefix += "_"

        dct["__prefix__"] = prefix
        dct["__topic__"] = dct.get("__topic__", name)
        dct["__exported__"] = dct.get("__exported__", "__all__")

        config_row_types = dct.get("__annotations__", {})
        config_row_choices = {}
        validators = {}

        for n, v in dct.items():
            if not n.startswith("__") and not n.endswith(
                (DESCRIPTION_SUFFIX, TAGS_SUFFIX, VALIDATORS_SUFFIX, CHOICES_SUFFIX)
            ):
                if prefix and n in config_row_types:
                    config_row_types[prefix + n] = config_row_types.pop(n)
                dct[n] = ConfigRowDescriptor(
                    prefix + n,
                    v,
                    description=dct.get(n + DESCRIPTION_SUFFIX),
                    tags=dct.get(n + TAGS_SUFFIX),
                    topic=dct["__topic__"],
                )
                config_row_choices[n] = dct.get(n + CHOICES_SUFFIX)
                validators[n] = dct.get(n + VALIDATORS_SUFFIX)

        dct = {
            name: value
            for name, value in dct.items()
            if not name.endswith(
                (DESCRIPTION_SUFFIX, TAGS_SUFFIX, VALIDATORS_SUFFIX, CHOICES_SUFFIX)
            )
        }

        ConfigRow.registered_row_types.update(config_row_types)
        ConfigRow.registered_row_choices.update(config_row_choices)
        ConfigRow.validators.update(validators)
        return super().__new__(cls, name, bases, dct)


class BaseConfig(metaclass=ConfigMeta):
    """От этого класса можно наследовать конфиги.
    За значениями этих конфигов система будет обращаться к БД и фоллбечиться
    на значения атрибутов, указаные в самом классе"""
