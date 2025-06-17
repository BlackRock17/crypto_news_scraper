#!/usr/bin/env python3
"""
CoinDesk Crypto News Scraper - Command Line Interface с Smart Scraping
Използване: python run_scraper.py [опции]
"""

import argparse
import time
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path

# Import за новия scraper
try:
    from improved_latest_news_scraper import CoinDeskLatestNewsScraper

    LATEST_NEWS_AVAILABLE = True
except ImportError:
    LATEST_NEWS_AVAILABLE = False

# Стандартни imports
from scraper import CoinDeskScraper
from postgres_database import PostgreSQLDatabaseManager as DatabaseManager


def scrape_command(args):
    """Команда за scraping на нови статии (оригинална)"""
    print("=== COINDESK CRYPTO NEWS SCRAPER ===")
    print(f"🎯 Scraping на максимум {args.limit} статии...")

    scraper = CoinDeskScraper(use_database=True)

    if args.verbose:
        print("\n📊 Начални database статистики:")
        stats = scraper.db.get_database_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

    start_time = time.time()
    articles = scraper.scrape_multiple_articles(max_articles=args.limit, save_to_db=True)
    scrape_time = time.time() - start_time

    print(f"\n📈 РЕЗУЛТАТИ:")
    print(f"   ✅ Нови статии: {len(articles)}")
    print(f"   🕒 Време: {scrape_time:.1f} секунди")

    stats = scraper.db.get_database_stats()
    print(f"   📊 Общо в база: {stats['total_articles']} статии")
    print(f"   📋 За анализ: {stats['unprocessed_articles']} статии")

    if len(articles) > 0:
        print(f"\n📰 Най-нови статии:")
        for i, article in enumerate(articles[:3], 1):
            print(f"   {i}. {article['title'][:60]}...")

    return len(articles)


def scrape_smart_command(args):
    """Smart scraping с date filtering"""
    if not LATEST_NEWS_AVAILABLE:
        print("❌ Smart scraping не е достъпен. Моля добави improved_latest_news_scraper.py")
        return False

    print("=== SMART COINDESK SCRAPER ===")
    print(f"🎯 Smart scraping: {args.limit} статии, филтър: {args.date_filter}")

    scraper = CoinDeskLatestNewsScraper(use_database=True)

    if args.verbose:
        print("\n📊 Начални database статистики:")
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

    print(f"\n📈 РЕЗУЛТАТИ:")
    print(f"   ✅ Нови статии: {len(articles)}")
    print(f"   🕒 Време: {scrape_time:.1f} секунди")

    if scraper.db:
        stats = scraper.db.get_database_stats()
        print(f"   📊 Общо в база: {stats['total_articles']} статии")
        print(f"   📋 За анализ: {stats['unprocessed_articles']} статии")

    if len(articles) > 0:
        print(f"\n📰 Scraped статии:")
        for i, article in enumerate(articles[:5], 1):
            print(f"   {i}. {article['title'][:60]}...")

    return len(articles)


def status_command(args):
    """Показва database статус"""
    print("=== DATABASE СТАТУС ===")

    db = DatabaseManager()
    stats = db.get_database_stats()

    print(f"📊 Статистики:")
    print(f"   📰 Общо статии: {stats['total_articles']}")
    print(f"   📋 Неанализирани: {stats['unprocessed_articles']}")
    print(f"   ✅ Анализирани: {stats['analyzed_articles']}")
    print(f"   🔗 Scraped URLs: {stats['total_scraped_urls']}")

    if stats['latest_article']:
        title, date = stats['latest_article']
        print(f"   📅 Най-нова: {title[:50]}... ({date})")

    if args.verbose and stats['unprocessed_articles'] > 0:
        print(f"\n📋 Неанализирани статии:")
        unprocessed = db.get_unprocessed_articles(limit=5)
        for i, article in enumerate(unprocessed, 1):
            print(f"   {i}. {article['title'][:60]}...")
            print(f"      📊 {article['content_length']} chars | {article['scraped_at']}")


