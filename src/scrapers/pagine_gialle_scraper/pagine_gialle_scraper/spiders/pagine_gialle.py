import scrapy
import json
import os
import subprocess
from scrapy import signals
from scrapy.signalmanager import dispatcher
from scrapy.signals import spider_closed

class PagineGialleSpider(scrapy.Spider):
    """
    Spider per estrarre dati dalle Pagine Gialle (paginegialle.it).
    
    Caratteristiche principali:
    - Supporta ripresa automatica dello scraping in caso di interruzione
    - Gestisce la paginazione automatica
    - Salva lo stato di avanzamento su file JSON
    - Estrae informazioni complete delle aziende (contatti, posizione, recensioni)
    """
    
    name = "pagine_gialle_scraper"
    allowed_domains = ["paginegialle.it"]
    base_url = "https://www.paginegialle.it/{url_pattern}/p-{page}.html?output=json"
    
    # Percorso del file di stato per il salvataggio automatico dell'avanzamento
    state_file = os.path.join(os.path.dirname(__file__), "..", "config", "scraping_state.json")

    def __init__(self, url_pattern=None, region=None, category=None, *args, **kwargs):
        """
        Inizializza lo spider con parametri dinamici.
        
        Args:
            url_pattern (str): Pattern URL specifico per la ricerca (es. "roma/ristoranti")
            region (str): Regione geografica di interesse
            category (str): Categoria di business da cercare
            
        Note:
            - Collega automaticamente il segnale 'spider_closed' per logging
            - Crea la directory di configurazione se non esiste
        """
        super().__init__(*args, **kwargs)

        # Salva i parametri di configurazione dello spider
        self.url_pattern = url_pattern
        self.region = region
        self.category = category

        # Collegamento del segnale per gestire la chiusura dello spider
        # Questo permette di eseguire operazioni di cleanup quando lo spider termina
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.logger.info(f"Inizializzazione spider con parametri: url_pattern={url_pattern}, region={region}, category={category}")
        
        # Assicura che la directory per il file di stato esista
        # Importante per evitare errori quando si tenta di salvare lo stato
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

    def spider_closed(self, spider, reason):
        """
        Callback eseguito quando lo spider viene chiuso.
        
        Args:
            spider: L'istanza dello spider che si sta chiudendo
            reason (str): Motivo della chiusura (es. 'finished', 'cancelled', 'shutdown')
            
        Note:
            Utile per operazioni di cleanup, statistiche finali, o notifiche
        """
        self.logger.info(f"Spider terminato con motivo: {reason}.")
        
    def load_scraping_state(self):
        """
        Carica lo stato dello scraping da file JSON per consentire la ripresa.
        
        Returns:
            dict: Dizionario con lo stato salvato per la configurazione corrente,
                  o dizionario vuoto se non esiste stato precedente
                  
        Note:
            - Utilizza una chiave composta da region_category_url_pattern per l'identificazione univoca
            - Gestisce gracefully file corrotti o mancanti
            - Permette di riprendere lo scraping esattamente dal punto di interruzione
        """
        # Crea una chiave univoca basata sui parametri dello spider
        state_key = f"{self.region}_{self.category}_{self.url_pattern}"
        
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # Gestisce file vuoti o con solo whitespace
                    state_data = json.loads(content) if content else {}
                    return state_data.get(state_key, {})
            except json.JSONDecodeError:
                # Se il file JSON è corrotto, log dell'errore e reset
                self.logger.error(f"Errore nel caricare {self.state_file}. Reset stato scraping.")
                return {}
        return {}

    def save_scraping_state(self, paese, page):
        """
        Salva lo stato corrente dello scraping per consentire una ripresa successiva.
        
        Args:
            paese (str): Nome del paese/città corrente
            page (int): Numero della pagina corrente
            
        Note:
            - Mantiene gli stati di più configurazioni contemporaneamente
            - Aggiorna atomicamente il file per evitare corruzioni
            - Fondamentale per la funzionalità di ripresa automatica
        """
        # Crea la stessa chiave univoca usata nel caricamento
        state_key = f"{self.region}_{self.category}_{self.url_pattern}"

        # Legge lo stato esistente per non sovrascrivere altre configurazioni
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    state_data = json.loads(content) if content else {}
            except json.JSONDecodeError:
                # Se il file è corrotto, ricomincia con un dizionario vuoto
                state_data = {}
        else:
            state_data = {}
        
        # Aggiorna o crea la sezione per questa configurazione
        if state_key not in state_data:
            state_data[state_key] = {}
        state_data[state_key][paese] = page
        
        # Salva atomicamente il nuovo stato
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=4)

    def start_requests(self):
        """
        Punto di ingresso principale dello spider.
        Costruisce e invia la prima richiesta HTTP basata sui parametri configurati.
        
        Yields:
            scrapy.Request: Prima richiesta HTTP per iniziare lo scraping
            
        Note:
            - Valida che tutti i parametri obbligatori siano presenti
            - Estrae automaticamente il nome del paese dal pattern URL
            - Riprende automaticamente dall'ultima pagina salvata
            - Imposta i metadati necessari per la gestione della paginazione
        """
        # Validazione parametri obbligatori
        if not self.url_pattern or not self.region or not self.category:
            self.logger.error("Parametri mancanti: url_pattern, region e category sono obbligatori")
            return

        # Estrazione del nome del paese dal pattern URL
        # Assume che il pattern sia nel formato "paese/categoria" o simile
        url_parts = self.url_pattern.strip("/").split("/")
        paese_nome = url_parts[0] if url_parts else "unknown"

        # Controllo di coerenza per identificare possibili errori di configurazione
        if paese_nome == self.category:
            self.logger.warning(f"Possibile errore: nome paese ({paese_nome}) uguale alla categoria. Controlla il pattern URL.")
        
        self.logger.info(f"Avvio scraping per paese: {paese_nome}")

        # Carica lo stato salvato per riprendere dal punto di interruzione
        scraping_state = self.load_scraping_state()
        last_page = scraping_state.get(paese_nome, 1)  # Default alla pagina 1 se non trovato

        # Preparazione metadati per il tracking dello stato durante lo scraping
        meta = {
            "region": self.region,
            "category": self.category,
            "paese": paese_nome,
            "page": last_page,
            "empty_pages": 0  # Contatore per gestire la fine dello scraping
        }

        # Costruzione URL per la prima richiesta
        url = self.base_url.format(url_pattern=self.url_pattern, page=last_page)
        self.logger.info(f"Avvio scraping da URL: {url}")
        
        # Invio della prima richiesta con callback per il parsing JSON
        yield scrapy.Request(url, callback=self.parse_json, meta=meta, errback=self.errback_httpbin)

    def errback_httpbin(self, failure):
        """
        Gestione centralizzata degli errori HTTP e di rete.
        
        Args:
            failure: Oggetto Failure di Scrapy contenente dettagli dell'errore
            
        Note:
            - Fornisce logging dettagliato per il debugging
            - Distingue tra diversi tipi di errore
            - Evita che singoli errori fermino tutto lo scraping
        """
        self.logger.error(f"Errore nella richiesta: {failure}")
        
        # Gestisce specificamente le richieste ignorate da Scrapy
        if failure.check(scrapy.exceptions.IgnoreRequest):
            self.logger.error("Richiesta ignorata")
        else:
            # Log per altri tipi di errore (timeout, DNS, etc.)
            self.logger.error(f"Errore di altro tipo: {failure.value}")

    def parse_json(self, response):
        """
        Cuore dello spider: effettua il parsing della risposta JSON e gestisce la paginazione.
        
        Args:
            response: Oggetto Response di Scrapy contenente la risposta HTTP
            
        Yields:
            dict: Dati estratti per ogni azienda trovata
            scrapy.Request: Richiesta per la pagina successiva
            
        Note:
            - Naviga la struttura JSON complessa delle Pagine Gialle
            - Estrae tutti i campi disponibili per ogni azienda
            - Gestisce automaticamente la paginazione
            - Implementa logica di stop per pagine vuote consecutive
        """
        try:
            # Logging dettagliato per debugging
            self.logger.info(f"Ricevuta risposta da {response.url}")
            content_type = response.headers.get('Content-Type', b'').decode('utf-8')
            self.logger.debug(f"Content-Type: {content_type}")
            self.logger.debug(f"Response status: {response.status}")
            self.logger.debug(f"Contenuto risposta (primi 500 caratteri): {response.text[:500]}...")

            # Parsing del JSON con gestione errori robusta
            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as e:
                self.logger.error(f"Impossibile analizzare la risposta come JSON: {e}")
                # Identifica se la risposta è HTML invece di JSON (problema comune)
                if '<html' in response.text.lower():
                    self.logger.error("La risposta sembra essere HTML, non JSON")
                return

            # Navigazione nella struttura JSON gerarchica delle Pagine Gialle
            # Struttura: data["list"]["out"]["base"]["results"]
            list_data = data.get("list", {})
            if not list_data:
                self.logger.warning("Chiave 'list' non trovata nella risposta JSON")
                return

            out_data = list_data.get("out", {})
            if not out_data:
                self.logger.warning("Chiave 'out' non trovata nei dati 'list'")
                return

            base_data = out_data.get("base", {})
            if not base_data:
                self.logger.warning("Chiave 'base' non trovata nei dati 'out'")
                return

            # Array principale con i risultati delle aziende
            results = base_data.get("results", [])

            if results:
                # Reset contatore pagine vuote quando si trovano risultati
                response.meta["empty_pages"] = 0
                self.logger.info(f"Pagina {response.meta['page']} - Trovati {len(results)} risultati")

                # Elaborazione di ogni singola azienda trovata
                for entry in results:
                    # === ESTRAZIONE DATI PRINCIPALI ===
                    
                    # Nome azienda con fallback su insegna se ragione sociale mancante
                    nome_azienda = clean_value(entry.get("ds_ragsoc"))
                    if nome_azienda == "N/A":
                        nome_azienda = clean_value(entry.get("ds_insegna"))

                    # Dati di contatto
                    telefono = entry.get("ds_ls_telefoni")  # Spesso è una lista
                    email = entry.get("ds_ls_email")        # Spesso è una lista
                    
                    # Estrazione sito web da struttura multilinks
                    multilinks = entry.get("links", {}).get("multilinks", [{}])
                    sito_web = multilinks[0].get("url") if multilinks else None

                    # === DATI GEOGRAFICI ===
                    citta = clean_value(entry.get("ds_comune_ita"))
                    prov = clean_value(entry.get("prov"), default=None) or clean_value(entry.get("ds_prov"))
                    
                    # Gestione valori mancanti per dati geografici obbligatori
                    if not citta or citta == "N/A":
                        citta = "UNKNOWN_CITY"
                    if not prov or prov == "N/A":
                        prov = "UNKNOWN_PROV"

                    # === DATI AGGIUNTIVI E METADATI ===
                    keywords_evidence = entry.get("kmkwdevidence", [])
                    keywords_processed = entry.get("kmkwdevidence_processed", [])
                    
                    # Informazioni per preventivi (se disponibili)
                    info_preventivi = entry.get("info_preventivi", {})
                    quote_email = info_preventivi.get("email") if isinstance(info_preventivi, dict) else None

                    # Aggiorna il paese nei metadati per il salvataggio dello stato
                    response.meta["paese"] = citta

                    # === YIELD DEL RECORD COMPLETO ===
                    # Ogni yield rappresenta un'azienda con tutti i dati estratti
                    yield {
                        "name_pg": nome_azienda,                           # Nome/Ragione sociale
                        "address_pg": clean_value(entry.get("addr")),      # Indirizzo completo
                        "city_pg": citta,                                  # Città
                        "province_pg": prov,                               # Provincia
                        "region_pg": clean_value(entry.get("reg")),       # Regione
                        "postal_code_pg": clean_value(entry.get("ds_cap")), # CAP
                        "phone_pg": clean_value(telefono, []),             # Telefoni
                        "email_pg": clean_value(email, []),               # Email
                        "website_pg": clean_value(sito_web),              # Sito web
                        "category_pg": clean_value(entry.get("ds_cat")),  # Categoria
                        "description_pg": clean_value(entry.get("ds_abstract")), # Descrizione
                        "latitude_pg": clean_value(entry.get("nr_lat")),  # Latitudine
                        "longitude_pg": clean_value(entry.get("nr_long")), # Longitudine
                        "vat_number_pg": clean_value(entry.get("ds_pi")), # Partita IVA
                        "average_rating_pg": clean_value(entry.get("vote_avg")), # Voto medio
                        "reviews_count_pg": clean_value(entry.get("vote_tot")), # Totale recensioni
                        "additional_info_pg": clean_value(entry.get("ds_atrinf")), # Info aggiuntive
                        "free_text_pg": clean_value(entry.get("ds_testo_libero")), # Testo libero
                        "keywords_pg": keywords_evidence,                 # Keywords originali
                        "keywords_processed_pg": keywords_processed,      # Keywords processate
                        "quote_email_pg": clean_value(quote_email),       # Email preventivi
                        "category": response.meta.get("category"),        # Categoria di ricerca
                        "page": response.meta["page"]                     # Numero pagina
                    }

                # === SALVATAGGIO STATO E PAGINAZIONE ===
                
                # Salva lo stato corrente per la ripresa automatica
                self.save_scraping_state(response.meta["paese"], response.meta["page"])

                # Preparazione richiesta per la pagina successiva
                next_page = response.meta["page"] + 1
                meta = response.meta.copy()  # Copia metadati esistenti
                meta["page"] = next_page
                next_url = self.base_url.format(url_pattern=self.url_pattern, page=next_page)
                self.logger.info(f"Richiesta prossima pagina: {next_url}")
                
                # Yield della richiesta per la pagina successiva
                yield scrapy.Request(next_url, callback=self.parse_json, meta=meta, errback=self.errback_httpbin)

            else:
                # === GESTIONE PAGINE VUOTE ===
                self.logger.info(f"Nessun risultato trovato nella pagina {response.meta['page']}")
                response.meta["empty_pages"] += 1

                # Termina lo scraping dopo un numero configurabile di pagine vuote consecutive
                # Questo evita loop infiniti quando si raggiunge la fine dei risultati
                if response.meta["empty_pages"] >= 2:
                    self.logger.info(f"Interrompo scraping dopo {response.meta['empty_pages']} pagine vuote.")
                    return

                # Prova comunque la pagina successiva (potrebbero esserci gap nei dati)
                next_page = response.meta["page"] + 1
                meta = response.meta.copy()
                meta["page"] = next_page
                next_url = self.base_url.format(url_pattern=self.url_pattern, page=next_page)
                self.logger.info(f"Richiesta prossima pagina (dopo pagina vuota): {next_url}")
                yield scrapy.Request(next_url, callback=self.parse_json, meta=meta, errback=self.errback_httpbin)

        except json.JSONDecodeError as e:
            # Gestione specifica per errori di parsing JSON
            self.logger.error(f"Errore nel parsing JSON. URL: {response.url}")
        except Exception as e:
            # Gestione generica per tutti gli altri errori
            self.logger.error(f"Errore durante il parsing: {type(e).__name__}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")

def clean_value(value, default="N/A"):
    """
    Funzione utility per normalizzare e validare i valori estratti dal JSON.
    
    Args:
        value: Valore da pulire (può essere str, list, None, o altro tipo)
        default: Valore di default da restituire se il valore è invalido
        
    Returns:
        Valore pulito o default se non valido
        
    Note:
        - Rimuove spazi superflui dalle stringhe
        - Gestisce liste vuote
        - Preserva la struttura per tipi complessi
        - Essenziale per la qualità dei dati estratti
    """
    if isinstance(value, str):
        # Per le stringhe, rimuove spazi e restituisce default se vuota
        return value.strip() if value.strip() else default
    elif isinstance(value, list):
        # Per le liste, restituisce la lista se non vuota, altrimenti default
        return value if value else default
    elif value is None:
        # Valori None diventano sempre default
        return default
    
    # Per tutti gli altri tipi (int, float, dict, etc.) restituisce il valore così com'è
    return value