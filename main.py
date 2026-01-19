import logging
import time
import telebot
import sqlite3
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

logger.info("🚀 НОВЫЙ БОТ ЗАПУЩЕН!")

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logger.error("❌ Ошибка: BOT_TOKEN не установлен!")
    raise SystemExit(1)

bot = telebot.TeleBot(TOKEN)

# Use script directory for the sqlite DB to avoid CWD issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'dutch_bot.db')

@bot.message_handler(commands=['start'])
def start(message):
    print(f"Получен /start от {message.from_user.id}")
    bot.reply_to(message, 
        "🚀 *НОВЫЙ БОТ ЗАПУЩЕН!*\n\n"
        "Команды:\n"
        "/word - слово\n"
        "/today - слова\n"
        "/stats - статистика",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['word'])
def send_word(message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 1')
    word = c.fetchone()
    conn.close()
    if word:
        bot.reply_to(message, f"📚 {word[0]} - {word[1]}")
    else:
        bot.reply_to(message, "📚 Слов нет в базе. Пожалуйста, инициализируйте базу командой `python init_bot.py`.")

@bot.message_handler(commands=['today'])
def today_words(message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 5')
    words = c.fetchall()
    conn.close()
    if not words:
        bot.reply_to(message, "📖 Слова на сегодня отсутствуют. Пожалуйста, запустите `python init_bot.py`.")
        return

    response = "📖 *Слова на сегодня:*\n\n"
    for i, (dutch, russian) in enumerate(words, 1):
        response += f"{i}. *{dutch}* - {russian}\n"

    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM words')
    count = c.fetchone()[0]
    conn.close()
    bot.reply_to(message, f"📊 *Статистика:*\n\nСлов в базе: *{count}*", parse_mode='Markdown')

if __name__ == '__main__':
    logger.info("✅ Бот готов!")
    # Resilient polling loop: restart on exceptions with a short delay
    while True:
        try:
            bot.infinity_polling()
        except Exception:
            logger.exception('Polling crashed, restarting in 5s...')
            time.sleep(5)
