import os
import sys
import json
import logging
import threading
import time
import traceback
from flask import Flask, render_template, request, jsonify

# Assicurati che il percorso del progetto principale sia nel PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.insert(0, project_root)

# Aggiungi anche il percorso src al PYTHONPATH per l'importazione
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

# Importa PipelineExecutor dal tuo progetto principale
try:
    # Prova diverse possibilità di importazione
    try:
        from pipeline.pipeline_executor import PipelineExecutor
        print("Importazione riuscita: from pipeline.pipeline_executor import PipelineExecutor")
    except ImportError:
        try:
            from src.pipeline.pipeline_executor import PipelineExecutor
            print("Importazione riuscita: from src.pipeline.pipeline_executor import PipelineExecutor")
        except ImportError:
            # Importazione diretta dal file
            pipeline_executor_path = os.path.join(project_root, 'src', 'pipeline', 'pipeline_executor.py')
            if os.path.exists(pipeline_executor_path):
                spec = __import__('importlib.util').util.spec_from_file_location("pipeline_executor", pipeline_executor_path)
                pipeline_module = __import__('importlib.util').util.module_from_spec(spec)
                spec.loader.exec_module(pipeline_module)
                PipelineExecutor = pipeline_module.PipelineExecutor
                print("Importazione riuscita: caricamento diretto del modulo")
            else:
                raise ImportError(f"File pipeline_executor.py non trovato in {pipeline_executor_path}")
                
except ImportError as e:
    print(f"Errore nell'importazione di PipelineExecutor: {e}")
    print(f"Percorsi controllati:")
    print(f"  - {os.path.join(project_root, 'src', 'pipeline', 'pipeline_executor.py')}")
    print(f"  - Percorso progetto: {project_root}")
    print(f"  - Percorso src: {src_path}")
    print(f"  - PYTHONPATH attuale: {sys.path}")
    sys.exit(1)

app = Flask(__name__)

# --- Funzione per configurare le directory necessarie alla GUI ---
def setup_gui_directories(base_path):
    """Crea le directory necessarie per i log della GUI."""
    log_dir = os.path.join(base_path, "logs")
    os.makedirs(log_dir, exist_ok=True)
    print(f"Directory logs per GUI verificata/creata: {log_dir}")

# --- Chiama la funzione di setup all'avvio dell'app ---
setup_gui_directories(project_root)

# Configurazione del logger per la GUI
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(os.path.join(project_root, 'logs', 'gui_app.log')),
                        logging.StreamHandler()
                    ])
logger = logging.getLogger(__name__)

# Variabili globali per gestire lo stato della pipeline
pipeline_thread = None
pipeline_executor_instance = None
pipeline_status = {
    "running": False, 
    "step": 0, 
    "total_steps": 0, 
    "log": [], 
    "log_sequence": 0,  # Add this missing field
    "error": False, 
    "message": "",
    "start_time": None,
    "last_activity": None
}
lock = threading.Lock()  # Lock per la sincronizzazione dell'accesso a pipeline_status

# Definisci CallbackHandler prima di usarlo
class CallbackHandler(logging.Handler):
    """Handler personalizzato per reindirizzare i log della pipeline alla GUI."""
    
    def __init__(self):
        super().__init__()
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        """Emette un record di log utilizzando la callback della GUI."""
        try:
            log_callback(self.format(record), record.levelname.lower())
        except Exception as e:
            print(f"Errore nel callback handler: {e}")

# FUNZIONE MIGLIORATA per il callback dei log
def log_callback(message, level="info"):
    """Callback per reindirizzare i log della pipeline alla GUI."""
    try:
        with lock:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level.upper()}] {message}"
            # Aggiungi il log con numero di sequenza
            pipeline_status["log"].append(log_entry)
            pipeline_status["log_sequence"] += 1
            pipeline_status["last_activity"] = time.time()
            # Mantieni un numero limitato di log in memoria (aumentato per più storia)
            max_logs = 1000  # Aumentato da 500 a 1000
            if len(pipeline_status["log"]) > max_logs:
                # Rimuovi i log più vecchi mantenendo gli ultimi max_logs
                pipeline_status["log"] = pipeline_status["log"][-max_logs:]
            
        logger.info(f"Pipeline Log [{level.upper()}]: {message}")
    except Exception as e:
        logger.error(f"Errore in log_callback: {e}")
        # Fallback: scrivi almeno nel logger principale
        logger.error(f"Log fallback: {message}")


