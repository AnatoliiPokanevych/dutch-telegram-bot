cd ~/Desktop/dutch_bot

cat > bot.py << 'EOF'
import telebot
import sqlite3
import os
import random

TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    print("❌ Ошибка: BOT_TOKEN не установлен!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, 
        "🇳🇱 *Hallo! Dutch Bot работает на Railway!*\n\n"
        "Команды:\n"
        "/word - случайное слово\n"
        "/today - 5 случайных слов\n"
        "/stats - статистика",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['word'])
def send_word(message):
    try:
        conn = sqlite3.connect('dutch_bot.db')
        c = conn.cursor()
        c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 1')
        word = c.fetchone()
        conn.close()
        
        if word:
            bot.reply_to(message, f"📚 *{word[0]}* - {word[1]}", parse_mode='Markdown')
        else:
            bot.reply_to(message, "База данных пуста!")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['today'])
def today_words(message):
    try:
        conn = sqlite3.connect('dutch_bot.db')
        c = conn.cursor()
        c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 5')
        words = c.fetchall()
        conn.close()
        
        if not words:
            bot.reply_to(message, "Нет слов в базе!")
            return
        
        response = "📖 *Слова на сегодня:*\n\n"
        for i, (dutch, russian) in enumerate(words, 1):
            response += f"{i}. *{dutch}* - {russian}\n"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['stats'])
def stats(message):
    try:
        conn = sqlite3.connect('dutch_bot.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM words')
        count = c.fetchone()[0]
        conn.close()
        
        bot.reply_to(message, f"📊 *Статистика:*\n\nСлов в базе: *{count}*", 
                    parse_mode='Markdown')
    except Exception as e:
        bot.reply_to_message = bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, f"Неизвестная команда: {message.text}")

if __name__ == '__main__':
    print("🤖 Dutch Bot запущен на Railway!")
    bot.infinity_polling()
EOF
