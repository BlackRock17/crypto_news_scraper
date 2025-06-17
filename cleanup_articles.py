#!/usr/bin/env python3
"""
Cleanup скрипт за изтриване на анализирани статии
Използване: python cleanup_articles.py [опции]
"""

import argparse
from datetime import datetime, timedelta
from postgres_database import PostgreSQLDatabaseManager


def cleanup_analyzed_articles(days_to_keep=7, dry_run=False):
    """
    Изтрива анализирани статии по-стари от определен брой дни

    Args:
        days_to_keep (int): Колко дни да пази анализираните статии
        dry_run (bool): Ако е True, само показва какво ще изтрие без да изтрива
    """
    print("🧹 CLEANUP НА АНАЛИЗИРАНИ СТАТИИ")
    print("=" * 50)

    db = PostgreSQLDatabaseManager()

    # Показваме статистики преди cleanup
    print("📊 Статистики преди cleanup:")
    stats_before = db.get_database_stats()
    for key, value in stats_before.items():
        print(f"   {key}: {value}")

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:

                # Намираме статиите за изтриване
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)

                if dry_run:
                    print(f"\n🔍 DRY RUN: Статии за изтриване (анализирани преди {days_to_keep} дни):")
                    cursor.execute('''
                        SELECT id, title, scraped_at
                        FROM articles 
                        WHERE is_analyzed = TRUE 
                        AND scraped_at < %s
                        ORDER BY scraped_at DESC
                    ''', (cutoff_date,))

                    articles_to_delete = cursor.fetchall()

                    if articles_to_delete:
                        for i, (article_id, title, scraped_at) in enumerate(articles_to_delete, 1):
                            print(f"   {i}. [{article_id}] {title[:60]}... ({scraped_at})")
                        print(f"\n📊 Общо {len(articles_to_delete)} статии ще бъдат изтрити")
                    else:
                        print("   Няма статии за изтриване")

                else:
                    print(f"\n🗑️ Изтриване на анализирани статии по-стари от {days_to_keep} дни...")

                    cursor.execute('''
                        DELETE FROM articles 
                        WHERE is_analyzed = TRUE 
                        AND scraped_at < %s
                    ''', (cutoff_date,))

                    deleted_count = cursor.rowcount
                    conn.commit()

                    print(f"✅ Изтрити {deleted_count} анализирани статии")

                    # Показваме статистики след cleanup
                    print("\n📊 Статистики след cleanup:")
                    stats_after = db.get_database_stats()
                    for key, value in stats_after.items():
                        print(f"   {key}: {value}")

                    return deleted_count

    except Exception as e:
        print(f"❌ Грешка при cleanup: {e}")
        return 0


def cleanup_all_analyzed_articles(dry_run=False):
    """Изтрива ВСИЧКИ анализирани статии (независимо от датата)"""
    print("🧹 CLEANUP НА ВСИЧКИ АНАЛИЗИРАНИ СТАТИИ")
    print("=" * 50)

    db = PostgreSQLDatabaseManager()

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:

                if dry_run:
                    print("🔍 DRY RUN: Всички анализирани статии:")
                    cursor.execute('''
                        SELECT id, title, scraped_at
                        FROM articles 
                        WHERE is_analyzed = TRUE
                        ORDER BY scraped_at DESC
                    ''')

                    articles = cursor.fetchall()

                    if articles:
                        for i, (article_id, title, scraped_at) in enumerate(articles, 1):
                            print(f"   {i}. [{article_id}] {title[:60]}... ({scraped_at})")
                        print(f"\n📊 Общо {len(articles)} статии ще бъдат изтрити")
                    else:
                        print("   Няма анализирани статии за изтриване")

                else:
                    cursor.execute('DELETE FROM articles WHERE is_analyzed = TRUE')
                    deleted_count = cursor.rowcount
                    conn.commit()

                    print(f"✅ Изтрити {deleted_count} анализирани статии")
                    return deleted_count

    except Exception as e:
        print(f"❌ Грешка при cleanup: {e}")
        return 0


def show_cleanup_status():
    """Показва статус за cleanup - колко статии има за изтриване"""
    print("📊 CLEANUP СТАТУС")
    print("=" * 30)

    db = PostgreSQLDatabaseManager()

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:

                # Общи статистики
                stats = db.get_database_stats()
                print("📈 Общи статистики:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")

                # Статии по възраст
                print("\n📅 Анализирани статии по възраст:")
                for days in [1, 3, 7, 14, 30]:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    cursor.execute('''
                        SELECT COUNT(*) FROM articles 
                        WHERE is_analyzed = TRUE AND scraped_at < %s
                    ''', (cutoff_date,))

                    count = cursor.fetchone()[0]
                    print(f"   По-стари от {days:2d} дни: {count} статии")

    except Exception as e:
        print(f"❌ Грешка при статус: {e}")


def main():
    """Главна функция"""
    parser = argparse.ArgumentParser(
        description="Cleanup скрипт за анализирани статии",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примери:

ОСНОВНИ КОМАНДИ:
  python cleanup_articles.py status                    # Показва статус
  python cleanup_articles.py cleanup --days 7          # Изтрива по-стари от 7 дни
  python cleanup_articles.py cleanup --days 7 --dry-run # Само показва какво ще изтрие
  python cleanup_articles.py cleanup --all             # Изтрива ВСИЧКИ анализирани
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Команди')

    # Status команда
    status_parser = subparsers.add_parser('status', help='Показва cleanup статус')

    # Cleanup команда
    cleanup_parser = subparsers.add_parser('cleanup', help='Изтрива анализирани статии')
    cleanup_parser.add_argument('--days', type=int, default=7,
                                help='Дни за пазене на анализирани статии (default: 7)')
    cleanup_parser.add_argument('--all', action='store_true',
                                help='Изтрива ВСИЧКИ анализирани статии')
    cleanup_parser.add_argument('--dry-run', action='store_true',
                                help='Само показва какво ще изтрие без да изтрива')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'status':
            show_cleanup_status()

        elif args.command == 'cleanup':
            if args.all:
                deleted = cleanup_all_analyzed_articles(dry_run=args.dry_run)
            else:
                deleted = cleanup_analyzed_articles(days_to_keep=args.days, dry_run=args.dry_run)

            if not args.dry_run and deleted > 0:
                print(f"\n🎉 Cleanup завършен! Изтрити {deleted} статии")

        else:
            print(f"❌ Неразпозната команда: {args.command}")

    except KeyboardInterrupt:
        print("\n⏹️ Прекратено")
    except Exception as e:
        print(f"\n❌ Грешка: {str(e)}")


if __name__ == "__main__":
    main()
