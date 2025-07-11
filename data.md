# 📊 DATI PER LEAD SCORING OTTIMALE

## ✅ 1. Dati Strutturati Classici (Base Necessaria)

| Tipo           | Esempi                                            | Fonte                              |
|----------------|---------------------------------------------------|-------------------------------------|
| **Bilanci**     | Fatturato, utile netto, ROE, EBITDA, debiti      | Camere di commercio, Cribis, Atoka |
| **Dipendenti**  | Numero, variazioni annuali                       | INPS, Atoka, LinkedIn              |
| **Settore**     | Categoria ATECO, categoria Pagine Gialle         | PG, CamCom, Atoka                  |
| **Geografia**   | Regione, provincia, densità industriale locale   | ISTAT, OpenStreetMap               |

---

## 🚀 2. Dati Comportamentali (Intent Data)

| Tipo                         | Esempi                                           | Fonte                                    |
|------------------------------|--------------------------------------------------|-------------------------------------------|
| **Navigazione sito**         | Visite su pagine di contatto, prezzi, servizi   | Google Analytics, Hotjar                  |
| **Interazioni marketing**    | Click email, aperture, interazioni LinkedIn     | Mailchimp, Hubspot, LinkedIn Ads          |
| **Download di materiali**    | PDF, preventivi, listini                        | CRM, Marketing Automation                 |
| **Query Ads/Search**         | Keyword cercate su Google o LinkedIn            | Google Ads, LinkedIn Campaign Manager     |

---

## 🌐 3. Dati Digitali & Presenza Online

| Tipo                        | Esempio                                          | Tecnica/Fonte                         |
|-----------------------------|--------------------------------------------------|----------------------------------------|
| **Sito Web attivo**         | Azienda ha un sito funzionante                  | Scraping, Atoka                        |
| **Tecnologie usate**        | CMS (WordPress), e-commerce, Pixel Facebook     | BuiltWith API, Wappalyzer              |
| **Presenza Social**         | Profili LinkedIn, Facebook, Instagram attivi    | Scraping, API ufficiali                |
| **Recensioni**              | Numero + media recensioni                       | Google Maps API                        |

---

## 🧠 4. Segnali di Cambiamento o Crescita

| Tipo                         | Esempio                                          | Fonte                                 |
|------------------------------|--------------------------------------------------|----------------------------------------|
| **Aumento dipendenti**       | +10% workforce negli ultimi 6 mesi              | LinkedIn API, Atoka                    |
| **Nuove sedi**               | Apertura recente filiali                        | CamCom, Atoka                          |
| **Job posting attivi**       | Ricerca di personale specifico                  | Indeed, LinkedIn Jobs                  |
| **Cambio di management**     | Nuovo CEO, Direttore vendite                    | Registro Imprese, Google News          |

---

## 💬 5. Dati Testuali e Non Strutturati

| Tipo                         | Esempio                                          | Tecnica                                |
|------------------------------|--------------------------------------------------|-----------------------------------------|
| **Descrizioni aziendali**    | “Stiamo rinnovando l’impianto tecnico”          | NLP su `free_text_pg`, `sito`          |
| **Recensioni utenti**        | “Locale rinnovato, personale tecnico ottimo”    | NLP: sentiment analysis, keyword spotting |
| **Comunicati stampa/news**   | “Vinto bando per digitalizzazione”              | Google News Scraping + NER             |
| **Social Comments**          | “Stiamo cercando software per gestione forniture”| Scraping, NLU                          |

---

## 🧠 Tecniche di Analisi Consigliate

- **Modelli supervisionati** (se hai esempi di acquisto):  
  `RandomForestClassifier`, `XGBoost`, `CatBoost`, `LogisticRegression`
  
- **Modelli non supervisionati** (senza target):  
  `KMeans`, `DBSCAN`, **ranking euristico**

- **Feature Engineering NLP**:  
  - Topic Modeling (LDA, BERTopic)  
  - Sentiment Analysis  
  - TF-IDF su keyword tecniche

- **Normalizzazione dei dati**:  
  - Scaling (MinMax, Z-score)  
  - Encoding per categoriche (One-Hot, Target Encoding)  

---

## 🎯 Esempio: DATASET FITTIZZIO

