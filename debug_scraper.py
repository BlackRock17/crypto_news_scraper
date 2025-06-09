import requests
from bs4 import BeautifulSoup
from config import REQUEST_HEADERS


def test_simple_request():
    """Прост тест за да видим какво получаваме"""
    url = "https://www.coindesk.com/"  # Главната страница

    print(f"🔍 Тестване на основна заявка към: {url}")

    try:
        # Опитваме с различни настройки
        session = requests.Session()

        # По-прости headers
        simple_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        session.headers.update(simple_headers)

        response = session.get(url, timeout=15)
        print(f"📊 Status код: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('content-type', 'Unknown')}")
        print(f"📦 Content-Length: {len(response.content)} bytes")
        print(f"🗜️ Content-Encoding: {response.headers.get('content-encoding', 'None')}")

        # Проверяваме дали получаваме HTML
        if 'text/html' in response.headers.get('content-type', ''):
            # Форсираме правилно декодиране
            content = response.content

            # Опитваме различни начини за декодиране
            try:
                # 1. Автоматично
                text_auto = response.text
                print(f"📝 Auto decode: {len(text_auto)} chars")

                # 2. UTF-8 директно
                text_utf8 = content.decode('utf-8', errors='ignore')
                print(f"📝 UTF-8 decode: {len(text_utf8)} chars")

                # Използваме UTF-8 версията
                soup = BeautifulSoup(text_utf8, 'html.parser')

                # Проверяваме основните елементи
                title = soup.find('title')
                print(f"📄 Title tag: {title.get_text() if title else 'None'}")

                # Проверяваме линкове
                links = soup.find_all('a', href=True)
                print(f"🔗 Намерени linкове: {len(links)}")

                # Показваме първите няколко линка
                for i, link in enumerate(links[:5], 1):
                    href = link.get('href', '')
                    text = link.get_text().strip()[:50]
                    print(f"  {i}. {text} → {href}")

                return soup

            except Exception as decode_error:
                print(f"❌ Декодиране грешка: {decode_error}")
                return None
        else:
            print("❌ Не получихме HTML съдържание")
            return None

    except Exception as e:
        print(f"❌ Грешка при заявката: {str(e)}")
        return None


def debug_article_structure(url):
    """Анализира HTML структурата на статия за да намерим правилните селектори"""
    print(f"\n🔍 Debugging HTML структура на: {url}")

    try:
        session = requests.Session()

        # По-прости headers
        simple_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        session.headers.update(simple_headers)

        response = session.get(url, timeout=15)
        response.raise_for_status()

        print(f"📊 Status код: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('content-type')}")

        # Форсираме UTF-8 декодиране
        content_text = response.content.decode('utf-8', errors='ignore')
        soup = BeautifulSoup(content_text, 'html.parser')

        # Проверяваме заглавието
        print("\n=== ЗАГЛАВИЕ ===")
        possible_titles = [
            soup.find('h1'),
            soup.find('title'),
            soup.select_one('[data-module="ArticleHeader"] h1'),
            soup.select_one('.headline'),
        ]

        for i, title in enumerate(possible_titles, 1):
            if title:
                print(f"  {i}. {title.name}: {title.get_text().strip()[:100]}")
            else:
                print(f"  {i}. None")

        # Проверяваме съдържанието
        print("\n=== СЪДЪРЖАНИЕ ===")

        # Търсим различни селектори за статии
        content_selectors = [
            '[data-module="ArticleBody"]',
            '.article-content',
            '.post-content',
            'article',
            '.entry-content',
            'main article',
            '.content'
        ]

        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = elements[0].get_text().strip()
                print(f"✅ {selector}: {len(content)} chars - {content[:150]}...")

                # Показваме и параграфите
                paragraphs = elements[0].find_all('p')
                print(f"   📝 Параграфи: {len(paragraphs)}")
                if paragraphs:
                    print(f"   📝 Първи параграф: {paragraphs[0].get_text().strip()[:100]}...")
            else:
                print(f"❌ {selector}: Не намерен")

        # Проверяваме всички <p> tags
        all_paragraphs = soup.find_all('p')
        print(f"\n📰 Общо <p> tags: {len(all_paragraphs)}")

        # Показваме първите 5 параграфа
        print("\n=== ПЪРВИ 5 ПАРАГРАФА ===")
        for i, p in enumerate(all_paragraphs[:5], 1):
            text = p.get_text().strip()
            if text:
                print(f"  {i}. ({len(text)} chars) {text[:100]}...")
            else:
                print(f"  {i}. (празен)")

        # Запазваме HTML за debugging (първите 2000 символа)
        print(f"\n=== HTML PREVIEW (първи 1000 chars) ===")
        html_preview = content_text[:1000]
        print(html_preview)

        return True

    except Exception as e:
        print(f"❌ Грешка при debugging: {str(e)}")
        return False


if __name__ == "__main__":
    print("=== DEBUGGING COINDESK SCRAPER ===")

    # Първо тестваме главната страница
    print("1. Тестване на главната страница...")
    soup = test_simple_request()

    if soup:
        print("\n2. Тестване на конкретна статия...")
        # Тестваме с актуална статия
        test_url = "https://www.coindesk.com/markets/2025/06/09/bitwise-proshares-file-for-etfs-tracking-soaring-circle-shares"
        debug_article_structure(test_url)
    else:
        print("❌ Не можем да достигнем CoinDesk. Възможно е сайтът да блокира scraping.")
