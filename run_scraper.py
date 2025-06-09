#!/usr/bin/env python3
"""
CoinDesk Crypto News Scraper - Command Line Interface
Използване: python run_scraper.py [опции]
"""

import argparse
import time
import sys
from pathlib import Path

from scraper import CoinDeskScraper
from database import DatabaseManager


def scrape_command(args):
    """Команда за scraping на нови статии"""
    print("=== COINDESK CRYPTO NEWS SCRAPER ===")
    print(f"🎯 Scraping на максимум {args.limit} статии...")

    # Създаваме scraper
    scraper = CoinDeskScraper(use_database=True)

    # Показваме начални статистики
    if args.verbose:
        print("\n📊 Начални database статистики:")
        stats = scraper.db.get_database_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")

    # Scrape-ваме статии
    start_time = time.time()
    articles = scraper.scrape_multiple_articles(
        max_articles=args.limit,
        save_to_db=True
    )
    scrape_time = time.time() - start_time

    # Показваме резултати
    print(f"\n📈 РЕЗУЛТАТИ:")
    print(f"   ✅ Нови статии: {len(articles)}")
    print(f"   🕒 Време: {scrape_time:.1f} секунди")

    # Финални статистики
    stats = scraper.db.get_database_stats()
    print(f"   📊 Общо в база: {stats['total_articles']} статии")
    print(f"   📋 За анализ: {stats['unprocessed_articles']} статии")

    if len(articles) > 0:
        print(f"\n📰 Най-нови статии:")
        for i, article in enumerate(articles[:3], 1):
            print(f"   {i}. {article['title'][:60]}...")

    return len(articles)


def status_command(args):
    """Команда за показване на database статус"""
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

    # Показваме неанализирани статии
    if args.verbose and stats['unprocessed_articles'] > 0:
        print(f"\n📋 Неанализирани статии:")
        unprocessed = db.get_unprocessed_articles(limit=5)
        for i, article in enumerate(unprocessed, 1):
            print(f"   {i}. {article['title'][:60]}...")
            print(f"      📊 {article['content_length']} chars | {article['scraped_at']}")


def export_command(args):
    """Команда за export на данни"""
    print("=== EXPORT НА ДАННИ ===")

    db = DatabaseManager()

    if args.all:
        count = db.export_articles_to_json(args.output)
        print(f"📤 Експортирани {count} статии в {args.output}")
    else:
        count = db.export_articles_to_json(args.output, processed_only=False)
        unprocessed_count = db.get_database_stats()['unprocessed_articles']
        print(f"📤 Експортирани {unprocessed_count} неанализирани статии в {args.output}")


def cleanup_command(args):
    """Команда за cleanup на стари данни"""
    print("=== CLEANUP НА СТАРИ ДАННИ ===")

    db = DatabaseManager()

    # Показваме статистики преди cleanup
    stats_before = db.get_database_stats()
    print(f"📊 Преди cleanup: {stats_before['analyzed_articles']} анализирани статии")

    # Правим cleanup
    if not args.dry_run:
        deleted_count = db.cleanup_old_analyzed_articles(days_to_keep=args.days)
        print(f"🧹 Изтрити {deleted_count} анализирани статии (по-стари от {args.days} дни)")

        # Статистики след cleanup
        stats_after = db.get_database_stats()
        print(f"📊 След cleanup: {stats_after['total_articles']} общо статии")
    else:
        print(f"🔍 DRY RUN: Би изтрил анализирани статии по-стари от {args.days} дни")