```json
  {
    "id_azienda": "IT58158395867",
    "ragione_sociale": "Guarneri, Mocenigo e Lovato s.r.l.",
    "bilanci": {
      "fatturato_2023": 2850000,
      "fatturato_2022": 2320000,
      "utile_netto_2023": 285000,
      "roe_2023": 12.5,
      "ebitda_2023": 427500,
      "debiti_totali": 890000,
      "patrimonio_netto": 1850000,
      "anno_ultimo_bilancio": 2023
    },
    "dipendenti": {
      "numero_attuale": 28,
      "numero_2022": 24,
      "variazione_annuale": 16.7,
      "trend_6_mesi": "crescita"
    },
    "settore": {
      "ateco_primario": "43.22.01",
      "ateco_descrizione": "Installazione di impianti idraulici",
      "categoria_pagine_gialle": "Impianti idraulici",
      "settore_macro": "Costruzioni e Impianti"
    },
    "geografia": {
      "regione": "Lombardia",
      "provincia": "Milano",
      "comune": "Monza",
      "cap": "20900",
      "densita_industriale_locale": "alta",
      "coordinate": [
        45.5845,
        9.2744
      ]
    },
    // "navigazione_sito": {
    //   "visite_totali_30gg": 145,
    //   "pagine_contatto_visite": 23,
    //   "pagine_prezzi_visite": 18,
    //   "pagine_servizi_visite": 67,
    //   "tempo_medio_sessione": 320,
    //   "bounce_rate": 0.42,
    //   "conversioni_form": 3
    // },                             TUTTI DATI PRIVATI
    // "interazioni_marketing": {
    //   "email_aperture_30gg": 12,
    //   "email_click_30gg": 4,
    //   "linkedin_interazioni": 8,
    //   "linkedin_visite_profilo": 15,
    //   "campagne_ads_click": 6,
    //   "engagement_score": 7.2
    // },
    // "download_materiali": {
    //   "pdf_catalogo": 2,
    //   "preventivi_richiesti": 1,
    //   "listini_scaricati": 1,
    //   "brochure_tecniche": 3,
    //   "ultimo_download": "2024-06-10"
    // },
    "query_ads_search": {
      "keyword_rilevanti": [ // STIMA
        "software gestione impianti",
        "digitalizzazione cantieri",
        "app tecnici idraulici"
      ],
      "volume_ricerche_mensili": 28,
      "posizione_media_organica": 3.2,
    },
    "presenza_digitale": {
      "sito_web": {
        "attivo": true,
        "url": "https://www.tecnoplumbsolutions.it",
        "ultimo_aggiornamento": "2024-05-28",
        "mobile_friendly": true,
        "velocita_caricamento": 2.8
      },
      "tecnologie_usate": {
        "cms": "WordPress",
        "ecommerce": false,
        "pixel_facebook": true,
        "google_analytics": true,
        "chat_bot": false,
        "crm_integrato": "Salesforce"
      },
      "social_media": {
        "linkedin": {
          "attivo": true,
          "followers": 892,
          "post_ultimo_mese": 8,
          "engagement_rate": 3.2
        },
        "facebook": {
          "attivo": true,
          "followers": 456,
          "post_ultimo_mese": 4
        },
        "instagram": {
          "attivo": false
        }
      },
      "recensioni": {
        "google_maps": {
          "numero": 47,
          "media_rating": 4.3,
          "ultima_recensione": "2024-06-08"
        },
        "pagine_gialle": {
          "numero": 12,
          "media_rating": 4.1
        }
      }
    },
    "segnali_crescita": {
      "aumento_dipendenti": {
        "variazione_6_mesi": 14.3,
        "nuove_assunzioni": 4,
        "posizioni_aperte": 2
      },
      "espansione": {
        "nuove_sedi": 1,
        "data_apertura_ultima_sede": "2024-03-15",
        "investimenti_recenti": 450000
      },
      "job_posting": {
        "posizioni_attive": [
          {
            "titolo": "Tecnico Impianti Senior",
            "piattaforma": "LinkedIn",
            "data_pubblicazione": "2024-06-05"
          },
          {
            "titolo": "Project Manager Digitalizzazione",
            "piattaforma": "Indeed",
            "data_pubblicazione": "2024-06-01"
          }
        ],
        "budget_recruiting_mensile": 3500
      },
      "management_changes": {
        "nuovo_cto": {
          "nome": "Marco Bianchi",
          "data_nomina": "2024-04-01",
          "precedente_azienda": "Digital Tech Solutions"
        },
        "investimenti_tech": true
      }
    },
    "dati_testuali": {
      "descrizione_aziendale": "Azienda leader nell'installazione di impianti idraulici moderni. Stiamo investendo nella digitalizzazione dei processi e nella formazione del personale tecnico per offrire soluzioni all'avanguardia ai nostri clienti.",
      "keywords_rilevanti": [
        "digitalizzazione",
        "formazione tecnica",
        "soluzioni moderne",
        "investimenti tecnologici",
        "efficienza operativa"
      ],
      "sentiment_analysis": {
        "score": 0.72,
        "classificazione": "positivo",
        "confidenza": 0.89
      },
      "recensioni_analisi": {
        "temi_ricorrenti": [
          "professionalità tecnici",
          "puntualità interventi",
          "moderne attrezzature",
          "servizio clienti"
        ],
        "sentiment_medio": 0.68,
        "menzioni_tecnologia": 23
      },
      "comunicati_news": [
        {
          "titolo": "TecnoPlumb vince bando per digitalizzazione impianti pubblici",
          "data": "2024-05-20",
          "fonte": "TecnoNews Milano",
          "rilevanza_score": 0.85
        }
      ],
      "social_mentions": {
        "ricerca_software": 3,
        "interesse_automazione": 5,
        "budget_tech_menzionato": true,
        "urgenza_segnali": 2
      }
    },
    "lead_scoring": {
      "score_totale": 78.5,
      "probabilita_acquisto": 0.73,
      "categoria_lead": "Hot Lead",
      "fattori_chiave": [
        "crescita_dipendenti",
        "investimenti_tech",
        "intent_data_positivi",
        "presenza_digitale_attiva"
      ],
      "prossima_azione_consigliata": "Contatto commerciale diretto",
      "timing_ottimale": "entro 15 giorni"
    },
    "metadati": {
      "data_creazione_record": "2024-06-15T10:30:00Z",
      "ultima_sincronizzazione": "2024-06-15T08:00:00Z",
      "fonti_dati": [
        "Atoka API",
        "Google Analytics",
        "LinkedIn Sales Navigator",
        "Registro Imprese",
        "Scraping sito aziendale"
      ],
      "affidabilita_dati": 0.87,
      "completezza_profilo": 0.92
    }
  },
