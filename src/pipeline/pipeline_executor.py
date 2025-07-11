#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import logging
import argparse
import datetime
import time
from pathlib import Path

class PipelineExecutor:
    def __init__(self, region=None, category=None, base_path=None, debug=False):
            """
            Inizializza l'esecutore della pipeline
        
            Args:
                region (str): Regione di destinazione (es. 'emilia_romagna')
                category (str): Categoria di destinazione (es. 'ristoranti')
                base_path (str, optional): Percorso base del progetto
                debug (bool): Attiva modalità debug
            """
            # creazione logger
            self.logger = logging.getLogger(f"PipelineExecutor.{region}.{category}")
            if not self.logger.handlers:  # Evita duplicazione handler
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
            
            self.region = region
            self.category = category
            self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
            self.debug = debug
            self._stop_requested = False
            
            # Salire di una directory se siamo in src/pipeline
            if os.path.basename(os.path.dirname(self.base_path)) == "src" and os.path.basename(self.base_path) == "pipeline":
                self.base_path = os.path.dirname(os.path.dirname(self.base_path))
        
            self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
            # Rileva se siamo in un ambiente virtuale e prepara il comando Python appropriato
            self.python_cmd = self._get_python_command()
        
            # Verifica e crea le cartelle necessarie
            self._setup_directories()
        
            if region and category:
                self.logger.info(f"Pipeline inizializzata per regione '{region}' e categoria '{category}'")
            self.logger.info(f"Base path: {self.base_path}")
            self.logger.info(f"Python command: {self.python_cmd}")
            
    def test_communication(self):
        """Testa la comunicazione con la GUI"""
        self.logger.info("Test di comunicazione dalla pipeline")
        return True

    def stop(self):
        """Richiede l'interruzione della pipeline"""
        self._stop_requested = True
        self.logger.info("Richiesta interruzione pipeline")

    def run_step(self, region, category, step, progress_callback=None):
        """
        Esegue un singolo step della pipeline
        
        Args:
            region (str): Regione target
            category (str): Categoria target
            step (int): Numero dello step da eseguire (1-4)
            progress_callback (callable): Callback per aggiornare il progresso
            
        Returns:
            bool: True se lo step è completato con successo
        """
        # Validazione più robusta
        if not isinstance(step, int) or step < 1 or step > 4:
            self.logger.error(f"Step {step} non valido. Deve essere tra 1 e 4.")
            return False
        
        # Aggiorna i parametri se necessario
        self.region = region
        self.category = category
        
        # Reset del flag di stop
        self._stop_requested = False
        
        # Mappa degli step
        steps = {
            1: (self.step1_collect_pagine_gialle, "Raccolta dati Pagine Gialle"),
            2: (self.step2_normalize_pagine_gialle_data, "Normalizzazione dati Pagine Gialle"),
            3: (self.step3_collect_google_reviews, "Raccolta rating e recensioni"),
            4: (self.step4_normalize_review_data, "Normalizzazione dati con recensioni")
        }
        
        if step not in steps:
            self.logger.error(f"Step {step} non valido. Deve essere tra 1 e 4.")
            return False
        
        step_func, step_name = steps[step]
        
        self.logger.info(f"Esecuzione step {step}: {step_name}")
        
        # Callback di progresso iniziale
        if progress_callback:
            progress_callback(0, 1)
        
        try:
            # Verifica se è stata richiesta l'interruzione
            if self._stop_requested:
                self.logger.info("Esecuzione interrotta dall'utente")
                return False
            
            success = step_func()
            
            # Callback di progresso finale
            if progress_callback:
                progress_callback(1, 1)
            
            if success:
                self.logger.info(f"Step {step} completato con successo")
            else:
                self.logger.error(f"Step {step} fallito")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Errore durante l'esecuzione dello step {step}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def run_full_pipeline(self, progress_callback=None):
        """
        Esegue l'intera pipeline
        
        Args:
            progress_callback (callable): Callback per aggiornare il progresso
            
        Returns:
            bool: True se tutti gli step sono completati con successo
        """
        total_steps = 4
        
        for step in range(1, total_steps + 1):
            if progress_callback:
                progress_callback(step - 1, total_steps)
            
            success = self.run_step(self.region, self.category, step)
            
            if not success:
                self.logger.error(f"Pipeline interrotta allo step {step}")
                return False
            
            if self._stop_requested:
                self.logger.info("Pipeline interrotta dall'utente")
                return False
        
        if progress_callback:
            progress_callback(total_steps, total_steps)
        
        self.logger.info("Pipeline completata con successo")
        return True

    def _get_python_command(self):
        """
        Rileva il comando Python appropriato da usare nei subprocess.
        Se siamo in un venv, usa il Python del venv, altrimenti usa sys.executable.
        """
        # Controlla se siamo in un ambiente virtuale
        venv_path = os.environ.get('VIRTUAL_ENV')

        if venv_path:
            self.logger.info(f"Virtual environment rilevato: {venv_path}")
            # Costruisci il percorso al Python del venv
            if sys.platform == 'win32':
                python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
            else:
                python_path = os.path.join(venv_path, 'bin', 'python')

            if os.path.exists(python_path):
                self.logger.info(f"Utilizzo Python del venv: {python_path}")
                return f'"{python_path}"'
            else:
                self.logger.warning(f"Python del venv non trovato in {python_path}, uso sys.executable")

        # Fallback a sys.executable (il Python corrente)
        return f'"{sys.executable}"'
   
    def _get_scrapy_command(self):
        """
        Ottiene il comando Scrapy appropriato per l'ambiente corrente.
        Prioritizza l'uso di 'python -m scrapy' che è più affidabile.
        """
        # Prima opzione: usa sempre python -m scrapy (più affidabile)
        scrapy_cmd = f'{self.python_cmd} -m scrapy'
        self.logger.debug(f"Utilizzo comando Scrapy: {scrapy_cmd}")
        return scrapy_cmd
   
    def _setup_directories(self):
        """Crea le directory necessarie per la pipeline se non esistono"""
        paths = [
            "temp",
            "logs",
            "logs/pipeline_reports"
        ]
        
        # Aggiungi percorsi specifici se region e category sono definiti
        if self.region and self.category:
            paths.extend([
                f"data/raw/raw_post_pagine_gialle/{self.region}/{self.category}",
                f"data/raw/raw_post_google_reviews/{self.region}/{self.category}",
                f"data/processed_data/clean_post_pagine_gialle/{self.region}",
                f"data/processed_data/clean_post_google_reviews/{self.region}",
            ])
       
        for path in paths:
            full_path = os.path.join(self.base_path, path)
            os.makedirs(full_path, exist_ok=True)
            self.logger.debug(f"Directory verificata/creata: {full_path}")
   
    def execute_command(self, command, cwd=None, description="", capture_output=True, timeout=300):
        """
        Esegue un comando di sistema con gestione degli errori migliorata
       
        Args:
            command (str): Comando da eseguire
            cwd (str, optional): Directory di lavoro
            description (str, optional): Descrizione del comando per i log
            capture_output (bool): Se catturare l'output o mostrarlo direttamente sul terminale
            timeout (int): Timeout in secondi per il comando
           
        Returns:
            bool: True se l'esecuzione è riuscita, False altrimenti
        """
        if self._stop_requested:
            self.logger.info("Comando interrotto: stop richiesto")
            return False
            
        start_time = time.time()
        self.logger.info(f"Esecuzione: {description}")
        self.logger.debug(f"Comando completo: {command}")
        self.logger.debug(f"Directory di lavoro: {cwd if cwd else os.getcwd()}")
       
        # Copia l'ambiente corrente per mantenere le variabili del venv
        env = os.environ.copy()
       
        try:
            if capture_output:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=cwd,
                    env=env
                )
               
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    self.logger.error(f"Timeout ({timeout}s) per comando: {description}")
                    return False
               
                if process.returncode != 0:
                    self.logger.error(f"Errore nell'esecuzione di: {description}")
                    self.logger.error(f"Return code: {process.returncode}")
                    if stdout:
                        self.logger.error(f"Stdout: {stdout}")
                    if stderr:
                        self.logger.error(f"Stderr: {stderr}")
                    return False
                else:
                    # Log dell'output anche in caso di successo
                    if stdout:
                        self.logger.debug(f"Output comando: {stdout[:500]}...")
            else:
                # Esegui il comando mostrando direttamente l'output nel terminale
                result = subprocess.run(
                    command,
                    shell=True,
                    cwd=cwd,
                    check=False,
                    env=env,
                    timeout=timeout
                )
                if result.returncode != 0:
                    self.logger.error(f"Errore nell'esecuzione di: {description}. Codice: {result.returncode}")
                    return False
    
            elapsed_time = time.time() - start_time
            self.logger.info(f"Completato: {description} in {elapsed_time:.2f} secondi")
            return True       
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout ({timeout}s) per comando: {description}")
            return False
        except Exception as e:
            self.logger.error(f"Eccezione durante: {description}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _load_region_paesi(self):
        """
        Carica il file regioni_paesi.json per ottenere l'elenco dei paesi per la regione
        con il loro corrispondente URL path

        Returns:
            list: Lista dei dizionari contenenti nome e url_path per la regione specificata
        """
        try:
            # Prova diversi percorsi possibili per il file
            possible_paths = [
                os.path.join(self.base_path, "config/regioni_paesi.json"),
                os.path.join(self.base_path, "src/scrapers/pagine_gialle_scraper/spiders/regioni_paesi.json"),
                os.path.join(self.base_path, "scrapers/pagine_gialle_scraper/spiders/regioni_paesi.json"),
            ]
            file_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    file_path = path
                    self.logger.info(f"File regioni_paesi.json trovato in: {path}")
                    break

            if not file_path:
                self.logger.error(f"Il file regioni_paesi.json non è stato trovato in nessuno dei percorsi possibili")
                self.logger.error(f"Percorsi controllati: {possible_paths}")
                return []

            with open(file_path, 'r', encoding='utf-8') as f:
                region_data = json.load(f)

            # Mostra una panoramica delle regioni disponibili
            available_regions = list(region_data.keys())
            self.logger.info(f"Regioni disponibili nel file: {', '.join(available_regions)}")

            # Verifica se la regione esiste nel file
            if self.region.lower() in region_data:
                region_info = region_data[self.region.lower()]
                paesi = region_info.get('paesi', [])

                if paesi:
                    self.logger.info(f"Trovati {len(paesi)} paesi per la regione '{self.region}'")
                    # Debug: mostra alcuni paesi come esempio
                    sample = paesi[:3] if len(paesi) > 3 else paesi
                    self.logger.debug(f"Esempio paesi: {json.dumps(sample, indent=2)}")
                    return paesi
                else:
                    self.logger.warning(f"Nessun paese trovato per la regione '{self.region}'")
                    return []
            else:
                self.logger.warning(f"La regione '{self.region}' non è presente nel file regioni_paesi.json")
                self.logger.info(f"Regioni disponibili: {', '.join(available_regions)}")
                return []

        except Exception as e:
            self.logger.error(f"Errore nel caricamento del file regioni_paesi.json: {e}")
            import traceback
            self.logger.error(f"Dettagli: {traceback.format_exc()}")
            return []

    def check_scrapy_installation(self):
        """Verifica che Scrapy sia installato e funzionante."""
        self.logger.info("Verifica dell'installazione di Scrapy...")

        # Test più semplice e affidabile
        test_cmd = f"{self.python_cmd} -c \"import scrapy; print('Scrapy version:', scrapy.__version__)\""

        self.logger.debug(f"Tentativo verifica Scrapy con: {test_cmd}")
        if self.execute_command(
            test_cmd,
            description="Verifica importazione Scrapy",
            capture_output=True,
            timeout=30
        ):
            self.logger.info("Scrapy verificato con successo")
           
            # Test aggiuntivo per verificare il comando scrapy
            scrapy_cmd = self._get_scrapy_command()
            version_cmd = f"{scrapy_cmd} version"
            self.logger.debug(f"Test comando scrapy: {version_cmd}")
           
            if self.execute_command(
                version_cmd,
                description="Test comando scrapy version",
                capture_output=True,
                timeout=30
            ):
                self.logger.info("Comando scrapy funzionante")
            else:
                self.logger.warning("Comando scrapy non funziona, ma Python può importare scrapy")
           
            return True
       
        self.logger.error("Scrapy non trovato o non funzionante")
        self.logger.error("Assicurati che Scrapy sia installato nel virtual environment:")
        self.logger.error("pip install scrapy")
        return False
   
    def check_spider_exists(self, spider_name, scrapy_path):
        """Verifica che lo spider specificato esista"""
        scrapy_cmd = self._get_scrapy_command()
        
        # Prima verifica che la directory del progetto scrapy sia valida
        scrapy_cfg_path = os.path.join(scrapy_path, "scrapy.cfg")
        if not os.path.exists(scrapy_cfg_path):
            self.logger.error(f"File scrapy.cfg non trovato in {scrapy_path}")
            return False
        
        # Lista gli spider disponibili e cerca quello specifico
        list_cmd = f"{scrapy_cmd} list"
        self.logger.info(f"Verifica spider disponibili in: {scrapy_path}")
        
        # Esegui il comando e cattura l'output
        try:
            result = subprocess.run(
                list_cmd,
                shell=True,
                cwd=scrapy_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                available_spiders = result.stdout.strip().split('\n')
                available_spiders = [s.strip() for s in available_spiders if s.strip()]
                
                self.logger.info(f"Spider disponibili: {available_spiders}")
                
                if spider_name in available_spiders:
                    self.logger.info(f"Spider '{spider_name}' trovato")
                    return True
                else:
                    self.logger.error(f"Spider '{spider_name}' non trovato tra: {available_spiders}")
                    return False
            else:
                self.logger.error(f"Errore nell'elencare gli spider: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Errore durante la verifica spider: {e}")
            return False
   
    def execute_command_list(self, command_list, cwd=None, description="", timeout=300):
        """
        Esegue un comando usando una lista di argomenti invece che una stringa
        
        Args:
            command_list (list): Lista degli argomenti del comando
            cwd (str, optional): Directory di lavoro
            description (str, optional): Descrizione del comando per i log
            timeout (int): Timeout in secondi per il comando
            
        Returns:
            bool: True se l'esecuzione è riuscita, False altrimenti
        """
        if self._stop_requested:
            self.logger.info("Comando interrotto: stop richiesto")
            return False
            
        start_time = time.time()
        self.logger.info(f"Esecuzione: {description}")
        self.logger.debug(f"Comando completo: {' '.join(command_list)}")
        self.logger.info(f"Directory di lavoro: {cwd if cwd else os.getcwd()}")
        
        # Copia l'ambiente corrente per mantenere le variabili del venv
        env = os.environ.copy()
        self.logger.debug(f"Comando finale: {command_list}")
        
        # Debug: Print each argument separately to check for issues
        self.logger.debug("Analisi argomenti del comando:")
        for i, arg in enumerate(command_list):
            self.logger.debug(f"  Arg {i}: '{arg}' (len: {len(arg)})")
            
        try:
            result = subprocess.run(
                command_list,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Errore nell'esecuzione di: {description}")
                self.logger.error(f"Return code: {result.returncode}")
                if result.stdout:
                    self.logger.error(f"Stdout: {result.stdout}")
                if result.stderr:
                    self.logger.error(f"Stderr: {result.stderr}")
                return False
            else:
                # Log dell'output anche in caso di successo
                if result.stdout:
                    self.logger.debug(f"Output comando: {result.stdout[:500]}...")
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Completato: {description} in {elapsed_time:.2f} secondi")
            return True
        
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout ({timeout}s) per comando: {description}")
            return False
        except Exception as e:
            self.logger.error(f"Eccezione durante: {description}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        

    def step1_collect_pagine_gialle(self):
        """Executes the Pagine Gialle spider to collect raw data into a single file"""
        self.logger.info("FASE 1: Raccolta dati da Pagine Gialle")
        
        if self._stop_requested:
            return False
            
        # Verifica installazione Scrapy
        if not self.check_scrapy_installation():
            self.logger.error("Scrapy non funzionante. Impossibile continuare.")
            return False
            
        # Carica i paesi
        paesi = self._load_region_paesi()
        if not paesi:
            self.logger.error("Impossibile continuare senza l'elenco dei paesi per la regione")
            return False
            
        self.logger.info(f"Elaborazione di {len(paesi)} paesi per la regione '{self.region}'")
        
        # Prepara file di output principale
        output_dir = os.path.join(self.base_path, "data", "raw", "raw_post_pagine_gialle",
                                self.region, self.category)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{self.region}_{self.category}_data.json")
        
        # === MODIFICA PRINCIPALE: NON ELIMINARE IL FILE SE ESISTE ===
        # Verifica se il file esiste e ha dati validi
        existing_data = []
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                self.logger.info(f"File esistente trovato con {len(existing_data)} record")
            except (json.JSONDecodeError, Exception) as e:
                self.logger.warning(f"File esistente corrotto o non valido: {e}. Sarà ricreato.")
                existing_data = []
        
        # Se il file non esiste o è corrotto, crealo vuoto
        if not os.path.exists(output_file) or not existing_data:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            self.logger.info(f"Creato file output principale: {output_file}")
            existing_data = []
        
        temp_dir = os.path.join(self.base_path, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Cartella del progetto Scrapy dedicato a Pagine Gialle
        scrapy_path = os.path.join(self.base_path, "src", "scrapers", "pagine_gialle_scraper")
        if not os.path.exists(scrapy_path):
            self.logger.error(f"Directory dello spider non trovata: {scrapy_path}")
            return False
        
        # Verifica che lo spider esista
        if not self.check_spider_exists("pagine_gialle_scraper", scrapy_path):
            self.logger.error("Spider 'pagine_gialle_scraper' non disponibile")
            return False
        
        # Carica lo stato dello scraping per determinare quali paesi processare
        scraping_state = self._load_scraping_state()
        
        scrapy_cmd = self._get_scrapy_command()
        all_success = True
        processed_countries = 0  # Contatore per i paesi effettivamente processati
        
        # Per ogni paese, controlla se deve essere processato o ripreso
        for i, paese in enumerate(paesi, 1):
            if self._stop_requested:
                self.logger.info("Interruzione richiesta durante la raccolta dati")
                return False
                
            nome_paese = paese.get('nome', '')
            url_base = paese.get('url_path', '')
            
            if not url_base:
                self.logger.warning(f"URL path mancante per '{nome_paese}', skip")
                continue
            
            url_pattern = f"{url_base.rstrip('/')}/{self.category}"
            
            # Controlla se questo paese è già stato completamente processato
            if self._is_paese_completed(nome_paese, scraping_state, existing_data):
                self.logger.info(f"[{i}/{len(paesi)}] {nome_paese}: già completato, skip")
                continue
            
            self.logger.info(f"[{i}/{len(paesi)}] {nome_paese}: {url_pattern}")
            processed_countries += 1  # Incrementa il contatore
            
            # Sanizza il nome del file temporaneo
            safe_nome_paese = nome_paese.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
            safe_nome_paese = ''.join(c for c in safe_nome_paese if c.isalnum() or c in ('_', '-'))
            temp_filename = f"temp_{safe_nome_paese}.json"
            temp_output = os.path.join(temp_dir, temp_filename)
            
            # Costruzione del comando come lista per evitare problemi con gli escape
            python_executable = self.python_cmd.strip('"')
            cmd_list = [
                python_executable,
                "-m", "scrapy",
                "crawl", "pagine_gialle_scraper",
                "-a", f"url_pattern={url_pattern}",
                "-a", f"region={self.region}",
                "-a", f"category={self.category}",
                "-o", f"{temp_output}"
            ]
            
            # Debug: mostra il comando che verrà eseguito
            self.logger.debug(f"Comando da eseguire: {' '.join(cmd_list)}")
        
            success = self.execute_command_list(
                cmd_list,
                cwd=scrapy_path,
                description=f"Raccolta dati per {nome_paese}",
                timeout=120
            )
        
            if not success:
                # CAMBIAMENTO IMPORTANTE: Non impostare all_success = False per singoli errori
                # all_success = False  # Commentato
                self.logger.warning(f"Fallito per {nome_paese}, continuo…")
                continue
                
            # Append dati temporanei al file principale
            if os.path.exists(temp_output) and os.path.getsize(temp_output) > 2:
                try:
                    with open(temp_output, 'r', encoding='utf-8') as tf:
                        temp_data = json.load(tf)
                    
                    # Leggi i dati attuali, aggiungi i nuovi, riscrivi
                    with open(output_file, 'r', encoding='utf-8') as mf:
                        main_data = json.load(mf)
                    
                    # Rimuovi eventuali duplicati basati su nome+indirizzo+citta
                    new_records = self._filter_duplicates(temp_data, main_data)
                    
                    if new_records:
                        main_data.extend(new_records)
                        
                        with open(output_file, 'w', encoding='utf-8') as mf:
                            json.dump(main_data, mf, indent=2)
                        
                        self.logger.info(f"Aggiunti {len(new_records)} nuovi record da {nome_paese} (duplicati filtrati: {len(temp_data) - len(new_records)})")
                    else:
                        self.logger.info(f"Nessun nuovo record da {nome_paese} (tutti duplicati)")
                        
                except Exception as e:
                    self.logger.error(f"Errore JSON append per {nome_paese}: {e}")
                    # Non impostare all_success = False per errori di processing
                    
            else:
                self.logger.warning(f"Nessun dato per {nome_paese}")
                
            # Pulisci file temporaneo
            if os.path.exists(temp_output):
                os.remove(temp_output)
        
        # Log totale
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                total = len(json.load(f))
            self.logger.info(f"Raccolta completata: {total} elementi totali")
        except Exception as e:
            self.logger.error(f"Errore lettura finale: {e}")
            return False  # Solo questo è un errore critico
        
        # LOGICA DI SUCCESSO MIGLIORATA:
        # Lo step è considerato riuscito se:
        # 1. Tutti i paesi già completati (processed_countries == 0) MA abbiamo dati
        # 2. Oppure abbiamo processato almeno qualche paese senza errori critici
        
        if processed_countries == 0:
            # Tutti i paesi erano già completati
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    total = len(json.load(f))
                if total > 0:
                    self.logger.info(f"Step 1 completato: tutti i paesi erano già processati, {total} record totali")
                    return True
                else:
                    self.logger.error("Nessun paese processato e nessun dato disponibile")
                    return False
            except:
                self.logger.error("Errore nella verifica dei dati finali")
                return False
        else:
            # Abbiamo processato almeno qualche paese
            self.logger.info(f"Step 1 completato: processati {processed_countries} paesi")
            return True  # Restituisci sempre True se abbiamo fatto qualche progresso

    
    def step2_normalize_pagine_gialle_data(self):
        """Normalizza i dati grezzi di Pagine Gialle"""
        self.logger.info("FASE 2: Normalizzazione dati Pagine Gialle")
        
        if self._stop_requested:
            return False
       
        # Costruisci il percorso verso lo script di pulizia
        script_path = os.path.join(
            self.base_path,
            "src", "data_processing", "data_cleaning_pagine_gialle", "cleanData.py"
        )                
        # Verifica che lo script esista
        if not os.path.exists(script_path):
            self.logger.error(f"Script di pulizia non trovato: {script_path}")
            return False
           
        cmd = (
            f"{self.python_cmd} \"{script_path}\""
            f" --region {self.region}"
            f" --category {self.category}"
            f" --base-path \"{self.base_path}\""
        )        
        return self.execute_command(
            cmd,
            description=f"Normalizzazione dati Pagine Gialle per {self.region} - {self.category}",
            capture_output=False,
            timeout=300
        )
   
    def step3_collect_google_reviews(self):
        """Raccoglie rating e recensioni da Google Maps"""
        self.logger.info("FASE 3: Raccolta rating e recensioni da Google Maps")
        
        if self._stop_requested:
            return False
       
        # Percorso specifico per lo spider Google Maps
        scrapy_path = os.path.join(
            self.base_path,
            "src", "scrapers", "google_reviews"
        )
        if not os.path.exists(scrapy_path):
            self.logger.error(f"Directory dello spider Google Maps non trovata: {scrapy_path}")
            return False
       
        # Verifica che lo spider esista
        if not self.check_spider_exists("google_reviews", scrapy_path):
            self.logger.error("Spider 'google_reviews' non disponibile")
            return False
       
        scrapy_cmd = self._get_scrapy_command()
       
        cmd = (
            f"{scrapy_cmd} crawl google_reviews "
            f"-a region=\"{self.region}\" "
            f"-a category=\"{self.category}\""
        )
        return self.execute_command(
            cmd,
            cwd=scrapy_path,
            description=f"Raccolta rating e recensioni per {self.region} - {self.category}",
            capture_output=False,
            timeout=600  # Timeout più lungo per le recensioni
        )
   
    def step4_normalize_review_data(self):
        """Normalizza i dati con recensioni e rating"""
        self.logger.info("FASE 4: Normalizzazione dati con recensioni e rating")
        
        if self._stop_requested:
            return False
       
        # Percorso dello script di pulizia per i dati con recensioni
        script_path = os.path.join(
            self.base_path,
            "src", "data_processing", "data_cleaning_reviews", "cleanDataReviews.py"
        )        
        # Verifica che lo script esista
        if not os.path.exists(script_path):
            self.logger.error(f"Script di pulizia recensioni non trovato: {script_path}")
            return False
           
        cmd = f"{self.python_cmd} \"{script_path}\" --region {self.region} --category {self.category}"
       
        return self.execute_command(
            cmd,
            description=f"Normalizzazione dati con recensioni per {self.region} - {self.category}",
            capture_output=False,
            timeout=300
        )
   
    def execute_pipeline(self):
        """Esegue l'intera pipeline dall'inizio alla fine"""
        self.logger.info(f"INIZIO PIPELINE per {self.region} - {self.category}")
        self.verify_project_structure()
        
        # Salva l'ora di inizio
        start_time = time.time()
       
        # Esegui ogni passaggio in sequenza, fermandoti se uno fallisce
        steps = [
            self.step1_collect_pagine_gialle,
            self.step2_normalize_pagine_gialle_data,
            self.step3_collect_google_reviews,
            self.step4_normalize_review_data
        ]
       
        step_names = [
            "Raccolta dati Pagine Gialle",
            "Normalizzazione dati Pagine Gialle",
            "Raccolta rating e recensioni",
            "Normalizzazione dati con recensioni"
        ]
       
        results = {}
       
        for i, (step, name) in enumerate(zip(steps, step_names), 1):
            if self._stop_requested:
                self.logger.info("Pipeline interrotta dall'utente")
                break
                
            self.logger.info(f"Esecuzione del passaggio {i}/{len(steps)}: {name}")
            step_start = time.time()
            success = step()
            step_time = time.time() - step_start
           
            results[name] = {
                "success": success,
                "time": f"{step_time:.2f} secondi"
            }
           
            if not success:
                self.logger.error(f"Il passaggio {i} ({name}) è fallito. Interrompo la pipeline.")
                break
       
        total_time = time.time() - start_time
        self.logger.info(f"FINE PIPELINE. Tempo totale: {total_time:.2f} secondi")
       
        # Salva un rapporto di esecuzione
        report = {
            "region": self.region,
            "category": self.category,
            "timestamp": self.timestamp,
            "total_time": f"{total_time:.2f} secondi",
            "steps": results
        }
       
        report_path = os.path.join(
            self.base_path,
            f"logs/pipeline_reports/report_{self.region}_{self.category}_{self.timestamp}.json"
        )
       
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
       
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
           
        self.logger.info(f"Report di esecuzione salvato in: {report_path}")
        return all(step["success"] for step in results.values())
   
    def verify_project_structure(self):
        """Verifica la struttura del progetto e mostra informazioni dettagliate per il debug"""
        self.logger.info("Verifica della struttura del progetto...")
       
        key_directories = [
            "src/scrapers/pagine_gialle_scraper",
            "src/scrapers/google_reviews",
            "src/data_processing/data_cleaning_pagine_gialle",
            "src/data_processing/data_cleaning_reviews",
            "logs/pipeline_reports",
            "data/raw/raw_post_pagine_gialle",
            "data/raw/raw_post_google_reviews"
        ]
       
        for directory in key_directories:
            path = os.path.join(self.base_path, directory)
            if os.path.exists(path):
                self.logger.info(f"Directory trovata: {path}")
                # Lista i primi 5 file nella directory
                try:
                    files = os.listdir(path)[:5]
                    if files:
                        self.logger.info(f"  Esempi di file: {files}")
                except PermissionError:
                    self.logger.warning(f"  Permessi insufficienti per leggere la directory")
            else:
                self.logger.warning(f"Directory mancante: {path}")
        
        # Verifica file di configurazione cruciali
        config_files = [
            "config/regioni_paesi.json",
            "src/scrapers/pagine_gialle_scraper/spiders/regioni_paesi.json"
        ]
        
        for config_file in config_files:
            path = os.path.join(self.base_path, config_file)
            if os.path.exists(path):
                self.logger.info(f"File di configurazione trovato: {path}")
            else:
                self.logger.warning(f"File di configurazione mancante: {path}")
        
        # Verifica file scrapy.cfg
        scrapy_configs = [
            "src/scrapers/pagine_gialle_scraper/scrapy.cfg",
            "src/scrapers/google_reviews/scrapy.cfg"
        ]
        
        for config_file in scrapy_configs:
            path = os.path.join(self.base_path, config_file)
            if os.path.exists(path):
                self.logger.info(f"File Scrapy config trovato: {path}")
            else:
                self.logger.warning(f"File Scrapy config mancante: {path}")
        
        return True
    def _load_scraping_state(self):
        """Carica lo stato dello scraping dal file state dello spider"""
        state_file = os.path.join(
            self.base_path, 
            "src", "scrapers", "pagine_gialle_scraper", "config", "scraping_state.json"
        )
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    state_data = json.loads(content) if content else {}
                    
                # Cerca lo stato per la combinazione corrente
                state_key = f"{self.region}_{self.category}"
                return state_data.get(state_key, {})
            except Exception as e:
                self.logger.error(f"Errore nel caricare lo stato dello scraping: {e}")
                return {}
        
        return {}

    def _is_paese_completed(self, nome_paese, scraping_state, existing_data):
        """
        Determina se un paese è già stato completamente processato.
        Un paese è considerato completato se:
        1. Ha dati nell'output finale E
        2. Non è presente nello stato di scraping (significa che lo scraping è terminato normalmente)
        """
        # Controlla se ci sono dati per questo paese nell'output
        has_data = any(
            record.get('paese', '').lower() == nome_paese.lower() or 
            record.get('citta', '').lower() == nome_paese.lower()
            for record in existing_data
        )
        
        # Se non ci sono dati, sicuramente non è completato
        if not has_data:
            return False
        
        # Se c'è ancora uno stato di scraping per questo paese, 
        # significa che lo scraping è stato interrotto
        has_pending_state = nome_paese in scraping_state
        
        # Completato = ha dati E non ha stato pendente
        is_completed = has_data and not has_pending_state
        
        if is_completed:
            self.logger.debug(f"Paese {nome_paese} considerato completato (ha dati, nessuno stato pendente)")
        else:
            self.logger.debug(f"Paese {nome_paese} da processare (dati: {has_data}, stato pendente: {has_pending_state})")
        
        return is_completed

    def _filter_duplicates(self, temp_data, main_data):
        """Filtra i record duplicati, gestendo sia i nuovi che i vecchi formati dei campi."""
        
        existing_ids = set()
        # Scansiona i dati già presenti e crea un identificatore univoco
        # Questo ciclo gestisce dati vecchi (italiano) e nuovi (inglese)
        for item in main_data:
            name = item.get('name_pg') or item.get('nome', 'N/A')
            address = item.get('address_pg') or item.get('indirizzo', 'N/A')
            city = item.get('city_pg') or item.get('citta', 'N/A')
            
            # Ignora record palesemente incompleti
            if name != 'N/A':
                identifier = f"{name}-{address}-{city}"
                existing_ids.add(identifier)

        unique_records = []
        # Scansiona i nuovi dati appena scaricati (che sono nel nuovo formato)
        for item in temp_data:
            # Qui usiamo direttamente i nuovi nomi dei campi
            name = item.get('name_pg', 'N/A')
            address = item.get('address_pg', 'N/A')
            city = item.get('city_pg', 'N/A')
            
            identifier = f"{name}-{address}-{city}"
            
            # Aggiungi il record solo se l'identificatore non è mai stato visto
            if name != 'N/A' and identifier not in existing_ids:
                unique_records.append(item)
                # Aggiungi l'ID al set per evitare di aggiungere duplicati presenti
                # nello stesso batch di dati temporanei.
                existing_ids.add(identifier)
                
        return unique_records

if __name__ == "__main__":
    # Configurazione del parser degli argomenti
    parser = argparse.ArgumentParser(description="Esecutore della pipeline di scraping e processamento dati")
    parser.add_argument("--region", required=True, help="Regione target (es. emilia_romagna)")
    parser.add_argument("--category", required=True, help="Categoria target (es. ristoranti)")
    parser.add_argument("--base-path", help="Percorso base del progetto")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], help="Esegui solo un passaggio specifico")
    parser.add_argument("--debug", action="store_true", help="Attiva modalità debug")
    
    args = parser.parse_args()
    
    # Imposta il livello di log se richiesto
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/pipeline_execution.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    if args.debug:
        logger.debug("Modalità DEBUG attivata")
    
    # Inizializza l'esecutore della pipeline
    executor = PipelineExecutor(args.region, args.category, args.base_path)
    
    # Esegui il passaggio specifico o l'intera pipeline
    if args.step:
        steps = {
            1: executor.step1_collect_pagine_gialle,
            2: executor.step2_normalize_pagine_gialle_data,
            3: executor.step3_collect_google_reviews,
            4: executor.step4_normalize_review_data
        }
        success = steps[args.step]()
        sys.exit(0 if success else 1)
    else:
        success = executor.execute_pipeline()
        sys.exit(0 if success else 1)