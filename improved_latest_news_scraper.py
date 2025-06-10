import sqlite3

import requests


def _extract_content_improved(self, soup):
    """КОРЕННО ПОДОБРЕНО извличане на съдържанието за CoinDesk"""

    print("🔍 Започвам FIXED content extraction...")

    # СТРАТЕГИЯ 1: CoinDesk-специфични patterns
    print("🎯 СТРАТЕГИЯ 1: CoinDesk patterns...")

    # Намираме "What to know:" marker и взимаме контейнера
    what_to_know = soup.find(text=lambda text: text and 'What to know:' in text)
    if what_to_know:
        print("✅ Намерен 'What to know:' marker")

        # Намираме parent container
        current = what_to_know.parent
        while current and current.name not in ['main', 'article', 'div', 'section']:
            current = current.parent

        if current:
            # Вземаме всички <p> в този container
            container_paragraphs = current.find_all('p')
            meaningful_text = []

            for p in container_paragraphs:
                text = p.get_text().strip()
                if (text and
                        len(text) > 30 and
                        'See all newsletters' not in text and
                        'What to know:' not in text and
                        not text.startswith('[')):  # Премахваме price links
                    meaningful_text.append(text)

            if meaningful_text:
                content = '\n\n'.join(meaningful_text)
                print(f"✅ CoinDesk pattern extraction: {len(content)} chars")
                if len(content) > 200:
                    return content

    # СТРАТЕГИЯ 2: Търсим main content container
    print("🎯 СТРАТЕГИЯ 2: Main containers...")
    main_selectors = [
        'main',
        'article',
        '[role="main"]',
        '.article-content',
        '.post-content',
        '.entry-content',
        'div[data-module="ArticleBody"]'
    ]

    for selector in main_selectors:
        container = soup.select_one(selector)
        if container:
            print(f"✅ Намерен container: {selector}")
            paragraphs = container.find_all('p')
            content = self._process_paragraphs_fixed(paragraphs)
            if len(content) > 200:
                print(f"✅ Main container extraction: {len(content)} chars")
                return content

    # СТРАТЕГИЯ 3: Всички <p> tags с по-умна филтрация
    print("🎯 СТРАТЕГИЯ 3: Всички <p> tags...")
    all_paragraphs = soup.find_all('p')
    print(f"📊 Намерени {len(all_paragraphs)} общо <p> tags")

    if all_paragraphs:
        content = self._process_paragraphs_fixed(all_paragraphs)
        if len(content) > 100:
            print(f"✅ All paragraphs extraction: {len(content)} chars")
            return content

    # СТРАТЕГИЯ 4: Търсим текст в div елементи
    print("🎯 СТРАТЕГИЯ 4: Div text extraction...")

    # Намираме всички div-ове с текст
    text_divs = soup.find_all('div')
    meaningful_texts = []

    for div in text_divs:
        # Взимаме директния текст от div-а
        direct_text = div.get_text(separator=' ', strip=True)

        # Филтрираме по дължина и съдържание
        if (50 < len(direct_text) < 2000 and
                '.' in direct_text and  # Трябва да има изречения
                not direct_text.startswith('[') and  # Не започва с [price links]
                'See all newsletters' not in direct_text):
            meaningful_texts.append(direct_text)

    if meaningful_texts:
        # Вземаме най-дългите и най-значимите текстове
        meaningful_texts.sort(key=len, reverse=True)
        selected_texts = meaningful_texts[:5]  # Първите 5 най-дълги

        content = '\n\n'.join(selected_texts)
        if len(content) > 200:
            print(f"✅ Div text extraction: {len(content)} chars")
            return content

    # СТРАТЕГИЯ 5: Fallback - body text
    print("🎯 СТРАТЕГИЯ 5: Body fallback...")
    body = soup.find('body')
    if body:
        # Премахваме нежелани елементи
        for unwanted in body(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()

        body_text = body.get_text(separator=' ', strip=True)

        # Разделяме по изречения и вземаме смислените
        sentences = [s.strip() for s in body_text.split('.') if s.strip()]
        meaningful_sentences = []

        for sentence in sentences:
            if (20 < len(sentence) < 500 and
                    not sentence.startswith('[') and
                    'See all newsletters' not in sentence and
                    'Sign up' not in sentence):
                meaningful_sentences.append(sentence)

        if meaningful_sentences:
            # Вземаме първите 20 изречения
            content = '. '.join(meaningful_sentences[:20]) + '.'
            if len(content) > 200:
                print(f"✅ Body fallback extraction: {len(content)} chars")
                return content

    print("❌ Всички стратегии неуспешни")
    return "Съдържанието не може да бъде извлечено"


def _process_paragraphs_fixed(self, paragraphs):
    """Подобрена обработка на параграфи"""
    meaningful_paragraphs = []

    for p in paragraphs:
        text = p.get_text().strip()

        # По-строга филтрация
        if self._is_meaningful_paragraph_fixed(text):
            meaningful_paragraphs.append(text)

    return '\n\n'.join(meaningful_paragraphs)


def _is_meaningful_paragraph_fixed(self, text):
    """Подобрена проверка за смислени параграфи"""

    # Основни проверки
    if len(text) < 20:
        return False

    # Изключваме price links и navigation
    if text.startswith('[') and text.endswith(']'):
        return False

    # Изключваме нежелани фрази
    exclude_phrases = [
        'Sign up', 'Subscribe', 'Newsletter', 'See all newsletters',
        'Don\'t miss', 'By signing up', 'privacy policy', 'terms of use',
        'Cookie', 'Advertisement', 'Sponsored', 'Follow us', 'Share this',
        'Read more', 'Click here', 'Download', 'Watch', 'Listen',
        'Back to menu', 'What to know:', 'See more'
    ]


def _is_meaningful_paragraph_fixed(self, text):
    """Подобрена проверка за смислени параграфи"""

    # Основни проверки
    if len(text) < 20:
        return False

    # Изключваме price links и navigation
    if text.startswith('[') and text.endswith(']'):
        return False

    # Изключваме нежелани фрази
    exclude_phrases = [
        'Sign up', 'Subscribe', 'Newsletter', 'See all newsletters',
        'Don\'t miss', 'By signing up', 'privacy policy', 'terms of use',
        'Cookie', 'Advertisement', 'Sponsored', 'Follow us', 'Share this',
        'Read more', 'Click here', 'Download', 'Watch', 'Listen',
        'Back to menu', 'What to know:', 'See more'
    ]

    text_lower = text.lower()
    for phrase in exclude_phrases:
        if phrase.lower() in text_lower:
            return False

    # Трябва да има поне едно изречение
    if text.count('.') < 1 and text.count('!') < 1 and text.count('?') < 1:
        return False

    # Не трябва да е само цифри или кратки фрази
    words = text.split()
    if len(words) < 5:
        return False

    return True


from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin
import re
import json

from config import (
    COINDESK_BASE_URL,
    REQUEST_HEADERS,
    SCRAPING_CONFIG,
    HTML_SELECTORS
)
from database import DatabaseManager


class CoinDeskLatestNewsScraper:
    def __init__(self, use_database=True):
        print("🚀 Инициализиране на CoinDesk Latest News Scraper...")
        self.session = requests.Session()

        # Headers
        simple_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(simple_headers)

        # URL за latest news
        self.latest_news_url = "https://www.coindesk.com/latest-crypto-news"

        # Database интеграция
        self.use_database = use_database
        if use_database:
            self.db = DatabaseManager()
        else:
            self.db = None

        print("✅ Latest News Scraper готов!")

    def get_articles_by_date_filter(self, date_filter='today', max_articles=50):
        """
        Получава статии от latest-crypto-news с date филтър

        date_filter може да е:
        - 'today' - само днешни статии
        - 'yesterday' - вчерашни статии
        - '2025-06-10' - конкретна дата
        - 'last_3_days' - последните 3 дни
        - 'all' - всички (до max_articles)
        """
        print(f"🔍 Търсене на статии с филтър: {date_filter}")

        # Определяме target дати
        target_dates = self._get_target_dates(date_filter)
        print(f"📅 Target дати: {target_dates}")

        # Започваме да скрапваме страници
        all_articles = []
        page_offset = 0
        pages_checked = 0
        max_pages = 10  # Ограничение за безопасност

        while len(all_articles) < max_articles and pages_checked < max_pages:
            print(f"📄 Обработка на страница {pages_checked + 1}...")

            # Скрапваме текущата страница
            page_articles = self._scrape_latest_news_page(page_offset)

            if not page_articles:
                print("❌ Няма повече статии")
                break

            # Филтрираме по дата
            filtered_articles = []
            for article in page_articles:
                article_date = self._extract_date_from_article_data(article)
                if article_date in target_dates or date_filter == 'all':
                    filtered_articles.append(article)
                elif date_filter != 'all' and article_date < min(target_dates):
                    # Ако статията е по-стара от най-старата target дата, спираме
                    print(f"⏹️ Достигнахме стари статии ({article_date}), спираме")
                    return all_articles[:max_articles]

            all_articles.extend(filtered_articles)
            pages_checked += 1
            page_offset += 16  # CoinDesk показва 16 статии на страница

            print(f"📊 Страница {pages_checked}: {len(filtered_articles)} релевантни статии")

            # Малка пауза между страници
            time.sleep(2)

        print(f"✅ Намерени {len(all_articles)} статии с филтър '{date_filter}'")
        return all_articles[:max_articles]

    def _get_target_dates(self, date_filter):
        """Връща списък с target дати за филтриране"""
        today = datetime.now().date()

        if date_filter == 'today':
            return [today]
        elif date_filter == 'yesterday':
            yesterday = today - timedelta(days=1)
            return [yesterday]
        elif date_filter == 'last_3_days':
            return [today - timedelta(days=i) for i in range(3)]
        elif date_filter == 'last_week':
            return [today - timedelta(days=i) for i in range(7)]
        elif isinstance(date_filter, str) and re.match(r'\d{4}-\d{2}-\d{2}', date_filter):
            # Конкретна дата в формат YYYY-MM-DD
            target_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            return [target_date]
        else:
            # 'all' или неразпознат филтър
            return []

    def _scrape_latest_news_page(self, offset=0):
        """Скрапва една страница от latest-crypto-news"""
        try:
            # URL за pagination може да използва offset параметър
            url = f"{self.latest_news_url}?offset={offset}" if offset > 0 else self.latest_news_url

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Търсим статии - обикновено са в article elements или специфични containers
            articles = []

            # Стратегия 1: Търсим article elements
            article_elements = soup.find_all('article')
            print(f"🔍 Намерени {len(article_elements)} article elements")

            for article_elem in article_elements:
                article_data = self._extract_article_data_from_element(article_elem)
                if article_data:
                    articles.append(article_data)

            # Стратегия 2: Ако няма article elements, търсим по линкове
            if not articles:
                print("🔍 Търся статии по линкове...")
                link_elements = soup.find_all('a', href=True)
                for link in link_elements:
                    href = link['href']
                    if self._is_valid_article_url(href):
                        article_data = {
                            'url': self._make_full_url(href),
                            'title': link.get_text().strip(),
                            'href': href
                        }
                        if article_data['title'] and len(article_data['title']) > 15:
                            articles.append(article_data)

            return articles[:16]  # CoinDesk показва 16 на страница

        except Exception as e:
            print(f"❌ Грешка при scraping на страница: {e}")
            return []

    def _extract_article_data_from_element(self, article_elem):
        """Извлича данни за статия от article element"""
        try:
            # Търсим линк в article element
            link = article_elem.find('a', href=True)
            if not link:
                return None

            href = link['href']
            if not self._is_valid_article_url(href):
                return None

            # Извличаме заглавието
            title = ""
            # Търсим h1, h2, h3 в article
            for header_tag in ['h1', 'h2', 'h3']:
                header = article_elem.find(header_tag)
                if header:
                    title = header.get_text().strip()
                    break

            # Ако няма header, вземаме от link text
            if not title:
                title = link.get_text().strip()

            if not title or len(title) < 15:
                return None

            return {
                'url': self._make_full_url(href),
                'title': title,
                'href': href
            }

        except Exception as e:
            print(f"⚠️ Грешка при извличане на article data: {e}")
            return None

    def _is_valid_article_url(self, href):
        """Проверява дали URL е валиден за статия"""
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
            '/_next/', '/api/', '/search', '/privacy', '/terms'
        ]

        for pattern in exclude_patterns:
            if pattern in href:
                return False

        # Приемаме статии с дата или от news категории
        date_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',  # /2025/06/10/
            r'/2025/', r'/2024/'
        ]

        has_date = any(re.search(pattern, href) for pattern in date_patterns)

        news_categories = ['/markets/', '/policy/', '/tech/', '/business/', '/layer2/', '/web3/', '/daybook']
        has_category = any(category in href for category in news_categories)

        return has_date or has_category

    def _make_full_url(self, href):
        """Прави пълен URL от relative href"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return f"https://www.coindesk.com{href}"
        else:
            return f"https://www.coindesk.com/{href}"

    def _extract_date_from_article_data(self, article_data):
        """Извлича дата от article data"""
        url = article_data['url']

        # Опитваме да извлечем от URL
        date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if date_match:
            year, month, day = date_match.groups()
            try:
                return datetime(int(year), int(month), int(day)).date()
            except:
                pass

        # Ако няма дата в URL, приемаме че е от днеска (latest news)
        return datetime.now().date()

    def scrape_articles_smart(self, date_filter='today', limit=10, save_to_db=True):
        """
        Smart scraping с date филтриране

        date_filter:
        - 'today' - само днешни статии
        - 'yesterday' - вчерашни статии
        - '2025-06-10' - конкретна дата
        - 'last_3_days' - последните 3 дни
        """
        print(f"🎯 Smart scraping: {limit} статии с филтър '{date_filter}'")

        # Вземаме статиите с филтър
        article_links = self.get_articles_by_date_filter(date_filter, max_articles=limit * 2)

        if not article_links:
            print("❌ Не са намерени статии с този филтър")
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

        # Ограничаваме до лимита
        article_links = article_links[:limit]

        if not article_links:
            print("ℹ️ Всички статии са вече scraped")
            return []

        # Scraping на статиите
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

        print(f"\n🎉 Smart scraping завършен!")
        print(f"📊 Резултат: {successful_count} успешни, {failed_count} неуспешни статии")

        return scraped_articles

    def scrape_single_article(self, article_url):
        """Извлича съдържанието на една статия (използва същата логика като стария scraper)"""
        print(f"📄 Scraping статия: {article_url}")

        try:
            time.sleep(SCRAPING_CONFIG['delay_between_requests'])

            response = self.session.get(article_url, timeout=15)
            response.raise_for_status()

            content_text = response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content_text, 'html.parser')

            # Използваме същите методи за извличане като в стария scraper
            title = self._extract_title_improved(soup)
            content = self._extract_content_improved(soup)
            date = self._extract_date_improved(soup)
            author = self._extract_author_improved(soup)

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

            print(f"✅ Успешно извлечена статия: {title[:50]}... ({len(content)} chars)")
            return article_data

        except Exception as e:
            print(f"❌ Грешка при scraping на {article_url}: {str(e)}")
            return None

    # Същите методи за извличане на съдържание като в стария scraper
    def _extract_title_improved(self, soup):
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            text = h1.get_text().strip()
            if text and len(text) > 10:
                return text

        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
            title = re.sub(r'\s*\|\s*CoinDesk.*$', '', title)
            if title:
                return title
        return "Неизвестно заглавие"

    def _extract_content_improved(self, soup):
        print("🔍 Започвам подобрено извличане на съдържание...")

        # СТРАТЕГИЯ 1: Main containers
        main_selectors = [
            'main',
            'article',
            '[role="main"]',
            '.article-content',
            '.post-content',
            '.entry-content'
        ]

        for selector in main_selectors:
            container = soup.select_one(selector)
            if container:
                print(f"✅ Намерен main container: {selector}")
                paragraphs = container.find_all('p')
                content = self._process_paragraphs(paragraphs)
                if len(content) > 200:
                    print(f"✅ Извлечени {len(content)} chars от {selector}")
                    return content

        # СТРАТЕГИЯ 2: Всички <p> tags но с по-умна филтрация
        print("🔍 Търся всички <p> tags...")
        all_paragraphs = soup.find_all('p')
        print(f"📊 Намерени {len(all_paragraphs)} общо <p> tags")

        if all_paragraphs:
            content = self._process_paragraphs(all_paragraphs)
            if len(content) > 100:
                print(f"✅ Извлечени {len(content)} chars от всички <p> tags")
                return content

        # СТРАТЕГИЯ 3: Div containers с текст
        print("🔍 Търся div containers с текст...")
        text_divs = soup.find_all('div')
        meaningful_text = []

        for div in text_divs:
            # Вземаме само direct text, не nested elements
            direct_text = div.get_text().strip()
            if 50 < len(direct_text) < 1000:  # Разумна дължина
                meaningful_text.append(direct_text)

        if meaningful_text:
            content = '\n\n'.join(meaningful_text[:10])  # Вземаме първите 10
            if len(content) > 100:
                print(f"✅ Извлечени {len(content)} chars от div containers")
                return content

        # СТРАТЕГИЯ 4: Fallback - всичко в body
        print("🔍 Fallback: Вземам всичко от body...")
        body = soup.find('body')
        if body:
            # Премахваме script и style tags
            for script in body(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            body_text = body.get_text()
            # Почистваме и вземаме разумна част
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            content = '\n'.join(lines[:50])  # Първите 50 реда

            if len(content) > 100:
                print(f"✅ Fallback извлечени {len(content)} chars от body")
                return content

        print("❌ Не успях да извлека съдържание")
        return "Съдържанието не може да бъде извлечено"

    def _process_paragraphs(self, paragraphs):
        meaningful_paragraphs = []
        for p in paragraphs:
            text = p.get_text().strip()
            if self._is_meaningful_paragraph(text):
                meaningful_paragraphs.append(text)
        return '\n\n'.join(meaningful_paragraphs)

    def _is_meaningful_paragraph(self, text):
        """Проверява дали параграфа е смислен"""
        if len(text) < 20:  # Твърде кратък
            return False

        # Изключваме нежелани фрази
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

        # Проверяваме за нормални изречения
        if text.count('.') < 1:  # Няма изречения
            return False

        return True

    def _extract_date_improved(self, soup):
        published_meta = soup.find('meta', property='article:published_time')
        if published_meta and published_meta.get('content'):
            try:
                date_str = published_meta['content']
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%Y-%m-%d')
            except:
                pass
        return datetime.now().strftime('%Y-%m-%d')

    def _extract_author_improved(self, soup):
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            return author_meta['content'].strip()
        return "Неизвестен автор"

    def get_scraping_status_by_date(self, date_str):
        """Показва статус на scraping за дадена дата"""
        if not self.db:
            return {'error': 'Database не е активна'}

        try:
            conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            # Статии от тази дата
            cursor.execute("""
                SELECT COUNT(*) FROM articles 
                WHERE url LIKE ? OR published_date = ?
            """, (f'%{date_str.replace("-", "/")}%', date_str))

            scraped_count = cursor.fetchone()[0]

            # Намираме потенциални статии от latest news
            potential_articles = self.get_articles_by_date_filter(date_str, max_articles=50)
            potential_count = len(potential_articles)

            new_count = 0
            for article in potential_articles:
                cursor.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (article['url'],))
                if not cursor.fetchone():
                    new_count += 1

            conn.close()

            return {
                'date': date_str,
                'scraped_articles': scraped_count,
                'potential_articles': potential_count,
                'new_to_scrape': new_count,
                'completion_rate': f"{(scraped_count / potential_count * 100):.1f}%" if potential_count > 0 else "N/A"
            }

        except Exception as e:
            return {'error': str(e)}


# Тестови функции
def test_latest_news_scraper():
    """Тества новия latest news scraper"""
    print("=== ТЕСТ НА LATEST NEWS SCRAPER ===")

    scraper = CoinDeskLatestNewsScraper(use_database=False)

    # Тест 1: Днешни статии
    print("\n1. Тест: Днешни статии")
    today_articles = scraper.get_articles_by_date_filter('today', max_articles=10)
    print(f"📊 Намерени {len(today_articles)} днешни статии")

    for i, article in enumerate(today_articles[:3], 1):
        print(f"   {i}. {article['title'][:60]}...")

    # Тест 2: Smart scraping
    print("\n2. Тест: Smart scraping на 3 статии")
    scraped = scraper.scrape_articles_smart('today', limit=3, save_to_db=False)
    print(f"📊 Успешно scraped: {len(scraped)} статии")

    return len(scraped) > 0


if __name__ == "__main__":
    success = test_latest_news_scraper()
    if success:
        print("\n✅ Latest News Scraper работи отлично!")
    else:
        print("\n❌ Има проблеми с Latest News Scraper")
