import openai
import sqlite3
import os
import time
from datetime import datetime, timedelta

# ========== НАСТРОЙКИ ==========
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # Ваш ключ из Railway
BOT_TOKEN = os.environ.get("BOT_TOKEN")           # Токен бота из Railway

# Промпт для OpenAI
PROMPT_TEMPLATE = """Объясни слово "{dutch_word}" (перевод: {russian_translation}) как для начинающего изучать нидерландский язык.

Требования:
1. Краткое объяснение на русском (2-3 предложения)
2. Два простых бытовых примера предложений на нидерландском с переводом
3. Укажи артикль (de/het) если это существительное
4. Для глаголов - укажи базовую форму

Формат ответа JSON:
{{
  "explanation": "твое объяснение",
  "examples": ["пример1 | перевод1", "пример2 | перевод2"],
  "article": "de/het/-",
  "part_of_speech": "существительное/глагол/прилагательное/...",
  "difficulty": "easy/medium/hard"
}}"""

# ========== ФУНКЦИИ ==========
def init_database():
    """Создание базы данных"""
    conn = sqlite3.connect('dutch_bot.db')
    c = conn.cursor()
    
    # Таблица всех слов
    c.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dutch TEXT NOT NULL,
            translation TEXT NOT NULL,
            explanation TEXT,
            examples TEXT,  # JSON список примеров
            article TEXT,
            part_of_speech TEXT,
            difficulty TEXT,
            theme_id INTEGER DEFAULT 1,
            processed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица прогресса пользователя
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word_id INTEGER NOT NULL,
            status TEXT DEFAULT 'new',  # new, learning, known, reviewed
            next_review DATE,
            review_count INTEGER DEFAULT 0,
            last_reviewed DATE,
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
    ''')
    
    # Таблица ежедневных слов
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word_id INTEGER NOT NULL,
            date DATE NOT NULL,
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
    ''')
    
    conn.commit()
    return conn

def process_word_with_openai(dutch_word, translation):
    """Обработка слова через OpenAI"""
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = PROMPT_TEMPLATE.format(
            dutch_word=dutch_word,
            russian_translation=translation
        )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "Ты помощник для изучения нидерландского языка. Отвечай строго в JSON формате."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        return eval(result)  # Парсим JSON
        
    except Exception as e:
        print(f"Ошибка при обработке слова {dutch_word}: {e}")
        return None

def load_words_from_file(filename='woorden.txt'):
    """Загрузка слов из файла"""
    words = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if ' - ' in line:
                dutch, translation = line.split(' - ', 1)
                words.append((dutch.strip(), translation.strip()))
    return words

def main():
    """Основная функция инициализации"""
    print("🚀 Начинаю инициализацию бота...")
    
    # Проверка ключей
    if not OPENAI_API_KEY:
        print("❌ Ошибка: OPENAI_API_KEY не установлен")
        print("Добавьте в Railway переменную OPENAI_API_KEY")
        return
    
    if not BOT_TOKEN:
        print("⚠️  Предупреждение: BOT_TOKEN не установлен")
    
    # Создаем БД
    conn = init_database()
    c = conn.cursor()
    
    # Загружаем слова
    print("📖 Загружаю слова из woorden.txt...")
    words = load_words_from_file()
    print(f"📊 Найдено слов: {len(words)}")
    
    # Обрабатываем слова через OpenAI
    print("🤖 Начинаю обработку слов через OpenAI...")
    
    for i, (dutch, translation) in enumerate(words, 1):
        print(f"  [{i}/{len(words)}] Обрабатываю: {dutch} -> {translation}")
        
        # Проверяем, не обработано ли уже
        c.execute("SELECT id FROM words WHERE dutch = ?", (dutch,))
        if c.fetchone():
            print(f"    ✓ Уже в базе, пропускаю")
            continue
        
        # Получаем данные от OpenAI
        ai_data = process_word_with_openai(dutch, translation)
        
        if ai_data:
            # Сохраняем в БД
            c.execute('''
                INSERT INTO words 
                (dutch, translation, explanation, examples, article, part_of_speech, difficulty, processed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                dutch,
                translation,
                ai_data.get('explanation', ''),
                str(ai_data.get('examples', [])),
                ai_data.get('article', '-'),
                ai_data.get('part_of_speech', 'unknown'),
                ai_data.get('difficulty', 'medium')
            ))
            conn.commit()
            print(f"    ✅ Сохранено")
        else:
            print(f"    ❌ Ошибка, сохраняю без обработки")
            c.execute('''
                INSERT INTO words (dutch, translation, processed)
                VALUES (?, ?, 0)
            ''', (dutch, translation))
            conn.commit()
        
        # Пауза чтобы не превысить лимиты API
        time.sleep(1.5)
    
    # Статистика
    c.execute("SELECT COUNT(*) FROM words WHERE processed = 1")
    processed = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM words WHERE processed = 0")
    not_processed = c.fetchone()[0]
    
    print(f"\n✅ Инициализация завершена!")
    print(f"📊 Статистика:")
    print(f"   Всего слов в базе: {len(words)}")
    print(f"   Обработано OpenAI: {processed}")
    print(f"   Без обработки: {not_processed}")
    print(f"\n💡 Запустите основного бота: python main_bot.py")
    
    conn.close()

if __name__ == "__main__":
    main()