def progress_callback(current, total):
    """Callback per aggiornare il progresso della pipeline."""
    try:
        with lock:
            pipeline_status["step"] = current
            pipeline_status["total_steps"] = total
            pipeline_status["last_activity"] = time.time()
            progress_message = f"Progresso: Step {current}/{total}"
            pipeline_status["log"].append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [PROGRESS] {progress_message}")
            pipeline_status["log"] = pipeline_status["log"][-500:]
        
        logger.info(f"Progress update: {current}/{total}")
    except Exception as e:
        logger.error(f"Errore in progress_callback: {e}")

def run_pipeline_task(region, category, full_pipeline, specific_step):
    """Task eseguito in un thread separato per la pipeline."""
    global pipeline_executor_instance
    
    logger.info(f"Thread pipeline avviato - Region: {region}, Category: {category}, Full: {full_pipeline}, Step: {specific_step}")
    
    try:
        with lock:
            pipeline_status["running"] = True
            pipeline_status["error"] = False
            pipeline_status["message"] = "Pipeline avviata..."
            pipeline_status["log"] = []  # Resetta i log per la nuova esecuzione
            pipeline_status["log_sequence"] = 0  # Reset the log sequence counter
            pipeline_status["step"] = 0
            pipeline_status["total_steps"] = 0
            pipeline_status["start_time"] = time.time()
            pipeline_status["last_activity"] = time.time()

        log_callback(f"Avvio pipeline per Regione: {region}, Categoria: {category}", level="info")
        
        start_time = time.time()
        timeout = 3600  # 1 ora timeout
        
        # Crea l'istanza del pipeline executor con gestione errori migliorata
        logger.info("Creazione istanza PipelineExecutor...")
        log_callback("Creazione istanza PipelineExecutor...", level="info")
        
        try:
            pipeline_executor_instance = PipelineExecutor(
                region=region,
                category=category,
                base_path=project_root,
                debug=True
            )
            
            if not pipeline_executor_instance:
                raise Exception("Impossibile creare istanza PipelineExecutor")
            
            logger.info("PipelineExecutor creato con successo")
            log_callback("PipelineExecutor creato con successo", level="info")
            
        except Exception as init_error:
            logger.error(f"Errore nella creazione di PipelineExecutor: {init_error}", exc_info=True)
            log_callback(f"Errore nella creazione di PipelineExecutor: {init_error}", level="error")
            raise init_error
        
        # Aggiungi il callback handler al logger della pipeline
        try:
            callback_handler = CallbackHandler()
            pipeline_executor_instance.logger.addHandler(callback_handler)
            pipeline_executor_instance.logger.setLevel(logging.info)  # Più dettagli
            logger.info("Handler callback aggiunto al logger della pipeline")
            log_callback("Handler callback configurato", level="info")
        except Exception as handler_error:
            logger.warning(f"Errore nell'aggiunta del callback handler: {handler_error}")
            log_callback(f"Avviso: problemi con il callback handler: {handler_error}", level="warning")

        success = False
        
        # Verifica attributi necessari prima dell'esecuzione
        log_callback("Verifica metodi disponibili...", level="info")
        
        if full_pipeline:
            if not hasattr(pipeline_executor_instance, 'run_full_pipeline'):
                raise AttributeError("Metodo run_full_pipeline non disponibile")
            log_callback("Metodo run_full_pipeline verificato", level="info")
        elif specific_step:
            if not hasattr(pipeline_executor_instance, 'run_step'):
                raise AttributeError("Metodo run_step non disponibile")
            log_callback(f"Metodo run_step verificato per step {specific_step}", level="info")
        
        # Controlla se è ancora entro il timeout
        if time.time() - start_time < timeout:
            try:
                if full_pipeline:
                    log_callback("Esecuzione pipeline completa...")
                    logger.info("Chiamata run_full_pipeline...")
                    
                    # Esecuzione con timeout e monitoraggio
                    log_callback("Avvio esecuzione run_full_pipeline...", level="info")
                    success = pipeline_executor_instance.run_full_pipeline(progress_callback=progress_callback)
                    logger.info(f"run_full_pipeline completato, successo: {success}")
                    log_callback(f"run_full_pipeline completato, risultato: {success}", level="info")
                        
                elif specific_step:
                    log_callback(f"Esecuzione step specifico: {specific_step}...")
                    logger.info(f"Chiamata run_step per step {specific_step}...")
                    
                    # Verifica parametri per run_step
                    log_callback(f"Parametri per run_step: region={region}, category={category}, step={specific_step}", level="info")
                    success = pipeline_executor_instance.run_step(region, category, specific_step, progress_callback=progress_callback)
                    logger.info(f"run_step completato, successo: {success}")
                    log_callback(f"run_step completato, risultato: {success}", level="info")
                else:
                    raise ValueError("Nessun tipo di esecuzione specificato (full_pipeline o specific_step)")
                    
            except Exception as exec_e:
                logger.error(f"Errore durante l'esecuzione della pipeline: {exec_e}", exc_info=True)
                log_callback(f"Errore durante l'esecuzione: {exec_e}", level="error")
                log_callback(f"Traceback: {traceback.format_exc()}", level="error")
                success = False
        else:
            log_callback("Timeout raggiunto prima dell'esecuzione", level="warning")
            logger.warning("Timeout raggiunto prima dell'esecuzione")
            success = False

        # Finalizzazione
        with lock:
            pipeline_status["running"] = False
            pipeline_status["error"] = not success
            pipeline_status["last_activity"] = time.time()
            if success:
                pipeline_status["message"] = "Pipeline completata con successo!"
                log_callback("Pipeline completata con successo!", level="info")
                logger.info("Pipeline completata con successo")
            else:
                pipeline_status["message"] = "Pipeline terminata con errori o interrotta."
                log_callback("Pipeline terminata con errori o interrotta.", level="error")
                logger.error("Pipeline terminata con errori")

    except Exception as e:
        logger.error(f"Errore critico nel thread della pipeline: {e}", exc_info=True)
        with lock:
            pipeline_status["running"] = False
            pipeline_status["error"] = True
            pipeline_status["message"] = f"Errore critico durante l'esecuzione della pipeline: {e}"
            pipeline_status["last_activity"] = time.time()
            log_callback(f"Errore critico: {e}", level="critical")
            log_callback(f"Traceback completo: {traceback.format_exc()}", level="critical")
    finally:
        logger.info("Pulizia finale del thread pipeline...")
        try:
            with lock:
                if pipeline_executor_instance:
                    try:
                        # Rimuovi il callback handler prima di rilasciare l'istanza
                        for handler in pipeline_executor_instance.logger.handlers[:]:
                            if isinstance(handler, CallbackHandler):
                                pipeline_executor_instance.logger.removeHandler(handler)
                        logger.info("Handler rimossi dal logger della pipeline")
                    except Exception as e:
                        logger.warning(f"Errore nella pulizia dell'handler: {e}")
                    pipeline_executor_instance = None  # Rilascia l'istanza
                    logger.info("Istanza PipelineExecutor rilasciata")
        except Exception as cleanup_error:
            logger.error(f"Errore durante la pulizia: {cleanup_error}")
        
        logger.info("Thread pipeline terminato")

