import asyncio
import os
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile, LabeledPrice, PreCheckoutQuery
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
GUIDE_FILE = os.getenv("GUIDE_FILE", "guide.pdf")
GUIDE_PRICE_RUB = int(os.getenv("GUIDE_PRICE_RUB", "390"))
PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "RUB")

if not BOT_TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN. Создай .env по примеру .env.example")

if not PAYMENT_PROVIDER_TOKEN:
    raise RuntimeError("Не найден PAYMENT_PROVIDER_TOKEN. Получи тестовый токен ЮKassa в BotFather и добавь его в .env")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dataclass
class UserSession:
    score: int = 0
    question_index: int = 0


sessions = {}

QUESTIONS = [
    "Ты заходишь в маркетплейсы “просто посмотреть”, без конкретной цели?",
    "Ты покупаешь из-за скидки, хотя заранее не планировал(а)?",
    "Ты добираешь товары до бесплатной доставки, даже если они не нужны?",
    "Ты покупаешь, когда устал(а), скучно или хочешь себя порадовать?",
    "Ты фиксируешь, сколько денег НЕ потратил(а)?",
]


def kb(buttons):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
            for row in buttons
        ]
    )


def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = UserSession()
    return sessions[user_id]


async def send_guide(chat_id):
    if os.path.exists(GUIDE_FILE):
        await bot.send_document(
            chat_id=chat_id,
            document=FSInputFile(GUIDE_FILE),
            caption=(
                "📘 Готово. Вот твоя система.\n\n"
                "Начни с первого блока и сегодня же зафиксируй первую сумму, которую не потратил."
                "❗Не забудь и перешли это сообщение к себе в Избранное, чтобы не потерять.\n\n"
                "Дополнительная ссылка для скачивания, на случай если файл не откроется ⬇️⬇️⬇️"
            ),
            reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="☁️ Открыть на Яндекс Диске",
                    url="https://disk.yandex.ru/..."
                )
            ]
        ]
    )
)
        )
    else:
        await bot.send_message(
            chat_id,
            (
                "Файл гайда пока не найден.\n\n"
                f"Положи PDF рядом с bot.py и назови его {GUIDE_FILE}.\n"
                "После этого бот сможет отправлять его автоматически."
            ),
        )


@dp.message(CommandStart())
async def start(message: Message):
    sessions[message.from_user.id] = UserSession()

    text = (
        "💰 Зарабатывай, не тратя лишнего\n\n"
        "Нет, это не про кэшбэк и не про скидки.\n\n"
        "👉 Ты зарабатываешь каждый раз, когда не покупаешь лишнее.\n\n"
        "Проблема в том, что ты этого не замечаешь, "
        "и деньги продолжают утекать.\n\n"
        "⏱ За 60 секунд покажу, где это происходит у тебя."
    )

    await message.answer(text, reply_markup=kb([[("🚀 Проверить себя", "start_test")]]))


@dp.callback_query(F.data == "start_test")
async def start_test(callback: CallbackQuery):
    session = get_session(callback.from_user.id)
    session.score = 0
    session.question_index = 0

    await callback.message.answer(
        "🧠 Отвечай честно, это только для тебя.\n\n"
        "Здесь нет правильных ответов. "
        "Но именно они покажут, где у тебя уходят деньги."
    )

    await ask_question(callback.message.chat.id, callback.from_user.id)
    await callback.answer()


async def ask_question(chat_id, user_id):
    session = get_session(user_id)
    question = "❓ " + QUESTIONS[session.question_index]

    await bot.send_message(
        chat_id,
        question,
        reply_markup=kb(
            [[("✅ Да", "answer_2"), ("🤔 Иногда", "answer_1"), ("❌ Нет", "answer_0")]]
        ),
    )


@dp.callback_query(F.data.startswith("answer_"))
async def answer_question(callback: CallbackQuery):
    points = int(callback.data.split("_")[1])
    session = get_session(callback.from_user.id)

    session.score += points
    session.question_index += 1

    if session.question_index < len(QUESTIONS):
        await ask_question(callback.message.chat.id, callback.from_user.id)
    else:
        await show_result(callback.message.chat.id, callback.from_user.id)

    await callback.answer()


