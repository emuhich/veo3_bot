from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from environs import Env

from tgbot.services.chat_gpt import ChatGPTService
from tgbot.services.video_generate import VideoGeneratorService


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

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN"),
            admin_ids=list(map(int, env.list("ADMINS"))),
            use_redis=env.bool("USE_REDIS"),
            veo_svc=VideoGeneratorService(
                prompt_file=env.str("PROMPT_FILE"),
                prompt_api_key=env.str("OPENROUTER_API_KEY"),
                video_api_token=env.str("VEO_API_KEY")
            ),
            gpt_svc=ChatGPTService(api_key=env.str("OPENAI_API_KEY"))
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
