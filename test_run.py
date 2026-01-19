import sqlite3

DB = 'dutch_bot.db'

def random_word():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT 1')
    w = c.fetchone()
    conn.close()
    return w

def today_words(limit=5):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT dutch, russian FROM words ORDER BY RANDOM() LIMIT ?',(limit,))
    ws = c.fetchall()
    conn.close()
    return ws

if __name__ == '__main__':
    print('Random word:')
    w = random_word()
    if w:
        print(f"{w[0]} - {w[1]}")
    else:
        print('No word found')

    print('\nToday words:')
    for i, (d,r) in enumerate(today_words(),1):
        print(f"{i}. {d} - {r}")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM words')
    print('\nTotal words in DB:', c.fetchone()[0])
    conn.close()
