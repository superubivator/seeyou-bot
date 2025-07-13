import os
import asyncio
import re
import asyncio
import time
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from aiogram import F
from aiohttp import web
from aiogram import Bot, Dispatcher

BOT_TOKEN = "7784812888:AAGDbKddmy117EyFPDPsA_FvSJcdXOe5nLc"
CHANNEL_USERNAME = "@seeyounvkz"
ADMIN_ID = 8004750966

# Инициализация
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

COOLDOWN_SECONDS = 300
POST_DELAY = 30

BAD_WORDS = [
    "хуй", "пизд", "еба", "ебл", "муда", "ганд", "сука", "шала", "бляд", "уеб", "выбляд",
    "fuck", "shit", "fag", "bitch", "dick", "fuc", "fuk", "suka", "blya", "yeb", "huy", "xuy", "xуй",
    "хyй", "хуе", "хуи", "cука", "пид", "xyй", "нax", "гaнд", "ёб", "е6", "e6a", "у6люд", "fuk", "nах", "cуч", "mудa"
]

AD_WORDS = [
    "купи", "продам", "заказ", "скидк", "акция", "распродаж", "магазин", "реклам", "бесплатно", "промокод",
    "доставк", "канал", "чат", "групп", "телеграм", "t.me", "vk.com", "инстаграм", "директ",
    "вайбер", "ватсап", "viber", "whatsapp", "telegram", "тг", "зайди", "перейди", "ссылка", "реклама", "продажа", "купить", "цена"
]

DOMAIN_PATTERNS = [
    r"(?:https?://|www\.)\S+",
    r"\b\w+\.(?:ru|com|рф|net|org|kz)\b",
    r"\b\w+[\.\s]*(?:ру|ком|рф|нет)\b",
    r"\b(?:точка|тчк|dot)[\s\.]*(?:ру|com|рф)\b",
    r"\w+@\w+\.\w+",
    r"\b[\w\.-]+\.(?:рф|com|ru|net|org)\b"
]

REPLACEMENTS = {
    'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'y': 'у', 'x': 'х',
    'b': 'в', 'm': 'м', 'k': 'к', 't': 'т', 'n': 'п'
}

user_cooldowns = {}

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    for latin, cyrillic in REPLACEMENTS.items():
        text = text.replace(latin, cyrillic)
    return re.sub(r'[^а-яa-zё\s]', '', text)

def contains_ads(text):
    if not text:
        return False
    for pattern in DOMAIN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    clean_text = normalize(text)
    return any(ad_word in clean_text for ad_word in AD_WORDS)

def contains_bad_words(text):
    if not text:
        return False
    clean_text = normalize(text)
    return any(bad_word in clean_text for bad_word in BAD_WORDS)

class PostStates(StatesGroup):
    waiting_for_content = State()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "👋 Привет! Хочешь признаться кому-то или найти человека с улицы?\n\n"
        "Просто нажми кнопку ниже и отправь фото с описанием или текст. Мы всё анонимно опубликуем!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✉️ Отправить анонимное сообщение", callback_data="send")]
        ])
    )

@dp.callback_query(F.data == "send")
async def request_post(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    current_time = time.time()

    if user_id in user_cooldowns and current_time - user_cooldowns[user_id] < COOLDOWN_SECONDS:
        cooldown_left = int(COOLDOWN_SECONDS - (current_time - user_cooldowns[user_id]))
        mins = cooldown_left // 60
        secs = cooldown_left % 60
        await callback_query.message.answer(
            f"⏳ Следующее сообщение можно отправить через {mins} мин. {secs} сек."
        )
        return

    await callback_query.message.answer("📸 Отправь фото с описанием или просто текст:")
    await state.set_state(PostStates.waiting_for_content)
    await callback_query.answer()

@dp.message(PostStates.waiting_for_content)
async def process_post(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = message.from_user

    user_cooldowns[user_id] = time.time()
    text_content = ""
    photo_id = None

    if message.photo:
        photo_id = message.photo[-1].file_id
        text_content = message.caption if message.caption else ""
    elif message.text:
        text_content = message.text
    else:
        await message.reply("❌ Поддерживаются только текст и фото!")
        await state.clear()
        return

    if contains_bad_words(text_content):
        await message.reply("❌ Сообщение содержит запрещённые слова!")
        await state.clear()
        return

    if contains_ads(text_content):
        await message.reply(
            "🚫 Запрещена реклама и ссылки! Не допускаются:\n- Контакты\n- Ссылки\n- Упоминания соцсетей\n- Товары/услуги")
        await state.clear()
        return

    await message.reply(f"⏳ Сообщение проверяется (задержка {POST_DELAY} сек.)...")
    await asyncio.sleep(POST_DELAY)

    try:
        if photo_id:
            await bot.send_photo(chat_id=CHANNEL_USERNAME, photo=photo_id, caption=text_content)
        else:
            await bot.send_message(chat_id=CHANNEL_USERNAME, text=text_content)
        await message.reply("✅ Сообщение опубликовано!")

        # 🔒 Отправка админу инфы о юзере
        admin_text = (
            f"📬 Новый пост в канал\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🆔 ID: {user.id}\n"
            f"🔗 Username: @{user.username if user.username else 'нет'}\n\n"
            f"📄 Текст: {text_content}"
        )
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text)

    except Exception as e:
        await message.reply(f"⚠️ Ошибка публикации: {str(e)}")

    await state.clear()

if __name__ == "__main__":
    dp.run_polling(bot)


async def http_handler(request):
    """Простой обработчик HTTP-запросов для Render"""
    return web.Response(text="🤖 Telegram Bot is running!")


async def start_http_server(port):
    """Запуск HTTP-сервера для Render"""
    app = web.Application()
    app.router.add_get('/', http_handler)
    app.router.add_get('/healthcheck', http_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 HTTP-сервер запущен на порту {port}")


async def main():
    """Основная асинхронная функция"""
    # Сброс соединения Telegram
    await hard_reset_telegram_connection()

    # Запуск HTTP-сервера для Render
    port = int(os.getenv("PORT", 8000))
    http_task = asyncio.create_task(start_http_server(port))

    # Запуск бота
    from aiogram import executor
    bot_task = asyncio.create_task(executor.start_polling(dp, skip_updates=True))

    print("=" * 50)
    print(f"🤖 Бот успешно запущен!")
    print(f"📡 HTTP-сервер: порт {port}")
    print(f"👑 Администратор: ID {ADMIN_ID}")
    print(f"📢 Канал: {CHANNEL_USERNAME}")
    print("=" * 50)

    # Ожидание обеих задач
    await asyncio.gather(http_task, bot_task)


if __name__ == "__main__":
    # Обработка сигналов для корректного завершения
    def handle_shutdown(signum, frame):
        print(f"🛑 Получен сигнал {signum}, завершаю работу...")
        release_lock()
        sys.exit(0)


    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    try:
        # Создание блокировки
        acquire_lock()

        # Запуск асинхронного приложения
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
    finally:
        release_lock()
