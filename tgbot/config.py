# tgbot/config.py
from dataclasses import dataclass
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from environs import Env

from tgbot.services.video_generate import VideoGeneratorService
from tgbot.services.chat_gpt import ChatGPTService
from tgbot.services.yookassa_service import YandexKassaService
from tgbot.services.cryptobot_service import CryptoBotService
from tgbot.services.stars_service import StarsPaymentService


@dataclass
class DbConfig:
    host: str
    password: str
    user: str
    database: str


@dataclass
class Redis:
    host: str
    port: int
    db_fsm: str
    job_store: str


@dataclass
class TgBot:
    token: str
    admin_ids: list[int]
    use_redis: bool
    veo_svc: VideoGeneratorService
    gpt_svc: ChatGPTService
    yookassa_svc: YandexKassaService | None
    cryptobot_svc: CryptoBotService | None
    stars_svc: StarsPaymentService | None


@dataclass
class Miscellaneous:
    user_redis: bool
    scheduler: AsyncIOScheduler
    super_user_name: str
    super_user_pass: str


@dataclass
class Config:
    tg_bot: TgBot
    db: DbConfig
    misc: Miscellaneous
    redis: Redis


def load_config(path: str = None):
    env = Env()
    env.read_env(path)

    # Инициализация платежных сервисов (если заданы переменные окружения)
    yookassa = None
    if env.str("YOOKASSA_SHOP_ID", default="") and env.str("YOOKASSA_API_KEY", default=""):
        yookassa = YandexKassaService(
            shop_id=env.str("YOOKASSA_SHOP_ID"),
            api_key=env.str("YOOKASSA_API_KEY"),
        )

    cryptobot = None
    if env.str("CRYPTOBOT_TOKEN", default=""):
        cryptobot = CryptoBotService(
            token=env.str("CRYPTOBOT_TOKEN"),
            mainnet=env.bool("CRYPTOBOT_MAINNET", default=True),
        )

    stars = StarsPaymentService()  # без параметров

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMINS"))),
            use_redis=env.bool("USE_REDIS"),
            veo_svc=VideoGeneratorService(
                prompt_file=env.str("PROMPT_FILE"),
                prompt_api_key=env.str("OPENROUTER_API_KEY"),
                video_api_token=env.str("VEO_API_KEY"),
            ),
            gpt_svc=ChatGPTService(api_key=env.str("OPENAI_API_KEY")),
            yookassa_svc=yookassa,
            cryptobot_svc=cryptobot,
            stars_svc=stars,
        ),
        db=DbConfig(
            host=env.str("DB_HOST"),
            password=env.str("PG_PASSWORD"),
            user=env.str("DB_USER"),
            database=env.str("DB_NAME"),
        ),
        misc=Miscellaneous(
            user_redis=env.bool("USE_REDIS"),
            scheduler=AsyncIOScheduler(timezone=env.str("TIME_ZONE")),
            super_user_name=env.str("SUPER_USER_NAME"),
            super_user_pass=env.str("SUPER_USER_PASS"),
        ),
        redis=Redis(
            host=env.str("REDIS_HOST"),
            port=env.int("REDIS_PORT"),
            db_fsm=env.str("REDIS_DB_FSM"),
            job_store=env.str("REDIS_DB_JOBSTORE"),
        ),
    )