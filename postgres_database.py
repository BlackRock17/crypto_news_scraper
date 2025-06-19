import psycopg2
import psycopg2.extras
import json
from datetime import datetime
import os


class PostgreSQLDatabaseManager:
        def __init__(self):
            print("🐘 Connecting to PostgreSQL...")

            # Database configuration
            self.db_config = {
                'host': 'localhost',
                'port': 5432,
                'database': 'crypto_news',
                'user': 'crypto_user',
                'password': 'password'
            }

            # Test the connection
            self._test_connection()
            self.init_database()
            print("✅ PostgreSQL ready!")

        def _test_connection(self):
            """Checks if it can connect to PostgreSQL"""
            try:
                conn = psycopg2.connect(**self.db_config)
                conn.close()
                print("✅ PostgreSQL connection successful")
            except psycopg2.Error as e:
                print(f"❌ Connection error: {e}")
                raise

        def get_connection(self):
            """Returns a new connection to the database"""
            return psycopg2.connect(**self.db_config)

        def init_database(self):
            """Creates tables for database A (articles for scraping)"""
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Articles table
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

                    # Scraped URLs table (to avoid duplicates)
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS scraped_urls (
                            id SERIAL PRIMARY KEY,
                            url TEXT UNIQUE NOT NULL,
                            first_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            scrape_count INTEGER DEFAULT 1
                        )
                    ''')

                    # Indexes for faster queries
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_is_analyzed ON articles(is_analyzed)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_urls_url ON scraped_urls(url)')

                    print("✅ Tables for database A created")
                    conn.commit()

        def save_article(self, article_data):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # Check if article already exists
                        cursor.execute("SELECT 1 FROM articles WHERE url = %s", (article_data['url'],))
                        if cursor.fetchone():
                            print(f"⚠️ Article already exists: {article_data['title'][:50]}...")
                            return False

                        # Save the article
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
                        print(f"✅ Saved article: {article_data['title'][:50]}...")

                        # ADD THIS LINE:
                        self.record_scraped_url(article_data['url'])

                        return True

            except psycopg2.Error as e:
                print(f"❌ Save error: {e}")
                return False


            except psycopg2.Error as e:
                print(f"❌ Save error: {e}")
                return False

        def save_multiple_articles(self, articles):
            """Saves multiple articles at once (faster)"""
            print(f"💾 Saving {len(articles)} articles...")

            saved_count = 0
            duplicate_count = 0

            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:

                        for article in articles:
                            # Check for duplicate articles
                            cursor.execute("SELECT 1 FROM articles WHERE url = %s", (article['url'],))
                            if cursor.fetchone():
                                duplicate_count += 1
                                continue

                            # Save the article
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
                print(f"❌ Save error: {e}")

            print(f"📊 Result: {saved_count} new articles, {duplicate_count} duplicates")
            return saved_count, duplicate_count

        def is_url_scraped_before(self, url):
            """Checks if URL has been scraped before"""
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM scraped_urls WHERE url = %s", (url,))
                        return cursor.fetchone() is not None
            except psycopg2.Error:
                return False

        def record_scraped_url(self, url):
            """Records URL in history (so we don't scrape it again)"""
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # PostgreSQL UPSERT syntax
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
                print(f"❌ URL record error: {e}")
                return False

        def get_database_stats(self):
            """Shows database statistics"""
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        # Total articles
                        cursor.execute("SELECT COUNT(*) FROM articles")
                        total_articles = cursor.fetchone()[0]

                        # Analyzed articles
                        cursor.execute("SELECT COUNT(*) FROM articles WHERE is_analyzed = TRUE")
                        analyzed_articles = cursor.fetchone()[0]

                        # Unanalyzed articles
                        cursor.execute("SELECT COUNT(*) FROM articles WHERE is_analyzed = FALSE")
                        unanalyzed_articles = cursor.fetchone()[0]

                        return {
                            'total_articles': total_articles,
                            'analyzed_articles': analyzed_articles,
                            'unprocessed_articles': unanalyzed_articles  # ← THIS LINE
                        }
            except psycopg2.Error as e:
                print(f"❌ Statistics error: {e}")
                return {}