@app.route('/')
def index():
    """Renderizza la pagina principale della GUI."""
    # Carica le regioni disponibili da regioni_paesi.json
    regions = []
    regioni_paesi_path = os.path.join(project_root, 'config', 'regioni_paesi.json')
    if not os.path.exists(regioni_paesi_path):
        # Fallback se non trovato in config
        regioni_paesi_path = os.path.join(project_root, 'src', 'scrapers', 'pagine_gialle_scraper', 'spiders', 'regioni_paesi.json')

    if os.path.exists(regioni_paesi_path):
        try:
            with open(regioni_paesi_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                regions = sorted(list(data.keys()))
        except Exception as e:
            logger.error(f"Errore nel caricamento di regioni_paesi.json: {e}")
            regions = []
    else:
        logger.warning(f"File regioni_paesi.json non trovato nei percorsi previsti")

    return render_template('index.html', regions=regions)

@app.route('/start_pipeline', methods=['POST'])
def start_pipeline():
    """Avvia la pipeline in un thread separato."""
    global pipeline_thread

    # Controlla se la pipeline è già in esecuzione
    with lock:
        if pipeline_status["running"]:
            return jsonify({"status": "error", "message": "Pipeline già in esecuzione."}), 409

    # Estrai i parametri dalla richiesta
    data = request.json
    if not data:
        # Se non ci sono dati JSON, prova con i form data
        data = request.form.to_dict()
    
    if not data:
        return jsonify({"status": "error", "message": "Dati della richiesta mancanti."}), 400
    
    region = data.get('region')
    category = data.get('category')
    run_type = data.get('run_type', 'full')  # Default a 'full'
    step = data.get('step')  # Il numero dello step se run_type è 'step'

    # Log dei parametri ricevuti per debug
    logger.info(f"Parametri ricevuti - Region: {region}, Category: {category}, Run Type: {run_type}, Step: {step}")

    if not region or not category:
        return jsonify({"status": "error", "message": "Regione e Categoria sono campi obbligatori."}), 400

    # Test di inizializzazione della pipeline con logging dettagliato e timeout
    try:
        logger.info(f"Tentativo di inizializzazione PipelineExecutor con region={region}, category={category}")
        test_executor = PipelineExecutor(region=region, category=category, base_path=project_root, debug=False)
        logger.info("PipelineExecutor inizializzato con successo per test")
        
        # Test di comunicazione opzionale con timeout
        if hasattr(test_executor, 'test_communication'):
            logger.info("Test di comunicazione disponibile, esecuzione...")
            try:
                # Aggiungi timeout per il test di comunicazione
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Test di comunicazione timeout")
                
                # Su Windows, signal.SIGALRM non è disponibile, usa threading
                if os.name == 'nt':  # Windows
                    import threading
                    test_result = [False]
                    exception_holder = [None]
                    
                    def run_test():
                        try:
                            test_result[0] = test_executor.test_communication()
                        except Exception as e:
                            exception_holder[0] = e
                    
                    test_thread = threading.Thread(target=run_test)
                    test_thread.start()
                    test_thread.join(timeout=30)  # 30 secondi timeout
                    
                    if test_thread.is_alive():
                        logger.error("Test di comunicazione timeout")
                        return jsonify({"status": "error", "message": "Test di comunicazione timeout"}), 500
                    
                    if exception_holder[0]:
                        raise exception_holder[0]
                    
                    if not test_result[0]:
                        logger.error("Test di comunicazione fallito")
                        return jsonify({"status": "error", "message": "Test di comunicazione con pipeline fallito"}), 500
                else:
                    # Unix/Linux
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(30)  # 30 secondi timeout
                    try:
                        if not test_executor.test_communication():
                            logger.error("Test di comunicazione fallito")
                            return jsonify({"status": "error", "message": "Test di comunicazione con pipeline fallito"}), 500
                    finally:
                        signal.alarm(0)
                
                logger.info("Test di comunicazione riuscito")
            except Exception as comm_error:
                logger.error(f"Errore nel test di comunicazione: {comm_error}")
                return jsonify({"status": "error", "message": f"Errore test comunicazione: {str(comm_error)}"}), 500
        else:
            logger.info("Test di comunicazione non disponibile, continuando...")
            
    except Exception as e:
        logger.error(f"Errore durante l'inizializzazione del PipelineExecutor: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Errore inizializzazione pipeline: {str(e)}"}), 500

    full_pipeline = (run_type == 'full')
    specific_step = int(step) if run_type == 'step' and step and step.isdigit() else None

    # Validazione dei parametri
    if not full_pipeline and specific_step is None:
        return jsonify({"status": "error", "message": "Specificare tipo di esecuzione valido."}), 400

    # Log pre-avvio
    logger.info(f"Avvio pipeline - Full: {full_pipeline}, Step: {specific_step}")

    # Avvia la pipeline in un thread separato
    try:
        pipeline_thread = threading.Thread(
            target=run_pipeline_task, 
            args=(region, category, full_pipeline, specific_step),
            name="PipelineThread"
        )
        pipeline_thread.daemon = True
        pipeline_thread.start()
        
        logger.info("Thread della pipeline avviato con successo")
        return jsonify({"status": "success", "message": "Pipeline avviata con successo."})
        
    except Exception as e:
        logger.error(f"Errore nell'avvio del thread della pipeline: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Errore nell'avvio della pipeline: {str(e)}"}), 500

