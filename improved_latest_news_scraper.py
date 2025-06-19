import sqlite3
import requests
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

def _extract_content_improved(self, soup):
    """RADICALLY IMPROVED content extraction for CoinDesk"""

    print("🔍 Starting FIXED content extraction...")

    # STRATEGY 1: CoinDesk-specific patterns
    print("🎯 STRATEGY 1: CoinDesk patterns...")

    # Find "What to know:" marker and take the container
    what_to_know = soup.find(text=lambda text: text and 'What to know:' in text)
    if what_to_know:
        print("✅ Found 'What to know:' marker")

        # Find parent container
        current = what_to_know.parent
        while current and current.name not in ['main', 'article', 'div', 'section']:
            current = current.parent

        if current:
            # Take all <p> in this container
            container_paragraphs = current.find_all('p')
            meaningful_text = []

            for p in container_paragraphs:
                text = p.get_text().strip()
                if (text and
                        len(text) > 30 and
                        'See all newsletters' not in text and
                        'What to know:' not in text and
                        not text.startswith('[')):  # Remove price links
                    meaningful_text.append(text)

            if meaningful_text:
                content = '\n\n'.join(meaningful_text)
                print(f"✅ CoinDesk pattern extraction: {len(content)} chars")
                if len(content) > 200:
                    return content

    # STRATEGY 2: Look for main content container
    print("🎯 STRATEGY 2: Main containers...")
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
            print(f"✅ Found container: {selector}")
            paragraphs = container.find_all('p')
            content = self._process_paragraphs_fixed(paragraphs)
            if len(content) > 200:
                print(f"✅ Main container extraction: {len(content)} chars")
                return content

    # STRATEGY 3: All <p> tags with smarter filtering
    print("🎯 STRATEGY 3: All <p> tags...")
    all_paragraphs = soup.find_all('p')
    print(f"📊 Found {len(all_paragraphs)} total <p> tags")

    if all_paragraphs:
        content = self._process_paragraphs_fixed(all_paragraphs)
        if len(content) > 100:
            print(f"✅ All paragraphs extraction: {len(content)} chars")
            return content

    # STRATEGY 4: Look for text in div elements
    print("🎯 STRATEGY 4: Div text extraction...")

    # Find all divs with text
    text_divs = soup.find_all('div')
    meaningful_texts = []

    for div in text_divs:
        # Get direct text from div
        direct_text = div.get_text(separator=' ', strip=True)

        # Filter by length and content
        if (50 < len(direct_text) < 2000 and
                '.' in direct_text and  # Must have sentences
                not direct_text.startswith('[') and  # Doesn't start with [price links]
                'See all newsletters' not in direct_text):
            meaningful_texts.append(direct_text)

    if meaningful_texts:
        # Take the longest and most meaningful texts
        meaningful_texts.sort(key=len, reverse=True)
        selected_texts = meaningful_texts[:5]  # First 5 longest

        content = '\n\n'.join(selected_texts)
        if len(content) > 200:
            print(f"✅ Div text extraction: {len(content)} chars")
            return content

    # STRATEGY 5: Fallback - body text
    print("🎯 STRATEGY 5: Body fallback...")
    body = soup.find('body')
    if body:
        # Remove unwanted elements
        for unwanted in body(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            unwanted.decompose()

        body_text = body.get_text(separator=' ', strip=True)

        # Split by sentences and take meaningful ones
        sentences = [s.strip() for s in body_text.split('.') if s.strip()]
        meaningful_sentences = []

        for sentence in sentences:
            if (20 < len(sentence) < 500 and
                    not sentence.startswith('[') and
                    'See all newsletters' not in sentence and
                    'Sign up' not in sentence):
                meaningful_sentences.append(sentence)

        if meaningful_sentences:
            # Take first 20 sentences
            content = '. '.join(meaningful_sentences[:20]) + '.'
            if len(content) > 200:
                print(f"✅ Body fallback extraction: {len(content)} chars")
                return content

    print("❌ All strategies unsuccessful")
    return "Content cannot be extracted"


def _process_paragraphs_fixed(self, paragraphs):
    """Improved paragraph processing"""
    meaningful_paragraphs = []

    for p in paragraphs:
        text = p.get_text().strip()

        # Stricter filtering
        if self._is_meaningful_paragraph_fixed(text):
            meaningful_paragraphs.append(text)

    return '\n\n'.join(meaningful_paragraphs)


def _is_meaningful_paragraph_fixed(self, text):
    """Improved check for meaningful paragraphs"""

    # Basic checks
    if len(text) < 20:
        return False

    # Exclude price links and navigation
    if text.startswith('[') and text.endswith(']'):
        return False

    # Exclude unwanted phrases
    exclude_phrases = [
        'Sign up', 'Subscribe', 'Newsletter', 'See all newsletters',
        'Don\'t miss', 'By signing up', 'privacy policy', 'terms of use',
        'Cookie', 'Advertisement', 'Sponsored', 'Follow us', 'Share this',
        'Read more', 'Click here', 'Download', 'Watch', 'Listen',
        'Back to menu', 'What to know:', 'See more'
    ]


def _is_meaningful_paragraph_fixed(self, text):
    """Improved check for meaningful paragraphs"""

    # Basic checks
    if len(text) < 20:
        return False

    # Exclude price links and navigation
    if text.startswith('[') and text.endswith(']'):
        return False

    # Exclude unwanted phrases
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

    # Must have at least one sentence
    if text.count('.') < 1 and text.count('!') < 1 and text.count('?') < 1:
        return False

    # Shouldn't be just numbers or short phrases
    words = text.split()
    if len(words) < 5:
        return False

    return True


class CoinDeskLatestNewsScraper:
    def __init__(self, use_database=True):
        print("🚀 Initializing CoinDesk Latest News Scraper...")
        self.session = requests.Session()

        # Headers
        simple_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(simple_headers)

        # URL for latest news
        self.latest_news_url = "https://www.coindesk.com/latest-crypto-news"

        # Database integration
        self.use_database = use_database
        if use_database:
            self.db = DatabaseManager()
        else:
            self.db = None

        print("✅ Latest News Scraper ready!")

    def get_articles_by_date_filter(self, date_filter='today', max_articles=50):
        """
        Gets articles from latest-crypto-news with date filter

        date_filter can be:
        - 'today' - only today's articles
        - 'yesterday' - yesterday's articles
        - '2025-06-10' - specific date
        - 'last_3_days' - last 3 days
        - 'all' - all (up to max_articles)
        """
        print(f"🔍 Searching for articles with filter: {date_filter}")

        # Determine target dates
        target_dates = self._get_target_dates(date_filter)
        print(f"📅 Target dates: {target_dates}")

        # Start scraping pages
        all_articles = []
        page_offset = 0
        pages_checked = 0
        max_pages = 10  # Safety limit

        while len(all_articles) < max_articles and pages_checked < max_pages:
            print(f"📄 Processing page {pages_checked + 1}...")

            # Scrape current page
            page_articles = self._scrape_latest_news_page(page_offset)

            if not page_articles:
                print("❌ No more articles")
                break

            # Filter by date
            filtered_articles = []
            for article in page_articles:
                article_date = self._extract_date_from_article_data(article)
                if article_date in target_dates or date_filter == 'all':
                    filtered_articles.append(article)
                elif date_filter != 'all' and article_date < min(target_dates):
                    # If article is older than oldest target date, stop
                    print(f"⏹️ Reached old articles ({article_date}), stopping")
                    return all_articles[:max_articles]

            all_articles.extend(filtered_articles)
            pages_checked += 1
            page_offset += 16  # CoinDesk shows 16 articles per page

            print(f"📊 Page {pages_checked}: {len(filtered_articles)} relevant articles")

            # Small pause between pages
            time.sleep(2)

        print(f"✅ Found {len(all_articles)} articles with filter '{date_filter}'")
        return all_articles[:max_articles]

    def _get_target_dates(self, date_filter):
        """Returns list of target dates for filtering"""
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
            # Specific date in YYYY-MM-DD format
            target_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            return [target_date]
        else:
            # 'all' or unrecognized filter
            return []

    def _scrape_latest_news_page(self, offset=0):
        """Scrapes one page from latest-crypto-news"""
        try:
            # URL for pagination might use offset parameter
            url = f"{self.latest_news_url}?offset={offset}" if offset > 0 else self.latest_news_url

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for articles - usually in article elements or specific containers
            articles = []

            # Strategy 1: Look for article elements
            article_elements = soup.find_all('article')
            print(f"🔍 Found {len(article_elements)} article elements")

            for article_elem in article_elements:
                article_data = self._extract_article_data_from_element(article_elem)
                if article_data:
                    articles.append(article_data)

            # Strategy 2: If no article elements, look for links
            if not articles:
                print("🔍 Looking for articles by links...")
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

            return articles[:16]  # CoinDesk shows 16 per page

        except Exception as e:
            print(f"❌ Error scraping page: {e}")
            return []

    def _extract_article_data_from_element(self, article_elem):
        """Extracts article data from article element"""
        try:
            # Look for link in article element
            link = article_elem.find('a', href=True)
            if not link:
                return None

            href = link['href']
            if not self._is_valid_article_url(href):
                return None

            # Extract title
            title = ""
            # Look for h1, h2, h3 in article
            for header_tag in ['h1', 'h2', 'h3']:
                header = article_elem.find(header_tag)
                if header:
                    title = header.get_text().strip()
                    break

            # If no header, take from link text
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
            print(f"⚠️ Error extracting article data: {e}")
            return None

    def _is_valid_article_url(self, href):
        """Checks if URL is valid for article"""
        if not href or href in ['#', '/', '']:
            return False

        if href.startswith('http') and 'coindesk.com' not in href:
            return False

        if href.startswith('#') or href.startswith('mailto:') or href.startswith('tel:'):
            return False

        # Exclude system pages
        exclude_patterns = [
            '/newsletters/', '/podcasts/', '/events/', '/about/', '/careers/',
            '/advertise/', '/price/', '/author/', '/tag/', '/sponsored-content/',
            '/_next/', '/api/', '/search', '/privacy', '/terms'
        ]

        for pattern in exclude_patterns:
            if pattern in href:
                return False

        # Accept articles with date or from news categories
        date_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',  # /2025/06/10/
            r'/2025/', r'/2024/'
        ]

        has_date = any(re.search(pattern, href) for pattern in date_patterns)

        news_categories = ['/markets/', '/policy/', '/tech/', '/business/', '/layer2/', '/web3/', '/daybook']
        has_category = any(category in href for category in news_categories)

        return has_date or has_category

    def _make_full_url(self, href):
        """Makes full URL from relative href"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return f"https://www.coindesk.com{href}"
        else:
            return f"https://www.coindesk.com/{href}"

    def _extract_date_from_article_data(self, article_data):
        """Extracts date from article data"""
        url = article_data['url']

        # Try to extract from URL
        date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if date_match:
            year, month, day = date_match.groups()
            try:
                return datetime(int(year), int(month), int(day)).date()
            except:
                pass

        # If no date in URL, assume it's from today (latest news)
        return datetime.now().date()

    def scrape_articles_smart(self, date_filter='today', limit=10, save_to_db=True):
        """
        Smart scraping with date filtering

        date_filter:
        - 'today' - only today's articles
        - 'yesterday' - yesterday's articles
        - '2025-06-10' - specific date
        - 'last_3_days' - last 3 days
        """
        print(f"🎯 Smart scraping: {limit} articles with filter '{date_filter}'")

        # Get articles with filter
        article_links = self.get_articles_by_date_filter(date_filter, max_articles=limit * 2)

        if not article_links:
            print("❌ No articles found with this filter")
            return []

        # Database filtering
        if self.db and save_to_db:
            print("🔍 Checking for duplicate URLs...")
            new_article_links = []
            skipped_count = 0

            for link_info in article_links:
                url = link_info['url']
                if not self.db.is_url_scraped_before(url):
                    new_article_links.append(link_info)
                else:
                    skipped_count += 1
                    self.db.record_scraped_url(url)

            print(f"📊 {len(new_article_links)} new articles, {skipped_count} already scraped")
            article_links = new_article_links

        # Limit to specified number
        article_links = article_links[:limit]

        if not article_links:
            print("ℹ️ All articles already scraped")
            return []

        # Scraping articles
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

        print(f"\n🎉 Smart scraping completed!")
        print(f"📊 Result: {successful_count} successful, {failed_count} failed articles")

        return scraped_articles

    def scrape_single_article(self, article_url):
        """Extracts content of one article (uses same logic as old scraper)"""
        print(f"📄 Scraping article: {article_url}")

        try:
            time.sleep(SCRAPING_CONFIG['delay_between_requests'])

            response = self.session.get(article_url, timeout=15)
            response.raise_for_status()

            content_text = response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content_text, 'html.parser')

            # Use same extraction methods as old scraper
            title = self._extract_title_improved(soup)
            content = self._extract_content_improved(soup)
            date = self._extract_date_improved(soup)
            author = self._extract_author_improved(soup)

            if len(content) < SCRAPING_CONFIG['min_article_length']:
                print(f"⚠️  Article too short ({len(content)} chars)")
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

            print(f"✅ Successfully extracted article: {title[:50]}... ({len(content)} chars)")
            return article_data

        except Exception as e:
            print(f"❌ Error scraping {article_url}: {str(e)}")
            return None

    # Same content extraction methods as old scraper
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
        return "Unknown title"

    def _extract_content_improved(self, soup):
        print("🔍 Starting improved content extraction...")

        # STRATEGY 1: Main containers
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
                print(f"✅ Found main container: {selector}")
                paragraphs = container.find_all('p')
                content = self._process_paragraphs(paragraphs)
                if len(content) > 200:
                    print(f"✅ Extracted {len(content)} chars from {selector}")
                    return content

        # STRATEGY 2: All <p> tags but with smarter filtering
        print("🔍 Looking for all <p> tags...")
        all_paragraphs = soup.find_all('p')
        print(f"📊 Found {len(all_paragraphs)} total <p> tags")

        if all_paragraphs:
            content = self._process_paragraphs(all_paragraphs)
            if len(content) > 100:
                print(f"✅ Extracted {len(content)} chars from all <p> tags")
                return content

        # STRATEGY 3: Div containers with text
        print("🔍 Looking for div containers with text...")
        text_divs = soup.find_all('div')
        meaningful_text = []

        for div in text_divs:
            # Take only direct text, not nested elements
            direct_text = div.get_text().strip()
            if 50 < len(direct_text) < 1000:  # Reasonable length
                meaningful_text.append(direct_text)

        if meaningful_text:
            content = '\n\n'.join(meaningful_text[:10])  # Take first 10
            if len(content) > 100:
                print(f"✅ Extracted {len(content)} chars from div containers")
                return content

        # STRATEGY 4: Fallback - everything from body
        print("🔍 Fallback: Taking everything from body...")
        body = soup.find('body')
        if body:
            # Remove script and style tags
            for script in body(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            body_text = body.get_text()
            # Clean and take reasonable part
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            content = '\n'.join(lines[:50])  # First 50 lines

            if len(content) > 100:
                print(f"✅ Fallback extracted {len(content)} chars from body")
                return content

        print("❌ Failed to extract content")
        return "Content cannot be extracted"

    def _process_paragraphs(self, paragraphs):
        meaningful_paragraphs = []
        for p in paragraphs:
            text = p.get_text().strip()
            if self._is_meaningful_paragraph(text):
                meaningful_paragraphs.append(text)
        return '\n\n'.join(meaningful_paragraphs)

    def _is_meaningful_paragraph(self, text):
        """Checks if paragraph is meaningful"""
        if len(text) < 20:  # Too short
            return False

        # Exclude unwanted phrases
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

        # Check for normal sentences
        if text.count('.') < 1:  # No sentences
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
        return "Unknown author"

    def get_scraping_status_by_date(self, date_str):
        """Shows scraping status for given date"""
        if not self.db:
            return {'error': 'Database not active'}

        try:
            conn = self.db.get_connection() if hasattr(self.db, 'get_connection') else sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()

            # Articles from this date
            cursor.execute("""
                SELECT COUNT(*) FROM articles 
                WHERE url LIKE ? OR published_date = ?
            """, (f'%{date_str.replace("-", "/")}%', date_str))

            scraped_count = cursor.fetchone()[0]

            # Find potential articles from latest news
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


# Test functions
def test_latest_news_scraper():
    """Tests the new latest news scraper"""
    print("=== LATEST NEWS SCRAPER TEST ===")

    scraper = CoinDeskLatestNewsScraper(use_database=False)

    # Test 1: Today's articles
    print("\n1. Test: Today's articles")
    today_articles = scraper.get_articles_by_date_filter('today', max_articles=10)
    print(f"📊 Found {len(today_articles)} today's articles")

    for i, article in enumerate(today_articles[:3], 1):
        print(f"   {i}. {article['title'][:60]}...")

    # Test 2: Smart scraping
    print("\n2. Test: Smart scraping of 3 articles")
    scraped = scraper.scrape_articles_smart('today', limit=3, save_to_db=False)
    print(f"📊 Successfully scraped: {len(scraped)} articles")

    return len(scraped) > 0


if __name__ == "__main__":
    success = test_latest_news_scraper()
    if success:
        print("\n✅ Latest News Scraper works great!")
    else:
        print("\n❌ There are issues with Latest News Scraper")
