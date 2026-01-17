import telebot
import sqlite3
import os
import json
import random
from datetime import datetime, timedelta
import schedule
import time
import threading

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get('BOT_TOKEN', '8526430720:AAHHkrhBZyonFxdKXYrZ1vcYqZlMKFYzm3s')
bot = telebot.TeleBot(TOKEN)

USER_ID = 123456789  # ЗАМЕНИТЕ на ваш Telegram ID (узнать: @userinfobot)

# ========== БАЗА ДАННЫХ ==========
def get_db():
    conn = sqlite3.connect('dutch_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

# ========== SRS СИСТЕМА (ПОВТОРЕНИЯ) ==========
def get_todays_words(user_id=USER_ID):
    """Получить слова на сегодня"""
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().date()
    
    # 1. Получаем слова для повторения
    c.execute('''
        SELECT w.* FROM words w
        JOIN user_progress up ON w.id = up.word_id
        WHERE up.user_id = ? 
        AND up.status IN ('learning', 'known')
        AND up.next_review <= ?
        ORDER BY up.next_review
        LIMIT 5
    ''', (user_id, today))
    
    review_words = c.fetchall()
    
    # 2. Получаем новые слова
    c.execute('''
        SELECT w.* FROM words w
        LEFT JOIN user_progress up ON w.id = up.word_id AND up.user_id = ?
        WHERE up.id IS NULL
        ORDER BY RANDOM()
        LIMIT 5
    ''', (user_id,))
    
    new_words = c.fetchall()
    
    conn.close()
    
    # Объединяем, но не более 5 слов всего
    all_words = list(review_words) + list(new_words)
    return all_words[:5]

def update_progress(user_id, word_id, status):
    """Обновить прогресс по слову"""
    conn = get_db()
    c = conn.cursor()
    
    today = datetime.now().date()
    
    if status == 'known':
        # Выучено: повторять через 7 дней
        next_review = today + timedelta(days=7)
    elif status == 'learning':
        # Учу: повторять через 3 дня
        next_review = today + timedelta(days=3)
    else:
        next_review = today + timedelta(days=1)
    
    c.execute('''
        INSERT OR REPLACE INTO user_progress 
        (user_id, word_id, status, next_review, review_count, last_reviewed)
        VALUES (?, ?, ?, ?, COALESCE((SELECT review_count FROM user_progress WHERE user_id = ? AND word_id = ?), 0) + 1, ?)
    ''', (user_id, word_id, status, next_review, user_id, word_id, today))
    
    conn.commit()
    conn.close()

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    """Начало работы"""
    user_id = message.from_user.id
    
    welcome = f"""
🇳🇱 *Hallo! Welkom bij Dutch AI Bot!*

Я помогу вам выучить нидерландский с помощью искусственного интеллекта.

*Основные команды:*
/word - Получить слово на изучение
/know - Отметить слово как выученное
/quiz - Пройти тест по сегодняшним словам
/stats - Ваша статистика
/today - Слова на сегодня
/help - Помощь

*Просто напишите любое слово на нидерландском или русском для перевода и объяснения!*
    """
    
    bot.reply_to(message, welcome, parse_mode='Markdown')
    
    # Добавляем пользователя в БД
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

@bot.message_handler(commands=['word'])
def send_word(message):
    """Отправить одно слово для изучения"""
    conn = get_db()
    c = conn.cursor()
    
    # Находим слово без прогресса или для повторения
    c.execute('''
        SELECT w.* FROM words w
        LEFT JOIN user_progress up ON w.id = up.word_id AND up.user_id = ?
        WHERE up.id IS NULL OR up.next_review <= date('now')
        ORDER BY RANDOM()
        LIMIT 1
    ''', (message.from_user.id,))
    
    word = c.fetchone()
    conn.close()
    
    if word:
        # Форматируем ответ
        examples = eval(word['examples']) if word['examples'] else []
        
        response = f"""
🎯 *Новое слово:*

*{word['dutch']}* ({word['article']})
*Перевод:* {word['translation']}

*Объяснение:*
{word['explanation'] or 'Нет объяснения'}

*Примеры:*
"""
        for example in examples[:2]:
            if ' | ' in str(example):
                nl, ru = str(example).split(' | ', 1)
                response += f"• {nl}\n  _{ru}_\n"
        
        response += f"\n📊 *Сложность:* {word['difficulty']}"
        response += f"\n\n💡 Используйте /know чтобы отметить как выученное"
        
        # Добавляем inline-кнопки
        markup = telebot.types.InlineKeyboardMarkup()
        know_btn = telebot.types.InlineKeyboardButton(
            text="✅ Знаю это слово", 
            callback_data=f"know_{word['id']}"
        )
        repeat_btn = telebot.types.InlineKeyboardButton(
            text="🔄 Повторить позже", 
            callback_data=f"repeat_{word['id']}"
        )
        markup.add(know_btn, repeat_btn)
        
        bot.reply_to(message, response, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.reply_to(message, "🎉 Вы изучили все слова! Добавьте новые в базу.")

@bot.message_handler(commands=['know'])
def mark_as_known(message):
    """Отметить последнее слово как выученное"""
    conn = get_db()
    c = conn.cursor()
    
    # Получаем последнее отправленное слово
    c.execute('''
        SELECT w.id FROM words w
        JOIN sent_words sw ON w.id = sw.word_id
        WHERE sw.user_id = ?
        ORDER BY sw.sent_at DESC
        LIMIT 1
    ''', (message.from_user.id,))
    
    last_word = c.fetchone()
    
    if last_word:
        update_progress(message.from_user.id, last_word['id'], 'known')
        bot.reply_to(message, f"✅ Отлично! Слово отмечено как выученное. Повторю через 7 дней.")
    else:
        bot.reply_to(message, "Сначала получите слово командой /word")

@bot.message_handler(commands=['today'])
def today_words(message):
    """Показать слова на сегодня"""
    words = get_todays_words(message.from_user.id)
    
    if not words:
        bot.reply_to(message, "На сегодня слов нет. Используйте /word для нового слова.")
        return
    
    response = "📚 *Ваши слова на сегодня:*\n\n"
    
    for i, word in enumerate(words, 1):
        response += f"{i}. *{word['dutch']}* - {word['translation']}\n"
    
    response += f"\n📊 Всего: {len(words)} слов"
    response += f"\n💡 Используйте /quiz для проверки знаний"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['quiz'])
def start_quiz(message):
    """Начать тест по сегодняшним словам"""
    words = get_todays_words(message.from_user.id)
    
    if len(words) < 2:
        bot.reply_to(message, "Нужно хотя бы 2 слова для теста. Изучите больше слов!")
        return
    
    # Выбираем случайное слово
    word = random.choice(words)
    other_words = [w for w in words if w['id'] != word['id']]
    
    # Создаем варианты ответов
    options = [word['translation']]
    options.extend([w['translation'] for w in random.sample(other_words, min(3, len(other_words)))])
    random.shuffle(options)
    
    # Создаем клавиатуру
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for option in options:
        markup.add(option)
    
    # Сохраняем правильный ответ
    bot.send_message(
        message.chat.id,
        f"❓ *Как переводится слово:*\n*{word['dutch']}*",
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    # Сохраняем состояние теста (упрощенная версия)
    bot.register_next_step_handler(message, check_quiz_answer, word['translation'], word['id'])

def check_quiz_answer(message, correct_answer, word_id):
    """Проверить ответ в тесте"""
    if message.text == correct_answer:
        update_progress(message.from_user.id, word_id, 'known')
        bot.reply_to(message, "✅ Правильно! Отличная работа!")
    else:
        update_progress(message.from_user.id, word_id, 'learning')
        bot.reply_to(message, f"❌ Неправильно. Правильный ответ: {correct_answer}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Показать статистику"""
    conn = get_db()
    c = conn.cursor()
    
    user_id = message.from_user.id
    
    # Общая статистика
    c.execute("SELECT COUNT(*) FROM words")
    total_words = c.fetchone()[0]
    
    c.execute('''
        SELECT COUNT(DISTINCT word_id) FROM user_progress 
        WHERE user_id = ? AND status = 'known'
    ''', (user_id,))
    known_words = c.fetchone()[0]
    
    c.execute('''
        SELECT COUNT(DISTINCT word_id) FROM user_progress 
        WHERE user_id = ? AND status = 'learning'
    ''', (user_id,))
    learning_words = c.fetchone()[0]
    
    # Прогресс за сегодня
    today = datetime.now().date()
    c.execute('''
        SELECT COUNT(*) FROM user_progress 
        WHERE user_id = ? AND date(last_reviewed) = ?
    ''', (user_id, today))
    today_reviews = c.fetchone()[0]
    
    conn.close()
    
    # Создаем визуализацию прогресса
    progress_percent = (known_words / total_words * 100) if total_words > 0 else 0
    progress_bar = "▓" * int(progress_percent / 10) + "░" * (10 - int(progress_percent / 10))
    
    response = f"""
📊 *Ваша статистика:*

{progress_bar} {progress_percent:.1f}%

*Выучено:* {known_words} из {total_words} слов
*Изучается:* {learning_words} слов
*Повторений сегодня:* {today_reviews}

*Прогресс по дням:*
- Новые слова: /word
- Повторение: /today
- Тест: /quiz

🎯 *Цель:* {total_words} слов
    """
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """Обработка любого текста (поиск слова)"""
    search_text = message.text.strip()
    
    conn = get_db()
    c = conn.cursor()
    
    # Ищем слово в базе
    c.execute('''
        SELECT * FROM words 
        WHERE dutch LIKE ? OR translation LIKE ?
        LIMIT 1
    ''', (f"%{search_text}%", f"%{search_text}%"))
    
    word = c.fetchone()
    conn.close()
    
    if word:
        # Показываем информацию о слове
        examples = eval(word['examples']) if word['examples'] else []
        
        response = f"""
🔍 *Найдено слово:*

*{word['dutch']}* ({word['article']})
*Перевод:* {word['translation']}

*Объяснение:*
{word['explanation'] or 'Нет объяснения'}

*Примеры:*
"""
        for example in examples[:2]:
            if ' | ' in str(example):
                nl, ru = str(example).split(' | ', 1)
                response += f"• {nl}\n  _{ru}_\n"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        bot.reply_to(message, f"Слово '{search_text}' не найдено в базе. Попробуйте другое слово.")

# ========== INLINE КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обработка inline-кнопок"""
    if call.data.startswith('know_'):
        word_id = int(call.data.split('_')[1])
        update_progress(call.from_user.id, word_id, 'known')
        bot.answer_callback_query(call.id, "✅ Слово отмечено как выученное!")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        
    elif call.data.startswith('repeat_'):
        word_id = int(call.data.split('_')[1])
        update_progress(call.from_user.id, word_id, 'learning')
        bot.answer_callback_query(call.id, "🔄 Слово добавлено в повторение через 3 дня")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# ========== ЕЖЕДНЕВНАЯ РАССЫЛКА ==========
def send_daily_notification():
    """Отправка ежедневного уведомления"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT id FROM users")
    users = c.fetchall()
    
    for user in users:
        user_id = user['id']
        words = get_todays_words(user_id)
        
        if words:
            message = f"📚 *Доброе утро!* Ваши слова на сегодня:\n\n"
            for word in words:
                message += f"• {word['dutch']} - {word['translation']}\n"
            
            message += f"\nВсего слов: {len(words)}\nИспользуйте /word для изучения"
            
            try:
                bot.send_message(user_id, message, parse_mode='Markdown')
            except:
                pass  # Пользователь заблокировал бота
    
    conn.close()

# ========== ЗАПУСК ==========
def run_scheduler():
    """Запуск планировщика для ежедневных уведомлений"""
    schedule.every().day.at("09:00").do(send_daily_notification)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    print("🤖 Бот запущен...")
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Запускаем бота
    bot.infinity_polling()