def analyze_command(args):
    """Команда за интеграция с sentiment analyzer"""
    print("=== ИНТЕГРАЦИЯ СЪС SENTIMENT ANALYZER ===")

    db = DatabaseManager()

    # Вземаме неанализирани статии
    unprocessed = db.get_unprocessed_articles(limit=args.limit)

    if not unprocessed:
        print("📋 Няма статии за анализ")
        return

    print(f"📋 {len(unprocessed)} статии за анализ")

    # Подготвяме данни за sentiment analyzer
    articles_for_analysis = []
    for article in unprocessed:
        articles_for_analysis.append({
            'id': article['id'],
            'title': article['title'],
            'content': article['content'],
            'url': article['url']
        })

    # Експортираме за анализ
    import json
    with open('articles_for_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(articles_for_analysis, f, ensure_ascii=False, indent=2)

    print(f"📤 Експортирани {len(articles_for_analysis)} статии в articles_for_analysis.json")
    print(f"💡 Използвай този файл във твоя sentiment analyzer проект!")
    print(f"💡 След анализ, маркирай статиите като processed с mark_analyzed команда")


def mark_analyzed_command(args):
    """Команда за маркиране на статии като анализирани"""
    print("=== МАРКИРАНЕ НА СТАТИИ КАТО АНАЛИЗИРАНИ ===")

    db = DatabaseManager()

    if args.article_id:
        # Маркиране на конкретна статия
        db.mark_article_as_analyzed(args.article_id)
        print(f"✅ Статия {args.article_id} маркирана като анализирана")
    elif args.all_processed:
        # Маркиране на всички текущо unprocessed като analyzed (за тестване)
        unprocessed = db.get_unprocessed_articles()
        for article in unprocessed:
            db.mark_article_as_analyzed(article['id'])
        print(f"✅ Маркирани {len(unprocessed)} статии като анализирани")


def main():
    """Главна функция за command line интерфейс"""
    parser = argparse.ArgumentParser(
        description="CoinDesk Crypto News Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примери за използване:
  python run_scraper.py scrape --limit 10           # Scrape до 10 нови статии
  python run_scraper.py status --verbose            # Покажи подробен статус
  python run_scraper.py export --output news.json   # Експорт на неанализирани статии
  python run_scraper.py cleanup --days 7            # Изтрий анализирани статии >7 дни
  python run_scraper.py analyze --limit 5           # Подготви 5 статии за анализ
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Налични команди')

    # Scrape команда
    scrape_parser = subparsers.add_parser('scrape', help='Scrape нови статии')
    scrape_parser.add_argument('--limit', type=int, default=10, help='Максимален брой статии (default: 10)')
    scrape_parser.add_argument('--verbose', action='store_true', help='Подробна информация')

    # Status команда
    status_parser = subparsers.add_parser('status', help='Покажи database статус')
    status_parser.add_argument('--verbose', action='store_true', help='Покажи неанализирани статии')

    # Export команда
    export_parser = subparsers.add_parser('export', help='Експорт на данни')
    export_parser.add_argument('--output', default='articles.json', help='Output файл (default: articles.json)')
    export_parser.add_argument('--all', action='store_true', help='Експорт на всички статии')

    # Cleanup команда
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup на стари данни')
    cleanup_parser.add_argument('--days', type=int, default=7, help='Дни за пазене (default: 7)')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='Само показва какво ще направи')

    # Analyze команда
    analyze_parser = subparsers.add_parser('analyze', help='Подготви статии за sentiment анализ')
    analyze_parser.add_argument('--limit', type=int, default=5, help='Брой статии за анализ (default: 5)')

    # Mark analyzed команда
    mark_parser = subparsers.add_parser('mark_analyzed', help='Маркирай статии като анализирани')
    mark_parser.add_argument('--article-id', type=int, help='ID на статия за маркиране')
    mark_parser.add_argument('--all-processed', action='store_true', help='Маркирай всички като анализирани')

    # Parse аргументите
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        # Изпълняване на командите
        if args.command == 'scrape':
            article_count = scrape_command(args)
            if article_count == 0:
                print("\nℹ️ Няма нови статии за scraping. Опитай пак по-късно.")
        elif args.command == 'status':
            status_command(args)
        elif args.command == 'export':
            export_command(args)
        elif args.command == 'cleanup':
            cleanup_command(args)
        elif args.command == 'analyze':
            analyze_command(args)
        elif args.command == 'mark_analyzed':
            mark_analyzed_command(args)

        print(f"\n✅ Команда '{args.command}' завършена успешно!")

    except KeyboardInterrupt:
        print("\n⏹️ Прекратено от потребителя")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Грешка: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
