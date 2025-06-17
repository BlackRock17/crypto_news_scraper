import psycopg2
import psycopg2.extras
import json
from datetime import datetime
import os


class PostgreSQLDatabaseManager:
        def __init__(self):
            print("🐘 Свързване с PostgreSQL...")

            # Конфигурация за базата
            self.db_config = {
                'host': 'localhost',
                'port': 5432,
                'database': 'crypto_news',
                'user': 'crypto_user',
                'password': 'password'
            }

            # Тестваме връзката
            self._test_connection()
            self.init_database()
            print("✅ PostgreSQL готов!")

        def _test_connection(self):
            """Проверява дали може да се свърже с PostgreSQL"""
            try:
                conn = psycopg2.connect(**self.db_config)
                conn.close()
                print("✅ Връзка с PostgreSQL успешна")
            except psycopg2.Error as e:
                print(f"❌ Грешка при свързване: {e}")
                raise

        def get_connection(self):
            """Връща нова връзка към базата"""
            return psycopg2.connect(**self.db_config)

        def init_database(self):
            """Създава таблиците за база данни А (статии за scraping)"""
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Таблица за статии
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS articles (
                            id SERIAL PRIMARY KEY,
                            url TEXT UNIQUE NOT NULL,
                            title TEXT NOT NULL,
                            content TEXT NOT NULL,
                            author TEXT,
                            published_date TEXT,
                            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            content_length INTEGER,
                            is_analyzed BOOLEAN DEFAULT FALSE
                        )
                    ''')

                    # Таблица за scraped URLs (за да не повтаряме)
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS scraped_urls (
                            id SERIAL PRIMARY KEY,
                            url TEXT UNIQUE NOT NULL,
                            first_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            scrape_count INTEGER DEFAULT 1
                        )
                    ''')

                    # Индекси за по-бързи заявки
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_is_analyzed ON articles(is_analyzed)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_urls_url ON scraped_urls(url)')

                    print("✅ Таблици за база данни А създадени")
                    conn.commit()

        def save_article(self, article_data):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # Проверяваме дали статията вече съществува
                        cursor.execute("SELECT 1 FROM articles WHERE url = %s", (article_data['url'],))
                        if cursor.fetchone():
                            print(f"⚠️ Статията вече съществува: {article_data['title'][:50]}...")
                            return False

                        # Запазваме статията
                        cursor.execute('''
                            INSERT INTO articles 
                            (url, title, content, author, published_date, content_length)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (
                            article_data['url'],
                            article_data['title'],
                            article_data['content'],
                            article_data['author'],
                            str(article_data['date']),
                            article_data['content_length']
                        ))

                        conn.commit()
                        print(f"✅ Запазена статия: {article_data['title'][:50]}...")

                        # ДОБАВИ ТОЗИ РЕД:
                        self.record_scraped_url(article_data['url'])

                        return True

            except psycopg2.Error as e:
                print(f"❌ Грешка при запазване: {e}")
                return False


            except psycopg2.Error as e:
                print(f"❌ Грешка при запазване: {e}")
                return False

        def save_multiple_articles(self, articles):
            """Запазва множество статии наведнъж (по-бързо)"""
            print(f"💾 Запазване на {len(articles)} статии...")

            saved_count = 0
            duplicate_count = 0

            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:

                        for article in articles:
                            # Проверяваме за дублиращи се статии
                            cursor.execute("SELECT 1 FROM articles WHERE url = %s", (article['url'],))
                            if cursor.fetchone():
                                duplicate_count += 1
                                continue

                            # Запазваме статията
                            cursor.execute('''
                                INSERT INTO articles 
                                (url, title, content, author, published_date, content_length)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            ''', (
                                article['url'],
                                article['title'],
                                article['content'],
                                article['author'],
                                str(article['date']),
                                article['content_length']
                            ))

                            saved_count += 1

                        conn.commit()

            except psycopg2.Error as e:
                print(f"❌ Грешка при запазване: {e}")

            print(f"📊 Резултат: {saved_count} нови статии, {duplicate_count} дублиращи се")
            return saved_count, duplicate_count

        def is_url_scraped_before(self, url):
            """Проверява дали URL-а е бил скрапван преди"""
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM scraped_urls WHERE url = %s", (url,))
                        return cursor.fetchone() is not None
            except psycopg2.Error:
                return False

        def record_scraped_url(self, url):
            """Записва URL в историята (за да не го скрапваме пак)"""
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # PostgreSQL UPSERT синтаксис
                        cursor.execute('''
                            INSERT INTO scraped_urls (url) 
                            VALUES (%s)
                            ON CONFLICT (url) 
                            DO UPDATE SET 
                                last_seen_at = CURRENT_TIMESTAMP,
                                scrape_count = scraped_urls.scrape_count + 1
                        ''', (url,))

                        conn.commit()
                        return True
            except psycopg2.Error as e:
                print(f"❌ Грешка при записване на URL: {e}")
                return False

        def get_database_stats(self):
            """Показва статистики за базата данни"""
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # Общ брой статии
                        cursor.execute("SELECT COUNT(*) FROM articles")
                        total_articles = cursor.fetchone()[0]

                        # Анализирани статии
                        cursor.execute("SELECT COUNT(*) FROM articles WHERE is_analyzed = TRUE")
                        analyzed_articles = cursor.fetchone()[0]

                        # Неанализирани статии
                        cursor.execute("SELECT COUNT(*) FROM articles WHERE is_analyzed = FALSE")
                        unanalyzed_articles = cursor.fetchone()[0]

                        return {
                            'total_articles': total_articles,
                            'analyzed_articles': analyzed_articles,
                            'unprocessed_articles': unanalyzed_articles  # ← ТОЗИ РЕД
                        }
            except psycopg2.Error as e:
                print(f"❌ Грешка при статистики: {e}")
                return {}
