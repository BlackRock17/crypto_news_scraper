import requests
from bs4 import BeautifulSoup
from config import REQUEST_HEADERS


def debug_article_structure(url):
    """Анализира HTML структурата на статия за да намерим правилните селектори"""
    print(f"🔍 Debugging HTML структура на: {url}")

    try:
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)

        response = session.get(url, timeout=15)
        response.raise_for_status()

        # Важно: Автоматично декодиране на compressed content
        if response.encoding is None:
            response.encoding = 'utf-8'

        # Използваме response.text вместо response.content за правилно декодиране
        soup = BeautifulSoup(response.text, 'html.parser')

        print(f"📊 Status код: {response.status_code}")
        print(f"📄 Encoding: {response.encoding}")

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

        # Проверяваме датата
        print("\n=== ДАТА ===")
        date_selectors = [
            'time[datetime]',
            '.article-date',
            '.post-date',
            '[data-timestamp]',
            'time'
        ]

        for selector in date_selectors:
            date_element = soup.select_one(selector)
            if date_element:
                print(
                    f"✅ {selector}: {date_element.get('datetime', 'Няма datetime')} | {date_element.get_text().strip()}")
            else:
                print(f"❌ {selector}: Не намерен")

        # Запазваме HTML за debugging (първите 10000 символа)
        print(f"\n=== HTML PREVIEW ===")
        html_preview = str(soup)[:2000]
        print(html_preview)

        return True

    except Exception as e:
        print(f"❌ Грешка при debugging: {str(e)}")
        return False


if __name__ == "__main__":
    # Тестваме с актуална статия
    test_url = "https://www.coindesk.com/markets/2025/06/09/bitwise-proshares-file-for-etfs-tracking-soaring-circle-shares"
    debug_article_structure(test_url)
