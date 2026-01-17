import telebot
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('BOT_TOKEN', '8526430720:AAHHkrhBZyonFxdKXYrZ1vcYqZlMKFYzm3s')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome = """
🇳🇱 *Hallo! Welkom bij Dutch Daily Bot!*

Ik draai op *Railway* 🚂

Commando's:
/start - dit bericht
/words - 5 nieuwe woorden
/test - bot status
    """
    bot.reply_to(message, welcome, parse_mode='Markdown')

@bot.message_handler(commands=['test'])
def test(message):
    status = """
🔄 *Bot Status*
ID: `8526430720`
📍 Host: Railway
✅ Status: Online
📊 Versie: 1.0
    """
    bot.reply_to(message, status, parse_mode='Markdown')

@bot.message_handler(commands=['words'])
def send_words(message):
    words = """
🎯 *Je woorden voor vandaag:*

1. *de appel* - яблоко
   _Voorbeeld:_ Ik eet een appel.

2. *het boek* - книга  
   _Voorbeeld:_ Dit boek is interessant.

3. *lopen* - идти
   _Voorbeeld:_ Wij lopen naar het park.
    """
    bot.reply_to(message, words, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.reply_to(message, f"Je schreef: {message.text}")

if __name__ == '__main__':
    logger.info("✅ Бот запущен на Railway!")
    logger.info(f"Bot ID: {TOKEN.split(':')[0]}")
    bot.infinity_polling()
