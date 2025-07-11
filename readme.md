# Documentazione Dettagliata Sistema di Scraping e Pipeline di Elaborazione

## Panoramica del Progetto

Questo progetto implementa un sistema completo di web scraping progettato per estrarre e processare dati strutturati da due importanti fonti:

1. **Pagine Gialle**: estrae informazioni dettagliate sulle attività commerciali in Italia, categorizzate per regione e tipologia.
2. **Google Maps/Reviews**: arricchisce i dati delle attività con valutazioni e recensioni da Google Maps.

L'architettura è basata sul framework Scrapy con estensioni personalizzate per gestire il rendering JavaScript tramite Selenium per i contenuti dinamici di Google Maps, implementando una pipeline di elaborazione end-to-end.

## Architettura del Sistema

Il sistema è organizzato con una chiara separazione delle componenti:

```
/
├── src/
│   ├── scrapers/
│   │   ├── pagine_gialle_scraper/    # Scraper per Pagine Gialle
│   │   └── google_reviews/           # Scraper per Google Maps/Reviews
│   ├── data_processing/              # Elaborazione dati
│   │   ├── data_cleaning_pagine_gialle/
│   │   └── data_cleaning_reviews/
│   └── pipeline/                     # Orchestrazione del flusso di lavoro
│       └── pipeline_executor.py
├── data/
│   ├── raw/                          # Dati grezzi
│   │   ├── raw_post_pagine_gialle/
│   │   └── raw_post_google_reviews/
│   └── processed_data/               # Dati elaborati
│       ├── clean_post_pagine_gialle/
│       └── clean_post_google_reviews/
├── config/                           # File di configurazione
│   └── regioni_paesi.json
├── logs/                             # Log e report
│   └── pipeline_reports/
└── temp/                             # File temporanei
```

## Pipeline Executor

La classe `PipelineExecutor` coordina l'intera pipeline di elaborazione, garantendo un flusso di lavoro coerente e gestendo gli errori in ogni fase.

### Caratteristiche Principali

- **Modularità**: Suddivide il processo in passaggi distinti e ben definiti
- **Gestione degli Errori**: Log dettagliati e recupero da errori
- **Configurabilità**: Parametrizzato per regione e categoria
- **Reporting**: Genera report completi di esecuzione

### Flusso di Esecuzione

1. **Inizializzazione e Verifica**: Controllo della struttura del progetto e creazione delle directory necessarie
2. **Raccolta dati da Pagine Gialle**: Estrazione sistematica per ogni località della regione
3. **Normalizzazione dei dati Pagine Gialle**: Pulizia e standardizzazione
4. **Raccolta rating e recensioni da Google Maps**: Arricchimento con dati da Google
5. **Normalizzazione dati con recensioni**: Elaborazione finale e integrazione

## 1. Scraper di Pagine Gialle

### Componenti Principali

- **Spider (`pagine_gialle.py`)**: coordina l'estrazione dei dati da Pagine Gialle
- **Items (`items.py`)**: definisce la struttura dei dati estratti
- **Middlewares (`middlewares.py`)**: fornisce hook per la personalizzazione del comportamento di Scrapy
- **Pipelines (`pipelines.py`)**: gestisce la post-elaborazione e il salvataggio dei dati
- **Settings (`settings.py`)**: configura i parametri operativi dello spider

### Funzionamento

Lo spider estrae sistematicamente informazioni aziendali dalle pagine JSON di Pagine Gialle utilizzando un metodo paginato. Per ogni attività commerciale, raccoglie:

- Nome dell'azienda
- Indirizzo completo (via, città, provincia, CAP)
- Contatti (telefono, email)
- Sito web
- Categoria
- Descrizione
- Coordinate geografiche (latitudine e longitudine)
- Metadati relativi alla regione e categoria

### Caratteristiche Tecniche

1. **Gestione dello Stato**: Implementa un sistema di persistenza dello stato per consentire la ripresa in caso di interruzione, salvando il progresso in file JSON.

2. **User-Agent Rotazione**: Utilizza `fake_useragent` per variare dinamicamente gli User-Agent e minimizzare il rischio di rilevamento.

3. **Sistema di Proxy Rotante**: Configura middleware per la rotazione di proxy, migliorando la resilienza contro blocchi IP.

4. **Throttling Intelligente**: Implementa ritardi randomizzati e autothrottling per evitare sovraccarichi del server target.

5. **Gestione degli Errori**: Include meccanismi di gestione degli errori e callback specifici per gestire fallimenti nelle richieste HTTP.

6. **Elaborazione Dati Robusta**: La funzione `clean_value()` gestisce vari tipi di dati (stringhe, liste, null) garantendo output consistenti.

## 2. Scraper di Google Reviews

### Componenti Principali

