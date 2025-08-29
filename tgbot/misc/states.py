from aiogram.fsm.state import StatesGroup, State


class States(StatesGroup):
    prompt = State()
    photo = State()


class ChatStates(StatesGroup):
    free_chat_question = State()