import sqlite3
import json
from datetime import datetime
from pathlib import Path


class DatabaseManager:
    def __init__(self, db_path="crypto_news.db"):
        """Initializes database connection"""
        self.db_path = db_path
        print(f"🗄️ Initializing database: {db_path}")
        self.init_database()
        print("✅ Database ready!")

    def init_database(self):
        """Creates tables if they don't exist"""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.cursor()

            # Settings for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=1000")
            cursor.execute("PRAGMA temp_store=memory")

            # Main table for articles
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

            # Table for scraped URLs (history)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraped_urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    first_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scrape_count INTEGER DEFAULT 1
                )
            ''')

            # Indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_urls_url ON scraped_urls(url)')

            conn.commit()

    def is_article_exists(self, url):
        """Checks if article already exists in database"""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
                return cursor.fetchone() is not None
        except Exception:
            return False

    def is_url_scraped_before(self, url):
        """Checks if URL has been scraped before"""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,))
                return cursor.fetchone() is not None
        except Exception:
            return False

    def record_scraped_url(self, url):
        """Records or updates URL in history - used separately"""
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                cursor = conn.cursor()

                # Check if it exists
                cursor.execute("SELECT scrape_count FROM scraped_urls WHERE url = ?", (url,))
                existing = cursor.fetchone()

                if existing:
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
                return True
        except Exception as e:
            print(f"❌ Error recording URL: {str(e)}")
            return False

    def save_article(self, article_data):
        """Saves article to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Check if article already exists
                cursor.execute("SELECT 1 FROM articles WHERE url = ?", (article_data['url'],))
                if cursor.fetchone():
                    print(f"⚠️ Article already exists: {article_data['title'][:50]}...")
                    # Record in URL history
                    self.record_scraped_url(article_data['url'])
                    return False

                # Save the article
                cursor.execute('''
                    INSERT INTO articles 
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

                # Record in URL history in separate transaction
                conn.commit()

            # Record URL history in separate connection
            with sqlite3.connect(self.db_path) as conn2:
                cursor2 = conn2.cursor()

                # Check if URL exists
                cursor2.execute("SELECT scrape_count FROM scraped_urls WHERE url = ?", (article_data['url'],))
                existing = cursor2.fetchone()

                if existing:
                    cursor2.execute('''
                        UPDATE scraped_urls 
                        SET last_seen_at = CURRENT_TIMESTAMP, 
                            scrape_count = scrape_count + 1 
                        WHERE url = ?
                    ''', (article_data['url'],))
                else:
                    cursor2.execute('''
                        INSERT INTO scraped_urls (url) VALUES (?)
                    ''', (article_data['url'],))

                conn2.commit()

            print(f"✅ Saved article: {article_data['title'][:50]}...")
            return True

        except Exception as e:
            print(f"❌ Error saving article: {str(e)}")
            return False

    def save_multiple_articles(self, articles):
        """Saves multiple articles"""
        print(f"💾 Saving {len(articles)} articles to database...")

        saved_count = 0
        duplicate_count = 0

        for article in articles:
            if self.save_article(article):
                saved_count += 1
            else:
                duplicate_count += 1

        print(f"📊 Result: {saved_count} new articles, {duplicate_count} duplicates")
        return saved_count, duplicate_count

    def get_unprocessed_articles(self, limit=None):
        """Returns unprocessed articles for analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # For dictionary-like results
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
        """Marks article as analyzed"""
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
            print(f"✅ Article {article_id} marked as analyzed")

    def cleanup_old_analyzed_articles(self, days_to_keep=7):
        """Deletes old analyzed articles (scraped_urls remain!)"""
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

            print(f"🧹 Deleted {deleted_count} old analyzed articles")
            return deleted_count

    def get_database_stats(self):
        """Returns database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total articles
            cursor.execute("SELECT COUNT(*) FROM articles")
            total_articles = cursor.fetchone()[0]

            # Unprocessed articles
            cursor.execute("SELECT COUNT(*) FROM articles WHERE processed = FALSE")
            unprocessed_articles = cursor.fetchone()[0]

            # Analyzed articles
            cursor.execute("SELECT COUNT(*) FROM articles WHERE processed = TRUE")
            analyzed_articles = cursor.fetchone()[0]

            # Total scraped URLs
            cursor.execute("SELECT COUNT(*) FROM scraped_urls")
            total_scraped_urls = cursor.fetchone()[0]

            # Newest article
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
        """Exports articles to JSON file"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM articles"
            if processed_only:
                query += " WHERE processed = TRUE"
            query += " ORDER BY scraped_at DESC"

            cursor.execute(query)
            articles = [dict(row) for row in cursor.fetchall()]

            # Save to JSON file
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2, default=str)

            print(f"📤 Exported {len(articles)} articles to {filename}")
            return len(articles)


# Test function
def test_database():
    """Tests database functionality"""
    print("=== DATABASE TEST ===")

    # Initialize database
    db = DatabaseManager("test_crypto_news.db")

    # Test data
    test_article = {
        'url': 'https://example.com/test-article',
        'title': 'Test Bitcoin Article',
        'content': 'This is a test article about Bitcoin and cryptocurrency market trends.',
        'author': 'Test Author',
        'date': '2025-06-09',
        'content_length': 75
    }

    # Test saving
    print("\n1. Testing article saving...")
    success = db.save_article(test_article)
    print(f"Result: {'Success' if success else 'Failure'}")

    # Test duplicate saving
    print("\n2. Testing duplicate saving...")
    success = db.save_article(test_article)
    print(f"Result: {'Unexpectedly successful' if success else 'Correctly blocked duplicate'}")

    # Test statistics
    print("\n3. Database statistics:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Test unprocessed articles
    print("\n4. Unprocessed articles:")
    unprocessed = db.get_unprocessed_articles()
    print(f"   Found: {len(unprocessed)} articles")

    # Clean up test database
    Path("test_crypto_news.db").unlink(missing_ok=True)
    print("\n✅ Database test completed successfully!")


if __name__ == "__main__":
    test_database()