- **Spider (`google_maps_spider.py`)**: coordina l'estrazione dei dati da Google Maps
- **Middleware Selenium personalizzato**: gestisce il rendering JavaScript e l'automazione del browser
- **Sistema di persistenza e recovery**: implementa salvataggio stato e backup automatici

### Funzionamento

Questo scraper prende in input i dati normalizzati dal primo spider (Pagine Gialle) e:

1. Cerca ogni attività su Google Maps utilizzando nome e città
2. Analizza i risultati e seleziona il miglior match utilizzando algoritmi di similarità del testo
3. Estrae valutazioni (rating) e conteggio recensioni
4. Verifica la corrispondenza degli indirizzi per garantire l'accuratezza dei dati

### Caratteristiche Tecniche

1. **Integrazione Selenium-Scrapy**: Implementa un middleware personalizzato (`CustomSeleniumMiddleware`) che integra Selenium con Scrapy per gestire il rendering JavaScript.

2. **Gestione delle Risorse del Browser**:
   - Gestione automatica del driver Chrome attraverso `webdriver_manager`
   - Pulizia dei profili temporanei del browser
   - Ottimizzazione della memoria attraverso la chiusura controllata delle istanze del browser

3. **Algoritmi di Matching Avanzati**:
   - Utilizza `SequenceMatcher` per calcolare la similarità tra stringhe
   - Implementa funzioni personalizzate come `check_location_similarity()` e `normalize_address()`
   - Applica pesi differenti a nome e città per migliorare l'accuratezza del matching

4. **Sistema di Recovery Avanzato**:
   - Backup automatico ogni 10 elementi elaborati
   - File di stato separati per ogni combinazione regione/categoria
   - Gestione dei segnali (es. SIGINT) per chiusure controllate

5. **Debugging Avanzato**:
   - Screenshot automatici delle pagine per debugging
   - Logging dettagliato con livelli di verbosità configurabili
   - Tracciamento completo degli errori

6. **Gestione Cookie e Consenso**: Implementa funzioni per gestire automaticamente popup di consenso cookie e GDPR.

## 3. Processo di Normalizzazione dei Dati

### Normalizzazione Dati Pagine Gialle

Lo script `cleanData.py` esegue operazioni di pulizia e standardizzazione sui dati grezzi estratti da Pagine Gialle:

1. Rimuove duplicati basati su identificatori univoci
2. Standardizza formati di dati (indirizzi, numeri di telefono, ecc.)
3. Separa campi compositi (es. indirizzo completo in componenti separate)
4. Aggiunge metadati per facilitare l'integrazione con altre fonti
5. Gestisce valori mancanti e anomalie dei dati

### Normalizzazione Dati Google Reviews

Lo script `cleanDataReviews.py` elabora e integra i dati delle recensioni:

1. Integra i rating con i dati principali delle attività commerciali
2. Standardizza i formati dei valori di rating
3. Calcola metriche aggiuntive basate sulle recensioni
4. Gestisce casi di mancata corrispondenza tra fonti diverse
5. Produce un dataset arricchito e pronto per l'analisi

## Orchestrazione della Pipeline

Il `PipelineExecutor` coordina il flusso di lavoro completo utilizzando un approccio modulare:

### Inizializzazione

```python
def __init__(self, region, category, base_path=None):
    """
    Inizializza l'esecutore della pipeline
    
    Args:
        region (str): Regione di destinazione (es. 'emilia_romagna')
        category (str): Categoria di destinazione (es. 'ristoranti')
        base_path (str, optional): Percorso base del progetto
    """
    # Inizializzazione attributi e struttura directory
```

### Gestione dell'Esecuzione dei Comandi

```python
def execute_command(self, command, cwd=None, description="", capture_output=True):
    """
    Esegue un comando di sistema con gestione degli errori
    
    Args:
        command (str): Comando da eseguire
        cwd (str, optional): Directory di lavoro
        description (str, optional): Descrizione del comando per i log
        capture_output (bool): Se catturare l'output o mostrarlo direttamente sul terminale
        
    Returns:
        bool: True se l'esecuzione è riuscita, False altrimenti
    """
    # Implementazione della gestione del comando
```

### Passaggi della Pipeline

1. **Raccolta dati da Pagine Gialle**:
   ```python
   def step1_collect_pagine_gialle(self):
       """Executes the Pagine Gialle spider to collect raw data into a single file"""
       # Implementazione dello step 1
   ```

2. **Normalizzazione dei dati di Pagine Gialle**:
   ```python
   def step2_normalize_pagine_gialle_data(self):
       """Normalizza i dati grezzi di Pagine Gialle"""
       # Implementazione dello step 2
   ```

3. **Raccolta dati da Google Maps**:
   ```python
   def step3_collect_google_reviews(self):
       """Raccoglie rating e recensioni da Google Maps"""
       # Implementazione dello step 3
   ```