def date_status_command(args):
    """Статус по дата"""
    print("=== СТАТУС ПО ДАТА ===")

    if not LATEST_NEWS_AVAILABLE:
        print("⚠️ Smart функции не са достъпни")
        return

    scraper = CoinDeskLatestNewsScraper(use_database=True)

    # Определяме дати за проверка
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

    print(f"📅 Проверяване на {len(dates_to_check)} дати...")

    total_scraped = 0
    total_new = 0

    for date_str in dates_to_check:
        status = scraper.get_scraping_status_by_date(date_str)

        if 'error' in status:
            print(f"❌ {date_str}: Грешка")
            continue

        # Форматиране на датата
        if date_str == datetime.now().strftime('%Y-%m-%d'):
            day_label = "днес"
        elif date_str == (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'):
            day_label = "вчера"
        else:
            day_label = ""

        print(f"📅 {date_str} ({day_label}):")
        print(f"   📰 Scraped: {status['scraped_articles']}")
        print(f"   🆕 Нови: {status['new_to_scrape']}")

        total_scraped += status['scraped_articles']
        total_new += status['new_to_scrape']

    print(f"\n📊 ОБОБЩЕНИЕ:")
    print(f"   📰 Общо scraped: {total_scraped}")
    print(f"   🆕 Общо нови: {total_new}")

    if total_new > 0:
        print(f"\n💡 ПРЕПОРЪКА:")
        limit = min(total_new, 15)
        print(f"   🎯 python run_scraper.py scrape-smart --date today --limit {limit}")


def recommend_scraping_command(args):
    """Препоръки за scraping"""
    print("=== ПРЕПОРЪКИ ЗА SCRAPING ===")

    db = DatabaseManager()
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE url LIKE ? OR published_date = ?
        """, (f'%{today.replace("-", "/")}/%', today))

        today_count = cursor.fetchone()[0]

        print(f"📅 Днес е: {today}")
        print(f"📊 Статии от днеска: {today_count}")

        print(f"\n💡 ПРЕПОРЪКИ:")

        if LATEST_NEWS_AVAILABLE:
            if today_count == 0:
                print("   🎯 python run_scraper.py scrape-smart --date today --limit 15")
            elif today_count < 5:
                print("   🎯 python run_scraper.py scrape-smart --date today --limit 10")
            else:
                print("   ✅ Добро покритие за днеска")

            print("\n🚀 НОВИ ВЪЗМОЖНОСТИ:")
            print("   📅 Вчера: python run_scraper.py scrape-smart --date yesterday --limit 10")
            print("   📅 Статус: python run_scraper.py date-status --date week")
        else:
            if today_count == 0:
                print("   🎯 python run_scraper.py scrape --limit 15")
            else:
                print("   🎯 python run_scraper.py scrape --limit 10")

        conn.close()

    except Exception as e:
        print(f"❌ Грешка: {e}")


def export_command(args):
    """Export на данни"""
    print("=== EXPORT НА ДАННИ ===")
    db = DatabaseManager()

    if args.all:
        count = db.export_articles_to_json(args.output)
        print(f"📤 Експортирани {count} статии в {args.output}")
    else:
        count = db.export_articles_to_json(args.output, processed_only=False)
        print(f"📤 Експортирани {count} неанализирани статии в {args.output}")


def cleanup_command(args):
    """Cleanup на стари данни"""
    print("=== CLEANUP НА СТАРИ ДАННИ ===")
    db = DatabaseManager()

    if not args.dry_run:
        deleted_count = db.cleanup_old_analyzed_articles(days_to_keep=args.days)
        print(f"🧹 Изтрити {deleted_count} анализирани статии (по-стари от {args.days} дни)")
    else:
        print(f"🔍 DRY RUN: Би изтрил анализирани статии по-стари от {args.days} дни")


def analyze_command(args):
    """Подготвя статии за sentiment анализ"""
    print("=== ИНТЕГРАЦИЯ СЪС SENTIMENT ANALYZER ===")
    db = DatabaseManager()

    unprocessed = db.get_unprocessed_articles(limit=args.limit)

    if not unprocessed:
        print("📋 Няма статии за анализ")
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

    print(f"📤 Експортирани {len(articles_for_analysis)} статии в articles_for_analysis.json")


def mark_analyzed_command(args):
    """Маркира статии като анализирани"""
    print("=== МАРКИРАНЕ НА СТАТИИ КАТО АНАЛИЗИРАНИ ===")
    db = DatabaseManager()

    if args.article_id:
        db.mark_article_as_analyzed(args.article_id)
        print(f"✅ Статия {args.article_id} маркирана като анализирана")
    elif args.all_processed:
        unprocessed = db.get_unprocessed_articles()
        for article in unprocessed:
            db.mark_article_as_analyzed(article['id'])
        print(f"✅ Маркирани {len(unprocessed)} статии като анализирани")


def main():
    """Главна функция"""
    parser = argparse.ArgumentParser(
        description="CoinDesk Crypto News Scraper с Smart функционалност",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примери:

КЛАСИЧЕСКИ:
  python run_scraper.py scrape --limit 10
  python run_scraper.py status --verbose

SMART SCRAPING:
  python run_scraper.py scrape-smart --date today --limit 10
  python run_scraper.py scrape-smart --date yesterday --limit 15
  python run_scraper.py scrape-smart --date 2025-06-09 --limit 20

СТАТУС:
  python run_scraper.py date-status --date today
  python run_scraper.py recommend
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Команди')

    # Scrape
    scrape_parser = subparsers.add_parser('scrape', help='Класически scraping')
    scrape_parser.add_argument('--limit', type=int, default=10)
    scrape_parser.add_argument('--verbose', action='store_true')

    # Smart scrape
    if LATEST_NEWS_AVAILABLE:
        smart_parser = subparsers.add_parser('scrape-smart', help='Smart scraping')
        smart_parser.add_argument('--date', dest='date_filter', default='today')
        smart_parser.add_argument('--limit', type=int, default=10)
        smart_parser.add_argument('--verbose', action='store_true')

    # Status
    status_parser = subparsers.add_parser('status', help='Database статус')
    status_parser.add_argument('--verbose', action='store_true')

    # Date status
    if LATEST_NEWS_AVAILABLE:
        date_status_parser = subparsers.add_parser('date-status', help='Статус по дата')
        date_status_parser.add_argument('--date', default='today')

    # Recommend
    recommend_parser = subparsers.add_parser('recommend', help='Препоръки')

    # Export
    export_parser = subparsers.add_parser('export', help='Експорт')
    export_parser.add_argument('--output', default='articles.json')
    export_parser.add_argument('--all', action='store_true')

    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup')
    cleanup_parser.add_argument('--days', type=int, default=7)
    cleanup_parser.add_argument('--dry-run', action='store_true')

    # Analyze
    analyze_parser = subparsers.add_parser('analyze', help='За sentiment анализ')
    analyze_parser.add_argument('--limit', type=int, default=5)

    # Mark analyzed
    mark_parser = subparsers.add_parser('mark_analyzed', help='Маркирай анализирани')
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
            print(f"❌ Неразпозната команда: {args.command}")
            if not LATEST_NEWS_AVAILABLE:
                print("💡 Smart функции не са достъпни")

        print(f"\n✅ Команда '{args.command}' завършена!")

    except KeyboardInterrupt:
        print("\n⏹️ Прекратено")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Грешка: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
