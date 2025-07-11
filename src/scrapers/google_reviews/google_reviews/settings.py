import os
from webdriver_manager.chrome import ChromeDriverManager

# CORREZIONE: Determina la root del progetto in modo più robusto
def get_project_root():
    """
    Determina la root del progetto con la stessa logica dello spider
    per garantire coerenza tra settings e spider.
    """
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    
    # Cerca partendo dalla directory del file settings
    search_dir = current_dir
    max_levels = 10
    
    for i in range(max_levels):
        # Verifica se questa directory è la root del progetto
        if _is_valid_project_root(search_dir):
            return search_dir
        
        # Risali di un livello
        parent_dir = os.path.dirname(search_dir)
        if parent_dir == search_dir:  # Siamo arrivati alla root del filesystem
            break
        search_dir = parent_dir
    
    # Fallback: usa il metodo originale
    return os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))

def _is_valid_project_root(path):
    """
    Verifica se una directory è una valida root del progetto.
    """
    if not os.path.exists(path):
        return False
        
    # Marker primari (DEVONO esistere)
    data_dir = os.path.join(path, "data")
    src_dir = os.path.join(path, "src")
    
    # Verifica marker primari
    primary_score = 0
    if os.path.exists(data_dir):
        primary_score += 2
    if os.path.exists(src_dir):
        primary_score += 2
        
    return primary_score >= 3  # Almeno data + src

# Determina PROJECT_ROOT usando la stessa logica dello spider
PROJECT_ROOT = get_project_root()
print(f"[SETTINGS] PROJECT_ROOT determinato: {PROJECT_ROOT}")

# Verifica che la root sia corretta
if not _is_valid_project_root(PROJECT_ROOT):
    print(f"[WARNING] PROJECT_ROOT potrebbe non essere corretto: {PROJECT_ROOT}")
    print("Verifica che esistano le directory 'data' e 'src'")

CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
os.makedirs(CONFIG_DIR, exist_ok=True)

# Esporta PROJECT_ROOT per lo spider
os.environ['PROJECT_ROOT'] = PROJECT_ROOT

BOT_NAME = 'google_reviews'
SPIDER_MODULES = ['google_reviews.spiders']
NEWSPIDER_MODULE = 'google_reviews.spiders'

# Aggiungi delay per evitare blocchi
DOWNLOAD_DELAY = 0.2
RANDOMIZE_DOWNLOAD_DELAY = True

# Riduce la concorrenza per evitare troppi browser aperti
CONCURRENT_REQUESTS = 10
CONCURRENT_REQUESTS_PER_DOMAIN = 7
CONCURRENT_REQUESTS_PER_IP = 8  # Aumentato da 1 a 16

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.1  # Ridotto da 2 a 0.1
AUTOTHROTTLE_MAX_DELAY = 2  # Ridotto da 10 a 2
AUTOTHROTTLE_TARGET_CONCURRENCY = 8.0  # Aumentato da 1.0 a 8.0
AUTOTHROTTLE_DEBUG = False  # Disabilitato per performance

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Usa il middleware personalizzato anziché quello di scrapy_selenium
DOWNLOADER_MIDDLEWARES = {
    'google_reviews.middlewares.CustomSeleniumMiddleware': 800,
    'scrapy_selenium.SeleniumMiddleware': None,  # Disabilitato
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
}

SELENIUM_DRIVER_NAME = 'chrome'
SELENIUM_DRIVER_EXECUTABLE_PATH = None  # webdriver_manager se lo scarica da sé

SELENIUM_DRIVER_ARGUMENTS = [
   '--headless=new',  # Usa la nuova versione headless (più veloce)
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-blink-features=AutomationControlled',
    '--disable-extensions',
    '--disable-plugins',
    '--disable-images',  # IMPORTANTE: Non caricare immagini
    '--window-size=1280,720',  # Dimensione più piccola
    '--memory-pressure-off',
    '--max_old_space_size=4096',
    '--disable-background-timer-throttling',
    '--disable-renderer-backgrounding',
    '--disable-backgrounding-occluded-windows',
    '--disable-features=TranslateUI',
    '--disable-ipc-flooding-protection',
    '--disable-default-apps',
    '--disable-sync',
    '--disable-background-networking',
    '--aggressive-cache-discard',
    '--disable-features=VizDisplayCompositor'
]

# Aumenta timeout per consentire caricamento pagine
DOWNLOAD_TIMEOUT = 15

# Abilita i retry per maggiore resilienza
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

REACTOR_THREADPOOL_MAXSIZE = 20
ASYNCIO_EVENT_LOOP = 'asyncio.SelectorEventLoop'
# CORREZIONE: Feeds con path validation
def get_feeds_config():
    """
    Configura i feeds con validazione del percorso
    """
    feeds_dir = os.path.join(PROJECT_ROOT, 'data', 'raw', 'raw_post_google_reviews')
    
    # Crea la directory base se non esiste
    os.makedirs(feeds_dir, exist_ok=True)
    
    feed_path = os.path.join(feeds_dir, '%(region)s', '%(category)s', '%(region)s_%(category)s_raw.json')
    
    print(f"[SETTINGS] Feed path configurato: {feed_path}")
    
    return {
        feed_path: {
            'format': 'json',
            'encoding': 'utf-8',
            'overwrite': True,
            'batch_item_export_timeout': 1.0,  # flush su disco ogni secondo
        }
    }

# Configura FEEDS
FEEDS = get_feeds_config()

# AGGIUNTA: Esporta PROJECT_ROOT come setting per gli spider
PROJECT_ROOT_SETTING = PROJECT_ROOT

# AGGIUNTA: Logging migliorato per debug path
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(PROJECT_ROOT, 'logs', 'scrapy.log')

# Crea directory logs se non esiste
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# AGGIUNTA: Settings personalizzati per debug
CUSTOM_SETTINGS = {
    'PROJECT_ROOT': PROJECT_ROOT,
    'DEBUG_PATH_INFO': True,
}

print(f"[SETTINGS] Configurazione completata:")
print(f"  - PROJECT_ROOT: {PROJECT_ROOT}")
print(f"  - CONFIG_DIR: {CONFIG_DIR}")
print(f"  - LOG_FILE: {LOG_FILE}")
print(f"  - Feeds directory: {os.path.dirname(list(FEEDS.keys())[0])}")