4. **Normalizzazione dei dati con recensioni**:
   ```python
   def step4_normalize_review_data(self):
       """Normalizza i dati con recensioni e rating"""
       # Implementazione dello step 4
   ```

### Esecuzione dell'Intera Pipeline

```python
def execute_pipeline(self):
    """Esegue l'intera pipeline dall'inizio alla fine"""
    logger.info(f"INIZIO PIPELINE per {self.region} - {self.category}")
    self.verify_project_structure()
    # Esecuzione sequenziale dei passaggi
    # Generazione del report finale
```

## Configurazione e Parametri

### Scraper Pagine Gialle

Parametri principali nel file `settings.py`:

```python
# Throttling e concorrenza
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 3
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 1
AUTOTHROTTLE_ENABLED = True
```

### Scraper Google Reviews

Parametri principali nel file `settings.py`:

```python
# Riduce la concorrenza per evitare troppi browser aperti
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Argumenti Selenium
SELENIUM_DRIVER_ARGUMENTS = [
    # '--headless=new',  # Commentato per debug
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-notifications',
    # altri parametri...
]
```

## Struttura dei Dati

### Input per Google Reviews

Il sistema si aspetta dati in questo formato JSON da Pagine Gialle (già processati):

```json
[
  {
    "strutture": [
      {
        "nome": "Nome Attività",
        "città": "Nome Città",
        "indirizzo": "Via Example 123",
        // altri campi...
      }
    ]
  }
]
```

### Output di Google Reviews

I dati vengono arricchiti con:

```json
{
  "nome": "Nome Attività",
  "città": "Nome Città",
  "indirizzo": "Via Example 123",
  "rating": "4.5",
  "review_count": "125",
  "google_url": "https://www.google.com/maps/place/...",
  // campi originali conservati...
}
```

## Meccanismi di Resilienza

### 1. Gestione delle Eccezioni

Implementazione di try-catch dettagliati su tutti i componenti critici:

```python
try:
    # Operazioni critiche
except Exception as e:
    logger.error(f"Eccezione durante: {description}: {e}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    return False
```

### 2. Backoff Esponenziale

Implementazione di ritardi crescenti tra i tentativi falliti, con randomizzazione per evitare sincronizzazioni:

```python
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
```

### 3. Salvataggio dello Stato

Meccanismo di salvataggio periodico dello stato di avanzamento per consentire la ripresa:

```python
def _save_state(self, idx):
    state = {
        "last_index": idx,
        "region": self.region,
        "category": self.category,
        "timestamp": time.time(),
        "items_processed": idx,
        "total_items": len(self.aziende),
        "progress_percentage": round((idx / len(self.aziende) * 100), 2)
    }
    with open(self.state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
```

### 4. Backup Automatico

Sistema di backup periodico per prevenire la perdita di dati:

```python
def _manual_save_results(self):
    backup_file = os.path.join(
        backup_dir, 
        f"{self.region}_{self.category}_backup_{int(time.time())}.json"
    )
    
    # Salvataggio dei dati
    with open(self.raw_path, 'w', encoding='utf-8') as f:
        json.dump(self.results, f, ensure_ascii=False, indent=2)
```

### 5. Gestione delle Risorse

Pulizia sistematica delle risorse utilizzate:
- Chiusura controllata dei driver Selenium
- Eliminazione dei profili temporanei di Chrome
- Rimozione dei file temporanei non più necessari

## Logging e Debugging

Il sistema implementa un sistema di logging esteso a più livelli:

```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_execution.log'),
        logging.StreamHandler()
    ]
)
```

### Caratteristiche del Sistema di Logging

1. **Logging Gerarchico**: Diversi livelli di dettaglio (DEBUG, INFO, WARNING, ERROR)
2. **Registrazione su File e Console**: Output duplicato per facilitare il monitoraggio
3. **Timestamp Precisi**: Ogni entry include data e ora esatte
4. **Traceback Completi**: Gli errori includono il traceback completo
5. **Reporting Strutturato**: Generazione di report JSON alla fine dell'esecuzione

### Modalità Debug

Attivabile tramite flag da linea di comando:

```bash
python pipeline_executor.py --region lombardia --category ristoranti --debug
```

Quando attivata, fornisce:
- Log più dettagliati su ogni passaggio
- Maggiori informazioni diagnostiche
- Tracciamento dettagliato delle operazioni interne

## Argomenti della Linea di Comando

Il `PipelineExecutor` può essere controllato tramite interfaccia CLI:

```python
parser = argparse.ArgumentParser(description="Esecutore della pipeline di scraping e processamento dati")
parser.add_argument("--region", required=True, help="Regione target (es. emilia_romagna)")
parser.add_argument("--category", required=True, help="Categoria target (es. ristoranti)")
parser.add_argument("--base-path", help="Percorso base del progetto")
parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], help="Esegui solo un passaggio specifico")
parser.add_argument("--debug", action="store_true", help="Attiva modalità debug")
```

