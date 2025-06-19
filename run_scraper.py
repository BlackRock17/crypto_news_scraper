#!/usr/bin/env python3
"""
CoinDesk Crypto News Scraper - Command Line Interface with Smart Scraping
Usage: python run_scraper.py [options]
"""

import argparse
import time
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path

# Import for the new scraper
try:
    from improved_latest_news_scraper import CoinDeskLatestNewsScraper

    LATEST_NEWS_AVAILABLE = True
except ImportError:
    LATEST_NEWS_AVAILABLE = False

# Standard imports
from scraper import CoinDeskScraper
from postgres_database import PostgreSQLDatabaseManager as DatabaseManager


def scrape_command(args):
    """Command for scraping new articles (original)"""
    print("=== COINDESK CRYPTO NEWS SCRAPER ===")
    print(f"🎯 Scraping maximum {args.limit} articles...")

    scraper = CoinDeskScraper(use_database=True)

    if args.verbose:
        print("\n📊 Initial database statistics:")
        stats = scraper.db.get_database_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

    start_time = time.time()
    articles = scraper.scrape_multiple_articles(max_articles=args.limit, save_to_db=True)
    scrape_time = time.time() - start_time

    print(f"\n📈 RESULTS:")
    print(f"   ✅ New articles: {len(articles)}")
    print(f"   🕒 Time: {scrape_time:.1f} seconds")

    stats = scraper.db.get_database_stats()
    print(f"   📊 Total in database: {stats['total_articles']} articles")
    print(f"   📋 For analysis: {stats['unprocessed_articles']} articles")

    if len(articles) > 0:
        print(f"\n📰 Newest articles:")
        for i, article in enumerate(articles[:3], 1):
            print(f"   {i}. {article['title'][:60]}...")

    return len(articles)


def scrape_smart_command(args):
    """Smart scraping with date filtering"""
    if not LATEST_NEWS_AVAILABLE:
        print("❌ Smart scraping not available. Please add improved_latest_news_scraper.py")
        return False

    print("=== SMART COINDESK SCRAPER ===")
    print(f"🎯 Smart scraping: {args.limit} articles, filter: {args.date_filter}")

    scraper = CoinDeskLatestNewsScraper(use_database=True)

    if args.verbose:
        print("\n📊 Initial database statistics:")
        stats = scraper.db.get_database_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

    start_time = time.time()
    articles = scraper.scrape_articles_smart(
        date_filter=args.date_filter,
        limit=args.limit,
        save_to_db=True
    )
    scrape_time = time.time() - start_time

    print(f"\n📈 RESULTS:")
    print(f"   ✅ New articles: {len(articles)}")
    print(f"   🕒 Time: {scrape_time:.1f} seconds")

    if scraper.db:
        stats = scraper.db.get_database_stats()
        print(f"   📊 Total in database: {stats['total_articles']} articles")
        print(f"   📋 For analysis: {stats['unprocessed_articles']} articles")

    if len(articles) > 0:
        print(f"\n📰 Scraped articles:")
        for i, article in enumerate(articles[:5], 1):
            print(f"   {i}. {article['title'][:60]}...")

    return len(articles)


def status_command(args):
    """Shows database status"""
    print("=== DATABASE STATUS ===")

    db = DatabaseManager()
    stats = db.get_database_stats()

    print(f"📊 Statistics:")
    print(f"   📰 Total articles: {stats['total_articles']}")
    print(f"   📋 Unanalyzed: {stats['unprocessed_articles']}")
    print(f"   ✅ Analyzed: {stats['analyzed_articles']}")
    print(f"   🔗 Scraped URLs: {stats['total_scraped_urls']}")

    if stats['latest_article']:
        title, date = stats['latest_article']
        print(f"   📅 Newest: {title[:50]}... ({date})")

    if args.verbose and stats['unprocessed_articles'] > 0:
        print(f"\n📋 Unanalyzed articles:")
        unprocessed = db.get_unprocessed_articles(limit=5)
        for i, article in enumerate(unprocessed, 1):
            print(f"   {i}. {article['title'][:60]}...")
            print(f"      📊 {article['content_length']} chars | {article['scraped_at']}")