async def show_result(chat_id, user_id):
    session = get_session(user_id)
    score = session.score

    if score >= 7:
        text = (
            "📊 Скажу прямо:\n\n"
            "У тебя включена система незаметных трат.\n\n"
            "Ты не тратишь деньги осознанно. Ты теряешь их в процессе.\n\n"
            "Ты не покупаешь — ты реагируешь.\n\n"
            "И самое неприятное: ты даже не замечаешь момент, где это происходит.\n\n"
            "Чтобы это изменить, тебе нужна система, которая покажет эти моменты "
            "и позволит остановить их до того, как деньги уходят.\n\n"
            "Именно это лежит в основе система “Заработай, не тратя лишнего”.\n\n"
            "Хочешь увидеть это в деньгах?"
        )
    elif score >= 4:
        text = (
            "📊 У тебя есть точки, где деньги уходят автоматически.\n\n"
            "Не критично, но регулярно. И именно из-за этого возникает ощущение, "
            "что деньги “куда-то исчезают”.\n\n"
            "Ты не всегда контролируешь покупки. Иногда ты просто реагируешь.\n\n"
            "И если это не увидеть — сумма со временем становится заметной.\n\n"
            "Чтобы взять это под контроль, нужна система, которая покажет, "
            "где именно это происходит.\n\n"
            "Это и есть система незаметных трат, на которой строится система "
            "“Заработай, не тратя лишнего”.\n\n"
            "Хочешь увидеть это в деньгах?"
        )
    else:
        text = (
            "📊 У тебя уже есть контроль над покупками. Но даже 1–2 привычки могут "
            "давать утечку денег.\n\n"
            "Проблема в том, что такие моменты почти не ощущаются, "
            "но именно они дают результат на дистанции.\n\n"
            "И чаще всего ты просто не фиксируешь это.\n\n"
            "Чтобы убрать эти незаметные потери, нужна система, которая делает их видимыми.\n\n"
            "Это и есть система незаметных трат внутри “Заработай, не тратя лишнего”.\n\n"
            "Хочешь увидеть это в деньгах?"
        )

    await bot.send_message(chat_id, text, reply_markup=kb([[("👀 Посмотреть в деньгах", "calc_start")]]))


