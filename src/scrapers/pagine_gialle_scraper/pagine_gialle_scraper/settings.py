import os
import random
from fake_useragent import UserAgent

# Percorso alla root del progetto (due livelli sopra questo file)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
os.makedirs(CONFIG_DIR, exist_ok=True)

BOT_NAME = 'pagine_gialle_scraper'

SPIDER_MODULES = [
    'pagine_gialle_scraper.spiders'
]
NEWSPIDER_MODULE = 'pagine_gialle_scraper.spiders'

# User-Agent dinamico
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_2 like Mac OS X) AppleWebKit/537.36 (KHTML, like Gecko) Version/15.2 Mobile/15E148 Safari/537.36",
    "Mozilla/5.0 (Android 11; Mobile; rv:97.0) Gecko/97.0 Firefox/97.0"
]
USER_AGENT = random.choice(USER_AGENTS)

# Throttling e concorrenza
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 3
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 1
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = True

ROBOTSTXT_OBEY = False

# Middlewares
SPIDER_MIDDLEWARES = {
    'pagine_gialle_scraper.middlewares.PagineGialleMiddleware': 543,
}
DOWNLOADER_MIDDLEWARES = {
    'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
    'pagine_gialle_scraper.middlewares.PagineGialleDownloaderMiddleware': 543,
}

# Proxy settings: punta ora a config/proxies.txt in root
ROTATING_PROXY_LIST_PATH = os.path.join(CONFIG_DIR, 'proxies.txt')
ROTATING_PROXY_CLOSE_SPIDER = False

# Pipelines
ITEM_PIPELINES = {
    'pagine_gialle_scraper.pipelines.PagineGiallePipeline': 300,
} 

# Impostazioni future-proof
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
FEED_EXPORT_ENCODING = 'utf-8'