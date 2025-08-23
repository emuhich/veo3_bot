from aiogram.filters.callback_data import CallbackData


class BaseCD(CallbackData, prefix="base"):
    def init_subclass(cls, **kwargs):
        if not cls.name.endswith("CD"):
            raise ValueError("callback data class should ends with CD")
        kwargs["prefix"] = cls.name.lower().removesuffix("cd")
        super().init_subclass(**kwargs)