@dp.callback_query(F.data == "calc_start")
async def calc_start(callback: CallbackQuery):
    await callback.message.answer(
        "💸 Давай переведём это в реальные деньги.\n\n"
        "Сколько примерно у тебя уходит на мелкие покупки в день?",
        reply_markup=kb(
            [
                [("💸 до 300 ₽", "calc_300"), ("💸 300–700 ₽", "calc_700")],
                [("💸 700–1500 ₽", "calc_1500"), ("🔥 больше", "calc_more")],
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("calc_"))
async def calc_result(callback: CallbackQuery):
    variants = {
        "calc_300": "😳 Это примерно:\n\n9.000 ₽ в месяц\n108.000 ₽ в год\n\nИ это только то, что ты замечаешь.",
        "calc_700": "😳 Это примерно:\n\n9.000–21.000 ₽ в месяц\n108.000–252.000 ₽ в год",
        "calc_1500": "😳 Это примерно:\n\n21.000–45.000 ₽ в месяц\n252.000–540.000 ₽ в год",
        "calc_more": "😳 Скорее всего ты даже не осознаёшь реальный масштаб.\n\nНо это десятки тысяч в месяц и сотни тысяч в год.",
    }

    calc_text = variants[callback.data]

    text = (
        f"{calc_text}\n\n"
        "И это не “расходы”.\n\n"
        "Это деньги, которые ты мог(ла) оставить у себя.\n\n"
        "Это и есть основа системы “Заработай, не тратя лишнего”.\n\n"
        "Ты не ищешь, где заработать. Ты перестаёшь терять то, что у тебя уже есть.\n\n"
        "Хочешь увидеть, как именно остановить эти потери "
        "и начать фиксировать эти деньги как результат?"
    )

    await callback.message.answer(text, reply_markup=kb([[("⚙️ Показать систему", "show_system")]]))
    await callback.answer()


@dp.callback_query(F.data == "show_system")
async def show_system(callback: CallbackQuery):
    text = (
        "⚙️ Сейчас ты увидел(а) цифры. Но проблема не в них.\n\n"
        "Проблема в том, что ты не видишь сам механизм:\n\n"
        "в какой момент ты входишь в покупку;\n"
        "где решение уже почти принято;\n"
        "почему ты платишь, даже если не хотел.\n\n"
        "Пока это не видно — деньги будут уходить автоматически.\n\n"
        "Именно поэтому я собрал систему, которая разбирает это по шагам.\n\n"
        "Внутри системы “Заработай, не тратя лишнего” ты получаешь:\n\n"
        "— систему незаметных трат: как именно ты теряешь деньги;\n"
        "— 3 момента, где ты уже согласился на покупку;\n"
        "— 5 правил, которые останавливают импульс до оплаты;\n"
        "— как перестать переплачивать;\n"
        "— как превратить “не потратил” в реальные деньги;\n"
        "— план на 7 дней, чтобы сразу увидеть результат.\n\n"
        "Это не теория.\n\n"
        "Если ты остановишь хотя бы одну лишнюю покупку на 1000 ₽, "
        "ты уже вернёшь деньги.\n\n"
        "И дальше это начинает повторяться.\n\n"
        "Это не про экономию. Это про контроль.\n\n"
        "Хочешь получить систему и начать применять это уже сегодня?"
    )

    await callback.message.answer(text, reply_markup=kb([[("Получить доступ", "value_message")]]))
    await callback.answer()


@dp.callback_query(F.data == "value_message")
async def value_message(callback: CallbackQuery):
    text = (
        "🎯 Сейчас важный момент.\n\n"
        "К сожалению, человек так устроен: всё, что достаётся бесплатно, мы обесцениваем. "
        "Даже самая полезная информация, полученная без усилий, чаще всего так и остаётся неприменённой.\n\n"
        "Поэтому здесь важно не просто получить файл, а задать ценность тому, что ты берёшь.\n\n"
        "Это не про оплату файла. Это про твоё решение действительно применить систему и получить результат.\n\n"
        f"Стоимость доступа — {GUIDE_PRICE_RUB} ₽.\n\n"
        "После оплаты бот автоматически отправит тебе PDF."
    )

    await callback.message.answer(
        text,
        reply_markup=kb(
            [
                [(f"💰 Оплатить {GUIDE_PRICE_RUB} ₽", "pay_guide")],
                [("🎁 Получить бесплатно", "free_guide")],
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "free_guide")
async def free_guide(callback: CallbackQuery):
    await callback.message.answer(
        "🎁 Забирай бесплатно.\n\n"
        "Но потом, когда забросишь этот гайд и забудешь про него через пару дней, "
        "просто вспомни одну вещь.\n\n"
        "Я предлагал тебе задать этому ценность и реально вытащить из него максимум.\n\n"
        "Потому что пока информация бесплатная, мозг почти всегда относится к ней "
        "как к чему-то неважному.\n\n"
        "Если в какой-то момент поймёшь, что хочешь действительно применить это "
        "и получить результат, просто вернись и оплати.\n\n"
        "И скорее всего эти деньги ты вернёшь себе уже в первый день.",
        reply_markup=kb(
            [
                [(f"⚡ Задать ценность в {GUIDE_PRICE_RUB} ₽", "pay_guide")],
                [(" Забыть завтра же (🎁Бесплатно)", "free_guide_confirm")],
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "free_guide_confirm")
async def free_guide_confirm(callback: CallbackQuery):
    await send_guide(callback.message.chat.id)
    await callback.answer()


@dp.callback_query(F.data == "pay_guide")
async def pay_guide(callback: CallbackQuery):
    prices = [LabeledPrice(label="Гайд «Заработай, не тратя лишнего»", amount=GUIDE_PRICE_RUB * 100)]

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Гайд «Заработай, не тратя лишнего»",
        description=(
            "PDF-гайд с системой контроля незаметных трат, "
            "правилами остановки импульсных покупок и планом на 7 дней."
        ),
        payload=f"guide_payment_{callback.from_user.id}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency=PAYMENT_CURRENCY,
        prices=prices,
        start_parameter="guide",
    )
    await callback.answer()


@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment

    await message.answer(
        "✅ Оплата прошла успешно.\n\n"
        f"Сумма: {payment.total_amount // 100} {payment.currency}\n"
        "Сейчас отправлю тебе гайд."
    )
    await send_guide(message.chat.id)


async def main():
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
