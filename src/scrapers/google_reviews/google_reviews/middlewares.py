import tempfile
import os
import time
import shutil
import glob
import stat

from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from scrapy_selenium import SeleniumRequest


class CustomSeleniumMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        driver_name = settings.get('SELENIUM_DRIVER_NAME', 'chrome')
        executable_path = settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH')
        driver_arguments = settings.getlist('SELENIUM_DRIVER_ARGUMENTS')
        middleware = cls(driver_name, executable_path, driver_arguments)
        return middleware

    def __init__(self, driver_name, executable_path, driver_arguments):
        self.driver_name = driver_name
        self.executable_path = executable_path or self._get_chromedriver_path()
        self.driver_arguments = driver_arguments
        print(f"[DEBUG] CustomSeleniumMiddleware inizializzato con: {self.executable_path}")

    def _get_chromedriver_path(self):
        try:
            path = ChromeDriverManager().install()
            print(f"[DEBUG] ChromeDriver installato in: {path}")
            if not path.lower().endswith("chromedriver.exe"):
                directory = os.path.dirname(path)
                candidate = os.path.join(directory, "chromedriver.exe")
                if os.path.isfile(candidate):
                    print(f"[DEBUG] Eseguibile trovato: {candidate}")
                    path = candidate
                else:
                    print(f"[DEBUG] Eseguibile non trovato in: {directory}")
            return path
        except Exception as e:
            raise RuntimeError(f"Errore durante l'installazione di ChromeDriver: {e}")

    def _create_driver(self):
        options = webdriver.ChromeOptions()
        for argument in self.driver_arguments:
            options.add_argument(argument)
        # Disabilita il caricamento delle immagini per velocizzare il caricamento delle pagine
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        # Creazione di un profilo temporaneo per questo driver
        user_data_dir = tempfile.mkdtemp()
        options.add_argument(f"--user-data-dir={user_data_dir}")
        try:
            service = Service(self.executable_path)
            driver = webdriver.Chrome(service=service, options=options)
            return driver, user_data_dir
        except WebDriverException as e:
            try:
                if os.path.exists(user_data_dir):
                    shutil.rmtree(user_data_dir, ignore_errors=True)
            except Exception as cleanup_error:
                print(f"[DEBUG] Cleanup error: {cleanup_error}")
            raise RuntimeError(f"Errore nell'avvio di ChromeDriver: {e}")

    @staticmethod
    def _on_rm_error(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            print(f"[DEBUG] Errore nel cambio dei permessi di {path}: {e}")

    def cleanup_chrome_bits(self):
        temp_dir = tempfile.gettempdir()
        pattern = os.path.join(temp_dir, "chrome_BITS_*")
        for folder in glob.glob(pattern):
            try:
                time.sleep(1)  # Attende brevemente per garantire che le risorse siano rilasciate
                shutil.rmtree(folder, onerror=self._on_rm_error)
                print(f"[DEBUG] Rimosso: {folder}")
            except Exception as e:
                print(f"[DEBUG] Errore nella rimozione di {folder}: {e}")

    def process_request(self, request, spider):
        # Gestisci solo le richieste SeleniumRequest
        if not isinstance(request, SeleniumRequest):
            return None
            
        print(f"[DEBUG] Elaborazione richiesta Selenium: {request.url}")
        driver, user_data_dir = self._create_driver()
        
        # Ottieni wait_time dal meta
        wait_time = request.meta.get('wait_time', 5)
        
        try:
            driver.get(request.url)
            time.sleep(wait_time)  # Attesa dopo caricamento pagina
            
            # Verifica se è presente una pagina di consenso cookie
            if "consent.google.com" in driver.current_url:
                self._accept_cookies(driver)
                driver.refresh()
                time.sleep(3)  # Attesa extra dopo refresh
            
            body = str.encode(driver.page_source)
            
            # Debug
            print(f"[DEBUG] URL corrente: {driver.current_url}")
            print(f"[DEBUG] Lunghezza pagina: {len(driver.page_source)}")
            
            response = HtmlResponse(
                driver.current_url, 
                body=body, 
                encoding='utf-8', 
                request=request
            )
            
            # Aggiungi il driver alla risposta
            response.meta['driver'] = driver
            response.meta['user_data_dir'] = user_data_dir

            def close_driver(response):
                print(f"[DEBUG] Chiusura driver per {request.url}")
                if driver:
                    try:
                        driver.quit()
                        print(f"[DEBUG] Driver chiuso con successo")
                    except Exception as e:
                        print(f"[DEBUG] Errore chiusura driver: {e}")
                
                if os.path.exists(user_data_dir):
                    try:
                        shutil.rmtree(user_data_dir, ignore_errors=True)
                        print(f"[DEBUG] Cartella utente rimossa: {user_data_dir}")
                    except Exception as e:
                        print(f"[DEBUG] Errore rimozione cartella: {e}")
                        
                self.cleanup_chrome_bits()
                return response
            
            # Registra la callback
            request.meta['close_driver_callback'] = close_driver
            
            # Crea una nuova funzione quit con pulizia
            original_quit = driver.quit
            def quit_and_cleanup():
                print(f"[DEBUG] Chiusura driver e pulizia risorse")
                original_quit()
                try:
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                    self.cleanup_chrome_bits()
                except Exception as e:
                    print(f"[DEBUG] Errore durante la pulizia: {e}")
                    
            driver.quit = quit_and_cleanup
            
            return response
        except Exception as e:
            print(f"[DEBUG] Errore durante il processo della richiesta: {e}")
            if driver:
                driver.quit()
            if os.path.exists(user_data_dir):
                shutil.rmtree(user_data_dir, ignore_errors=True)
            raise
            
    def _accept_cookies(self, driver):
        print("[DEBUG] Tentativo di accettare i cookie")
        try:
            for xpath in [
                "//button[contains(text(),'Accetta tutto')]",
                "//button[contains(text(),'Acconsento')]", 
                "//button[contains(@aria-label,'Accetta')]",
                "//button[contains(@jsname,'tWT92d')]"
            ]:
                try:
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC
                    
                    btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    print(f"[DEBUG] Pulsante cookie trovato: {xpath}")
                    driver.execute_script("arguments[0].click()", btn)
                    time.sleep(2)  # Breve pausa dopo il click
                    return True
                except Exception as e:
                    print(f"[DEBUG] Pulsante non trovato ({xpath}): {e}")
                    continue
        except Exception as e:
            print(f"[DEBUG] Errore nell'accettazione cookie: {e}")
        return False