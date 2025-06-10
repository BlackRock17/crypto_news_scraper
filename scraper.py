#!/usr/bin/env python3
"""
Тест на подобрения CoinDesk scraper
Замени оригиналния scraper.py с новия код за да тестваш
"""

import sys
import time
from pathlib import Path

# Добави current directory към path за import
sys.path.append(str(Path(__file__).parent))


def test_with_existing_project():
    """Тества с існуващия проект (замени scraper.py)"""
    print("=== ТЕСТ НА ПОДОБРЕНИЯ SCRAPER ===")
    print("⚠️  За този тест трябва да замениш scraper.py с новия код!")
    print()

    try:
        # Import на подобрения scraper
        from scraper import CoinDeskScraper

        print("✅ Scraper imported успешно")

        # Тест 1: URL validation
        print("\n🔍 Тест 1: Проверка на URL detection...")
        scraper = CoinDeskScraper(use_database=False)
        article_links = scraper.get_article_links()

        print(f"📊 Намерени {len(article_links)} статии")

        if len(article_links) == 0:
            print("❌ Няма намерени статии - проблем с URL detection")
            return False

        # Показваме първите 3
        print("\n📋 Първи 3 статии:")
        for i, link in enumerate(article_links[:3], 1):
            print(f"  {i}. {link['title'][:60]}...")
            print(f"     → {link['url']}")

        # Тест 2: Single article scraping
        print(f"\n🔍 Тест 2: Scraping на първата статия...")
        first_article_url = article_links[0]['url']
        article_data = scraper.scrape_single_article(first_article_url)

        if article_data:
            print(f"✅ Успешно извлечена статия!")
            print(f"   📄 Заглавие: {article_data['title']}")
            print(f"   📊 Дължина: {article_data['content_length']} chars")
            print(f"   👤 Автор: {article_data['author']}")
            print(f"   📅 Дата: {article_data['date']}")
            print(f"   📝 Първи 200 chars: {article_data['content'][:200]}...")
        else:
            print("❌ Неуспешно извличане на статията")
            return False

        # Тест 3: Multiple articles
        print(f"\n🔍 Тест 3: Scraping на 5 статии...")
        articles = scraper.scrape_multiple_articles(max_articles=5, save_to_db=False)

        print(f"\n📊 РЕЗУЛТАТИ:")
        print(f"   ✅ Успешно извлечени: {len(articles)} статии")
        print(f"   📈 Success rate: {len(articles)}/5 = {(len(articles) / 5) * 100:.1f}%")

        if len(articles) >= 3:
            print("🎉 ТЕСТЪТ УСПЕШЕН! Scraper-ът работи добре!")
            print("\nИзвлечени статии:")
            for i, article in enumerate(articles, 1):
                print(f"  {i}. {article['title'][:50]}... ({article['content_length']} chars)")
            return True
        else:
            print("⚠️  Scraper-ът работи, но успешността е ниска")
            return False

    except ImportError as e:
        print(f"❌ Грешка при import: {e}")
        print("💡 Уверете се, че сте заменили scraper.py с новия код")
        return False
    except Exception as e:
        print(f"❌ Неочаквана грешка: {e}")
        return False


