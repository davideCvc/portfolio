import os
import json
import signal
import random
import re
import urllib.parse
import time
from difflib import SequenceMatcher
import traceback

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy_selenium import SeleniumRequest
from scrapy.utils.project import get_project_settings
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def check_location_similarity(name: str, city: str, text: str):
    if not text:
        return (0, 0, 0)
    txt = text.lower().replace("chiuso definitivamente", "").strip()
    ns  = similar(name, txt)
    cs  = similar(city, txt)
    return (ns * 0.7 + cs * 0.3, ns, cs)


def normalize_address(addr: str) -> str:
    a = addr.replace("\\n", " ")
    a = re.sub(r'[,.]', '', a)
    a = re.sub(r'\s+', ' ', a).strip().lower()
    return re.sub(r'\d+', '', a).strip()


class GoogleMapsSpider(scrapy.Spider):
    name = "google_reviews"

    custom_settings = {
        "SELENIUM_DRIVER_EXECUTABLE_PATH": None,
        "LOG_LEVEL": "INFO",
        "DOWNLOAD_TIMEOUT": 180,
    }

    # soglie
    MIN_COMBINED = 0.6
    MIN_NAME     = 0.5
    MIN_CITY     = 0.3
    MIN_ADDR     = 0.45

    def __init__(self, region=None, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region   = region
        self.category = category
        self.results  = []  # Lista per mantenere i risultati

        # handler SIGINT
        signal.signal(signal.SIGINT, self._on_sigint)

        # Determina PROJECT_ROOT correttamente
        self.root_dir = self._get_project_root()
        self.logger.info(f"PROJECT_ROOT determinato: {self.root_dir}")

        # input JSON
        self.data_file = os.path.join(
            self.root_dir, "data", "processed_data", "clean_post_pagine_gialle",
            region, category,
            f"{category}_categorized_{region}.json"
        )

        # raw-output dir
        raw_dir = os.path.join(
            self.root_dir, "data", "raw", "raw_post_google_reviews",
            region, category
        )
        os.makedirs(raw_dir, exist_ok=True)
        raw_file = f"{region}_{category}_raw.json"
        self.raw_path = os.path.join(raw_dir, raw_file)

        # stato e debug
        temp_dir = os.path.join(self.root_dir, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        self.state_file = os.path.join(
            temp_dir, f"google_reviews_state_{region}_{category}.json"
        )

        # Verifica struttura directories
        self._verify_directories()

        # Debug output file
        self.logger.info(f"I dati verranno salvati in: {self.raw_path}")
        
        # Controlla se esiste già un file parziale
        if os.path.exists(self.raw_path):
            self.logger.info(f"Il file esiste già, dimensione: {os.path.getsize(self.raw_path)} byte")
        else:
            self.logger.info(f"Il file verrà creato durante l'esecuzione")

        self.last_index = 0

    def _get_project_root(self):
        """
        Determina correttamente la root del progetto con strategia migliorata.
        Versione sincronizzata con settings.py
        """
        # METODO 1: Usa PROJECT_ROOT da variabile ambiente (set da settings)
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and os.path.exists(env_root) and self._is_valid_project_root(env_root):
            self.logger.info(f"ROOT da variabile ambiente: {env_root}")
            return env_root
        
        # METODO 2: Usa PROJECT_ROOT da settings se disponibile
        try:
            settings = get_project_settings()
            project_root = settings.get("PROJECT_ROOT")
            if project_root and os.path.exists(project_root):
                # Verifica che sia effettivamente la root corretta
                if self._is_valid_project_root(project_root):
                    self.logger.info(f"ROOT da settings validata: {project_root}")
                    return project_root
        except Exception as e:
            self.logger.debug(f"Settings PROJECT_ROOT non disponibile: {e}")

        # METODO 3: Cerca partendo dalla directory del file spider
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.logger.info(f"Directory corrente spider: {current_dir}")
        
        # Risali fino a trovare la root del progetto
        search_dir = current_dir
        max_levels = 10
        
        for i in range(max_levels):
            self.logger.debug(f"Controllo directory livello {i}: {search_dir}")
            
            if self._is_valid_project_root(search_dir):
                self.logger.info(f"ROOT trovata a livello {i}: {search_dir}")
                return search_dir
            
            # Risali di un livello
            parent_dir = os.path.dirname(search_dir)
            if parent_dir == search_dir:  # Siamo arrivati alla root del filesystem
                break
            search_dir = parent_dir

        # METODO 4: Prova percorsi relativi comuni
        possible_roots = [
            os.path.join(current_dir, '..', '..', '..', '..'),  # 4 livelli su
            os.path.join(current_dir, '..', '..', '..'),       # 3 livelli su
            os.path.join(current_dir, '..', '..'),             # 2 livelli su
        ]
        
        for possible_root in possible_roots:
            abs_root = os.path.abspath(possible_root)
            if self._is_valid_project_root(abs_root):
                self.logger.info(f"ROOT trovata tramite percorso relativo: {abs_root}")
                return abs_root

        # METODO 5: Cerca directory con nomi comuni del progetto
        search_dir = current_dir
        project_names = ['web-scraping-project', 'scraping', 'project', 'google_reviews']
        
        for i in range(8):  # Cerca più in alto
            dir_name = os.path.basename(search_dir).lower()
            if any(name in dir_name for name in project_names):
                if self._is_valid_project_root(search_dir):
                    self.logger.info(f"ROOT trovata tramite nome progetto: {search_dir}")
                    return search_dir
            search_dir = os.path.dirname(search_dir)
            if search_dir == os.path.dirname(search_dir):
                break

        # ULTIMO FALLBACK: crea nella directory corrente (NON IDEALE)
        fallback_root = os.path.dirname(current_dir)
        self.logger.warning(f"FALLBACK: usando directory superiore: {fallback_root}")
        self.logger.warning("ATTENZIONE: Potrebbe creare strutture directory non corrette!")
        
        # Crea le directory minime necessarie nel fallback
        try:
            os.makedirs(os.path.join(fallback_root, 'data'), exist_ok=True)
            os.makedirs(os.path.join(fallback_root, 'temp'), exist_ok=True)
            self.logger.info("Directory minime create nel fallback")
        except Exception as e:
            self.logger.error(f"Errore creazione directory fallback: {e}")
        
        return fallback_root

    def _is_valid_project_root(self, path):
        """
        Verifica migliorata se una directory è una valida root del progetto.
        """
        if not os.path.exists(path):
            return False
            
        # Marker primari (DEVONO esistere)
        data_dir = os.path.join(path, "data")
        src_dir = os.path.join(path, "src")
        
        # Marker secondari (DOVREBBERO esistere)
        config_dir = os.path.join(path, "config")
        requirements_file = os.path.join(path, "requirements.txt")
        readme_file = os.path.join(path, "README.md")
        scrapy_cfg = os.path.join(path, "scrapy.cfg")
        
        # Verifica marker primari
        primary_score = 0
        if os.path.exists(data_dir):
            primary_score += 2
            self.logger.debug(f"✓ Data directory trovata: {data_dir}")
        else:
            self.logger.debug(f"✗ Data directory mancante: {data_dir}")
            
        if os.path.exists(src_dir):
            primary_score += 2
            self.logger.debug(f"✓ Src directory trovata: {src_dir}")
        else:
            self.logger.debug(f"✗ Src directory mancante: {src_dir}")
            
        # Verifica marker secondari
        secondary_score = 0
        for marker, desc in [
            (config_dir, "Config directory"),
            (requirements_file, "Requirements file"),
            (readme_file, "README file"),
            (scrapy_cfg, "Scrapy config file")
        ]:
            if os.path.exists(marker):
                secondary_score += 1
                self.logger.debug(f"✓ {desc} trovato: {marker}")
            else:
                self.logger.debug(f"✗ {desc} mancante: {marker}")
                
        total_score = primary_score + secondary_score
        is_valid = primary_score >= 3  # Almeno data + src
        
        self.logger.debug(f"Validazione {path}: primary={primary_score}, secondary={secondary_score}, total={total_score}, valid={is_valid}")
        return is_valid

    def _verify_directories(self):
        """Verifica e crea le directory necessarie con logging migliorato"""
        
        # Lista delle directory e file da verificare
        paths_to_check = [
            {
                'path': self.data_file,
                'type': 'file',
                'description': 'File di input',
                'critical': True
            },
            {
                'path': os.path.dirname(self.raw_path),
                'type': 'directory',
                'description': 'Directory output raw',
                'critical': False
            },
            {
                'path': os.path.dirname(self.state_file),
                'type': 'directory', 
                'description': 'Directory temp/state',
                'critical': False
            },
            {
                'path': os.path.join(self.root_dir, 'logs'),
                'type': 'directory',
                'description': 'Directory logs',
                'critical': False
            }
        ]
        
        self.logger.info("=== VERIFICA STRUTTURA DIRECTORY ===")
        self.logger.info(f"PROJECT_ROOT: {self.root_dir}")
        
        all_ok = True
        
        for item in paths_to_check:
            path = item['path']
            path_type = item['type']
            description = item['description']
            critical = item['critical']
            
            if path_type == 'file':
                # Per i file, verifica la directory padre e il file stesso
                dir_path = os.path.dirname(path)
                
                # Verifica directory padre
                if os.path.exists(dir_path):
                    self.logger.info(f"✓ Directory per {description}: {dir_path}")
                else:
                    self.logger.warning(f"✗ Directory per {description} mancante: {dir_path}")
                    try:
                        os.makedirs(dir_path, exist_ok=True)
                        self.logger.info(f"✓ Directory creata: {dir_path}")
                    except Exception as e:
                        self.logger.error(f"✗ Errore creazione directory {dir_path}: {e}")
                        if critical:
                            all_ok = False
                
                # Verifica file
                if os.path.exists(path):
                    file_size = os.path.getsize(path)
                    self.logger.info(f"✓ {description} trovato: {path} ({file_size} byte)")
                else:
                    self.logger.error(f"✗ {description} MANCANTE: {path}")
                    if critical:
                        all_ok = False
                        self.logger.error("ERRORE CRITICO: File di input necessario per continuare!")
            
            elif path_type == 'directory':
                if os.path.exists(path):
                    self.logger.info(f"✓ {description}: {path}")
                else:
                    self.logger.warning(f"✗ {description} mancante: {path}")
                    try:
                        os.makedirs(path, exist_ok=True)
                        self.logger.info(f"✓ {description} creata: {path}")
                    except Exception as e:
                        self.logger.error(f"✗ Errore creazione {description} {path}: {e}")
                        if critical:
                            all_ok = False
        
        self.logger.info("=== FINE VERIFICA DIRECTORY ===")
        
        if not all_ok:
            self.logger.error("ATTENZIONE: Alcuni elementi critici sono mancanti!")
            self.logger.error("Verifica la struttura del progetto e i processi precedenti.")
        
        return all_ok

    def _on_sigint(self, signum, frame):
        self.logger.info("SIGINT ricevuto: CloseSpider")
        self._manual_save_results()  # Salva i risultati prima di chiudere
        raise CloseSpider("shutdown")

    def start_requests(self):
        # resume
        if os.path.exists(self.state_file):
            try:
                state = json.load(open(self.state_file))
                self.last_index = state.get("last_index", 0)
                self.logger.info(f"Ripresa dall'indice {self.last_index}")
                self.logger.info(f"Info state: {state}")
            except Exception as e:
                self.logger.error(f"Errore caricamento state: {e}")

        if not os.path.exists(self.data_file):
            self.logger.error(f"Input mancante: {self.data_file}")
            self.logger.error("Verifica la struttura del progetto e che lo step precedente sia completato")
            return

        try:
            data = json.load(open(self.data_file, encoding="utf-8"))
            self.aziende = [s for item in data for s in item.get("strutture", [item])]
            
            # Debug primi elementi
            if self.aziende:
                self.logger.info(f"Primi 3 elementi: {self.aziende[:3]}")
            else:
                self.logger.error("Nessun dato trovato nel file di input!")
                return
                
            self.logger.info(f"{len(self.aziende)} businesses, resuming at {self.last_index}")
            
            for idx, struct in enumerate(self.aziende[self.last_index:], start=self.last_index):
                struct["__index"] = idx
                nome, citta = struct.get("nome"), struct.get("città")
                if not nome or not citta:
                    self.logger.warning(f"Elemento {idx} mancante di nome o città, skip")
                    continue
                    
                q   = urllib.parse.quote_plus(f"{nome} {citta}")
                url = f"https://www.google.com/maps/search/{q}"
                self.logger.info(f"Scheduling [{idx}]: {nome} — {url}")
                
                yield SeleniumRequest(
                    url=url,
                    callback=self.parse,
                    meta={"struct": struct},
                    wait_time=1,  # Ridotto per velocità
                    dont_filter=True,
                )
        except Exception as e:
            self.logger.error(f"Errore inizializzazione: {traceback.format_exc()}")

    def parse(self, response):
        struct = response.meta["struct"]
        driver = response.meta["driver"]
        url    = response.url
        idx    = struct['__index']

        self.logger.info(f"Parsing [{idx}]: {url}")
        self.logger.info(f"URL corrente driver: {driver.current_url}")
        
        try:
            output_item = self._try_parse(response)
            # Debug output
            self.logger.info(f"Risultato [{idx}]: rating={output_item.get('rating')}, reviews={output_item.get('review_count')}")
            output_item["google_url"] = driver.current_url
            
            # Aggiungi il risultato alla lista per il backup
            self.results.append(output_item)
            
            # Salva manualmente i risultati ogni 5 elementi (più frequente)
            if idx % 5 == 0:
                self._manual_save_results()
                
            # Salva stato e aggiorna indice
            self._save_state(idx + 1)  # Importante: incrementa indice  
            yield output_item
        except CloseSpider:
            raise
        except Exception as e:
            self.logger.error(f"ERROR [{idx}] {struct.get('nome')}: {e}")
            self.logger.error(traceback.format_exc())
            output_item = dict(struct)
            output_item["rating"] = None
            output_item["review_count"] = None
            output_item["error"] = str(e)

            # Aggiungi anche risultati con errore
            self.results.append(output_item)
            
            self._save_state(idx + 1)
            yield output_item
        finally:
            # Chiudi sempre il driver a fine elaborazione
            close_driver = response.meta.get('close_driver_callback')
            if close_driver:
                close_driver(response)
            elif driver:
                try:
                    driver.quit()
                    self.logger.info(f"Driver chiuso manualmente")
                except Exception as e:
                    self.logger.error(f"Errore chiusura driver: {e}")

    def _try_parse(self, response):
        driver = response.meta["driver"]
        struct = response.meta["struct"] 
        idx    = struct["__index"]
        nome   = struct.get("nome", "")
        citta  = struct.get("città", "")
        exp_adr= struct.get("indirizzo", "").lower().strip()
        wait   = WebDriverWait(driver, 4)  # Ottimizzato per velocità

        # Verifica consenso cookie (ottimizzato)
        if "consent.google.com" in driver.current_url:
            self.logger.info("Rilevata pagina consenso cookie")
            if self._accept_cookies_fast(driver):
                driver.refresh()
                time.sleep(1)  # Ridotto per velocità
        try:
        # Timeout più aggressivo
            WebDriverWait(driver, 3).until(lambda d: 
            "maps/place" in d.current_url or 
            d.find_elements(By.CSS_SELECTOR, "a.hfpxzc"))
        except Exception as e:
        # Se timeout, prova comunque a procedere
            self.logger.warning(f"Timeout attesa, procedo comunque: {e}")
            
        self.logger.info(f"Page title: {driver.title}")
        self.logger.info(f"Current URL: {driver.current_url}")

        # Attendi posto o risultati con gestione timeout ottimizzata
        try:
            wait.until(lambda d: "maps/place" in d.current_url or 
                                d.find_elements(By.CSS_SELECTOR, "a.hfpxzc"))
            self.logger.info("Elemento di ricerca trovato")
        except Exception as e:
            self.logger.error(f"Timeout attesa elementi: {e}")
            raise Exception(f"Pagina non caricata in tempo: {e}")

        # Se lista risultati, scegli best match
        if "maps/place" not in driver.current_url:
            self.logger.info("Pagina di risultati - cercando il miglior match")
            els = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.hfpxzc")))
            self.logger.info(f"Trovati {len(els)} risultati possibili")
            
            best, best_score = None, (0,0,0)
            for i, el in enumerate(els):
                lbl = el.get_attribute("aria-label") or ""
                self.logger.info(f"Risultato {i}: {lbl}")
                score = check_location_similarity(nome, citta, lbl)
                self.logger.info(f"Score: {score}")
                if score[0] > best_score[0]:
                    best_score, best = score, el
                    
            if not best or best_score[0] < self.MIN_COMBINED:
                self.logger.error(f"Nessun risultato con score sufficiente. Miglior score: {best_score}")
                raise Exception("No matching result")
                
            self.logger.info(f"Miglior match trovato con score {best_score}")
            driver.execute_script("arguments[0].click()", best)
            wait.until(lambda d: "maps/place" in d.current_url)
            self.logger.info(f"Nuova URL: {driver.current_url}")

        # Verifica chiusura
        if "chiuso definitivamente" in driver.page_source.lower():
            self.logger.info("Locale chiuso definitivamente")
            struct["rating"] = None
            struct["review_count"] = None
            return struct

        # Verifica indirizzo (con timeout ridotto)
        try:
            adr_el = WebDriverWait(driver, 2).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "button[data-item-id='address']")))
            found = adr_el.text.lower().strip()
            self.logger.info(f"Indirizzo trovato: {found}")
            
            if exp_adr and found:
                addr_sim = similar(normalize_address(exp_adr), normalize_address(found))
                self.logger.info(f"Similarità indirizzo: {addr_sim}")
                if addr_sim < self.MIN_ADDR:
                    self.logger.warning(f"Indirizzo non corrisponde: atteso '{exp_adr}', trovato '{found}'")
                    raise Exception("Address mismatch")
        except Exception as e:
            self.logger.warning(f"Errore verifica indirizzo: {e}")
            # Continua anche se l'indirizzo non è verificabile

        # rating & reviews con selettori ottimizzati (meno tentativi)
        rating = review_count = None
        for r_sel, rv_sel in [
            ("div.F7nice span[aria-hidden='true']", "div.F7nice span[aria-label*='recensioni']"),
            ("span.fontDisplayLarge", "button[aria-label*='recensioni']"),
            ("span.ceHGZc", "button.HHrUdb"),
            ("div.fontBodyMedium.dmRWX span.ceHGZc", "div.fontBodyMedium.dmRWX span[aria-label]"),
        ]:
            try:
                self.logger.debug(f"Tentativo selettore: {r_sel}")
                r = driver.find_element(By.CSS_SELECTOR, r_sel).text.strip()
                rv = driver.find_element(By.CSS_SELECTOR, rv_sel).text
                rv = "".join(filter(str.isdigit, rv))
                if r or rv:
                    rating, review_count = r or None, rv or None
                    self.logger.info(f"Rating trovato: {rating}, reviews: {review_count}")
                    break
            except Exception as e:
                self.logger.debug(f"Selettore fallito ({r_sel}): {e}")
                continue

        struct["rating"] = rating
        struct["review_count"] = review_count
        self.logger.info(f"[{idx}] Risultato → rating={rating}, reviews={review_count}")
        return struct
    
    def _accept_cookies_fast(self, driver):
        """Versione velocizzata accettazione cookie"""
        try:
            # Prova solo i selettori più comuni, timeout più breve
            for xpath in [
                "//button[contains(@jsname,'tWT92d')]",  # Il più specifico per Google
                "//button[contains(text(),'Accetta tutto')]",
            ]:
                try:
                    btn = WebDriverWait(driver, 2).until(  # ERA 5, ora 2
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    driver.execute_script("arguments[0].click()", btn)
                    time.sleep(0.5)  # ERA 2, ora 0.5
                    return True
                except:
                    continue
        except:
            pass
        return False
    
    def _save_state(self, idx):
        try:
            state = {
                "last_index": idx,
                "region": self.region,
                "category": self.category,
                "timestamp": time.time(),
                "items_processed": idx,
                "total_items": len(self.aziende) if hasattr(self, 'aziende') else 0,
                "progress_percentage": round((idx / len(self.aziende) * 100), 2) if hasattr(self, 'aziende') and len(self.aziende) > 0 else 0
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            self.logger.info(f"State saved at index {idx}")
        except Exception as e:
            self.logger.error(f"Errore salvataggio state: {e}")

    def _manual_save_results(self):
        """Salva manualmente i risultati come backup"""
        if not self.results:
            self.logger.info("Nessun risultato da salvare")
            return
            
        try:
            # Assicurati che la directory esista
            os.makedirs(os.path.dirname(self.raw_path), exist_ok=True)
            
            # Salva nel percorso principale
            with open(self.raw_path, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Salvataggio manuale completato: {self.raw_path}")
            
            # Crea un backup per sicurezza
            backup_file = os.path.join(
                os.path.dirname(self.raw_path), 
                f"{self.region}_{self.category}_backup_{int(time.time())}.json"
            )
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Backup salvato in: {backup_file}")
            
        except Exception as e:
            self.logger.error(f"Errore salvataggio manuale: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")

    def _accept_cookies(self, driver):
        self.logger.info("Tentativo accettazione cookie")
        try:
            for xpath in [
                "//button[contains(text(),'Accetta tutto')]",
                "//button[contains(text(),'Acconsento')]", 
                "//button[contains(@aria-label,'Accetta')]",
                "//button[contains(@jsname,'tWT92d')]"
            ]:
                try:
                    btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    self.logger.info(f"Pulsante cookie trovato: {xpath}")
                    driver.execute_script("arguments[0].click()", btn)
                    time.sleep(2)  # Breve pausa dopo il click
                    return True
                except Exception as e:
                    self.logger.debug(f"Pulsante non trovato ({xpath}): {e}")
                    continue
        except Exception as e:
            self.logger.error(f"Errore nell'accettazione cookie: {e}")
        return False

    def close(self, reason):
        """Override del metodo close per salvare i risultati"""
        self._manual_save_results()
        self._save_state(self.last_index)
        self.logger.info("Spider closed: " + reason)
        super().close(reason)

    def spider_closed(self, spider):
        self._save_state(self.last_index)
        self._manual_save_results()
        self.logger.info("Spider closed cleanly")