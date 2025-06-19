"""
Cleanup script for deleting analyzed articles
Usage: python cleanup_articles.py [options]
"""

import argparse
from datetime import datetime, timedelta
from postgres_database import PostgreSQLDatabaseManager


def cleanup_analyzed_articles(days_to_keep=7, dry_run=False):
    """
    Deletes analyzed articles older than a specified number of days

    Args:
        days_to_keep (int): How many days to keep analyzed articles
        dry_run (bool): If True, only shows what would be deleted without deleting
    """
    print("🧹 CLEANUP OF ANALYZED ARTICLES")
    print("=" * 50)

    db = PostgreSQLDatabaseManager()

    # Show statistics before cleanup
    print("📊 Statistics before cleanup:")
    stats_before = db.get_database_stats()
    for key, value in stats_before.items():
        print(f"   {key}: {value}")

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:

                # Find articles to delete
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)

                if dry_run:
                    print(f"\n🔍 DRY RUN: Articles to delete (analyzed before {days_to_keep} days):")
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
                        print(f"\n📊 Total {len(articles_to_delete)} articles would be deleted")
                    else:
                        print("   No articles to delete")

                else:
                    print(f"\n🗑️ Deleting analyzed articles older than {days_to_keep} days...")

                    cursor.execute('''
                        DELETE FROM articles 
                        WHERE is_analyzed = TRUE 
                        AND scraped_at < %s
                    ''', (cutoff_date,))

                    deleted_count = cursor.rowcount
                    conn.commit()

                    print(f"✅ Deleted {deleted_count} analyzed articles")

                    # Show statistics after cleanup
                    print("\n📊 Statistics after cleanup:")
                    stats_after = db.get_database_stats()
                    for key, value in stats_after.items():
                        print(f"   {key}: {value}")

                    return deleted_count

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return 0


def cleanup_all_analyzed_articles(dry_run=False):
    """Deletes ALL analyzed articles (regardless of date)"""
    print("🧹 CLEANUP OF ALL ANALYZED ARTICLES")
    print("=" * 50)

    db = PostgreSQLDatabaseManager()

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:

                if dry_run:
                    print("🔍 DRY RUN: All analyzed articles:")
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
                        print(f"\n📊 Total {len(articles)} articles would be deleted")
                    else:
                        print("   No analyzed articles to delete")

                else:
                    cursor.execute('DELETE FROM articles WHERE is_analyzed = TRUE')
                    deleted_count = cursor.rowcount
                    conn.commit()

                    print(f"✅ Deleted {deleted_count} analyzed articles")
                    return deleted_count

    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return 0


def show_cleanup_status():
    """Shows cleanup status - how many articles are available for deletion"""
    print("📊 CLEANUP STATUS")
    print("=" * 30)

    db = PostgreSQLDatabaseManager()

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:

                # General statistics
                stats = db.get_database_stats()
                print("📈 General statistics:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")

                # Articles by age
                print("\n📅 Analyzed articles by age:")
                for days in [1, 3, 7, 14, 30]:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    cursor.execute('''
                        SELECT COUNT(*) FROM articles 
                        WHERE is_analyzed = TRUE AND scraped_at < %s
                    ''', (cutoff_date,))

                    count = cursor.fetchone()[0]
                    print(f"   Older than {days:2d} days: {count} articles")

    except Exception as e:
        print(f"❌ Error getting status: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Cleanup script for analyzed articles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

BASIC COMMANDS:
  python cleanup_articles.py status                    # Show status
  python cleanup_articles.py cleanup --days 7          # Delete older than 7 days
  python cleanup_articles.py cleanup --days 7 --dry-run # Only show what would be deleted
  python cleanup_articles.py cleanup --all             # Delete ALL analyzed articles
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show cleanup status')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Delete analyzed articles')
    cleanup_parser.add_argument('--days', type=int, default=7,
                                help='Days to keep analyzed articles (default: 7)')
    cleanup_parser.add_argument('--all', action='store_true',
                                help='Delete ALL analyzed articles')
    cleanup_parser.add_argument('--dry-run', action='store_true',
                                help='Only show what would be deleted without deleting')

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
                print(f"\n🎉 Cleanup completed! Deleted {deleted} articles")

        else:
            print(f"❌ Unrecognized command: {args.command}")

    except KeyboardInterrupt:
        print("\n⏹️ Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
