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

        # Използваме по-прости headers
        simple_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(simple_headers)
        self.scraped_urls = set()

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

            # Търсим всички <a> тагове с href
            article_links = []
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                href = link['href']

                # Правим пълен URL
                if href.startswith('/'):
                    full_url = f"https://www.coindesk.com{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                # Подобрена валидация на URL
                if self._is_valid_article_url_improved(href):
                    title = self._extract_link_title(link)
                    if title and len(title) > 15:
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

            # DEBUG информация
            print("🔍 Първи 5 статии за проверка:")
            for i, article in enumerate(unique_articles[:5], 1):
                print(f"  {i}. {article['title'][:60]}...")

            return unique_articles

        except Exception as e:
            print(f"❌ Грешка при извличането на линкове: {str(e)}")
            return []

    def _is_valid_article_url_improved(self, href):
        """Подобрена логика за валидация на article URLs"""

        if not href or href in ['#', '/', '']:
            return False

        if href.startswith('http') and 'coindesk.com' not in href:
            return False

        if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
            return False

        # Изключваме системни страници
        exclude_patterns = [
            '/newsletters/', '/podcasts/', '/events/', '/about/', '/careers/',
            '/advertise/', '/price/', '/author/', '/tag/', '/sponsored-content/',
            '/_next/', '/api/'
        ]

        for pattern in exclude_patterns:
            if pattern in href:
                return False

        # Търсим статии с година в URL-а или категории
        date_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',  # /2025/06/09/
            r'/2025/', r'/2024/'
        ]

        has_date = any(re.search(pattern, href) for pattern in date_patterns)

        news_categories = ['/markets/', '/policy/', '/tech/', '/business/', '/layer2/', '/web3/']
        has_category = any(category in href for category in news_categories)

        return has_date or has_category

    def _extract_link_title(self, link):
        """Извлича заглавието от link element"""
        text = link.get_text().strip()
        if text and len(text) > 5:
            return ' '.join(text.split())

        title_attr = link.get('title', '').strip()
        if title_attr:
            return title_attr

        aria_label = link.get('aria-label', '').strip()
        if aria_label:
            return aria_label

        return ""

    def scrape_single_article(self, article_url):
        """Извлича съдържанието на една статия"""
        print(f"📄 Scraping статия: {article_url}")

        try:
            time.sleep(SCRAPING_CONFIG['delay_between_requests'])

            response = self.session.get(
                article_url,
                timeout=SCRAPING_CONFIG['request_timeout']
            )
            response.raise_for_status()

            content_text = response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content_text, 'html.parser')

            # Извличаме данните
            title = self._extract_title_improved(soup)
            content = self._extract_content_improved(soup)
            date = self._extract_date_improved(soup)
            author = self._extract_author_improved(soup)

            # Проверяваме дължината
            if len(content) < SCRAPING_CONFIG['min_article_length']:
                print(f"⚠️  Статията е твърде кратка ({len(content)} chars)")
                print(f"🔍 DEBUG първи 200 chars: {content[:200]}")
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

            print(f"✅ Успешно извлечена статия: {title[:50]}... ({len(content)} chars)")
            return article_data

        except Exception as e:
            print(f"❌ Грешка при scraping на {article_url}: {str(e)}")
            return None

    def _extract_title_improved(self, soup):
        """Подобрено извличане на заглавието"""

        # h1 tag първо
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            text = h1.get_text().strip()
            if text and len(text) > 10:
                return text

        # meta og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        # title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            title = re.sub(r'\s*\|\s*CoinDesk.*$', '', title)
            if title:
                return title

        return "Неизвестно заглавие"

    def _extract_content_improved(self, soup):
        """Подобрено извличане на съдържанието"""

        print("🔍 Започвам подобрено извличане на съдържание...")

        # Стратегия 1: Main containers
        main_selectors = ['main', 'article', '[role="main"]', '.article-content', '.post-content']

        for selector in main_selectors:
            container = soup.select_one(selector)
            if container:
                print(f"✅ Намерен main container: {selector}")
                paragraphs = container.find_all('p')
                content = self._process_paragraphs(paragraphs)
                if len(content) > 200:
                    print(f"✅ Извлечени {len(content)} chars от {selector}")
                    return content

        # Стратегия 2: Всички <p> tags
        print("🔍 Търся всички <p> tags...")
        all_paragraphs = soup.find_all('p')
        print(f"📊 Намерени {len(all_paragraphs)} общо <p> tags")

        if all_paragraphs:
            content = self._process_paragraphs(all_paragraphs)
            if len(content) > 100:
                print(f"✅ Извлечени {len(content)} chars от всички <p> tags")
                return content

        # Стратегия 3: Div containers
        print("🔍 Търся div containers с текст...")
        text_divs = soup.find_all('div')
        meaningful_text = []

        for div in text_divs:
            direct_text = div.get_text().strip()
            if 50 < len(direct_text) < 1000:
                meaningful_text.append(direct_text)

        if meaningful_text:
            content = '\n\n'.join(meaningful_text[:10])
            if len(content) > 100:
                print(f"✅ Извлечени {len(content)} chars от div containers")
                return content

        # Стратегия 4: Fallback
        print("🔍 Fallback: Вземам всичко от body...")
        body = soup.find('body')
        if body:
            for script in body(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            body_text = body.get_text()
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            content = '\n'.join(lines[:50])

            if len(content) > 100:
                print(f"✅ Fallback извлечени {len(content)} chars от body")
                return content

        print("❌ Не успях да извлека съдържание")
        return "Съдържанието не може да бъде извлечено"

    def _process_paragraphs(self, paragraphs):
        """Обработва списък от <p> tags"""
        meaningful_paragraphs = []

        for p in paragraphs:
            text = p.get_text().strip()
            if self._is_meaningful_paragraph(text):
                meaningful_paragraphs.append(text)

        return '\n\n'.join(meaningful_paragraphs)

    def _is_meaningful_paragraph(self, text):
        """Проверява дали параграфа е смислен"""
        if len(text) < 20:
            return False

        exclude_phrases = [
            'Sign up', 'Subscribe', 'Newsletter', 'See all newsletters',
            'Don\'t miss', 'By signing up', 'privacy policy', 'terms of use',
            'Cookie', 'Advertisement', 'Sponsored', 'Follow us', 'Share this',
            'Read more', 'Click here', 'Download', 'Watch', 'Listen'
        ]

        text_lower = text.lower()
        for phrase in exclude_phrases:
            if phrase.lower() in text_lower:
                return False

        if text.count('.') < 1:
            return False

        return True

    def _extract_date_improved(self, soup):
        """Подобрено извличане на датата"""

        # meta published_time
        published_meta = soup.find('meta', property='article:published_time')
        if published_meta and published_meta.get('content'):
            try:
                date_str = published_meta['content']
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
            except:
                pass

        # time tags
        time_tags = soup.find_all('time')
        for time_tag in time_tags:
            datetime_attr = time_tag.get('datetime')
            if datetime_attr:
                try:
                    return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                except:
                    pass

        # От URL-а
        canonical = soup.find('link', rel='canonical')
        if canonical:
            url_date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', canonical.get('href', ''))
            if url_date_match:
                year, month, day = url_date_match.groups()
                return f"{year}-{month}-{day}"

        return datetime.now().strftime('%Y-%m-%d')

    def _extract_author_improved(self, soup):
        """Подобрено извличане на автора"""

        # meta author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            return author_meta['content'].strip()

        # author links
        author_selectors = [
            'a[href*="/author/"]', '.author-name', '.byline',
            '[data-author]', '.post-author'
        ]

        for selector in author_selectors:
            author_element = soup.select_one(selector)
            if author_element:
                author_text = author_element.get_text().strip()
                if author_text and len(author_text) < 100:
                    return author_text

        return "Неизвестен автор"

    def scrape_multiple_articles(self, max_articles=None, save_to_db=True):
        """Scrape-ва множество статии"""
        if max_articles is None:
            max_articles = SCRAPING_CONFIG['max_articles_per_session']

        print(f"🎯 Започвам scraping на максимум {max_articles} статии...")

        # Получаваме линковете
        article_links = self.get_article_links()

        if not article_links:
            print("❌ Не са намерени статии за scraping")
            return []

        # Database филтриране
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
                    self.db.record_scraped_url(url)

            print(f"📊 {len(new_article_links)} нови статии, {skipped_count} вече scraped")
            article_links = new_article_links

        # Ограничаваме броя
        article_links = article_links[:max_articles]

        if not article_links:
            print("ℹ️ Всички статии са вече scraped")
            return []

        # Scraping
        scraped_articles = []
        successful_count = 0
        failed_count = 0

        for i, link_info in enumerate(article_links, 1):
            url = link_info['url']
            print(f"\n[{i}/{len(article_links)}] {link_info['title'][:60]}...")

            article_data = self.scrape_single_article(url)
            if article_data:
                scraped_articles.append(article_data)
                successful_count += 1

                if self.db and save_to_db:
                    self.db.save_article(article_data)
            else:
                failed_count += 1
                print(f"❌ Неуспешно извличане на статия {i}")

            if i % 5 == 0:
                print(f"📊 Прогрес: {i}/{len(article_links)} статии обработени")
                print(f"    ✅ Успешни: {successful_count}, ❌ Неуспешни: {failed_count}")

        print(f"\n🎉 Scraping завършен!")
        print(f"📊 Финален резултат: {successful_count} успешни, {failed_count} неуспешни статии")

        if self.db and save_to_db:
            stats = self.db.get_database_stats()
            print(
                f"📊 Database статистики: {stats['total_articles']} общо статии, {stats['unprocessed_articles']} за анализ")

        return scraped_articles


def test_single_article():
    """Тества scraping на една статия"""
    scraper = CoinDeskScraper(use_database=False)

    test_url = "https://www.coindesk.com/markets/2025/06/09/bitwise-proshares-file-for-etfs-tracking-soaring-circle-shares"

    print(f"\n🧪 Тестване на scraping на една статия...")
    article = scraper.scrape_single_article(test_url)

    if article:
        print(f"\n✅ УСПЕХ! Извлечена статия:")
        print(f"   📄 Заглавие: {article['title']}")
        print(f"   📅 Дата: {article['date']}")
        print(f"   👤 Автор: {article['author']}")
        print(f"   📊 Дължина: {article['content_length']} символа")
        print(f"   📝 Първи 300 символа: {article['content'][:300]}...")
        return True
    else:
        print("❌ Неуспешно извличане на статията")
        return False


if __name__ == "__main__":
    print("=== ПОДОБРЕН COINDESK SCRAPER TEST ===")
    success = test_single_article()

    if success:
        print("\n🎉 Single article test успешен!")
    else:
        print("❌ Single article test неуспешен")
