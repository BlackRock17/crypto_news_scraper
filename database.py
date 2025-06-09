import sqlite3
import json
from datetime import datetime
from pathlib import Path


class DatabaseManager:
    def __init__(self, db_path="crypto_news.db"):
        """Инициализира database connection"""
        self.db_path = db_path
        print(f"🗄️ Инициализиране на база данни: {db_path}")
        self.init_database()
        print("✅ База данни готова!")

    def init_database(self):
        """Създава таблиците ако не съществуват"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Главна таблица за статии
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author TEXT,
                    published_date TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    content_length INTEGER,
                    processed BOOLEAN DEFAULT FALSE,
                    analyzed_at TIMESTAMP NULL,
                    sentiment_result TEXT NULL
                )
            ''')

            # Таблица за scraped URLs (history)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraped_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    first_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scrape_count INTEGER DEFAULT 1
                )
            ''')

            # Индекси за производителност
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_urls_url ON scraped_urls(url)')

            conn.commit()

    def is_article_exists(self, url):
        """Проверява дали статията вече съществува в базата"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
            return cursor.fetchone() is not None

    def is_url_scraped_before(self, url):
        """Проверява дали URL-а е бил скрапван преди"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,))
            return cursor.fetchone() is not None

    def record_scraped_url(self, url):
        """Записва или update-ва URL в историята"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if self.is_url_scraped_before(url):
                # Update existing record
                cursor.execute('''
                    UPDATE scraped_urls 
                    SET last_seen_at = CURRENT_TIMESTAMP, 
                        scrape_count = scrape_count + 1 
                    WHERE url = ?
                ''', (url,))
            else:
                # Insert new record
                cursor.execute('''
                    INSERT INTO scraped_urls (url) VALUES (?)
                ''', (url,))

            conn.commit()

    def save_article(self, article_data):
        """Запазва статия в базата данни"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Записваме статията
                cursor.execute('''
                    INSERT OR IGNORE INTO articles 
                    (url, title, content, author, published_date, content_length)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    article_data['url'],
                    article_data['title'],
                    article_data['content'],
                    article_data['author'],
                    str(article_data['date']),
                    article_data['content_length']
                ))

                # Записваме в URL историята
                self.record_scraped_url(article_data['url'])

                conn.commit()

                if cursor.rowcount > 0:
                    print(f"✅ Запазена статия: {article_data['title'][:50]}...")
                    return True
                else:
                    print(f"⚠️ Статията вече съществува: {article_data['title'][:50]}...")
                    return False

        except Exception as e:
            print(f"❌ Грешка при запазване на статия: {str(e)}")
            return False

    def save_multiple_articles(self, articles):
        """Запазва множество статии"""
        print(f"💾 Запазване на {len(articles)} статии в базата...")

        saved_count = 0
        duplicate_count = 0

        for article in articles:
            if self.save_article(article):
                saved_count += 1
            else:
                duplicate_count += 1

        print(f"📊 Резултат: {saved_count} нови статии, {duplicate_count} дублиращи се")
        return saved_count, duplicate_count

    def get_unprocessed_articles(self, limit=None):
        """Връща непроцесирани статии за анализ"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # За dictionary-like резултати
            cursor = conn.cursor()

            query = '''
                SELECT id, url, title, content, author, published_date, content_length, scraped_at
                FROM articles 
                WHERE processed = FALSE 
                ORDER BY scraped_at DESC
            '''

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def mark_article_as_analyzed(self, article_id, sentiment_result=None):
        """Маркира статия като анализирана"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            sentiment_json = json.dumps(sentiment_result) if sentiment_result else None

            cursor.execute('''
                UPDATE articles 
                SET processed = TRUE, 
                    analyzed_at = CURRENT_TIMESTAMP,
                    sentiment_result = ?
                WHERE id = ?
            ''', (sentiment_json, article_id))

            conn.commit()
            print(f"✅ Статия {article_id} маркирана като анализирана")

    def cleanup_old_analyzed_articles(self, days_to_keep=7):
        """Изтрива стари анализирани статии (scraped_urls остават!)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM articles 
                WHERE processed = TRUE 
                AND analyzed_at IS NOT NULL 
                AND datetime(analyzed_at) < datetime('now', '-{} days')
            '''.format(days_to_keep))

            deleted_count = cursor.rowcount
            conn.commit()

            print(f"🧹 Изтрити {deleted_count} стари анализирани статии")
            return deleted_count

    def get_database_stats(self):
        """Връща статистики за базата данни"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Общ брой статии
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]

            # Непроцесирани статии
            cursor.execute("SELECT COUNT(*) FROM articles WHERE processed = FALSE")
            unprocessed_articles = cursor.fetchone()[0]

            # Анализирани статии
            cursor.execute("SELECT COUNT(*) FROM articles WHERE processed = TRUE")
            analyzed_articles = cursor.fetchone()[0]

            # Общо scraped URLs
            cursor.execute("SELECT COUNT(*) FROM scraped_urls")
            total_scraped_urls = cursor.fetchone()[0]

            # Най-нова статия
            cursor.execute("SELECT title, scraped_at FROM articles ORDER BY scraped_at DESC LIMIT 1")
            latest_article = cursor.fetchone()

            return {
                'total_articles': total_articles,
                'unprocessed_articles': unprocessed_articles,
                'analyzed_articles': analyzed_articles,
                'total_scraped_urls': total_scraped_urls,
                'latest_article': latest_article
            }

    def export_articles_to_json(self, filename="articles_export.json", processed_only=False):
        """Експортира статии в JSON файл"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM articles"
            if processed_only:
                query += " WHERE processed = TRUE"
            query += " ORDER BY scraped_at DESC"

            cursor.execute(query)
            articles = [dict(row) for row in cursor.fetchall()]

            # Запазваме в JSON файл
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2, default=str)

            print(f"📤 Експортирани {len(articles)} статии в {filename}")
            return len(articles)


# Тестова функция
def test_database():
    """Тества database функционалността"""
    print("=== ТЕСТ НА DATABASE ===")

    # Инициализираме database
    db = DatabaseManager("test_crypto_news.db")

    # Тестови данни
    test_article = {
        'url': 'https://example.com/test-article',
        'title': 'Test Bitcoin Article',
        'content': 'This is a test article about Bitcoin and cryptocurrency market trends.',
        'author': 'Test Author',
        'date': '2025-06-09',
        'content_length': 75
    }

    # Тестваме запазване
    print("\n1. Тестване на запазване на статия...")
    success = db.save_article(test_article)
    print(f"Резултат: {'Успех' if success else 'Неуспех'}")

    # Тестваме дублирано запазване
    print("\n2. Тестване на дублирано запазване...")
    success = db.save_article(test_article)
    print(f"Резултат: {'Неочаквано успешно' if success else 'Правилно блокирано дублиране'}")

    # Тестваме статистики
    print("\n3. Статистики на базата данни:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Тестваме unprocessed статии
    print("\n4. Непроцесирани статии:")
    unprocessed = db.get_unprocessed_articles()
    print(f"   Намерени: {len(unprocessed)} статии")

    # Почистваме test базата
    Path("test_crypto_news.db").unlink(missing_ok=True)
    print("\n✅ Database тест завършен успешно!")


if __name__ == "__main__":
    test_database()
