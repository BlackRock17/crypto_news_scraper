from scraper import CoinDeskScraper
import time


def test_multiple_articles():
    """Тества scraping на множество статии"""
    print("=== ТЕСТ НА МНОЖЕСТВО СТАТИИ ===")

    scraper = CoinDeskScraper()

    # Първо вземаме линковете
    print("🔍 Намиране на статии...")
    article_links = scraper.get_article_links()

    print(f"📰 Намерени {len(article_links)} статии")
    print("\n📋 Първи 10 статии:")
    for i, link in enumerate(article_links[:10], 1):
        title = link['title'][:60] + "..." if len(link['title']) > 60 else link['title']
        print(f"  {i}. {title}")
        print(f"     → {link['href']}")

    # Scrape-ваме първите 3 статии за тест
    print(f"\n🎯 Тествам scraping на първите 3 статии...")

    scraped_articles = scraper.scrape_multiple_articles(max_articles=3)

    print(f"\n📊 РЕЗУЛТАТИ:")
    print(f"   ✅ Успешно извлечени: {len(scraped_articles)} статии")

    # Показваме резултатите
    for i, article in enumerate(scraped_articles, 1):
        print(f"\n📄 Статия {i}:")
        print(f"   📰 Заглавие: {article['title']}")
        print(f"   📅 Дата: {article['date']}")
        print(f"   👤 Автор: {article['author']}")
        print(f"   📊 Дължина: {article['content_length']} символa")
        print(f"   🔗 URL: {article['url']}")
        print(f"   📝 Първи 150 символа: {article['content'][:150]}...")

    return scraped_articles


def test_link_validation():
    """Тества URL validation логиката"""
    print("\n=== ТЕСТ НА URL VALIDATION ===")

    scraper = CoinDeskScraper()

    # Вземаме всички линкове
    article_links = scraper.get_article_links()

    print(f"📊 Статистики:")
    print(f"   📰 Валидни статии: {len(article_links)}")

    # Показваме разпределението по категории
    categories = {}
    for link in article_links:
        href = link['href']
        if '/markets/' in href:
            categories['markets'] = categories.get('markets', 0) + 1
        elif '/policy/' in href:
            categories['policy'] = categories.get('policy', 0) + 1
        elif '/tech/' in href:
            categories['tech'] = categories.get('tech', 0) + 1
        elif '/business/' in href:
            categories['business'] = categories.get('business', 0) + 1
        else:
            categories['other'] = categories.get('other', 0) + 1

    print(f"   📈 Разпределение по категории:")
    for category, count in categories.items():
        print(f"      - {category}: {count} статии")


if __name__ == "__main__":
    start_time = time.time()

    # Тест 1: URL validation
    test_link_validation()

    # Тест 2: Scraping на множество статии
    articles = test_multiple_articles()

    total_time = time.time() - start_time

    print(f"\n🕒 Общо време: {total_time:.1f} секунди")
    print(f"🎉 Тестът завърши успешно!")

    if articles:
        print(f"💾 Готов за добавяне на database функционалност!")
