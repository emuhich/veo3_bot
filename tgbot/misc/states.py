from aiogram.fsm.state import StatesGroup, State


class States(StatesGroup):
    prompt = State()
    photo = State()


class ChatStates(StatesGroup):
    free_chat_question = State()


class BalanceStates(StatesGroup):
    choose_amount = State()
    custom_amount = State()
    waiting_method = State()
    waiting_payment = State()
