from django.core.management.base import BaseCommand

from admin_panel.liveconfigs.models import ConfigRow
from admin_panel.liveconfigs.utils import get_actual_config_names


class Command(BaseCommand):
    help = "Удалить конфиги, которые есть в БД, но нет в коде"

    def handle(self, *args, **kwargs):
        actual_configs = get_actual_config_names()
        unused_configs = ConfigRow.objects.exclude(name__in=actual_configs)

        if not unused_configs:
            print("Нет неиспользуемых конфигов")
            return

        names_to_delete = "\n".join([c.name for c in unused_configs])
        print(f"Будут удалены {len(unused_configs)} конфигов:")
        print(names_to_delete)

        if not kwargs.get("no_input", False):
            ack = input("Вы точно хотите удалить конфиги из списка выше? (y/n)\n")
            if ack != "y":
                return
        unused_configs.delete()
        print("Неиспользуемые конфиги удалены")

    def add_arguments(self, parser):
        parser.add_argument(
            "-ni", "--no-input", action="store_true", default=False, help="Без подтверждения"
        )
