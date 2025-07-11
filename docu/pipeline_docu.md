# Documentazione Tecnica Completa - Pipeline di Scraping e Data Processing

## Indice
1. [Panoramica Generale](#panoramica-generale)
2. [Architettura del Sistema](#architettura-del-sistema)
3. [Analisi Dettagliata del Codice](#analisi-dettagliata-del-codice)
4. [Flusso di Esecuzione](#flusso-di-esecuzione)
5. [Gestione degli Errori e Logging](#gestione-degli-errori-e-logging)
6. [Configurazione e Dipendenze](#configurazione-e-dipendenze)
7. [Considerazioni di Performance](#considerazioni-di-performance)
8. [Sicurezza e Resilienza](#sicurezza-e-resilienza)

---

## Panoramica Generale

### Scopo del Sistema
La pipeline è un sistema di data engineering progettato per automatizzare la raccolta, normalizzazione e processamento di dati business provenienti da due fonti principali:
- **Pagine Gialle**: Per informazioni base delle attività commerciali
- **Google Maps**: Per rating e recensioni degli utenti

### Paradigma Architetturale
Il sistema segue un approccio **ETL (Extract, Transform, Load)** suddiviso in 4 fasi sequenziali:
1. **Extract**: Raccolta dati da Pagine Gialle
2. **Transform**: Normalizzazione dati di base
3. **Extract**: Arricchimento con dati Google Maps  
4. **Transform**: Normalizzazione finale con merge dei dataset

### Stack Tecnologico
- **Linguaggio**: Python 3.x
- **Framework di Scraping**: Scrapy
- **Gestione Processi**: subprocess module
- **Serializzazione Dati**: JSON
- **Logging**: Python logging module
- **Gestione CLI**: argparse

---

## Architettura del Sistema

### Struttura delle Directory
```
project_root/
├── src/
│   ├── pipeline/                     # Core pipeline executor
│   ├── scrapers/
│   │   ├── pagine_gialle_scraper/    # Spider Scrapy per Pagine Gialle
│   │   │   ├── spiders/
│   │   │   ├── scrapy.cfg
│   │   │   └── regioni_paesi.json
│   │   └── google_reviews/           # Spider Scrapy per Google Maps
│   │       ├── spiders/
│   │       └── scrapy.cfg
│   └── data_processing/
│       ├── data_cleaning_pagine_gialle/  # Normalizzazione dati PG
│       └── data_cleaning_reviews/        # Normalizzazione dati review
├── data/
│   ├── raw/                          # Dati grezzi
│   │   ├── raw_post_pagine_gialle/
│   │   └── raw_post_google_reviews/
│   └── processed_data/               # Dati normalizzati
│       ├── clean_post_pagine_gialle/
│       └── clean_post_google_reviews/
├── config/
│   └── regioni_paesi.json           # Configurazione regioni/città
├── logs/
│   ├── pipeline_execution.log       # Log di esecuzione
│   └── pipeline_reports/            # Report dettagliati
└── temp/                            # File temporanei
```

### Pattern di Design Utilizzati

#### 1. Command Pattern
La classe `PipelineExecutor` implementa il Command Pattern attraverso i metodi `step1_*`, `step2_*`, etc., permettendo:
- Esecuzione controllata di operazioni complesse
- Possibilità di eseguire singoli step in isolamento
- Gestione uniforme degli errori per ogni comando

#### 2. Template Method Pattern
Il metodo `execute_pipeline()` definisce lo scheletro dell'algoritmo, delegando i dettagli implementativi ai metodi step specifici.

#### 3. Strategy Pattern
La gestione dei comandi di sistema attraverso `execute_command()` e `execute_command_list()` implementa strategie diverse per l'esecuzione di subprocess.

---

## Analisi Dettagliata del Codice

### Classe PipelineExecutor

#### Costruttore (`__init__`)
```python
def __init__(self, region=None, category=None, base_path=None, debug=False):
```

**Responsabilità**:
- Inizializzazione del logger con configurazione appropriata
- Rilevamento automatico del percorso base del progetto
- Configurazione del comando Python per virtual environment
- Setup delle directory necessarie
- Validazione dell'ambiente di esecuzione

**Dettagli Implementativi**:
```python
# Rilevamento automatico virtual environment
if os.path.basename(os.path.dirname(self.base_path)) == "src" and os.path.basename(self.base_path) == "pipeline":
    self.base_path = os.path.dirname(os.path.dirname(self.base_path))
```
Questa logica gestisce automaticamente la navigazione della struttura directory quando lo script viene eseguito da posizioni diverse.

#### Gestione Virtual Environment (`_get_python_command`)

**Algoritmo di Rilevamento**:
1. Controlla variabile ambiente `VIRTUAL_ENV`
2. Se presente, costruisce il path al Python del venv
3. Verifica l'esistenza dell'eseguibile
4. Fallback a `sys.executable` se il venv non è valido

**Cross-Platform Compatibility**:
```python
if sys.platform == 'win32':
    python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
else:
    python_path = os.path.join(venv_path, 'bin', 'python')
```

#### Gestione Subprocess (`execute_command` e `execute_command_list`)

**execute_command**: Per comandi stringa con shell=True
**execute_command_list**: Per comandi lista senza shell (più sicuro)

**Caratteristiche Avanzate**:
- **Timeout Management**: Previene processi zombie
- **Environment Preservation**: Mantiene variabili del virtual environment
- **Output Capture vs Stream**: Modalità configurabile per debug
- **Graceful Interruption**: Supporto per `_stop_requested` flag

**Gestione Timeout**:
```python
try:
    stdout, stderr = process.communicate(timeout=timeout)
except subprocess.TimeoutExpired:
    process.kill()
    self.logger.error(f"Timeout ({timeout}s) per comando: {description}")
    return False
```

#### Sistema di Logging Avanzato

**Livelli di Logging**:
- `DEBUG`: Dettagli implementativi e debugging
- `INFO`: Flusso normale di esecuzione
- `WARNING`: Situazioni anomale ma gestibili
- `ERROR`: Errori che compromettono l'esecuzione

**Output Multiplo**:
```python
logging.basicConfig(
    level=logging.DEBUG if args.debug else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_execution.log'),
        logging.StreamHandler()
    ]
)
```

### Step 1: Raccolta Dati Pagine Gialle

#### Architettura del Processo

**Flusso di Alto Livello**:
1. Verifica installazione e funzionamento Scrapy
2. Carica configurazione regioni/paesi da JSON
3. Gestione stato scraping per resume capability
4. Esecuzione spider per ogni città/paese
5. Aggregazione dati con deduplicazione
6. Gestione file temporanei e cleanup

#### Gestione Stato Scraping

**Resume Capability**:
La pipeline implementa un sistema di checkpoint che permette di riprendere lo scraping interrotto:

```python
def _is_paese_completed(self, nome_paese, scraping_state, existing_data):
    # Un paese è completato se:
    # 1. Ha dati nell'output finale
    # 2. Non è presente nello stato di scraping
    has_data = any(record.get('paese', '').lower() == nome_paese.lower() for record in existing_data)
    has_pending_state = nome_paese in scraping_state
    return has_data and not has_pending_state
```

#### Strategia Anti-Duplicazione

**Algoritmo di Deduplicazione**:
```python
def _filter_duplicates(self, new_data, existing_data):
    # Utilizza tupla (nome, indirizzo, città) come chiave univoca
    key = (
        record.get('nome', '').lower().strip(),
        record.get('indirizzo', '').lower().strip(),
        record.get('citta', '').lower().strip()
    )
```

**Vantaggi**:
- Prevenzione duplicati inter-città
- Gestione case-insensitive
- Trim automatico whitespace
- Efficienza O(n) attraverso set lookup

#### Gestione File di Output

**Strategia di Scrittura**:
- **Appending Incrementale**: I dati vengono aggiunti progressivamente
- **Atomic Operations**: Lettura completa → Modifica → Scrittura completa
- **Error Recovery**: Gestione file corrotti con ricreazione

### Step 2: Normalizzazione Dati Pagine Gialle

#### Architettura di Processamento
```python
def step2_normalize_pagine_gialle_data(self):
    script_path = os.path.join(
        self.base_path,
        "src", "data_processing", "data_cleaning_pagine_gialle", "cleanData.py"
    )
```

**Delegazione a Script Specializzato**:
- Separazione delle responsabilità
- Riusabilità del codice di pulizia
- Testabilità isolata delle logiche di normalizzazione

### Step 3: Raccolta Google Reviews

#### Integrazione Multi-Spider
La pipeline gestisce due progetti Scrapy separati:
- **pagine_gialle_scraper**: Per dati base
- **google_reviews**: Per arricchimento con rating/recensioni

**Vantaggi dell'Approccio Multi-Spider**:
- Isolamento delle configurazioni
- Sviluppo e debug indipendenti  
- Scaling orizzontale possibile
- Timeout differenziati (600s vs 120s)

### Step 4: Normalizzazione Finale

**Merge e Consolidamento**:
Il step finale combina i dati delle due fonti attraverso uno script specializzato che:
- Esegue matching tra record Pagine Gialle e Google Maps
- Risolve conflitti di dati
- Standardizza formati
- Produce output finale consolidato

---

## Flusso di Esecuzione

### Modalità di Esecuzione

#### 1. Esecuzione Completa
```bash
python pipeline_executor.py --region emilia_romagna --category ristoranti
```

#### 2. Esecuzione Singolo Step
```bash
python pipeline_executor.py --region emilia_romagna --category ristoranti --step 1
```

#### 3. Debug Mode
```bash
python pipeline_executor.py --region emilia_romagna --category ristoranti --debug
```

### Gestione degli Stati

#### Interruzione Controllata
```python
def stop(self):
    self._stop_requested = True
    self.logger.info("Richiesta interruzione pipeline")
```

**Punti di Controllo**:
- Inizio ogni step
- Loop iterazione città/paesi  
- Prima di ogni comando subprocess
- Durante operazioni I/O lunghe

#### Progress Callbacks
```python
def run_step(self, region, category, step, progress_callback=None):
    if progress_callback:
        progress_callback(step - 1, total_steps)
```

Supporto per UI/monitoring esterni attraverso callback pattern.

---

## Gestione degli Errori e Logging

### Strategie di Error Handling

#### 1. Graceful Degradation
```python
if not success:
    all_success = False
    self.logger.warning(f"Fallito per {nome_paese}, continuo…")
    continue
```
La pipeline continua l'esecuzione anche se alcune città falliscono.

#### 2. Circuit Breaker Pattern
Per errori critici (Scrapy non installato, file configurazione mancanti), la pipeline si interrompe immediatamente.

#### 3. Retry Logic
Timeout configurabili con gestione subprocess zombie:
```python
except subprocess.TimeoutExpired:
    process.kill()
    return False
```

### Sistema di Reporting

#### Report JSON Strutturato
```python
report = {
    "region": self.region,
    "category": self.category,
    "timestamp": self.timestamp,
    "total_time": f"{total_time:.2f} secondi",
    "steps": results
}
```

**Metriche Incluse**:
- Timestamp esecuzione
- Tempo per step e totale
- Success/failure rate
- Metadata configurazione

---

## Configurazione e Dipendenze

### File regioni_paesi.json

**Struttura**:
```json
{
  "emilia_romagna": {
    "paesi": [
      {
        "nome": "Bologna",
        "url_path": "/bologna-bo"
      },
      {
        "nome": "Modena", 
        "url_path": "/modena-mo"
      }
    ]
  }
}
```

**Ricerca Multi-Path**:
```python
possible_paths = [
    os.path.join(self.base_path, "config/regioni_paesi.json"),
    os.path.join(self.base_path, "src/scrapers/pagine_gialle_scraper/spiders/regioni_paesi.json"),
    os.path.join(self.base_path, "scrapers/pagine_gialle_scraper/spiders/regioni_paesi.json"),
]
```

### Dipendenze Sistema

#### Python Packages
- **scrapy**: Framework scraping principale
- **subprocess**: Esecuzione comandi sistema
- **json**: Serializzazione dati
- **logging**: Sistema logging
- **argparse**: CLI interface
- **pathlib**: Gestione path moderna

#### Verifica Scrapy
```python
def check_scrapy_installation(self):
    test_cmd = f"{self.python_cmd} -c \"import scrapy; print('Scrapy version:', scrapy.__version__)\""
```

**Doppia Verifica**:
1. Import test per verificare installazione
2. Command test per verificare CLI funzionante

---

## Considerazioni di Performance

### Ottimizzazioni Implementate

#### 1. Gestione Memoria
- **Streaming JSON**: Lettura/scrittura incrementale per file grandi
- **Temporary File Cleanup**: Rimozione automatica file temporanei
- **Process Isolation**: Ogni spider in processo separato

#### 2. I/O Optimization
- **Batch Processing**: Aggregazione dati per città
- **Atomic Writes**: Prevenzione corruzione durante scrittura
- **Path Caching**: Risoluzione path una volta sola

#### 3. Network Resilience  
- **Timeout Configurabili**: Prevenzione hanging
- **Graceful Failure**: Continue-on-error per singole città
- **Resume Capability**: Ripartenza da interruzioni

### Bottleneck Potenziali

#### 1. Sequential City Processing
Attualmente le città vengono processate sequenzialmente. Possibile parallelizzazione futura.

#### 2. JSON File Locking
Lettura/scrittura file principale può diventare collo di bottiglia con molte città.

#### 3. Subprocess Overhead
Creazione processo per ogni città introduce overhead. Possibile ottimizzazione con process pooling.

---

## Sicurezza e Resilienza

### Gestione Input

#### Path Sanitization
```python
safe_nome_paese = nome_paese.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
safe_nome_paese = ''.join(c for c in safe_nome_paese if c.isalnum() or c in ('_', '-'))
```

#### Command Injection Prevention
Utilizzo di `execute_command_list` con array invece di string shell per comandi critici.

### Data Integrity

#### 1. Backup Strategy
File temporanei mantengono dati prima del merge nel file principale.

#### 2. Corruption Recovery
```python
try:
    with open(output_file, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
except (json.JSONDecodeError, Exception) as e:
    self.logger.warning(f"File esistente corrotto: {e}. Sarà ricreato.")
    existing_data = []
```

#### 3. Atomic Operations
Lettura completa → Modifica in memoria → Scrittura completa per prevenire stati inconsistenti.

### Logging Security

#### Sensitive Data Filtering
I log evitano di esporre:
- URL completi con parametri
- Dati business sensibili
- Credenziali (se presenti)

#### Log Rotation
Implementabile attraverso configurazione logging Python per gestire dimensioni file.

---

## Estensibilità e Manutenzione

### Design Patterns per Estensione

#### 1. Strategy Pattern per Nuovi Spider
La struttura permette facilmente l'aggiunta di nuovi spider:
```python
def step5_collect_tripadvisor(self):
    scrapy_path = os.path.join(self.base_path, "src", "scrapers", "tripadvisor")
    # Implementazione simile agli altri step
```

#### 2. Plugin Architecture per Processing
Gli script di data processing sono completamente modulari e sostituibili.

#### 3. Configuration-Driven Behavior
Tutte le configurazioni sono esternalizzate in file JSON.

### Monitoring e Debugging

#### 1. Comprehensive Logging
Ogni operazione significativa viene loggata con livello appropriato.

#### 2. Execution Reports
Report JSON dettagliati per ogni esecuzione pipeline.

#### 3. Debug Mode
Flag `--debug` abilita logging verboso per troubleshooting.

### Deployment Considerations

#### 1. Environment Isolation
Full support per virtual environment con auto-detection.

#### 2. Cross-Platform Compatibility
Gestione differenze Windows/Unix per path ed eseguibili.

#### 3. Containerization Ready
Struttura compatibile con Docker deployment.

---

## Conclusioni

La pipeline rappresenta un sistema di data engineering robusto e ben architettato che bilancia:

- **Semplicità d'uso**: CLI intuitiva e configurazione minima
- **Robustezza**: Gestione completa degli errori e recovery
- **Scalabilità**: Architettura modulare estensibile  
- **Manutenibilità**: Separazione responsabilità e logging completo
- **Performance**: Ottimizzazioni I/O e gestione memoria

Il codice dimostra best practices di Python enterprise development con particolare attenzione a:
- Error handling graceful
- Logging strutturato
- Gestione subprocess sicura
- Data integrity
- Testabilità e debugging

La pipeline può servire come base solida per sistemi di scraping più complessi o come riferimento per implementazioni simili in altri domini.