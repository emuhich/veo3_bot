import os
from enum import Enum

from admin_panel.liveconfigs import models


class ConfigTags(str, Enum):
   bot = "Настройки для бота"
   admin = "Настройки для админки"


class MainConfig(models.BaseConfig):
    __topic__ = "Основные настройки"

    CONT_MONEY_PER_FAST_VERSION: int = os.getenv("CONT_MONEY_PER_FAST_VERSION", 2)
    CONT_MONEY_PER_FAST_VERSION_DESCRIPTION = "Стоимость видео в ускоренной версии (в монетах)"
    CONT_MONEY_PER_FAST_VERSION_TAGS = [ConfigTags.bot]

    CONT_MONEY_PER_NORMAL_VERSION: int = os.getenv("CONT_MONEY_PER_NORMAL_VERSION", 4)
    CONT_MONEY_PER_NORMAL_VERSION_DESCRIPTION = "Стоимость видео в нормальной версии (в монетах)"
    CONT_MONEY_PER_NORMAL_VERSION_TAGS = [ConfigTags.bot]

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_API_KEY_DESCRIPTION = "API ключ для OpenRouter (ChatGPT)"
    OPENROUTER_API_KEY_TAGS = [ConfigTags.bot]

    VEO_API_KEY: str = os.getenv("VEO_API_KEY", "")
    VEO_API_KEY_DESCRIPTION = "API ключ для Veo (генерация видео)"
    VEO_API_KEY_TAGS = [ConfigTags.bot]

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_KEY_DESCRIPTION = "API ключ для OpenAI (ChatGPT)"
    OPENAI_API_KEY_TAGS = [ConfigTags.bot]

    YOOKASSA_SHOP_ID: str = os.getenv("YOOKASSA_SHOP_ID", "")
    YOOKASSA_SHOP_ID_DESCRIPTION = "ID магазина в ЮKassa"
    YOOKASSA_SHOP_ID_TAGS = [ConfigTags.bot, ConfigTags.admin]

    YOOKASSA_API_KEY: str = os.getenv("YOOKASSA_API_KEY", "")
    YOOKASSA_API_KEY_DESCRIPTION = "Секретный ключ магазина в ЮKassa"
    YOOKASSA_API_KEY_TAGS = [ConfigTags.bot, ConfigTags.admin]

    CRYPTOBOT_TOKEN: str = os.getenv("CRYPTOBOT_TOKEN", "")
    CRYPTOBOT_TOKEN_DESCRIPTION = "Токен для CryptoBot"
    CRYPTOBOT_TOKEN_TAGS = [ConfigTags.bot, ConfigTags.admin]

    REF_INVITER_REWARD: int = os.getenv("REF_INVITER_REWARD", 3)
    REF_INVITER_REWARD_DESCRIPTION = "Вознаграждение пригласившему (в монетах)"
    REF_INVITER_REWARD_TAGS = [ConfigTags.bot]

    REF_INVITED_BONUS: int = os.getenv("REF_INVITED_BONUS", 1)
    REF_INVITED_BONUS_DESCRIPTION = "Бонус приглашённому (в монетах)"
    REF_INVITED_BONUS_TAGS = [ConfigTags.bot]

    COIN_RATE_RUB: float = os.getenv("COIN_RATE_RUB", 80)
    COIN_RATE_RUB_DESCRIPTION = "Оценочный курс 1 монеты в RUB (для расчёта стоимости в монетах)"
    COIN_RATE_RUB_TAGS = [ConfigTags.bot]

    TG_STARS_RATE_RUB: float = os.getenv("TG_STARS_RATE_RUB", 2.5)
    TG_STARS_RATE_RUB_DESCRIPTION = "Оценочный курс 1 Star (XTR) в RUB (для расчёта стоимости в монетах)"
    TG_STARS_RATE_RUB_TAGS = [ConfigTags.bot]
