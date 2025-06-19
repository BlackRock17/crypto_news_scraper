#!/usr/bin/env python3
"""
Debug tool for analyzing CoinDesk Scraper behavior
"""

import sqlite3
from datetime import datetime, timedelta
import re
from collections import defaultdict


def analyze_scraped_data():
    """Analyzes the data in the SQLite database"""
    print("=== SCRAPER DATA ANALYSIS ===")

    try:
        conn = sqlite3.connect('crypto_news.db')
        cursor = conn.cursor()

        # 1. General statistics
        print("\n📊 GENERAL STATISTICS:")
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]
        print(f"   📰 Total articles in database: {total_articles}")

        cursor.execute("SELECT COUNT(*) FROM scraped_urls")
        total_urls = cursor.fetchone()[0]
        print(f"   🔗 Total scraped URLs: {total_urls}")

        # 2. Statistics by scraping date
        print("\n📅 STATISTICS BY SCRAPING DATE:")
        cursor.execute("""
            SELECT DATE(scraped_at) as date, COUNT(*) as count,
                   AVG(content_length) as avg_length
            FROM articles 
            GROUP BY DATE(scraped_at) 
            ORDER BY date DESC
            LIMIT 7
        """)

        scraping_by_date = cursor.fetchall()
        for date, count, avg_length in scraping_by_date:
            print(f"   📅 {date}: {count} articles (average {int(avg_length)} chars)")

        # 3. URL patterns analysis
        print("\n🔍 URL PATTERNS ANALYSIS:")
        cursor.execute("SELECT url FROM articles ORDER BY scraped_at DESC LIMIT 10")
        recent_urls = cursor.fetchall()

        url_patterns = defaultdict(int)
        dates_in_urls = []

        for (url,) in recent_urls:
            # Extract category
            if '/markets/' in url:
                url_patterns['markets'] += 1
            elif '/policy/' in url:
                url_patterns['policy'] += 1
            elif '/tech/' in url:
                url_patterns['tech'] += 1
            elif '/business/' in url:
                url_patterns['business'] += 1
            elif '/daybook' in url:
                url_patterns['daybook'] += 1
            else:
                url_patterns['other'] += 1

            # Extract date from URL
            date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
            if date_match:
                year, month, day = date_match.groups()
                dates_in_urls.append(f"{year}-{month}-{day}")

        print("   📋 Categories of the last 10 articles:")
        for category, count in url_patterns.items():
            print(f"      - {category}: {count}")

        print("   📅 Dates in URLs of the last 10 articles:")
        unique_dates = list(set(dates_in_urls))
        for date in sorted(unique_dates, reverse=True):
            count = dates_in_urls.count(date)
            print(f"      - {date}: {count} articles")

        # 4. Newest vs oldest articles
        print("\n🕒 TEMPORAL ANALYSIS:")
        cursor.execute("""
            SELECT title, url, scraped_at 
            FROM articles 
            ORDER BY scraped_at DESC 
            LIMIT 3
        """)
        newest = cursor.fetchall()

        cursor.execute("""
            SELECT title, url, scraped_at 
            FROM articles 
            ORDER BY scraped_at ASC 
            LIMIT 3
        """)
        oldest = cursor.fetchall()

        print("   📰 Newest articles:")
        for title, url, scraped_at in newest:
            date_in_url = extract_date_from_url(url)
            print(f"      - {title[:50]}... (scraped: {scraped_at}, URL date: {date_in_url})")

        print("   📰 Oldest articles:")
        for title, url, scraped_at in oldest:
            date_in_url = extract_date_from_url(url)
            print(f"      - {title[:50]}... (scraped: {scraped_at}, URL date: {date_in_url})")

        conn.close()

    except Exception as e:
        print(f"❌ Error during analysis: {e}")


def extract_date_from_url(url):
    """Extracts date from CoinDesk URL"""
    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if date_match:
        year, month, day = date_match.groups()
        return f"{year}-{month}-{day}"
    return "unknown"


