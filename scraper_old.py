import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from urllib.parse import urljoin
import re

from config import (
    COINDESK_MAIN_PAGE,
    REQUEST_HEADERS,
    NEWS_URL_PATTERNS,
    SCRAPING_CONFIG,
    HTML_SELECTORS,
    is_valid_article_url,
    get_full_url
)
from database import DatabaseManager


class CoinDeskScraper:
    def __init__(self, use_database=True):
        print("🚀 Инициализиране на CoinDesk Scraper...")
        self.session = requests.Session()

        # Използваме по-прости headers като в debug скрипта
        simple_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.session.headers.update(simple_headers)
        self.scraped_urls = set()  # За да избягваме дублиране

        # Database интеграция
        self.use_database = use_database
        if use_database:
            self.db = DatabaseManager()
        else:
            self.db = None

        print("✅ Scraper готов!")

    def get_article_links(self):
        """Намира всички линкове към статии от главната страница"""
        print("🔍 Търсене на статии в главната страница...")

        try:
            response = self.session.get(
                COINDESK_MAIN_PAGE,
                timeout=SCRAPING_CONFIG['request_timeout']
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Намираме всички линкове
            all_links = soup.find_all('a', href=True)

            # Филтрираме валидните статии
            article_links = []
            for link in all_links:
                href = link['href']

                # Правим пълен URL
                full_url = get_full_url(href)

                # Проверяваме дали е валиден article URL
                if is_valid_article_url(href):
                    # Вземаме заглавието на линка
                    title = link.text.strip()
                    if title and len(title) > 10:  # Само със смислено заглавие
                        article_links.append({
                            'url': full_url,
                            'title': title,
                            'href': href
                        })

            # Премахваме дублираните URLs
            unique_articles = []
            seen_urls = set()
            for article in article_links:
                if article['url'] not in seen_urls:
                    unique_articles.append(article)
                    seen_urls.add(article['url'])

            print(f"📰 Намерени {len(unique_articles)} уникални статии")
            return unique_articles

        except Exception as e:
            print(f"❌ Грешка при извличането на линкове: {str(e)}")
            return []

    def scrape_single_article(self, article_url):
        """Извлича съдържанието на една статия"""
        print(f"📄 Scraping статия: {article_url}")

        try:
            # Малка пауза между заявките
            time.sleep(SCRAPING_CONFIG['delay_between_requests'])

            response = self.session.get(
                article_url,
                timeout=SCRAPING_CONFIG['request_timeout']
            )
            response.raise_for_status()

            # Правилно декодиране като в debug скрипта
            content_text = response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content_text, 'html.parser')

            # Извличаме заглавието
            title = self._extract_title(soup)

            # Извличаме съдържанието
            content = self._extract_content(soup)

            # Извличаме датата
            date = self._extract_date(soup)

            # Извличаме автора (ако има)
            author = self._extract_author(soup)

            # Проверяваме дали статията е достатъчно дълга
            if len(content) < SCRAPING_CONFIG['min_article_length']:
                print(f"⚠️  Статията е твърде кратка ({len(content)} chars)")
                return None

            article_data = {
                'url': article_url,
                'title': title,
                'content': content,
                'date': date,
                'author': author,
                'scraped_at': datetime.now(),
                'content_length': len(content)
            }

            print(f"✅ Успешно извлечена статия: {title[:50]}...")
            return article_data

        except Exception as e:
            print(f"❌ Грешка при scraping на {article_url}: {str(e)}")
            return None

    def _extract_title(self, soup):
        """Извлича заглавието на статията"""
        for selector in HTML_SELECTORS['article_title']:
            title_element = soup.select_one(selector)
            if title_element:
                return title_element.get_text().strip()

        # Fallback - търсим в <title> tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            # Почистваме от " | CoinDesk" в края
            title = re.sub(r'\s*\|\s*CoinDesk.*$', '', title)
            return title

        return "Неизвестно заглавие"

    def _extract_content(self, soup):
        """Извлича съдържанието на статията"""
        # Първо опитваме специфичните селектори
        for selector in HTML_SELECTORS['article_content'][1:]:  # Пропускаме 'p' за сега
            content_element = soup.select_one(selector)
            if content_element:
                # Вземаме всички параграфи
                paragraphs = content_element.find_all('p')
                content = '\n\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                if content:
                    return content

        # Fallback - използваме всички <p> tags (това работи за CoinDesk!)
        all_paragraphs = soup.find_all('p')
        if all_paragraphs:
            # Филтрираме само параграфите със съдържание
            meaningful_paragraphs = []
            for p in all_paragraphs:
                text = p.get_text().strip()
                # Взимаме само параграфи с достатъчно текст
                if len(text) > 30 and not text.startswith('Sign up') and not text.startswith('Get the'):
                    meaningful_paragraphs.append(text)

            content = '\n\n'.join(meaningful_paragraphs)
            return content

        return "Съдържанието не може да бъде извлечено"

    def _extract_date(self, soup):
        """Извлича датата на статията"""
        for selector in HTML_SELECTORS['article_date']:
            date_element = soup.select_one(selector)
            if date_element:
                # Търсим datetime атрибут
                datetime_str = date_element.get('datetime')
                if datetime_str:
                    try:
                        return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    except:
                        pass

                # Опитваме да парсираме текста
                date_text = date_element.get_text().strip()
                if date_text:
                    return date_text

        return datetime.now().strftime('%Y-%m-%d')

    def _extract_author(self, soup):
        """Извлича автора на статията"""
        for selector in HTML_SELECTORS['article_author']:
            author_element = soup.select_one(selector)
            if author_element:
                return author_element.get_text().strip()

        return "Неизвестен автор"

    def scrape_multiple_articles(self, max_articles=None, save_to_db=True):
        """Scrape-ва множество статии и ги запазва в базата данни"""
        if max_articles is None:
            max_articles = SCRAPING_CONFIG['max_articles_per_session']

        print(f"🎯 Започвам scraping на максимум {max_articles} статии...")

        # Получаваме линковете
        article_links = self.get_article_links()

        if not article_links:
            print("❌ Не са намерени статии за scraping")
            return []

        # Ако използваме database, филтрираме вече scraped URLs
        if self.db and save_to_db:
            print("🔍 Проверяване за дублиращи се URLs...")
            new_article_links = []
            skipped_count = 0

            for link_info in article_links:
                url = link_info['url']
                if not self.db.is_url_scraped_before(url):
                    new_article_links.append(link_info)
                else:
                    skipped_count += 1
                    # Update последно виждане
                    self.db.record_scraped_url(url)

            print(f"📊 {len(new_article_links)} нови статии, {skipped_count} вече scraped")
            article_links = new_article_links

        # Ограничаваме броя
        article_links = article_links[:max_articles]

        if not article_links:
            print("ℹ️ Всички статии са вече scraped")
            return []

        # Scrape-ваме всяка статия
        scraped_articles = []
        for i, link_info in enumerate(article_links, 1):
            url = link_info['url']
            print(f"\n[{i}/{len(article_links)}] {link_info['title'][:60]}...")

            article_data = self.scrape_single_article(url)
            if article_data:
                scraped_articles.append(article_data)

                # Запазваме в базата данни ако е заявено
                if self.db and save_to_db:
                    self.db.save_article(article_data)

            # Прогрес информация
            if i % 5 == 0:
                print(f"📊 Прогрес: {i}/{len(article_links)} статии обработени")

        print(f"\n🎉 Scraping завършен! Успешно извлечени {len(scraped_articles)} статии")

        # Database статистики
        if self.db and save_to_db:
            stats = self.db.get_database_stats()
            print(
                f"📊 Database статистики: {stats['total_articles']} общо статии, {stats['unprocessed_articles']} за анализ")

        return scraped_articles


# Тестова функция
def test_single_article():
    """Тества scraping на една статия"""
    scraper = CoinDeskScraper()

    # Тестваме с конкретна статия
    test_url = "https://www.coindesk.com/markets/2025/06/09/bitwise-proshares-file-for-etfs-tracking-soaring-circle-shares"

    print(f"\n🧪 Тестване на scraping на една статия...")
    article = scraper.scrape_single_article(test_url)

    if article:
        print(f"\n✅ УСПЕХ! Извлечена статия:")
        print(f"   📄 Заглавие: {article['title']}")
        print(f"   📅 Дата: {article['date']}")
        print(f"   👤 Автор: {article['author']}")
        print(f"   📊 Дължина: {article['content_length']} символа")
        print(f"   📝 Първи 200 символа: {article['content'][:200]}...")
        return True
    else:
        print("❌ Неуспешно извличане на статията")
        return False


if __name__ == "__main__":
    print("=== COINDESK SCRAPER TEST ===")

    # Тестваме основната функционалност
    test_single_article()