def run_quick_debug():
    """Бърз debug на проблема без замяна на файлове"""
    print("=== БЪРЗ DEBUG НА ПРОБЛЕМА ===")

    import requests
    from bs4 import BeautifulSoup

    # Тестваме директно една статия
    test_url = "https://www.coindesk.com/markets/2025/06/09/bitwise-proshares-file-for-etfs-tracking-soaring-circle-shares"

    print(f"🔍 Тествам директно: {test_url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(test_url, headers=headers, timeout=15)
        print(f"📊 Status: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            # Тест 1: Title
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else "No H1"
            print(f"📄 Title: {title}")

            # Тест 2: Paragraphs
            all_p = soup.find_all('p')
            print(f"📝 Намерени {len(all_p)} <p> tags")

            # Показваме първите 3 параграфа
            meaningful_p = []
            for p in all_p[:10]:  # Първите 10
                text = p.get_text().strip()
                if len(text) > 30:
                    meaningful_p.append(text)

            print(f"📝 Смислени параграфи: {len(meaningful_p)}")

            if meaningful_p:
                print("📝 Първи 3 параграфа:")
                for i, para in enumerate(meaningful_p[:3], 1):
                    print(f"  {i}. {para[:100]}...")

                total_content = '\n\n'.join(meaningful_p)
                print(f"📊 Общо съдържание: {len(total_content)} chars")

                if len(total_content) > 200:
                    print("✅ Достатъчно съдържание за извличане!")
                    return True
                else:
                    print("❌ Недостатъчно съдържание")
            else:
                print("❌ Няма смислени параграфи")

        else:
            print(f"❌ HTTP грешка: {response.status_code}")

    except Exception as e:
        print(f"❌ Грешка: {e}")

    return False


def analyze_current_scraper_issue():
    """Анализира проблема с текущия scraper"""
    print("=== АНАЛИЗ НА ТЕКУЩИЯ SCRAPER ПРОБЛЕМ ===")

    try:
        # Опитваме да намерим проблема в оригиналния scraper
        print("🔍 Търся config.py...")
        with open('config.py', 'r', encoding='utf-8') as f:
            config_content = f.read()

        print("✅ config.py намерен")

        # Проверяваме HTML_SELECTORS
        if 'HTML_SELECTORS' in config_content:
            print("✅ HTML_SELECTORS намерени в config")

            # Извличаме article_content селекторите
            import re
            content_match = re.search(r"'article_content':\s*\[(.*?)\]", config_content, re.DOTALL)
            if content_match:
                selectors = content_match.group(1)
                print(f"📋 Текущи content селектори: {selectors}")

        print("\n💡 ПРОБЛЕМЪТ: Селекторите в config.py не работят с новата CoinDesk структура")
        print("💡 РЕШЕНИЕ: Трябва да обновим scraper.py с новата логика")

    except FileNotFoundError:
        print("❌ config.py не е намерен")
    except Exception as e:
        print(f"❌ Грешка при анализ: {e}")


def provide_solution_steps():
    """Предоставя стъпки за решение"""
    print("\n" + "=" * 60)
    print("🚀 СТЪПКИ ЗА РЕШАВАНЕ НА ПРОБЛЕМА")
    print("=" * 60)

    print("""
🔧 СТЪПКА 1: Замени scraper.py
   - Копирай новия код от artifacts
   - Замести съществуващия scraper.py файл

🔧 СТЪПКА 2: Тествай
   - Изпълни: python -c "from scraper import CoinDeskScraper; s=CoinDeskScraper(False); print(len(s.get_article_links()))"

🔧 СТЪПКА 3: Пълен тест
   - Изпълни: python run_scraper.py scrape --limit 5 --verbose

🔧 СТЪПКА 4: Провери резултата
   - Трябва да видиш повече от 3 статии
   - Success rate трябва да е >80%
    """)

    print("💡 Ако има проблеми, изпрати грешките и ще помогна!")


if __name__ == "__main__":
    print("🧪 COINDESK SCRAPER ДИАГНОСТИКА")
    print("=" * 50)

    # Избор на тест
    print("\nВъзможни тестове:")
    print("1. Бърз debug (без промени на файлове)")
    print("2. Тест с подобрения scraper (изисква замяна на scraper.py)")
    print("3. Анализ на текущия проблем")
    print("4. Стъпки за решение")

    try:
        choice = input("\nИзбери тест (1-4): ").strip()

        if choice == "1":
            success = run_quick_debug()
        elif choice == "2":
            success = test_with_existing_project()
        elif choice == "3":
            analyze_current_scraper_issue()
            success = True
        elif choice == "4":
            provide_solution_steps()
            success = True
        else:
            print("❌ Невалиден избор")
            success = False

        if success:
            print("\n✅ Тест завършен успешно!")
        else:
            print("\n❌ Тест неуспешен")

    except KeyboardInterrupt:
        print("\n⏹️ Прекратено от потребителя")
    except Exception as e:
        print(f"\n❌ Грешка: {e}")