@app.route('/stop_pipeline', methods=['POST'])
def stop_pipeline():
    """Interrompe la pipeline se in esecuzione."""
    global pipeline_executor_instance
    
    with lock:
        if pipeline_status["running"] and pipeline_executor_instance:
            try:
                if hasattr(pipeline_executor_instance, 'stop'):
                    pipeline_executor_instance.stop()
                    pipeline_status["message"] = "Richiesta di interruzione inviata alla pipeline."
                    log_callback("Richiesta di interruzione dalla GUI", level="warning")
                    logger.info("Richiesta di interruzione pipeline da GUI.")
                    return jsonify({"status": "success", "message": "Richiesta di interruzione inviata."})
                else:
                    pipeline_status["message"] = "Metodo di interruzione non disponibile."
                    return jsonify({"status": "warning", "message": "Metodo di interruzione non disponibile per questa pipeline."})
            except Exception as e:
                logger.error(f"Errore durante l'interruzione della pipeline: {e}")
                return jsonify({"status": "error", "message": f"Errore durante l'interruzione: {e}"}), 500
        else:
            return jsonify({"status": "info", "message": "Nessuna pipeline in esecuzione da interrompere."})

@app.route('/debug/pipeline', methods=['GET'])
def debug_pipeline():
    """Endpoint di debug per verificare la configurazione della pipeline."""
    try:
        # Test di importazione
        debug_info = {
            "pipeline_executor_available": True,
            "methods_available": [],
            "project_root": project_root,
            "regions_file_exists": False,
            "regions_data": [],
            "python_paths": sys.path[:5],  # Prime 5 vie
            "current_working_directory": os.getcwd()
        }
        
        # Controlla i metodi disponibili
        try:
            test_instance = PipelineExecutor(region="test", category="test", base_path=project_root)
            debug_info["methods_available"] = [method for method in dir(test_instance) if not method.startswith('_')]
            
            # Test di comunicazione se disponibile
            if hasattr(test_instance, 'test_communication'):
                try:
                    debug_info["test_communication_available"] = True
                    # Non eseguire il test qui per evitare rallentamenti
                except Exception as test_e:
                    debug_info["test_communication_error"] = str(test_e)
            else:
                debug_info["test_communication_available"] = False
                
        except Exception as instance_error:
            debug_info["pipeline_executor_available"] = False
            debug_info["instance_error"] = str(instance_error)
            debug_info["instance_error_traceback"] = traceback.format_exc()
        
        # Controlla file regioni
        regioni_paesi_path = os.path.join(project_root, 'config', 'regioni_paesi.json')
        if not os.path.exists(regioni_paesi_path):
            regioni_paesi_path = os.path.join(project_root, 'src', 'scrapers', 'pagine_gialle_scraper', 'spiders', 'regioni_paesi.json')
        
        if os.path.exists(regioni_paesi_path):
            debug_info["regions_file_exists"] = True
            debug_info["regions_file_path"] = regioni_paesi_path
            try:
                with open(regioni_paesi_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    debug_info["regions_data"] = list(data.keys())[:5]  # Prime 5 regioni
                    debug_info["total_regions"] = len(data.keys())
            except Exception as e:
                debug_info["regions_file_error"] = str(e)
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "pipeline_executor_available": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }), 500