def date_status_command(args):
    """Status by date"""
    print("=== STATUS BY DATE ===")

    if not LATEST_NEWS_AVAILABLE:
        print("⚠️ Smart functions not available")
        return

    scraper = CoinDeskLatestNewsScraper(use_database=True)

    # Determine dates to check
    dates_to_check = []
    if args.date == 'today':
        dates_to_check = [datetime.now().strftime('%Y-%m-%d')]
    elif args.date == 'yesterday':
        yesterday = datetime.now() - timedelta(days=1)
        dates_to_check = [yesterday.strftime('%Y-%m-%d')]
    elif args.date == 'week':
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            dates_to_check.append(date.strftime('%Y-%m-%d'))
    elif re.match(r'\d{4}-\d{2}-\d{2}', args.date):
        dates_to_check = [args.date]
    else:
        for i in range(3):
            date = datetime.now() - timedelta(days=i)
            dates_to_check.append(date.strftime('%Y-%m-%d'))

    print(f"📅 Checking {len(dates_to_check)} dates...")

    total_scraped = 0
    total_new = 0

    for date_str in dates_to_check:
        status = scraper.get_scraping_status_by_date(date_str)

        if 'error' in status:
            print(f"❌ {date_str}: Error")
            continue

        # Date formatting
        if date_str == datetime.now().strftime('%Y-%m-%d'):
            day_label = "today"
        elif date_str == (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'):
            day_label = "yesterday"
        else:
            day_label = ""

        print(f"📅 {date_str} ({day_label}):")
        print(f"   📰 Scraped: {status['scraped_articles']}")
        print(f"   🆕 New: {status['new_to_scrape']}")

        total_scraped += status['scraped_articles']
        total_new += status['new_to_scrape']

    print(f"\n📊 SUMMARY:")
    print(f"   📰 Total scraped: {total_scraped}")
    print(f"   🆕 Total new: {total_new}")

    if total_new > 0:
        print(f"\n💡 RECOMMENDATION:")
        limit = min(total_new, 15)
        print(f"   🎯 python run_scraper.py scrape-smart --date today --limit {limit}")


def recommend_scraping_command(args):
    """Scraping recommendations"""
    print("=== SCRAPING RECOMMENDATIONS ===")

    db = DatabaseManager()
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE url LIKE ? OR published_date = ?
        """, (f'%/{today.replace("-", "/")}/%', f'%{today}%'))

        today_count = cursor.fetchone()[0]

        print(f"📅 Today is: {today}")
        print(f"📊 Articles from today: {today_count}")

        print(f"\n💡 RECOMMENDATIONS:")

        if LATEST_NEWS_AVAILABLE:
            if today_count == 0:
                print("   🎯 python run_scraper.py scrape-smart --date today --limit 15")
            elif today_count < 5:
                print("   🎯 python run_scraper.py scrape-smart --date today --limit 10")
            else:
                print("   ✅ Good coverage for today")

            print("\n🚀 NEW POSSIBILITIES:")
            print("   📅 Yesterday: python run_scraper.py scrape-smart --date yesterday --limit 10")
            print("   📅 Status: python run_scraper.py date-status --date week")
        else:
            if today_count == 0:
                print("   🎯 python run_scraper.py scrape --limit 15")
            else:
                print("   🎯 python run_scraper.py scrape --limit 10")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")


def export_command(args):
    """Data export"""
    print("=== DATA EXPORT ===")
    db = DatabaseManager()

    if args.all:
        count = db.export_articles_to_json(args.output)
        print(f"📤 Exported {count} articles to {args.output}")
    else:
        count = db.export_articles_to_json(args.output, processed_only=False)
        print(f"📤 Exported {count} unanalyzed articles to {args.output}")


def cleanup_command(args):
    """Cleanup old data"""
    print("=== CLEANUP OLD DATA ===")
    db = DatabaseManager()

    if not args.dry_run:
        deleted_count = db.cleanup_old_analyzed_articles(days_to_keep=args.days)
        print(f"🧹 Deleted {deleted_count} analyzed articles (older than {args.days} days)")
    else:
        print(f"🔍 DRY RUN: Would delete analyzed articles older than {args.days} days")


def analyze_command(args):
    """Prepares articles for sentiment analysis"""
    print("=== INTEGRATION WITH SENTIMENT ANALYZER ===")
    db = DatabaseManager()

    unprocessed = db.get_unprocessed_articles(limit=args.limit)

    if not unprocessed:
        print("📋 No articles for analysis")
        return

    articles_for_analysis = []
    for article in unprocessed:
        articles_for_analysis.append({
            'id': article['id'],
            'title': article['title'],
            'content': article['content'],
            'url': article['url']
        })

    import json
    with open('articles_for_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(articles_for_analysis, f, ensure_ascii=False, indent=2)

    print(f"📤 Exported {len(articles_for_analysis)} articles to articles_for_analysis.json")


def mark_analyzed_command(args):
    """Marks articles as analyzed"""
    print("=== MARKING ARTICLES AS ANALYZED ===")
    db = DatabaseManager()

    if args.article_id:
        db.mark_article_as_analyzed(args.article_id)
        print(f"✅ Article {args.article_id} marked as analyzed")
    elif args.all_processed:
        unprocessed = db.get_unprocessed_articles()
        for article in unprocessed:
            db.mark_article_as_analyzed(article['id'])
        print(f"✅ Marked {len(unprocessed)} articles as analyzed")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="CoinDesk Crypto News Scraper with Smart functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

CLASSIC:
  python run_scraper.py scrape --limit 10
  python run_scraper.py status --verbose

SMART SCRAPING:
  python run_scraper.py scrape-smart --date today --limit 10
  python run_scraper.py scrape-smart --date yesterday --limit 15
  python run_scraper.py scrape-smart --date 2025-06-09 --limit 20

STATUS:
  python run_scraper.py date-status --date today
  python run_scraper.py recommend
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Scrape
    scrape_parser = subparsers.add_parser('scrape', help='Classic scraping')
    scrape_parser.add_argument('--limit', type=int, default=10)
    scrape_parser.add_argument('--verbose', action='store_true')

    # Smart scrape
    if LATEST_NEWS_AVAILABLE:
        smart_parser = subparsers.add_parser('scrape-smart', help='Smart scraping')
        smart_parser.add_argument('--date', dest='date_filter', default='today')
        smart_parser.add_argument('--limit', type=int, default=10)
        smart_parser.add_argument('--verbose', action='store_true')

    # Status
    status_parser = subparsers.add_parser('status', help='Database status')
    status_parser.add_argument('--verbose', action='store_true')

    # Date status
    if LATEST_NEWS_AVAILABLE:
        date_status_parser = subparsers.add_parser('date-status', help='Status by date')
        date_status_parser.add_argument('--date', default='today')

    # Recommend
    recommend_parser = subparsers.add_parser('recommend', help='Recommendations')

    # Export
    export_parser = subparsers.add_parser('export', help='Export')
    export_parser.add_argument('--output', default='articles.json')
    export_parser.add_argument('--all', action='store_true')

    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup')
    cleanup_parser.add_argument('--days', type=int, default=7)
    cleanup_parser.add_argument('--dry-run', action='store_true')

    # Analyze
    analyze_parser = subparsers.add_parser('analyze', help='For sentiment analysis')
    analyze_parser.add_argument('--limit', type=int, default=5)

    # Mark analyzed
    mark_parser = subparsers.add_parser('mark_analyzed', help='Mark analyzed')
    mark_parser.add_argument('--article-id', type=int)
    mark_parser.add_argument('--all-processed', action='store_true')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'scrape':
            scrape_command(args)
        elif args.command == 'scrape-smart' and LATEST_NEWS_AVAILABLE:
            scrape_smart_command(args)
        elif args.command == 'status':
            status_command(args)
        elif args.command == 'date-status' and LATEST_NEWS_AVAILABLE:
            date_status_command(args)
        elif args.command == 'recommend':
            recommend_scraping_command(args)
        elif args.command == 'export':
            export_command(args)
        elif args.command == 'cleanup':
            cleanup_command(args)
        elif args.command == 'analyze':
            analyze_command(args)
        elif args.command == 'mark_analyzed':
            mark_analyzed_command(args)
        else:
            print(f"❌ Unrecognized command: {args.command}")
            if not LATEST_NEWS_AVAILABLE:
                print("💡 Smart functions not available")

        print(f"\n✅ Command '{args.command}' completed!")

    except KeyboardInterrupt:
        print("\n⏹️ Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
