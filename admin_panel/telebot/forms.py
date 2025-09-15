from django import forms


class MailingForm(forms.Form):
    media_type = forms.ChoiceField(choices=[
        ('no_media', 'Без медиа'),
        ('photo', 'Фото'),
        ('video', 'Видео'),
        ('document', 'Документ'),
    ], label='Тип медиа', initial='no_media')
    file = forms.FileField(
        required=False,
        label='Файл',
        help_text='Максимальный размер файла 50 мб',
        widget=forms.FileInput(attrs={'style_attribute': 'display:none'})
    )
    message_text = forms.CharField(widget=forms.Textarea(), max_length=4096, required=False, label='Текст рассылки',
                                   help_text='Если у вас есть медиа, текст рассылки не должен превышать 1024 символа,'
                                             'без медиа - 4096'
                                   )
    schedule_checkbox = forms.BooleanField(required=False, label='Разослать по времени',
                                           initial=False)
    schedule_datetime = forms.DateTimeField(
        required=False,
        label='Дата и время рассылки',
        widget=forms.DateTimeInput(attrs={'style_attribute': 'display:none', 'type': 'datetime-local'})
    )

    def __init__(self, *args, **kwargs):
        super(MailingForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            class_bootstrap = 'form-control' if field_name != 'schedule_checkbox' else 'form-check-input'
            field.widget.attrs.update({
                'class': class_bootstrap,
                'id': field_name,
                'name': field_name,
            })

    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')
        message_text = cleaned_data.get('message_text')
        schedule_checkbox = cleaned_data.get('schedule_checkbox')
        schedule_datetime = cleaned_data.get('schedule_datetime')
        file = cleaned_data.get('file')

        if not media_type:
            self.add_error('media_type', "Не выбран тип медиа")
        elif media_type != "no_media" and not file:
            self.add_error('media_type', "Не указано медиа рассылки")
        elif media_type == "no_media" and not message_text:
            self.add_error('message_text', "Не указан текст рассылки")
        elif schedule_checkbox and not schedule_datetime:
            self.add_error('schedule_datetime', "Не указано время рассылки")
        elif media_type == "no_media" and len(message_text) > 4096:
            self.add_error('message_text', "Длина текста рассылки не должна превышать 4096 символов")
        elif media_type != "no_media" and len(message_text) > 1024:
            self.add_error('message_text', "Длина текста рассылки с медиа не должна превышать 1024 символа")
        elif file:
            file_type = file.content_type.split('/')[0]
            if (media_type == "photo" and file_type != "image") or (media_type == "video" and file_type != "video") or \
                    (media_type == "document" and file_type != "application"):
                self.add_error('file', "Выбран неверный тип медиа")
            elif file.size > 52428800:
                self.add_error('file', "Максимальный размер файла: 50 мб")
