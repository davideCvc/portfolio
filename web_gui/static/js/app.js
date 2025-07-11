document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const themeToggle = document.getElementById('themeToggle');
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const statusDiv = document.getElementById('statusMessages');
    const progressBar = document.getElementById('progressBar');
    const currentStepSpan = document.getElementById('currentStep');
    const totalStepsSpan = document.getElementById('totalSteps');
    const pipelineLog = document.getElementById('pipelineLog');
    const regionSelect = document.getElementById('regionSelect');
    const categoryInput = document.getElementById('categoryInput');
    const runTypeSelect = document.getElementById('runType');
    const stepSelectContainer = document.getElementById('stepSelectContainer');
    const specificStepInput = document.getElementById('specificStepInput');

    // AGGIUNGI QUESTA LINEA MANCANTE - Seleziona tutti i link di navigazione
    const navLinks = document.querySelectorAll('.nav-link');

    // Theme management
    let currentTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', currentTheme);
    updateThemeIcon();

    function updateThemeIcon() {
        const icon = themeToggle.querySelector('i');
        icon.className = currentTheme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
    }

    themeToggle.addEventListener('click', function () {
        currentTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.body.setAttribute('data-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
        updateThemeIcon();
    });

    // Sidebar management
    menuToggle.addEventListener('click', function () {
        sidebar.classList.toggle('visible');
        if (window.innerWidth > 1024) {
            mainContent.classList.toggle('expanded');
        }
    });

    mainContent.addEventListener('click', function () {
        if (window.innerWidth <= 1024 && sidebar.classList.contains('visible')) {
            sidebar.classList.remove('visible');
        }
    });

    // Navigation - SEZIONE CORRETTA
    function showSection(sectionName) {
        // Nascondi tutte le sezioni
        document.querySelectorAll('.section').forEach(section => {
            section.classList.add('hidden');
            section.classList.remove('active');
        });

        // Mostra la sezione selezionata
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.remove('hidden');
            targetSection.classList.add('active');
        }
    }

    // AGGIUNGI IL LISTENER PER I LINK DI NAVIGAZIONE
    navLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            // Rimuovi la classe active da tutti i link
            navLinks.forEach(l => l.classList.remove('active'));
            // Aggiungi la classe active al link cliccato
            this.classList.add('active');

            // Ottieni la sezione dal data-section
            const section = this.dataset.section;
            showSection(section);
            addLog('info', `Navigato alla sezione: ${section}`);

            // Chiudi la sidebar su mobile
            if (window.innerWidth <= 1024) {
                sidebar.classList.remove('visible');
            }
        });
    });

    // Form management
    runTypeSelect.addEventListener('change', function () {
        if (this.value === 'step') {
            stepSelectContainer.classList.remove('hidden');
        } else {
            stepSelectContainer.classList.add('hidden');
            specificStepInput.value = '';
        }
    });

    // VARIABILI PER TRACCIARE I LOG
    let lastLogCount = 0;
    let logProcessedIds = new Set(); // Per evitare log duplicati

    // Log functions
    function addLog(type, message, forceAdd = false) {
        // Crea un ID unico per il log basato su timestamp + messaggio
        const logId = Date.now() + '_' + message.substring(0, 50);

        // Evita duplicati se non forzato
        if (!forceAdd && logProcessedIds.has(logId)) {
            return;
        }

        logProcessedIds.add(logId);

        const logEntry = document.createElement('div');
        logEntry.classList.add('log-entry', `log-${type}`);
        logEntry.dataset.logId = logId; // Aggiungi ID al DOM

        let iconClass = '';
        switch (type) {
            case 'info': iconClass = 'fas fa-info-circle'; break;
            case 'success': iconClass = 'fas fa-check-circle'; break;
            case 'warning': iconClass = 'fas fa-exclamation-triangle'; break;
            case 'error': iconClass = 'fas fa-times-circle'; break;
            case 'critical': iconClass = 'fas fa-skull-crossbones'; break;
            case 'debug': iconClass = 'fas fa-bug'; break;
            case 'progress': iconClass = 'fas fa-tasks'; break;
            default: iconClass = 'fas fa-info-circle';
        }
        const timestamp = new Date().toLocaleTimeString('it-IT');
        logEntry.innerHTML = `
            <i class="${iconClass}"></i>
            [${timestamp}] ${message}
        `;
        pipelineLog.appendChild(logEntry);
        pipelineLog.scrollTop = pipelineLog.scrollHeight;

        // Mantieni solo gli ultimi 200 log per performance
        while (pipelineLog.children.length > 200) {
            const oldestLog = pipelineLog.firstChild;
            const oldId = oldestLog.dataset.logId;
            if (oldId) {
                logProcessedIds.delete(oldId);
            }
            pipelineLog.removeChild(oldestLog);
        }
    }

    function clearLogs() {
        pipelineLog.innerHTML = '';
        logProcessedIds.clear();
        lastLogCount = 0;
    }

    // Status management
    let statusInterval;
    let pipelineRunning = false;
    let consecutiveErrors = 0; // Contatore per errori consecutivi
    const maxConsecutiveErrors = 5; // Massimo numero di errori prima di fermare il polling

    function updateUI(statusData) {
        const iconElement = statusDiv.querySelector('i');

        statusDiv.classList.remove('status-info', 'status-success', 'status-error', 'status-warning', 'pulse');
        iconElement.className = '';

        if (statusData.running) {
            pipelineRunning = true;
            startButton.disabled = true;
            stopButton.disabled = false;
            statusDiv.classList.add('status-info', 'pulse');
            iconElement.classList.add('fas', 'fa-spinner', 'fa-spin');
            statusDiv.innerHTML = `<i class="${iconElement.className}"></i> ${statusData.message}`;

            // Update progress bar
            if (statusData.total_steps > 0) {
                const progressPercentage = (statusData.step / statusData.total_steps) * 100;
                progressBar.style.width = `${progressPercentage}%`;
                currentStepSpan.textContent = statusData.step;
                totalStepsSpan.textContent = statusData.total_steps;
            } else {
                progressBar.style.width = '10%'; // Show some activity even without specific progress
                currentStepSpan.textContent = '?';
                totalStepsSpan.textContent = '?';
            }
        } else {
            pipelineRunning = false;
            startButton.disabled = false;
            stopButton.disabled = true;

            if (statusData.error) {
                statusDiv.classList.add('status-error');
                iconElement.classList.add('fas', 'fa-exclamation-triangle');
                statusDiv.innerHTML = `<i class="${iconElement.className}"></i> ${statusData.message}`;
                progressBar.style.width = '0%';
                currentStepSpan.textContent = '0';
                totalStepsSpan.textContent = '0';
            } else if (statusData.message && statusData.message.includes("successo")) {
                statusDiv.classList.add('status-success');
                iconElement.classList.add('fas', 'fa-check-circle');
                statusDiv.innerHTML = `<i class="${iconElement.className}"></i> ${statusData.message}`;
                progressBar.style.width = '100%';
                if (statusData.total_steps > 0) {
                    currentStepSpan.textContent = statusData.total_steps;
                    totalStepsSpan.textContent = statusData.total_steps;
                }
            } else if (statusData.message && statusData.message.includes("interrott")) {
                statusDiv.classList.add('status-warning');
                iconElement.classList.add('fas', 'fa-pause-circle');
                statusDiv.innerHTML = `<i class="${iconElement.className}"></i> ${statusData.message}`;
                progressBar.style.width = '0%';
            } else {
                statusDiv.classList.add('status-info');
                iconElement.classList.add('fas', 'fa-clock');
                statusDiv.innerHTML = `<i class="${iconElement.className}"></i> ${statusData.message || 'In attesa...'}`;
                progressBar.style.width = '0%';
                currentStepSpan.textContent = '0';
                totalStepsSpan.textContent = '0';
            }
        }
    }

    // FUNZIONE MIGLIORATA per aggiornare i log dal server
    function updateLogsFromStatus(statusData) {
        if (!statusData.log || !Array.isArray(statusData.log)) {
            return;
        }

        console.log(`Ricevuti ${statusData.log.length} log dal server, processati finora: ${lastLogCount}`);
        if (statusData.log.length < lastLogCount) {
            clearLogs();
            lastLogCount = 0;
        }
        // Processa solo i nuovi log
        const newLogs = statusData.log.slice(lastLogCount);

        if (newLogs.length > 0) {
            console.log(`Processando ${newLogs.length} nuovi log`);

            newLogs.forEach((logMessage, index) => {
                if (logMessage && typeof logMessage === 'string' && logMessage.trim()) {
                    // Estrai il tipo di log dal messaggio
                    let logType = 'info';
                    if (logMessage.includes('[ERROR]') || logMessage.includes('[CRITICAL]')) {
                        logType = 'error';
                    } else if (logMessage.includes('[WARNING]')) {
                        logType = 'warning';
                    } else if (logMessage.includes('[SUCCESS]')) {
                        logType = 'success';
                    } else if (logMessage.includes('[DEBUG]')) {
                        logType = 'debug';
                    } else if (logMessage.includes('[PROGRESS]')) {
                        logType = 'progress';
                    }

                    // Rimuovi il timestamp dal server se presente
                    let cleanMessage = logMessage.replace(/^\[[\d\-\s:]+\]\s*\[[\w]+\]\s*/, '');

                    if (cleanMessage.trim()) {
                        addLog(logType, cleanMessage, true); // Forza l'aggiunta
                    }
                }
            });

            // Aggiorna il contatore
            lastLogCount = statusData.log.length;
        }
    }

    // FUNZIONE MIGLIORATA per monitorare lo stato della pipeline
    function startStatusMonitoring() {
        console.log('Avvio monitoraggio stato pipeline...');

        if (statusInterval) {
            clearInterval(statusInterval);
        }

        // Reset contatori
        consecutiveErrors = 0;
        lastLogCount = 0;

        statusInterval = setInterval(async function () {
            try {
                console.log('Richiesta stato pipeline...');

                const response = await fetch('/status', {
                    method: 'GET',
                    headers: {
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                });

                if (response.ok) {
                    const statusData = await response.json();
                    console.log('Stato ricevuto:', {
                        running: statusData.running,
                        logCount: statusData.log ? statusData.log.length : 0,
                        step: statusData.step,
                        message: statusData.message
                    });

                    updateUI(statusData);
                    updateLogsFromStatus(statusData);

                    // Reset contatore errori se la richiesta ha successo
                    consecutiveErrors = 0;

                    // Se la pipeline non è più in esecuzione, ferma il monitoraggio dopo un delay
                    if (!statusData.running && pipelineRunning) {
                        console.log('Pipeline terminata, fermo il monitoraggio tra 10 secondi...');
                        setTimeout(() => {
                            if (statusInterval) {
                                clearInterval(statusInterval);
                                statusInterval = null;
                                console.log('Monitoraggio fermato');
                            }
                        }, 10000); // 10 secondi per catturare log finali
                    }
                } else {
                    consecutiveErrors++;
                    console.error('Errore nel recupero dello stato:', response.status);
                    addLog('error', `Errore comunicazione server: ${response.status}`, true);

                    if (consecutiveErrors >= maxConsecutiveErrors) {
                        console.error('Troppi errori consecutivi, fermo il monitoraggio');
                        addLog('error', 'Troppi errori di comunicazione, monitoraggio fermato', true);
                        stopStatusMonitoring();
                    }
                }
            } catch (error) {
                consecutiveErrors++;
                console.error('Errore nella richiesta di stato:', error);
                addLog('error', `Errore connessione: ${error.message}`, true);

                if (consecutiveErrors >= maxConsecutiveErrors) {
                    console.error('Troppi errori consecutivi, fermo il monitoraggio');
                    addLog('error', 'Troppi errori di connessione, monitoraggio fermato', true);
                    stopStatusMonitoring();
                }
            }
        }, 3000); // Ogni 3 secondi invece di 2 per ridurre il carico
    }

    function stopStatusMonitoring() {
        console.log('Fermo monitoraggio stato pipeline...');
        if (statusInterval) {
            clearInterval(statusInterval);
            statusInterval = null;
        }
        consecutiveErrors = 0;
    }

    // PIPELINE START - Chiamata reale all'API
    startButton.addEventListener('click', async function () {
        const region = regionSelect.value;
        const category = categoryInput.value.trim();
        const runType = runTypeSelect.value;
        const specificStep = specificStepInput.value;

        // Validazione input
        if (!region || !category) {
            addLog('error', 'Errore: Seleziona una Regione e inserisci una Categoria Business.');
            updateUI({ running: false, error: true, message: 'Configurazione incompleta.' });
            return;
        }

        if (runType === 'step' && (!specificStep || parseInt(specificStep) <= 0)) {
            addLog('error', 'Errore: Inserisci un numero di step valido per l\'esecuzione specifica.');
            updateUI({ running: false, error: true, message: 'Configurazione step incompleta.' });
            return;
        }

        if (pipelineRunning) {
            addLog('warning', 'La pipeline è già in esecuzione.');
            return;
        }

        // Pulisci i log precedenti
        clearLogs();

        // Prepara i dati per la richiesta
        const requestData = {
            region: region,
            category: category,
            run_type: runType
        };

        if (runType === 'step') {
            requestData.step = specificStep;
        }

        addLog('info', `Invio richiesta avvio pipeline...`);
        addLog('info', `Regione: ${region}, Categoria: ${category}, Tipo: ${runType}${runType === 'step' ? ', Step: ' + specificStep : ''}`);

        try {
            // Disabilita il pulsante durante la richiesta
            startButton.disabled = true;
            updateUI({ running: false, message: 'Invio richiesta...' });

            // Chiamata REALE all'API Flask
            const response = await fetch('/start_pipeline', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (response.ok && result.status === 'success') {
                addLog('success', result.message);
                addLog('info', 'Avvio monitoraggio stato pipeline...');
                updateUI({ running: true, message: 'Pipeline avviata, in attesa di aggiornamenti...' });

                // Avvia il monitoraggio dello stato
                startStatusMonitoring();
            } else {
                addLog('error', `Errore nell'avvio: ${result.message}`);
                updateUI({ running: false, error: true, message: result.message });
                startButton.disabled = false;
            }
        } catch (error) {
            addLog('error', `Errore di connessione: ${error.message}`);
            updateUI({ running: false, error: true, message: 'Errore di connessione al server' });
            startButton.disabled = false;
        }
    });

    // PIPELINE STOP - Chiamata reale all'API
    stopButton.addEventListener('click', async function () {
        if (!pipelineRunning) {
            addLog('info', 'Nessuna pipeline in esecuzione da fermare.');
            return;
        }

        addLog('warning', 'Richiesta interruzione pipeline...');

        try {
            const response = await fetch('/stop_pipeline', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const result = await response.json();

            if (response.ok) {
                addLog('warning', result.message);
                updateUI({ running: false, message: 'Interruzione richiesta...' });

                // Continua il monitoraggio per un po' per vedere i risultati dell'interruzione
                setTimeout(() => {
                    stopStatusMonitoring();
                }, 15000); // 15 secondi invece di 10
            } else {
                addLog('error', `Errore nell'interruzione: ${result.message}`);
            }
        } catch (error) {
            addLog('error', `Errore di connessione durante l'interruzione: ${error.message}`);
        }
    });

    // Test di connessione al caricamento della pagina
    async function testConnection() {
        try {
            const response = await fetch('/debug/pipeline');
            if (response.ok) {
                const debugInfo = await response.json();
                addLog('success', 'Connessione al server stabilita');
                if (debugInfo.pipeline_executor_available) {
                    addLog('success', 'PipelineExecutor disponibile e funzionante');
                } else {
                    addLog('error', 'PipelineExecutor non disponibile');
                }
            } else {
                addLog('warning', `Server risponde ma con errore: ${response.status}`);
            }
        } catch (error) {
            addLog('error', `Impossibile connettersi al server: ${error.message}`);
        }
    }

    // Initial UI state e test connessione
    updateUI({ running: false, message: 'Inizializzazione...' });
    testConnection();

    // Controlla lo stato iniziale
    setTimeout(async () => {
        try {
            const response = await fetch('/status');
            if (response.ok) {
                const statusData = await response.json();
                updateUI(statusData);
                if (statusData.running) {
                    addLog('info', 'Pipeline già in esecuzione rilevata, avvio monitoraggio...');
                    startStatusMonitoring();
                }
            }
        } catch (error) {
            console.log('Stato iniziale non disponibile:', error);
        }
    }, 1000);
});