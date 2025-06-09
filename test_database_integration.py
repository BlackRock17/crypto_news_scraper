from scraper import CoinDeskScraper
from database import DatabaseManager
import time


def test_database_integration():
    """Тества scraper с database интеграция"""
    print("=== ТЕСТ НА DATABASE ИНТЕГРАЦИЯ ===")

    # Създаваме scraper с database
    scraper = CoinDeskScraper(use_database=True)

    print("\n📊 Начални database статистики:")
    stats = scraper.db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Scrape-ваме 5 статии
    print(f"\n🎯 Scraping на 5 статии с database запазване...")
    articles = scraper.scrape_multiple_articles(max_articles=5, save_to_db=True)

    print(f"\n📊 Database статистики след scraping:")
    stats = scraper.db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Тестваме дублиране - опитваме същото отново
    print(f"\n🔄 Тест за дублиране - опитваме същите статии отново...")
    articles2 = scraper.scrape_multiple_articles(max_articles=5, save_to_db=True)

    # Показваме unprocesed статии
    print(f"\n📋 Непроцесирани статии за анализ:")
    unprocessed = scraper.db.get_unprocessed_articles(limit=3)
    for i, article in enumerate(unprocessed, 1):
        print(f"  {i}. {article['title'][:60]}...")
        print(f"     📊 Дължина: {article['content_length']} chars")
        print(f"     🔗 URL: {article['url']}")

    # Тестваме маркиране като анализирана
    if unprocessed:
        first_article = unprocessed[0]
        print(f"\n✅ Маркиране на първата статия като анализирана...")

        # Симулираме sentiment резултат
        fake_sentiment = {
            'sentiment': 'positive',
            'confidence': 0.85,
            'summary': 'Positive article about crypto markets'
        }

        scraper.db.mark_article_as_analyzed(first_article['id'], fake_sentiment)

    # Финални статистики
    print(f"\n📊 Финални database статистики:")
    stats = scraper.db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    return len(articles)


def test_export_functionality():
    """Тества export функционалността"""
    print("\n=== ТЕСТ НА EXPORT ===")

    db = DatabaseManager()

    # Експортираме всички статии
    count = db.export_articles_to_json("exported_articles.json")
    print(f"📤 Експортирани {count} статии")

    # Експортираме само анализираните
    count_processed = db.export_articles_to_json("analyzed_articles.json", processed_only=True)
    print(f"📤 Експортирани {count_processed} анализирани статии")


def test_cleanup():
    """Тества cleanup функционалността"""
    print("\n=== ТЕСТ НА CLEANUP ===")

    db = DatabaseManager()

    print("🧹 Cleanup на стари анализирани статии...")
    deleted_count = db.cleanup_old_analyzed_articles(days_to_keep=30)  # 30 дни за тест

    print(f"📊 Финални database статистики след cleanup:")
    stats = db.get_database_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")


if __name__ == "__main__":
    start_time = time.time()

    # Основен тест
    article_count = test_database_integration()

    # Export тест
    if article_count > 0:
        test_export_functionality()

    # Cleanup тест
    test_cleanup()

    total_time = time.time() - start_time

    print(f"\n🕒 Общо време: {total_time:.1f} секунди")
    print(f"🎉 Database интеграция тест завършен успешно!")
    print(f"💡 Готов за създаване на командния ред интерфейс!")
