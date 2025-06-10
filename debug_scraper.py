#!/usr/bin/env python3
"""
Debug инструмент за анализ на CoinDesk Scraper поведението
"""

import sqlite3
from datetime import datetime, timedelta
import re
from collections import defaultdict


def analyze_scraped_data():
    """Анализира данните в SQLite базата"""
    print("=== АНАЛИЗ НА SCRAPER ДАННИ ===")

    try:
        conn = sqlite3.connect('crypto_news.db')
        cursor = conn.cursor()

        # 1. Общи статистики
        print("\n📊 ОБЩИ СТАТИСТИКИ:")
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]
        print(f"   📰 Общо статии в базата: {total_articles}")

        cursor.execute("SELECT COUNT(*) FROM scraped_urls")
        total_urls = cursor.fetchone()[0]
        print(f"   🔗 Общо scraped URLs: {total_urls}")

        # 2. Статистики по дата на scraping
        print("\n📅 СТАТИСТИКИ ПО ДАТА НА SCRAPING:")
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
            print(f"   📅 {date}: {count} статии (средно {int(avg_length)} chars)")

        # 3. Анализ на URL patterns
        print("\n🔍 АНАЛИЗ НА URL PATTERNS:")
        cursor.execute("SELECT url FROM articles ORDER BY scraped_at DESC LIMIT 10")
        recent_urls = cursor.fetchall()

        url_patterns = defaultdict(int)
        dates_in_urls = []

        for (url,) in recent_urls:
            # Извличаме категорията
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

            # Извличаме датата от URL
            date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
            if date_match:
                year, month, day = date_match.groups()
                dates_in_urls.append(f"{year}-{month}-{day}")

        print("   📋 Категории на последните 10 статии:")
        for category, count in url_patterns.items():
            print(f"      - {category}: {count}")

        print("   📅 Дати в URL-ата на последните 10 статии:")
        unique_dates = list(set(dates_in_urls))
        for date in sorted(unique_dates, reverse=True):
            count = dates_in_urls.count(date)
            print(f"      - {date}: {count} статии")

        # 4. Най-нови vs най-стари статии
        print("\n🕒 ВРЕМЕНСКИ АНАЛИЗ:")
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

        print("   📰 Най-нови статии:")
        for title, url, scraped_at in newest:
            date_in_url = extract_date_from_url(url)
            print(f"      - {title[:50]}... (scraped: {scraped_at}, URL date: {date_in_url})")

        print("   📰 Най-стари статии:")
        for title, url, scraped_at in oldest:
            date_in_url = extract_date_from_url(url)
            print(f"      - {title[:50]}... (scraped: {scraped_at}, URL date: {date_in_url})")

        conn.close()

    except Exception as e:
        print(f"❌ Грешка при анализ: {e}")


def extract_date_from_url(url):
    """Извлича дата от CoinDesk URL"""
    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if date_match:
        year, month, day = date_match.groups()
        return f"{year}-{month}-{day}"
    return "неизвестна"


def simulate_scraping_decision():
    """Симулира как scraper-ът решава кои статии да scrape-не"""
    print("\n=== СИМУЛАЦИЯ НА SCRAPING РЕШЕНИЯ ===")

    try:
        from scraper import CoinDeskScraper

        # Създаваме scraper без database за тест
        scraper = CoinDeskScraper(use_database=False)
        print("📡 Свързване с CoinDesk...")

        # Вземаме статиите от главната страница
        article_links = scraper.get_article_links()
        print(f"📰 Намерени {len(article_links)} статии от главната страница")

        # Анализираме първите 10
        print("\n🔍 АНАЛИЗ НА ПЪРВИТЕ 10 СТАТИИ:")
        for i, article in enumerate(article_links[:10], 1):
            url = article['url']
            title = article['title']
            date_in_url = extract_date_from_url(url)

            # Проверяваме дали е в базата
            is_scraped = check_if_url_scraped(url)
            status = "🟢 НОВ" if not is_scraped else "🔴 SCRAPED"

            print(f"   {i:2d}. {status} | {date_in_url} | {title[:45]}...")

        # Статистики по дата
        print("\n📊 СТАТИСТИКИ ПО ДАТА НА СТАТИИТЕ:")
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
            print(f"   📅 {date}: {stats['total']} общо | {stats['new']} нови | {stats['scraped']} scraped")

    except Exception as e:
        print(f"❌ Грешка при симулация: {e}")


def check_if_url_scraped(url):
    """Проверява дали URL е скрапнат"""
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
    """Препоръчва стратегия за scraping"""
    print("\n=== ПРЕПОРЪКИ ЗА SCRAPING СТРАТЕГИЯ ===")

    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"📅 Днес е: {today}")
    print(f"📅 Вчера беше: {yesterday}")

    try:
        conn = sqlite3.connect('crypto_news.db')
        cursor = conn.cursor()

        # Проверяваме дали имаме статии от днеска
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

        print(f"\n📊 СТАТИСТИКИ:")
        print(f"   📰 Статии от днеска в базата: {today_count}")
        print(f"   📰 Статии от вчера в базата: {yesterday_count}")

        # Препоръки
        print(f"\n💡 ПРЕПОРЪКИ:")
        if today_count == 0:
            print("   🎯 Препоръчвам: Скрапни статии от днеска с лимит 10-15")
            print("   📝 Команда: python run_scraper.py scrape --limit 15")
        elif today_count < 5:
            print("   🎯 Препоръчвам: Скрапни още статии с лимит 10")
            print("   📝 Команда: python run_scraper.py scrape --limit 10")
        else:
            print("   ✅ Добро покритие за днеска, можеш да скрапнеш 5-10 нови")
            print("   📝 Команда: python run_scraper.py scrape --limit 5")

        conn.close()

    except Exception as e:
        print(f"❌ Грешка при препоръки: {e}")


def main():
    """Главна функция"""
    print("🔍 COINDESK SCRAPER DEBUG TOOL")
    print("=" * 50)

    print("\nИзбери анализ:")
    print("1. Анализ на scraped данни")
    print("2. Симулация на scraping решения")
    print("3. Препоръки за scraping стратегия")
    print("4. Всички анализи")

    try:
        choice = input("\nВъведи номер (1-4): ").strip()

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
            print("❌ Невалиден избор")

    except KeyboardInterrupt:
        print("\n⏹️ Прекратено от потребителя")
    except Exception as e:
        print(f"\n❌ Грешка: {e}")


if __name__ == "__main__":
    main()