@app.route('/status')
def status():
    """Restituisce lo stato attuale della pipeline."""
    with lock:
        # Crea una copia dello stato per evitare modifiche durante la serializzazione
        status_copy = pipeline_status.copy()
        
        # Aggiungi informazioni aggiuntive
        if status_copy["start_time"]:
            status_copy["elapsed_time"] = time.time() - status_copy["start_time"]
        
        if status_copy["last_activity"]:
            status_copy["time_since_last_activity"] = time.time() - status_copy["last_activity"]
        
        # Limita i log per la trasmissione (ultimi 50)
        # if len(status_copy["log"]) > 50:
        #     status_copy["log"] = status_copy["log"][-50:]
            
        return jsonify(status_copy)

@app.route('/logs')
def get_logs():
    """Restituisce solo i log della pipeline."""
    with lock:
        return jsonify({
            "logs": pipeline_status["log"][-100:],  # Ultimi 100 log
            "total_logs": len(pipeline_status["log"])
        })

@app.errorhandler(404)
def not_found(error):
    """Gestisce gli errori 404."""
    return jsonify({"status": "error", "message": "Endpoint non trovato."}), 404

@app.errorhandler(500)
def internal_error(error):
    """Gestisce gli errori 500."""
    logger.error(f"Errore interno del server: {error}")
    return jsonify({"status": "error", "message": "Errore interno del server."}), 500

if __name__ == '__main__':
    logger.info("Avvio dell'applicazione Flask...")
    logger.info(f"Percorso progetto: {project_root}")
    logger.info(f"Percorsi PYTHONPATH: {sys.path[:3]}...")  # Mostra i primi 3 per debug
    
    # Test iniziale di PipelineExecutor
    try:
        logger.info("Test iniziale di PipelineExecutor...")
        test_instance = PipelineExecutor(region="test", category="test", base_path=project_root, debug=False)
        logger.info("Test iniziale di PipelineExecutor riuscito")
    except Exception as e:
        logger.error(f"Errore nel test iniziale di PipelineExecutor: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Applicazione interrotta dall'utente")
    except Exception as e:
        logger.error(f"Errore durante l'avvio dell'applicazione: {e}")
        sys.exit(1)