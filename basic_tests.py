import requests
from bs4 import BeautifulSoup


def test_coindesk_connection():
    """Прост тест дали можем да достигнем CoinDesk"""
    print("🔍 Тестване на връзката с CoinDesk...")

    url = "https://www.coindesk.com/"

    # Настройваме headers за да изглеждаме като браузър
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # Правим GET заявка
        response = requests.get(url, headers=headers, timeout=10)

        # Проверяваме статус кода
        print(f"📊 Status код: {response.status_code}")

        if response.status_code == 200:
            print("✅ Успешна връзка с CoinDesk!")

            # Парсираме HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Намираме заглавието на страницата
            title = soup.find('title')
            if title:
                print(f"📄 Заглавие на страницата: {title.text.strip()}")

            # Намираме всички линкове
            links = soup.find_all('a', href=True)

            # Търсим различни варианти за новинарски линкове
            news_patterns = ['/news/', '/policy/', '/markets/', '/tech/', '/business/']
            all_news_links = []

            for link in links:
                href = link['href']
                if any(pattern in href for pattern in news_patterns):
                    all_news_links.append(link)

            # Също така търсим линкове, които съдържат актуални новини
            article_links = [link for link in links if
                             link.get('href', '').startswith('/') and len(link.text.strip()) > 20]

            print(f"🔗 Намерени {len(links)} общо линка")
            print(f"📰 Намерени {len(all_news_links)} новинарски линка с patterns")
            print(f"📄 Намерени {len(article_links)} възможни статии")

            # Показваме първите 5 интересни линка
            print("\n📋 Първи 5 възможни статии:")
            for i, link in enumerate(article_links[:5], 1):
                href = link['href']
                text = link.text.strip()[:80] + "..." if len(link.text.strip()) > 80 else link.text.strip()
                print(f"  {i}. {text}")
                print(f"     → {href}")

            print("\n📋 Примерни новинарски линкове:")
            for i, link in enumerate(all_news_links[:3], 1):
                href = link['href']
                text = link.text.strip()[:80] + "..." if len(link.text.strip()) > 80 else link.text.strip()
                print(f"  {i}. {text}")
                print(f"     → {href}")

            assert len(links) > 0, "Трябва да има поне няколко линка"
            print("\n✅ Тестът премина успешно!")
            return True

        else:
            print(f"❌ Грешка: Статус код {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Грешка при връзката: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Неочаквана грешка: {str(e)}")
        return False


if __name__ == "__main__":
    print("=== ТЕСТ НА COINDESK SCRAPER ===")
    success = test_coindesk_connection()

    if success:
        print("\n🎉 Основният тест премина успешно! Готови сме за следващата стъпка.")
    else:
        print("\n💡 Има проблем с връзката. Проверете интернет връзката.")
