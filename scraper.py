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
from postgres_database import PostgreSQLDatabaseManager


class CoinDeskScraper:
    def __init__(self, use_database=True):
        print("🚀 Initializing CoinDesk Scraper...")
        self.session = requests.Session()

        # Use simpler headers
        simple_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(simple_headers)
        self.scraped_urls = set()

        # Database integration
        self.use_database = use_database
        if use_database:
            self.db = PostgreSQLDatabaseManager()
        else:
            self.db = None

        print("✅ Scraper ready!")

    def get_article_links(self):
        """Finds all links to articles from the main page"""
        print("🔍 Looking for articles on the main page...")

        try:
            response = self.session.get(
                COINDESK_MAIN_PAGE,
                timeout=SCRAPING_CONFIG['request_timeout']
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for all <a> tags with href
            article_links = []
            all_links = soup.find_all('a', href=True)

            for link in all_links:
                href = link['href']

                # Make full URL
                if href.startswith('/'):
                    full_url = f"https://www.coindesk.com{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                # Improved URL validation
                if self._is_valid_article_url_improved(href):
                    title = self._extract_link_title(link)
                    if title and len(title) > 15:
                        article_links.append({
                            'url': full_url,
                            'title': title,
                            'href': href
                        })

            # Remove duplicate URLs
            unique_articles = []
            seen_urls = set()
            for article in article_links:
                if article['url'] not in seen_urls:
                    unique_articles.append(article)
                    seen_urls.add(article['url'])

            print(f"📰 Found {len(unique_articles)} unique articles")

            # DEBUG information
            print("🔍 First 5 articles for verification:")
            for i, article in enumerate(unique_articles[:5], 1):
                print(f"  {i}. {article['title'][:60]}...")

            return unique_articles

        except Exception as e:
            print(f"❌ Error extracting links: {str(e)}")
            return []

    def _is_valid_article_url_improved(self, href):
        """Improved logic for validating article URLs"""

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
            '/_next/', '/api/'
        ]

        for pattern in exclude_patterns:
            if pattern in href:
                return False

        # Look for articles with year in URL or categories
        date_patterns = [
            r'/\d{4}/\d{2}/\d{2}/',  # /2025/06/09/
            r'/2025/', r'/2024/'
        ]

        has_date = any(re.search(pattern, href) for pattern in date_patterns)

        news_categories = ['/markets/', '/policy/', '/tech/', '/business/', '/layer2/', '/web3/']
        has_category = any(category in href for category in news_categories)

        return has_date or has_category

    def _extract_link_title(self, link):
        """Extracts title from link element"""
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
        """Extracts content of one article"""
        print(f"📄 Scraping article: {article_url}")

        try:
            time.sleep(SCRAPING_CONFIG['delay_between_requests'])

            response = self.session.get(
                article_url,
                timeout=SCRAPING_CONFIG['request_timeout']
            )
            response.raise_for_status()

            content_text = response.content.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(content_text, 'html.parser')

            # Extract data
            title = self._extract_title_improved(soup)
            content = self._extract_content_improved(soup)
            date = self._extract_date_improved(soup)
            author = self._extract_author_improved(soup)

            # Check length
            if len(content) < SCRAPING_CONFIG['min_article_length']:
                print(f"⚠️  Article too short ({len(content)} chars)")
                print(f"🔍 DEBUG first 200 chars: {content[:200]}")
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

    def _extract_title_improved(self, soup):
        """Improved title extraction"""

        # h1 tag first
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

        return "Unknown title"

    def _extract_content_improved(self, soup):
        """Improved content extraction"""

        print("🔍 Starting improved content extraction...")

        # Strategy 1: Main containers
        main_selectors = ['main', 'article', '[role="main"]', '.article-content', '.post-content']

        for selector in main_selectors:
            container = soup.select_one(selector)
            if container:
                print(f"✅ Found main container: {selector}")
                paragraphs = container.find_all('p')
                content = self._process_paragraphs(paragraphs)
                if len(content) > 200:
                    print(f"✅ Extracted {len(content)} chars from {selector}")
                    return content

        # Strategy 2: All <p> tags
        print("🔍 Looking for all <p> tags...")
        all_paragraphs = soup.find_all('p')
        print(f"📊 Found {len(all_paragraphs)} total <p> tags")

        if all_paragraphs:
            content = self._process_paragraphs(all_paragraphs)
            if len(content) > 100:
                print(f"✅ Extracted {len(content)} chars from all <p> tags")
                return content

        # Strategy 3: Div containers
        print("🔍 Looking for div containers with text...")
        text_divs = soup.find_all('div')
        meaningful_text = []

        for div in text_divs:
            direct_text = div.get_text().strip()
            if 50 < len(direct_text) < 1000:
                meaningful_text.append(direct_text)

        if meaningful_text:
            content = '\n\n'.join(meaningful_text[:10])
            if len(content) > 100:
                print(f"✅ Extracted {len(content)} chars from div containers")
                return content

        # Strategy 4: Fallback
        print("🔍 Fallback: Taking everything from body...")
        body = soup.find('body')
        if body:
            for script in body(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            body_text = body.get_text()
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            content = '\n'.join(lines[:50])

            if len(content) > 100:
                print(f"✅ Fallback extracted {len(content)} chars from body")
                return content

        print("❌ Failed to extract content")
        return "Content cannot be extracted"

    def _process_paragraphs(self, paragraphs):
        """Processes list of <p> tags"""
        meaningful_paragraphs = []

        for p in paragraphs:
            text = p.get_text().strip()
            if self._is_meaningful_paragraph(text):
                meaningful_paragraphs.append(text)

        return '\n\n'.join(meaningful_paragraphs)

    def _is_meaningful_paragraph(self, text):
        """Checks if paragraph is meaningful"""
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
        """Improved date extraction"""

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

        # From URL
        canonical = soup.find('link', rel='canonical')
        if canonical:
            url_date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', canonical.get('href', ''))
            if url_date_match:
                year, month, day = url_date_match.groups()
                return f"{year}-{month}-{day}"

        return datetime.now().strftime('%Y-%m-%d')

    def _extract_author_improved(self, soup):
        """Improved author extraction"""

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

        return "Unknown author"

    def scrape_multiple_articles(self, max_articles=None, save_to_db=True):
        """Scrapes multiple articles"""
        if max_articles is None:
            max_articles = SCRAPING_CONFIG['max_articles_per_session']

        print(f"🎯 Starting scraping of maximum {max_articles} articles...")

        # Get links
        article_links = self.get_article_links()

        if not article_links:
            print("❌ No articles found for scraping")
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

        # Limit number
        article_links = article_links[:max_articles]

        if not article_links:
            print("ℹ️ All articles already scraped")
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
                print(f"❌ Failed to extract article {i}")

            if i % 5 == 0:
                print(f"📊 Progress: {i}/{len(article_links)} articles processed")
                print(f"    ✅ Successful: {successful_count}, ❌ Failed: {failed_count}")

        print(f"\n🎉 Scraping completed!")
        print(f"📊 Final result: {successful_count} successful, {failed_count} failed articles")

        if self.db and save_to_db:
            stats = self.db.get_database_stats()
            print(
                f"📊 Database statistics: {stats['total_articles']} total articles, {stats['unprocessed_articles']} for analysis")

        return scraped_articles


def test_single_article():
    """Tests scraping of one article"""
    scraper = CoinDeskScraper(use_database=True)

    test_url = "https://www.coindesk.com/markets/2025/06/09/bitwise-proshares-file-for-etfs-tracking-soaring-circle-shares"

    print(f"\n🧪 Testing scraping of one article...")
    article = scraper.scrape_single_article(test_url)

    if article:
        print(f"\n✅ SUCCESS! Extracted article:")
        print(f"   📄 Title: {article['title']}")
        print(f"   📅 Date: {article['date']}")
        print(f"   👤 Author: {article['author']}")
        print(f"   📊 Length: {article['content_length']} characters")
        print(f"   📝 First 300 characters: {article['content'][:300]}...")

        # ADD THESE LINES:
        print(f"\n💾 Testing PostgreSQL save...")
        success = scraper.db.save_article(article)
        if success:
            print("✅ Article saved to database!")

            # Show statistics
            stats = scraper.db.get_database_stats()
            print(f"📊 Statistics: {stats}")
        else:
            print("❌ Save error")

        return True
    else:
        print("❌ Failed to extract article")
        return False


if __name__ == "__main__":
    print("=== IMPROVED COINDESK SCRAPER TEST ===")
    success = test_single_article()

    if success:
        print("\n🎉 Single article test successful!")
    else:
        print("❌ Single article test failed")
