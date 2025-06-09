# CoinDesk Scraper Configuration

# Основни URL адреси
COINDESK_BASE_URL = "https://www.coindesk.com"
COINDESK_MAIN_PAGE = "https://www.coindesk.com/"

# Headers за requests (за да изглеждаме като браузър)
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
}

# Patterns за намиране на новинарски статии
NEWS_URL_PATTERNS = [
    '/markets/',  # Пазарни новини
    '/policy/',  # Политика и регулации
    '/tech/',  # Технологични новини
    '/business/',  # Бизнес новини
    '/news/',  # Общи новини
    '/layer2/',  # Layer 2 технологии
    '/web3/',  # Web3 новини
]

# Patterns за изключване (избягваме podcast-и, newsletters, etc.)
EXCLUDE_PATTERNS = [
    '/podcasts/',
    '/newsletters/',
    '/sponsored-content/',
    '/events/',
    '/about/',
    '/careers/',
    '/advertise/',
    '#',  # Anchor links
    'mailto:',  # Email links
    'tel:',  # Phone links
]

# Настройки за scraping
SCRAPING_CONFIG = {
    'request_timeout': 15,  # Timeout за HTTP requests (секунди)
    'delay_between_requests': 2,  # Пауза между заявки (секунди)
    'max_articles_per_session': 30,  # Максимален брой статии за един session
    'max_retries': 3,  # Максимален брой опити при грешка
    'min_article_length': 100,  # Минимална дължина на статия (символи)
}

# HTML селектори за CoinDesk (ще ги тестваме и подобрим)
HTML_SELECTORS = {
    # За главната страница
    'article_links': 'a[href*="/2025/"]',  # Линкове с 2025 година

    # За отделна статия (примерни, ще ги тестваме)
    'article_title': [
        'h1[data-module="ArticleHeader"]',
        'h1.headline',
        'h1',
        '.article-title'
    ],
    'article_content': [
        'div[data-module="ArticleBody"]',
        '.article-content',
        '.post-content',
        'article .content'
    ],
    'article_date': [
        'time[datetime]',
        '.article-date',
        '.post-date',
        '[data-timestamp]'
    ],
    'article_author': [
        '.author-name',
        '.byline',
        '[data-author]'
    ]
}

# Database настройки (за по-късно)
DATABASE_CONFIG = {
    'sqlite_file': 'crypto_news.db',
    'table_name': 'articles',
}

# Logging настройки
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': 'scraper.log'
}

# Debug настройки
DEBUG_CONFIG = {
    'save_html_files': False,  # Запазва HTML файлове за debugging
    'verbose_logging': True,  # Подробно логване
    'test_mode': False,  # Test mode (ограничава заявките)
}


def get_full_url(relative_url):
    """Конвертира относителен URL в пълен URL"""
    if relative_url.startswith('http'):
        return relative_url
    elif relative_url.startswith('/'):
        return COINDESK_BASE_URL + relative_url
    else:
        return COINDESK_BASE_URL + '/' + relative_url


def is_valid_article_url(url):
    """Проверява дали URL е валиден за статия"""
    # Проверяваме дали съдържа някой от новинарските patterns
    has_news_pattern = any(pattern in url for pattern in NEWS_URL_PATTERNS)

    # Проверяваме дали НЕ съдържа изключените patterns
    has_exclude_pattern = any(pattern in url for pattern in EXCLUDE_PATTERNS)

    # Проверяваме дали съдържа актуална дата (2025)
    has_current_year = '/2025/' in url

    return has_news_pattern and not has_exclude_pattern and has_current_year


# Test функция за config
if __name__ == "__main__":
    print("=== COINDESK SCRAPER CONFIG TEST ===")

    # Тестваме URL validation
    test_urls = [
        "/markets/2025/06/09/bitwise-proshares-file-for-etfs-tracking-soaring-circle-shares",
        "/podcasts/coindesk-podcast-network",
        "/markets/2025/06/09/michael-saylors-strategy-added-1045-bitcoin-for-110m-last-week",
        "/newsletters/daybook-us",
        "/sponsored-content/bahamut-blockchain-a-new-playbook-for-validator-incentives"
    ]

    print("\n🔍 Тестване на URL validation:")
    for url in test_urls:
        full_url = get_full_url(url)
        is_valid = is_valid_article_url(url)
        status = "✅ ВАЛИДЕН" if is_valid else "❌ НЕВАЛИДЕН"
        print(f"{status} | {url}")

    print(f"\n📊 Конфигурация заредена:")
    print(f"   - Новинарски patterns: {len(NEWS_URL_PATTERNS)}")
    print(f"   - Exclude patterns: {len(EXCLUDE_PATTERNS)}")
    print(f"   - Max статии/session: {SCRAPING_CONFIG['max_articles_per_session']}")
    print(f"   - Timeout: {SCRAPING_CONFIG['request_timeout']}s")
