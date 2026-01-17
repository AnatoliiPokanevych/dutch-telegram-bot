import os
import sys

# ========== АВТОМАТИЧЕСКАЯ ИНИЦИАЛИЗАЦИЯ ==========
if not os.path.exists('dutch_bot.db'):
    print("🔄 База данных не найдена, запускаю инициализацию...")
    
    # Проверяем наличие ключа OpenAI
    if not os.environ.get('OPENAI_API_KEY'):
        print("❌ ОШИБКА: Не найден OPENAI_API_KEY")
        print("Добавьте в Railway переменную OPENAI_API_KEY с вашим ключом OpenAI")
        sys.exit(1)
    
    # Проверяем наличие файла со словами
    if not os.path.exists('woorden.txt'):
        print("❌ ОШИБКА: Не найден файл woorden.txt")
        sys.exit(1)
    
    # Запускаем инициализацию
    try:
        os.system('python init_bot.py')
        print("✅ Инициализация завершена!")
    except Exception as e:
        print(f"❌ Ошибка при инициализации: {e}")
        sys.exit(1)

# ========== ОСНОВНОЙ КОД БОТА ==========
import telebot
import sqlite3
import json
import random
from datetime import datetime, timedelta
import schedule
import time
import threading

# ========== НАСТРОЙКИ ==========
TOKEN = os.environ.get('BOT_TOKEN', '8526430720:AAHHkrhBZyonFxdKXYrZ1vcYqZlMKFYzm3s')
bot = telebot.TeleBot(TOKEN)


USER_ID = 6623026027

