# -*- coding: utf-8 -*-
"""Телеграм-бот «Внутренний путь» — проводник по этапам развития."""

import asyncio
import logging
import os
from collections import Counter

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import db
from content import LETTERS, PRACTICES, QUESTIONS, TYPES, WELCOME
from tasks import PROGRAM_NOT_READY, TASKS, get_final

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

dp = Dispatcher()

# user_id -> список ответов (индексы 0..3)
sessions: dict[int, list[int]] = {}


# ---------- Клавиатуры ----------

def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню, разбитое на секции."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            # Узнать себя
            [InlineKeyboardButton(text="📝  Пройти тест", callback_data="start_test")],
            # Мой путь
            [
                InlineKeyboardButton(text="📅  Задание дня",  callback_data="daily_task"),
                InlineKeyboardButton(text="🧘  Моя практика", callback_data="my_practice"),
            ],
            # Изучить
            [
                InlineKeyboardButton(text="📖  4 типа людей", callback_data="show_types"),
                InlineKeyboardButton(text="✨  Все практики",  callback_data="show_practices"),
            ],
        ]
    )


def question_kb(q_index: int) -> InlineKeyboardMarkup:
    """Кнопки только с буквой — полный текст варианта уже в сообщении."""
    row = [
        InlineKeyboardButton(text=LETTERS[i], callback_data=f"ans:{q_index}:{i}")
        for i in range(4)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row])


def types_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1-й тип", callback_data="type:1"),
                InlineKeyboardButton(text="2-й тип", callback_data="type:2"),
            ],
            [
                InlineKeyboardButton(text="3-й тип", callback_data="type:3"),
                InlineKeyboardButton(text="4-й тип", callback_data="type:4"),
            ],
            [InlineKeyboardButton(text="⬅️  В меню", callback_data="menu")],
        ]
    )


def practices_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Для 1-го типа", callback_data="practice:1"),
                InlineKeyboardButton(text="Для 2-го типа", callback_data="practice:2"),
            ],
            [
                InlineKeyboardButton(text="Для 3-го типа", callback_data="practice:3"),
                InlineKeyboardButton(text="Для 4-го типа", callback_data="practice:4"),
            ],
            [InlineKeyboardButton(text="⬅️  В меню", callback_data="menu")],
        ]
    )


def result_kb(type_num: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧘  Моя практика",         callback_data=f"practice:{type_num}")],
            [InlineKeyboardButton(text="📅  Начать 30-дневную программу", callback_data="start_program")],
            [InlineKeyboardButton(text="🔄  Пройти тест заново",   callback_data="start_test")],
            [InlineKeyboardButton(text="⬅️  В меню",               callback_data="menu")],
        ]
    )


# ---------- Логика теста ----------

async def send_question(message: Message, q_index: int) -> None:
    q = QUESTIONS[q_index]
    options_text = "\n".join(
        f"{LETTERS[i]})  {opt}"
        for i, opt in enumerate(q["options"])
    )
    text = (
        f"<b>Вопрос {q_index + 1} из {len(QUESTIONS)}</b>\n\n"
        f"{q['text']}\n\n"
        f"{options_text}"
    )
    await message.answer(text, reply_markup=question_kb(q_index))


def calc_result(answers: list[int]) -> int:
    counts = Counter(answers)
    best_type, best_count = 1, -1
    for t in (1, 2, 3, 4):
        c = counts.get(t - 1, 0)
        if c > best_count:
            best_count, best_type = c, t
    return best_type


# ---------- Хендлеры ----------

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@dp.message(Command("test"))
async def cmd_test(message: Message) -> None:
    sessions[message.from_user.id] = []
    await send_question(message, 0)


@dp.message(Command("types"))
async def cmd_types(message: Message) -> None:
    await message.answer("Выберите тип, чтобы прочитать описание:", reply_markup=types_kb())


@dp.message(Command("practices"))
async def cmd_practices(message: Message) -> None:
    await message.answer("Выберите практику для своего типа:", reply_markup=practices_kb())


@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery) -> None:
    await callback.message.answer(WELCOME, reply_markup=main_menu_kb())
    await callback.answer()


@dp.callback_query(F.data == "start_test")
async def cb_start_test(callback: CallbackQuery) -> None:
    sessions[callback.from_user.id] = []
    await callback.message.answer(
        "📝 <b>Тест: на каком этапе взаимодействия с сознанием ты находишься?</b>\n\n"
        "12 вопросов. Отвечай честно, выбирая вариант, который ближе всего "
        "к твоему опыту.\n\n"
        "Варианты перечислены в тексте каждого вопроса — "
        "нажми кнопку с нужной буквой."
    )
    await send_question(callback.message, 0)
    await callback.answer()


