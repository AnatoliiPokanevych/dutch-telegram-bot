import telebot
import sqlite3
import os

print("🚀 НОВЫЙ БОТ ЗАПУЩЕН!")

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ Ошибка: BOT_TOKEN не установлен!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

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
    conn = sqlite3.connect('dutch_bot.db')
    c = conn.cursor()
    c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 1')
    word = c.fetchone()
    conn.close()
    
    if word:
        bot.reply_to(message, f"📚 {word[0]} - {word[1]}")

@bot.message_handler(commands=['today'])
def today_words(message):
    conn = sqlite3.connect('dutch_bot.db')
    c = conn.cursor()
    c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 5')
    words = c.fetchall()
    conn.close()
    
    response = "📖 *Слова на сегодня:*\n\n"
    for i, (dutch, russian) in enumerate(words, 1):
        response += f"{i}. *{dutch}* - {russian}\n"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    conn = sqlite3.connect('dutch_bot.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM words')
    count = c.fetchone()[0]
    conn.close()
    
    bot.reply_to(message, f"📊 *Статистика:*\n\nСлов в базе: *{count}*", 
                parse_mode='Markdown')

if __name__ == '__main__':
    print("✅ Бот готов!")
    bot.infinity_polling()