def simulate_scraping_decision():
    """Simulates how the scraper decides which articles to scrape"""
    print("\n=== SCRAPING DECISION SIMULATION ===")

    try:
        from scraper import CoinDeskScraper

        # Create scraper without database for testing
        scraper = CoinDeskScraper(use_database=False)
        print("📡 Connecting to CoinDesk...")

        # Get articles from main page
        article_links = scraper.get_article_links()
        print(f"📰 Found {len(article_links)} articles from main page")

        # Analyze first 10
        print("\n🔍 ANALYSIS OF FIRST 10 ARTICLES:")
        for i, article in enumerate(article_links[:10], 1):
            url = article['url']
            title = article['title']
            date_in_url = extract_date_from_url(url)

            # Check if it's in the database
            is_scraped = check_if_url_scraped(url)
            status = "🟢 NEW" if not is_scraped else "🔴 SCRAPED"

            print(f"   {i:2d}. {status} | {date_in_url} | {title[:45]}...")

        # Statistics by date
        print("\n📊 STATISTICS BY ARTICLE DATE:")
        date_stats = defaultdict(lambda: {'total': 0, 'new': 0, 'scraped': 0})

        for article in article_links:
            url = article['url']
            date_in_url = extract_date_from_url(url)
            is_scraped = check_if_url_scraped(url)

            date_stats[date_in_url]['total'] += 1
            if is_scraped:
                date_stats[date_in_url]['scraped'] += 1
            else:
                date_stats[date_in_url]['new'] += 1

        for date in sorted(date_stats.keys(), reverse=True):
            stats = date_stats[date]
            print(f"   📅 {date}: {stats['total']} total | {stats['new']} new | {stats['scraped']} scraped")

    except Exception as e:
        print(f"❌ Error during simulation: {e}")


def check_if_url_scraped(url):
    """Checks if URL has been scraped"""
    try:
        conn = sqlite3.connect('crypto_news.db')
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    except:
        return False


def recommend_scraping_strategy():
    """Recommends scraping strategy"""
    print("\n=== SCRAPING STRATEGY RECOMMENDATIONS ===")

    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"📅 Today is: {today}")
    print(f"📅 Yesterday was: {yesterday}")

    try:
        conn = sqlite3.connect('crypto_news.db')
        cursor = conn.cursor()

        # Check if we have articles from today
        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE url LIKE ? OR url LIKE ?
        """, (f'%/{today.replace("-", "/")}/%', f'%{today}%'))

        today_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE url LIKE ? OR url LIKE ?
        """, (f'%/{yesterday.replace("-", "/")}/%', f'%{yesterday}%'))

        yesterday_count = cursor.fetchone()[0]

        print(f"\n📊 STATISTICS:")
        print(f"   📰 Articles from today in database: {today_count}")
        print(f"   📰 Articles from yesterday in database: {yesterday_count}")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if today_count == 0:
            print("   🎯 Recommended: Scrape articles from today with limit 10-15")
            print("   📝 Command: python run_scraper.py scrape --limit 15")
        elif today_count < 5:
            print("   🎯 Recommended: Scrape more articles with limit 10")
            print("   📝 Command: python run_scraper.py scrape --limit 10")
        else:
            print("   ✅ Good coverage for today, you can scrape 5-10 new ones")
            print("   📝 Command: python run_scraper.py scrape --limit 5")

        conn.close()

    except Exception as e:
        print(f"❌ Error in recommendations: {e}")


def main():
    """Main function"""
    print("🔍 COINDESK SCRAPER DEBUG TOOL")
    print("=" * 50)

    print("\nChoose analysis:")
    print("1. Scraped data analysis")
    print("2. Scraping decision simulation")
    print("3. Scraping strategy recommendations")
    print("4. All analyses")

    try:
        choice = input("\nEnter number (1-4): ").strip()

        if choice == "1":
            analyze_scraped_data()
        elif choice == "2":
            simulate_scraping_decision()
        elif choice == "3":
            recommend_scraping_strategy()
        elif choice == "4":
            analyze_scraped_data()
            simulate_scraping_decision()
            recommend_scraping_strategy()
        else:
            print("❌ Invalid choice")

    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
