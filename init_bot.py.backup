
import sqlite3
import os

DB_NAME = "dutch_bot.db"
WORDS_FILE = "woorden.txt"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dutch TEXT NOT NULL UNIQUE,
        russian TEXT NOT NULL,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        word_id INTEGER NOT NULL,
        stage INTEGER DEFAULT 0,
        next_review DATE,
        last_reviewed DATE,
        correct_count INTEGER DEFAULT 0,
        wrong_count INTEGER DEFAULT 0,
        FOREIGN KEY (word_id) REFERENCES words(id),
        UNIQUE(user_id, word_id)
    )""")
    
    conn.commit()
    conn.close()

def main():
    print("🚀 Инициализация базы данных...")
    
    init_database()
    
    if not os.path.exists(WORDS_FILE):
        print(f"❌ Файл {WORDS_FILE} не найден!")
        return
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or " - " not in line:
                continue
            
            dutch, russian = line.split(" - ", 1)
            dutch = dutch.strip()
            russian = russian.strip()
            
            if not dutch or not russian:
                continue
            
            try:
                c.execute("INSERT OR IGNORE INTO words (dutch, russian) VALUES (?, ?)",
                         (dutch, russian))
            except Exception as e:
                print(f"⚠️ Ошибка в строке {line_num}: {e}")
    
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM words")
    count = c.fetchone()[0]
    
    print(f"✅ Загружено слов: {count}")
    conn.close()

if __name__ == "__main__":
    main()

