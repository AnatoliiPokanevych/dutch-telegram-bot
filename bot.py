import telebot
import os

# Ваш токен (уже вставлен)
TOKEN = '8526430720:AAHHkrhBZyonFxdKXYrZ1vcYqZlMKFYzm3s'
bot = telebot.TeleBot(TOKEN)

# Ответ на команду /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = """
    🇳🇱 *Hallo! Welkom bij Dutch Daily Bot!*

    Я помогу вам учить нидерландский язык каждый день.

    Доступные команды:
    /start - это приветствие
    /words - получить 5 новых слов на сегодня
    /quiz - пройти мини-тест

    Удачи! Veel succes! 😊
    """
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

# Команда для получения слов (пока тестовых)
@bot.message_handler(commands=['words'])
def send_words(message):
    words_list = """
    *🎯 Ваши слова на сегодня:*

    1. *de appel* - яблоко
       *Пример:* Ik eet een appel. (Я ем яблоко.)

    2. *het boek* - книга
       *Пример:* Dit boek is interessant. (Эта книга интересная.)

    3. *lopen* - идти
       *Пример:* Wij lopen naar het park. (Мы идем в парк.)

    4. *de hamer* - молоток
       *Пример:* Geef mij de hamer. (Дай мне молоток.)

    5. *zwanger* - беременная
       *Пример:* Mijn zus is zwanger. (Моя сестра беременна.)

    *📝 Повторите эти слова! Через час пришлю вам мини-тест.*
    """
    bot.reply_to(message, words_list, parse_mode='Markdown')

# Просто эхо для теста
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Вы написали: {message.text}")

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
