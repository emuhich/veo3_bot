import json
import logging
import typing
from datetime import datetime, date, time
from decimal import Decimal

from django import VERSION
from django.contrib.postgres.fields import ArrayField
from django.core import exceptions
from django.db import models

if VERSION[0] == 3:
    from django.contrib.postgres.fields import JSONField
else:
    from django.db.models import JSONField

logger = logging.getLogger()


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (time, date, datetime)):
            return obj.isoformat()
        return super().default(obj)


class ConfigRow(models.Model):
    """Простая модель для значения одного конфига"""

    name = models.TextField(primary_key=True)
    value = JSONField(blank=True, null=True, encoder=CustomJSONEncoder)
    topic = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = ArrayField(models.TextField(blank=True, null=True), blank=True, null=True)
    last_read = models.DateTimeField(blank=True, null=True)
    last_set = models.DateTimeField(blank=True, null=True)
    registered_row_types: dict[str, typing.Any] = dict()
    registered_row_choices: dict[str, typing.Any] = dict()
    validators: dict[str, typing.Any] = dict()

    def validate_type(self):
        config_row_type = self.registered_row_types.get(self.name)
        if not config_row_type:
            return
        if not isinstance(self.value, config_row_type) and isinstance(
            config_row_type, (str, bool, int, float, list, dict, Decimal)
        ):
            raise exceptions.ValidationError(
                f"Type error of the input value '{self.name}': Expected type {config_row_type}, got {type(self.value)}"
            )

    def validate_value(self):
        validators = self.validators.get(self.name, None)
        if validators:
            for validator in validators:
                if not validator(self.value):
                    raise exceptions.ValidationError(
                        f"Validation error. Validator '{validator.__name__}', input value '{self.name}': {self.value}"
                    )

    def clean(self):
        self.validate_type()
        self.validate_value()

    def __repr__(self):
        return f"ConfigRow('{self.name}', {self.value})"

    def __str__(self):
        return f"Config '{self.name}' = {self.value}, {self.description or ''}"