### Esempi di Utilizzo

Per eseguire l'intera pipeline:
```bash
python src/pipeline/pipeline_executor.py --region lombardia --category ristoranti
```

Per eseguire solo un passaggio specifico:
```bash
python src/pipeline/pipeline_executor.py --region lombardia --category ristoranti --step 2
```

Per attivare la modalità debug:
```bash
python src/pipeline/pipeline_executor.py --region lombardia --category ristoranti --debug
```

## Gestione delle Performance

### Ottimizzazioni Pagine Gialle

- Utilizzo di `RANDOMIZE_DOWNLOAD_DELAY` e `AUTOTHROTTLE_ENABLED`
- Limitazione delle richieste concorrenti con `CONCURRENT_REQUESTS` e `CONCURRENT_REQUESTS_PER_DOMAIN`
- Rotazione degli User-Agent per minimizzare il rilevamento
- Gestione efficiente delle risorse con pulizia tempestiva dei file temporanei

### Ottimizzazioni Google Reviews

- Disabilitazione del caricamento delle immagini
   ```python
   prefs = {"profile.managed_default_content_settings.images": 2}
   options.add_experimental_option("prefs", prefs)
   ```
- Gestione precisa delle risorse del browser con chiusura controllata
- Profili utente temporanei separati per ogni istanza del browser
- Parametrizzazione delle richieste concorrenti per evitare sovraccarichi

## Verifiche e Quality Assurance

Il sistema implementa diverse verifiche per garantire l'integrità del processo:

### Verifica della Struttura del Progetto

```python
def verify_project_structure(self):
    """Verifica la struttura del progetto e mostra informazioni dettagliate per il debug"""
    logger.info("Verifica della struttura del progetto...")
    
    key_directories = [
        "src/scrapers/pagine_gialle_scraper",
        "src/scrapers/google_reviews",
        # altre directory...
    ]
    
    for directory in key_directories:
        path = os.path.join(self.base_path, directory)
        if os.path.exists(path):
            logger.info(f"Directory trovata: {path}")
            # Ulteriori verifiche...
        else:
            logger.warning(f"Directory mancante: {path}")
    
    # Verifica file di configurazione cruciali
    # ...
```

### Verifica delle Dipendenze

```python
def check_scrapy_installation(self):
    """Verifica che Scrapy sia installato e funzionante."""
    logger.info("Verifica dell'installazione di Scrapy...")
    
    # Verifica la versione di Scrapy
    return self.execute_command(
        "scrapy version",
        description="Verifica versione Scrapy",
        capture_output=True
    )
```

## Limitazioni e Problematiche Note

1. **Dipendenza dal DOM di Google Maps**: Cambiamenti nell'interfaccia di Google Maps potrebbero richiedere aggiornamenti ai selettori CSS/XPath.

2. **Rilevamento Bot**: Google Maps implementa sistemi avanzati di rilevamento bot che potrebbero bloccare le richieste nonostante le contromisure.

3. **Gestione Cookie**: I popup di consenso cookie richiedono interazione specifica che potrebbe cambiare nel tempo.

4. **Risorse Computazionali**: L'utilizzo di Selenium richiede risorse significative, in particolare memoria e CPU.

5. **Stagnazione dello Scraping**: Lo spider potrebbe bloccarsi su determinate richieste (gestito tramite timeout e retry).

6. **Dipendenza da Configurazione Regionale**: Il file `regioni_paesi.json` deve essere accuratamente mantenuto e aggiornato.

## Best Practices Implementate

1. **Log Dettagliati**: Ogni fase del processo viene registrata con livelli appropriati di verbosità.

2. **Pulizia delle Risorse**: Gestione attenta della chiusura di browser e file temporanei.

3. **Verifica dei Dati**: Controlli di qualità sui dati estratti mediante algoritmi di similarità.

4. **Throttling Rispettoso**: Implementazione di ritardi e limiti di concorrenza per ridurre il carico sui server target.

5. **Resilienza agli Errori**: Meccanismi di ripresa e backup per garantire la continuità dell'estrazione.

6. **Modularità**: Separazione chiara delle responsabilità tra i diversi componenti.

7. **Documentazione**: Codice ben documentato con docstring e commenti esplicativi.

## Considerazioni Etiche e Legali

- Il sistema implementa delay e throttling per minimizzare l'impatto sui server target
- Il rispetto delle politiche robots.txt è configurabile attraverso `ROBOTSTXT_OBEY`
- L'uso di questo strumento deve essere conforme ai termini di servizio delle piattaforme target
- La rotazione degli User-Agent e proxy dovrebbe essere utilizzata responsabilmente
