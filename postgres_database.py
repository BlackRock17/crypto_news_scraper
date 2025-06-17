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
            """Запазва една статия в базата данни"""
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
                        return True

            except psycopg2.Error as e:
                print(f"❌ Грешка при запазване: {e}")
                return False
