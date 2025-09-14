import json
from datetime import datetime, date, time
from decimal import Decimal

from django import forms
from django.conf import settings
from django_json_widget.widgets import JSONEditorWidget

from .models import ConfigRow


class PrettyJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, indent, sort_keys, **kwargs):
        super().__init__(*args, indent=2, sort_keys=True, **kwargs)


class ConfigRowForm(forms.ModelForm):
    class Meta:
        model = ConfigRow
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance_type = self.instance.registered_row_types.get(self.instance.name)
        if settings.LC_ENABLE_PRETTY_INPUT and not (
            isinstance(instance_type, list) or isinstance(instance_type, dict)
        ):
            max_len = settings.LC_MAX_STR_LENGTH_DISPLAYED_AS_TEXTINPUT or 50
            val = self.instance.value
            if isinstance(val, bool):
                self.fields["value"] = forms.BooleanField(
                    required=False,
                )
            elif isinstance(val, int):
                self.fields["value"] = forms.IntegerField(
                    required=False,
                )
            elif isinstance(val, float):
                self.fields["value"] = forms.FloatField(
                    required=False,
                    widget=forms.NumberInput(attrs={"step": "0.1"}),
                )
            elif isinstance(val, Decimal):
                self.fields["value"] = forms.DecimalField(
                    required=False,
                )
            elif isinstance(val, str):
                instance_choices = self.instance.registered_row_choices.get(self.instance.name)
                if instance_choices:
                    self.fields["value"] = forms.ChoiceField(
                        required=False, choices=instance_choices, widget=forms.Select()
                    )
                elif len(val) <= max_len:
                    self.fields["value"] = forms.CharField(
                        required=False, widget=forms.TextInput({"size": max_len})
                    )
            elif isinstance(val, (list, dict)):
                self.fields["value"] = forms.JSONField(
                    required=False, widget=JSONEditorWidget, encoder=PrettyJSONEncoder
                )
            elif isinstance(val, datetime):
                self.fields["value"] = forms.DateTimeField(
                    required=False,
                )
            elif isinstance(val, date):
                self.fields["value"] = forms.DateField(
                    required=False,
                )
            elif isinstance(val, time):
                self.fields["value"] = forms.TimeField(
                    required=False,
                )