# ========== БАЗА ДАННЫХ ==========
def get_db():
    conn = sqlite3.connect('dutch_bot.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_user_progress(user_id):
    """Инициализировать прогресс для нового пользователя"""
    conn = get_db()
    c = conn.cursor()
    
    # Добавляем пользователя
    c.execute('INSERT OR IGNORE INTO users (id, created_at) VALUES (?, ?)', 
              (user_id, datetime.now()))
    
    # Получаем все слова без прогресса
    c.execute('''
        SELECT id FROM words 
        WHERE id NOT IN (SELECT word_id FROM user_progress WHERE user_id = ?)
    ''', (user_id,))
    
    new_words = c.fetchall()
    
    # Добавляем их в прогресс со статусом 'new'
    for word in new_words:
        c.execute('''
            INSERT OR IGNORE INTO user_progress (user_id, word_id, status, next_review)
            VALUES (?, ?, 'new', ?)
        ''', (user_id, word['id'], datetime.now().date()))
    
    conn.commit()
    conn.close()

# ========== SRS СИСТЕМА (ПОВТОРЕНИЯ) ==========
def get_todays_words(user_id):
    """Получить слова на сегодня"""
    conn = get_db()
    c = conn.cursor()
    today = datetime.now().date()
    
    # 1. Слова для повторения (статус 'learning' или 'known')
    c.execute('''
        SELECT w.*, up.status, up.next_review FROM words w
        JOIN user_progress up ON w.id = up.word_id
        WHERE up.user_id = ? 
        AND up.status IN ('learning', 'known')
        AND up.next_review <= ?
        ORDER BY up.next_review
        LIMIT 10
    ''', (user_id, today))
    
    review_words = c.fetchall()
    
    # 2. Новые слова (статус 'new')
    c.execute('''
        SELECT w.* FROM words w
        JOIN user_progress up ON w.id = up.word_id
        WHERE up.user_id = ? AND up.status = 'new'
        ORDER BY RANDOM()
        LIMIT 5
    ''', (user_id,))
    
    new_words = c.fetchall()
    
    conn.close()
    
    # Объединяем, но не более 5 слов всего для нового дня
    all_words = list(review_words) + list(new_words)
    return all_words[:5]

def update_progress(user_id, word_id, status):
    """Обновить прогресс по слову"""
    conn = get_db()
    c = conn.cursor()
    
    today = datetime.now().date()
    
    # Определяем следующий повтор
    if status == 'known':
        next_review = today + timedelta(days=7)  # Через 7 дней
    elif status == 'learning':
        next_review = today + timedelta(days=3)  # Через 3 дня
    else:  # 'new'
        next_review = today + timedelta(days=1)
    
    # Обновляем или создаем запись
    c.execute('''
        INSERT OR REPLACE INTO user_progress 
        (user_id, word_id, status, next_review, review_count, last_reviewed)
        VALUES (?, ?, ?, ?, 
                COALESCE((SELECT review_count FROM user_progress WHERE user_id = ? AND word_id = ?), 0) + 1, 
                ?)
    ''', (user_id, word_id, status, next_review, user_id, word_id, today))
    
    conn.commit()
    conn.close()
    
    # Логируем
    print(f"📝 Обновлен прогресс: user={user_id}, word={word_id}, status={status}, next={next_review}")

def get_word_info(word_id):
    """Получить информацию о слове"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM words WHERE id = ?', (word_id,))
    word = c.fetchone()
    conn.close()
    return word

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    """Начало работы"""
    user_id = message.from_user.id
    
    # Инициализируем прогресс пользователя
    init_user_progress(user_id)
    
    welcome = f"""
🇳🇱 *Hallo! Welkom bij Dutch AI Bot!*

Я интеллектуальный бот для изучения нидерландского. 
Все слова обогащены искусственным интеллектом для лучшего запоминания.

*📚 Основные команды:*
/word - Получить слово на изучение
/today - Слова на сегодня
/quiz - Тест по сегодняшним словам
/stats - Ваша статистика
/know - Отметить слово как выученное

*🔍 Просто напишите слово на нидерландском или русском для перевода!*

*🎯 Система повторений:*
• Новые слова → каждый день
• Слова "учу" → повтор через 3 дня  
• Слова "знаю" → повтор через 7 дней
    """
    
    bot.reply_to(message, welcome, parse_mode='Markdown')
    print(f"👤 Новый пользователь: {user_id}")

@bot.message_handler(commands=['word'])
def send_word(message):
    """Отправить одно слово для изучения"""
    user_id = message.from_user.id
    words = get_todays_words(user_id)
    
    if not words:
        # Если нет слов на сегодня, берем любое новое
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT w.* FROM words w
            JOIN user_progress up ON w.id = up.word_id
            WHERE up.user_id = ? AND up.status = 'new'
            ORDER BY RANDOM()
            LIMIT 1
        ''', (user_id,))
        word = c.fetchone()
        conn.close()
        
        if not word:
            bot.reply_to(message, "🎉 Вы изучили все слова! Добавьте новые в базу.")
            return
        words = [word]
    
    word = words[0]
    
    # Форматируем ответ
    examples = []
    if word['examples']:
        try:
            examples = eval(word['examples'])
        except:
            examples = []
    
    response = f"""
🎯 *Слово для изучения:*

*{word['dutch']}* ({word['article']})
*Перевод:* {word['translation']}

📖 *Объяснение:*
{word['explanation'] or 'Нет объяснения'}

*📝 Примеры:*
"""
    
    for i, example in enumerate(examples[:2], 1):
        if ' | ' in str(example):
            nl, ru = str(example).split(' | ', 1)
            response += f"{i}. *{nl}*\n   _{ru}_\n"
        else:
            response += f"{i}. {example}\n"
    
    response += f"""
📊 *Сложность:* {word.get('difficulty', 'medium')}
🎭 *Часть речи:* {word.get('part_of_speech', 'не указано')}

💡 *Что делать дальше?*
1. Изучите слово и примеры
2. Используйте /know чтобы отметить как выученное
3. Или просто продолжайте - я запомню ваш прогресс
"""
    
    # Добавляем inline-кнопки
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    know_btn = telebot.types.InlineKeyboardButton(
        "✅ Знаю", 
        callback_data=f"know_{word['id']}"
    )
    repeat_btn = telebot.types.InlineKeyboardButton(
        "🔄 Повторить позже", 
        callback_data=f"repeat_{word['id']}"
    )
    another_btn = telebot.types.InlineKeyboardButton(
        "🎲 Другое слово", 
        callback_data="another"
    )
    markup.add(know_btn, repeat_btn)
    markup.add(another_btn)
    
    bot.reply_to(message, response, parse_mode='Markdown', reply_markup=markup)
    
    # Логируем
    print(f"📨 Отправлено слово {word['id']} пользователю {user_id}")

@bot.message_handler(commands=['today'])
def today_words(message):
    """Показать слова на сегодня"""
    user_id = message.from_user.id
    words = get_todays_words(user_id)
    
    if not words:
        bot.reply_to(message, "🎉 На сегодня слов нет! Все выучено или еще не назначено.\nИспользуйте /word для получения нового слова.")
        return
    
    response = "📚 *Ваши слова на сегодня:*\n\n"
    
    for i, word in enumerate(words, 1):
        status_icon = "🟢" if word.get('status') == 'new' else "🟡" if word.get('status') == 'learning' else "🔵"
        response += f"{i}. {status_icon} *{word['dutch']}* - {word['translation']}\n"
    
    # Статистика
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = "known"', (user_id,))
    known = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM words')
    total = c.fetchone()[0]
    conn.close()
    
    response += f"\n📊 *Статистика:*\n"
    response += f"• Выучено: {known}/{total} слов\n"
    response += f"• На сегодня: {len(words)} слов\n"
    response += f"• Прогресс: {int(known/total*100 if total > 0 else 0)}%\n"
    response += f"\n💡 Используйте /quiz для проверки знаний или /word для изучения"
    
    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(commands=['quiz'])
def start_quiz(message):
    """Начать тест по сегодняшним словам"""
    user_id = message.from_user.id
    words = get_todays_words(user_id)
    
    if len(words) < 2:
        bot.reply_to(message, "❌ Нужно хотя бы 2 слова для теста. Изучите больше слов с помощью /word!")
        return
    
    # Выбираем случайное слово
    word = random.choice(words)
    other_words = [w for w in words if w['id'] != word['id']]
    
    # Создаем варианты ответов (правильный + 3 неправильных)
    options = [word['translation']]
    options.extend([w['translation'] for w in random.sample(other_words, min(3, len(other_words)))])
    random.shuffle(options)
    
    # Создаем клавиатуру с вариантами
    markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, 
        one_time_keyboard=True,
        row_width=2
    )
    
    for option in options:
        markup.add(telebot.types.KeyboardButton(option))
    
    # Отправляем вопрос
    question = f"❓ *Как переводится слово:*\n*{word['dutch']}*"
    
    msg = bot.send_message(
        message.chat.id,
        question,
        parse_mode='Markdown',
        reply_markup=markup
    )
    
    # Сохраняем правильный ответ для проверки
    bot.register_next_step_handler(
        msg, 
        check_quiz_answer, 
        correct_answer=word['translation'], 
        word_id=word['id']
    )

def check_quiz_answer(message, correct_answer, word_id):
    """Проверить ответ в тесте"""
    user_id = message.from_user.id
    
    if message.text == correct_answer:
        update_progress(user_id, word_id, 'known')
        bot.reply_to(message, "✅ *Правильно! Отличная работа!*\n\nЭто слово будет повторено через 7 дней.", 
                    parse_mode='Markdown')
    else:
        update_progress(user_id, word_id, 'learning')
        bot.reply_to_message = bot.reply_to(message, 
            f"❌ *Неправильно.*\nПравильный ответ: *{correct_answer}*\n\nЭто слово будет повторено через 3 дня.",
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['know'])
def mark_as_known(message):
    """Отметить последнее слово как выученное"""
    user_id = message.from_user.id
    
    # Ищем последнее отправленное слово
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT word_id FROM message_log 
        WHERE user_id = ? 
        ORDER BY sent_at DESC 
        LIMIT 1
    ''', (user_id,))
    
    result = c.fetchone()
    conn.close()
    
    if result:
        word_id = result[0]
        update_progress(user_id, word_id, 'known')
        
        # Получаем информацию о слове для ответа
        word = get_word_info(word_id)
        if word:
            bot.reply_to(message, 
                f"✅ *Отлично!*\nСлово *{word['dutch']}* отмечено как выученное.\n\nПовторю через 7 дней для закрепления.",
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(message, "✅ Слово отмечено как выученное.")
    else:
        bot.reply_to(message, "🤔 Не могу найти последнее слово.\nСначала получите слово командой /word")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Показать статистику"""
    user_id = message.from_user.id
    conn = get_db()
    c = conn.cursor()
    
    # Общая статистика
    c.execute("SELECT COUNT(*) FROM words")
    total_words = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = "known"', (user_id,))
    known_words = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = "learning"', (user_id,))
    learning_words = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = "new"', (user_id,))
    new_words = c.fetchone()[0]
    
    # Прогресс за сегодня
    today = datetime.now().date()
    c.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND date(last_reviewed) = ?', 
              (user_id, today))
    today_reviews = c.fetchone()[0]
    
    # Недавняя активность
    c.execute('''
        SELECT date(last_reviewed) as day, COUNT(*) as count 
        FROM user_progress 
        WHERE user_id = ? AND last_reviewed IS NOT NULL
        GROUP BY date(last_reviewed)
        ORDER BY day DESC
        LIMIT 7
    ''', (user_id,))
    
    recent_activity = c.fetchall()
    
    conn.close()
    
    # Создаем визуализацию прогресса
    progress_percent = (known_words / total_words * 100) if total_words > 0 else 0
    filled = int(progress_percent / 10)
    progress_bar = "▓" * filled + "░" * (10 - filled)
    
    # Статистика по дням
    activity_text = ""
    for activity in recent_activity:
        activity_text += f"• {activity['day']}: {activity['count']} слов\n"
    
    response = f"""
📊 *Ваша статистика:*

{progress_bar} {progress_percent:.1f}%

*📈 Общий прогресс:*
• Выучено: *{known_words}* из *{total_words}* слов
• Изучается: *{learning_words}* слов
• Новых: *{new_words}* слов

*📅 Сегодня:*
• Повторений: *{today_reviews}* слов

*📆 Активность за неделю:*
{activity_text if activity_text else "• Пока нет активности"}

*🎯 Команды:*
/word - Новое слово
/today - Слова на сегодня  
/quiz - Тест знаний
/know - Отметить как выученное
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
        LIMIT 3
    ''', (f"%{search_text}%", f"%{search_text}%"))
    
    words = c.fetchall()
    conn.close()
    
    if words:
        response = f"🔍 *Найдено по запросу '{search_text}':*\n\n"
        
        for word in words:
            response += f"• *{word['dutch']}* - {word['translation']}\n"
        
        response += f"\n💡 Напишите точное слово для подробной информации"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    else:
        bot.reply_to(message, 
            f"🤔 Слово '{search_text}' не найдено в базе.\n\nПопробуйте:\n• Написать точнее\n• Использовать /word для нового слова\n• Проверить /today для сегодняшних слов"
        )

# ========== INLINE КНОПКИ ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обработка inline-кнопок"""
    user_id = call.from_user.id
    
    if call.data.startswith('know_'):
        word_id = int(call.data.split('_')[1])
        update_progress(user_id, word_id, 'known')
        
        # Получаем информацию о слове
        word = get_word_info(word_id)
        if word:
            response = f"✅ *{word['dutch']}* отмечено как выученное!\n\nПовтор через 7 дней 🗓️"
        else:
            response = "✅ Слово отмечено как выученное!"
        
        bot.answer_callback_query(call.id, response, show_alert=True)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        
    elif call.data.startswith('repeat_'):
        word_id = int(call.data.split('_')[1])
        update_progress(user_id, word_id, 'learning')
        
        bot.answer_callback_query(call.id, "🔄 Слово добавлено в повторение через 3 дня", show_alert=False)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        
    elif call.data == 'another':
        bot.answer_callback_query(call.id, "Ищу другое слово...")
        # Удаляем старые кнопки
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        # Отправляем новое слово
        send_word(call.message)

