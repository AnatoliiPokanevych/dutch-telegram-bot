import telebot
import sqlite3
import os
import random

TOKEN = os.environ.get('BOT_TOKEN', '8526430720:AAHHkrhBZyonFxdKXYrZ1vcYqZlMKFYzm3s')
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
    conn = sqlite3.connect('dutch_bot.db')
    c = conn.cursor()
    c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 1')
    word = c.fetchone()
    conn.close()
    
    if word:
        bot.reply_to(message, f"📚 *{word[0]}* - {word[1]}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "База данных пуста!")

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
    print("🤖 Dutch Bot запущен!")
    bot.infinity_polling()