@dp.callback_query(F.data == "show_types")
async def cb_show_types(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Выберите тип, чтобы прочитать описание:", reply_markup=types_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "show_practices")
async def cb_show_practices(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "Выберите практику для своего типа:", reply_markup=practices_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "my_practice")
async def cb_my_practice(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    type_num = db.get_user_type(user_id)
    if type_num is None:
        await callback.message.answer(
            "Сначала пройди тест — тогда я покажу практику именно для твоего типа 🙂",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📝  Пройти тест", callback_data="start_test")]]
            ),
        )
    else:
        await callback.message.answer(PRACTICES[type_num], reply_markup=practices_kb())
    await callback.answer()


@dp.callback_query(F.data.startswith("type:"))
async def cb_type(callback: CallbackQuery) -> None:
    type_num = int(callback.data.split(":")[1])
    await callback.message.answer(TYPES[type_num], reply_markup=types_kb())
    await callback.answer()


@dp.callback_query(F.data.startswith("practice:"))
async def cb_practice(callback: CallbackQuery) -> None:
    type_num = int(callback.data.split(":")[1])
    await callback.message.answer(PRACTICES[type_num], reply_markup=practices_kb())
    await callback.answer()


@dp.callback_query(F.data.startswith("ans:"))
async def cb_answer(callback: CallbackQuery) -> None:
    _, q_index_str, opt_str = callback.data.split(":")
    q_index, opt = int(q_index_str), int(opt_str)
    user_id = callback.from_user.id

    answers = sessions.setdefault(user_id, [])

    if q_index != len(answers):
        await callback.answer("Этот вопрос уже отвечен 🙂", show_alert=False)
        return

    answers.append(opt)

    try:
        await callback.message.edit_text(
            callback.message.html_text + f"\n\n✅ Твой ответ: {LETTERS[opt]}"
        )
    except Exception:
        pass

    if len(answers) < len(QUESTIONS):
        await send_question(callback.message, len(answers))
    else:
        type_num = calc_result(answers)
        sessions.pop(user_id, None)
        db.set_user_type(user_id, type_num)
        await callback.message.answer(
            f"🎯 <b>Твой результат: {type_num}-й тип</b>\n\n{TYPES[type_num]}",
            reply_markup=result_kb(type_num),
        )
    await callback.answer()


# ---------- 30-дневная программа ----------

async def send_daily_task(message: Message, user_id: int) -> None:
    type_num = db.get_user_type(user_id)
    if type_num is None:
        await message.answer(
            "Сначала пройди тест — тогда я подберу задания именно для твоего типа 🙂",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📝  Пройти тест", callback_data="start_test")]]
            ),
        )
        return

    tasks = TASKS.get(type_num)
    if not tasks:
        await message.answer(PROGRAM_NOT_READY, reply_markup=main_menu_kb())
        return

    day = db.get_program_day(user_id)
    if day is None:
        await message.answer(
            f"📅 <b>30-дневная программа — {type_num}-й тип</b>\n\n"
            "Каждый день одно задание. "
            "Новое открывается на следующий календарный день.\n\n"
            "Начать сегодня?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🚀  Начать программу", callback_data="start_program")],
                    [InlineKeyboardButton(text="⬅️  В меню",           callback_data="menu")],
                ]
            ),
        )
        return

    if day > len(tasks):
        await message.answer(
            get_final(type_num),
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄  Пройти тест заново",       callback_data="start_test")],
                    [InlineKeyboardButton(text="🔁  Начать программу заново",  callback_data="restart_program")],
                    [InlineKeyboardButton(text="⬅️  В меню",                   callback_data="menu")],
                ]
            ),
        )
        return

    await message.answer(
        f"📅 <b>День {day} из {len(tasks)}</b>\n\n{tasks[day - 1]}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️  В меню", callback_data="menu")]]
        ),
    )


@dp.message(Command("day"))
async def cmd_day(message: Message) -> None:
    await send_daily_task(message, message.from_user.id)


@dp.callback_query(F.data == "daily_task")
async def cb_daily_task(callback: CallbackQuery) -> None:
    await send_daily_task(callback.message, callback.from_user.id)
    await callback.answer()


@dp.callback_query(F.data == "start_program")
async def cb_start_program(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    type_num = db.get_user_type(user_id)
    if type_num is None:
        await callback.answer("Сначала пройди тест 🙂", show_alert=True)
        return
    if not TASKS.get(type_num):
        await callback.message.answer(PROGRAM_NOT_READY, reply_markup=main_menu_kb())
        await callback.answer()
        return
    if db.get_program_day(user_id) is None:
        db.start_program(user_id)
    await send_daily_task(callback.message, user_id)
    await callback.answer()


@dp.callback_query(F.data == "restart_program")
async def cb_restart_program(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    db.reset_program(user_id)
    db.start_program(user_id)
    await send_daily_task(callback.message, user_id)
    await callback.answer()


@dp.message()
async def fallback(message: Message) -> None:
    await message.answer(
        "Воспользуйся меню или командами:\n"
        "/start — главное меню\n"
        "/test — пройти тест\n"
        "/day — задание дня\n"
        "/types — четыре типа людей\n"
        "/practices — все практики",
        reply_markup=main_menu_kb(),
    )


async def main() -> None:
    db.init_db()
    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN. Укажите токен в переменной окружения BOT_TOKEN или в файле .env"
        )
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logger.info("Бот «Внутренний путь» запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
        BOT_TOKEN = os.getenv("BOT_TOKEN")
    except ImportError:
        pass
    asyncio.run(main())
