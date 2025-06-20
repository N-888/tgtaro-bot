import asyncio
import logging
import os
import io

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from openai import OpenAI
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Твои токены
BOT_TOKEN = "7625718706:AAETeaPXHHpqxI-iDyX28r08ytmNH5a8Dbc"
OPENAI_API_KEY = "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"

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

# Кнопки раскладов
keyboard = InlineKeyboardMarkup(inline_keyboard=[
[
InlineKeyboardButton(text="Расклад на день", callback_data="spread_day"),
InlineKeyboardButton(text="Расклад на неделю", callback_data="spread_week"),
InlineKeyboardButton(text="Расклад на месяц", callback_data="spread_month")
]
])

# Кнопка продолжения
continue_keyboard = InlineKeyboardMarkup(inline_keyboard=[
[InlineKeyboardButton(text="🔄 Задать новый вопрос", callback_data="new_question")]
])

# /start
@dp.message(Command("start"))
async def start(message: types.Message):
await message.answer(
"Привет! Выбери расклад кнопкой или задай вопрос голосом/текстом.",
reply_markup=keyboard
)

# Выбор расклада
@dp.callback_query(F.data.startswith("spread_"))
async def handle_spread(callback: CallbackQuery):
spread_type = callback.data.split("_")[1]
await callback.message.answer(f"Твой расклад на {spread_type} готов! (пример)")
await callback.answer()

# Новый вопрос
@dp.callback_query(F.data == "new_question")
async def handle_new_question(callback: CallbackQuery):
await callback.message.answer("Задай новый вопрос голосом или текстом.")
await callback.answer()

# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
if message.voice:
file_info = await bot.get_file(message.voice.file_id)
file_path = file_info.file_path
audio_file = await bot.download_file(file_path)

with open("voice.oga", "wb") as f:
f.write(audio_file.read())

AudioSegment.from_file("voice.oga").export("voice.wav", format="wav")

recognizer = sr.Recognizer()
with sr.AudioFile("voice.wav") as source:
audio_data = recognizer.record(source)
try:
lang_code = message.from_user.language_code or "ru-RU"
question = recognizer.recognize_google(audio_data, language=lang_code)
logging.info(f"🎤 Голосовой вопрос: {question}")
except sr.UnknownValueError:
await message.answer("Не смог распознать речь, попробуй ещё раз.")
return
except Exception as e:
await message.answer(f"Ошибка распознавания: {e}")
return
finally:
os.remove("voice.oga")
os.remove("voice.wav")
else:
question = message.text
logging.info(f"💬 Текстовый вопрос: {question}")

try:
completion = client.chat.completions.create(
model="gpt-4o-mini",
messages=[ # type: ignore
{"role": "system", "content": "Отвечай подробно, логично и заканчивай мысль полностью."},
{"role": "user", "content": question}
],
temperature=0.7,
max_tokens=500
)
answer = completion.choices[0].message.content.strip()
logging.info(f"⭐ Ответ OpenAI: {answer}")
except Exception as e:
await message.answer(f"❌ Ошибка OpenAI: {e}")
return

try:
lang = message.from_user.language_code or "ru"
if not lang.startswith("ru") and not lang.startswith("en"):
lang = "ru"
tts = gTTS(text=answer, lang=lang)
audio_bytes = io.BytesIO()
tts.write_to_fp(audio_bytes)
audio_bytes.seek(0)
await message.answer_voice(voice=audio_bytes)
except Exception as e:
logging.error(f"Ошибка gTTS: {e}")
await message.answer("⚠️ Не удалось озвучить ответ.")

await message.answer(answer, reply_markup=continue_keyboard)

# Запуск
async def main():
print("✅ Бот запускается...")
await dp.start_polling(bot)

if __name__ == "__main__":
asyncio.run(main())