# ========== ЕЖЕДНЕВНАЯ РАССЫЛКА ==========
def send_daily_notification():
    """Отправка ежедневного уведомления"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT id FROM users")
        users = c.fetchall()
        
        for user in users:
            user_id = user['id']
            words = get_todays_words(user_id)
            
            if words:
                message = f"🌅 *Доброе утро!*\n\n*Ваши слова на сегодня:*\n\n"
                
                for i, word in enumerate(words, 1):
                    message += f"{i}. *{word['dutch']}* - {word['translation']}\n"
                
                # Статистика
                c.execute('SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND status = "known"', (user_id,))
                known = c.fetchone()[0]
                c.execute('SELECT COUNT(*) FROM words')
                total = c.fetchone()[0]
                
                message += f"\n📊 *Прогресс:* {known}/{total} слов ({int(known/total*100 if total > 0 else 0)}%)\n"
                message += f"🎯 *Цель на сегодня:* {len(words)} слов\n"
                message += f"\n💡 Используйте /word для изучения или /quiz для проверки знаний"
                
                try:
                    bot.send_message(user_id, message, parse_mode='Markdown')
                    print(f"📨 Отправлено daily уведомление пользователю {user_id}")
                except Exception as e:
                    print(f"❌ Не удалось отправить пользователю {user_id}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка в daily рассылке: {e}")

# ========== ПЛАНИРОВЩИК ==========
def run_scheduler():
    """Запуск планировщика для ежедневных уведомлений"""
    # Рассылка в 9:00 утра
    schedule.every().day.at("09:00").do(send_daily_notification)
    
    # Проверка каждую минуту
    while True:
        schedule.run_pending()
        time.sleep(60)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    print("=" * 50)
    print("🤖 Dutch AI Bot запускается...")
    print(f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Проверяем наличие базы данных
    if not os.path.exists('dutch_bot.db'):
        print("❌ Критическая ошибка: База данных не создана!")
        print("   Запустите сначала: python init_bot.py")
        sys.exit(1)
    
    # Проверяем таблицы в базе
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM words")
        word_count = c.fetchone()[0]
        conn.close()
        print(f"📊 Загружено слов в базе: {word_count}")
    except:
        print("❌ Ошибка доступа к базе данных")
        sys.exit(1)
    
    # Запускаем планировщик в отдельном потоке
    print("⏰ Запускаю планировщик ежедневных уведомлений...")
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Запускаем бота
    print("✅ Бот готов к работе!")
    print("💡 Отправьте /start в Telegram для начала")
    print("=" * 50)
    
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Ошибка бота: {e}")
        print("🔄 Перезапуск через 10 секунд...")
        time.sleep(10)
        # Можно добавить автоматический перезапуск
