import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def load_data(file_path):
    """
    Carica il file JSON e restituisce i dati.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def flatten_strutture(data):
    """
    Appiattisce la struttura dei dati: per ogni record con una 'categoria' e una lista di 'strutture',
    aggiunge a ciascuna struttura il campo 'categoria_superiore'.
    """
    flattened_data = []
    for record in data:
        top_categoria = record.get("categoria")
        strutture = record.get("strutture")
        if isinstance(strutture, list):
            for s in strutture:
                s["categoria_superiore"] = top_categoria
                flattened_data.append(s)
    return flattened_data

def compute_lead_score(df):
    """
    Calcola un lead score combinando le feature:
      - rating (normalizzato rispetto al massimo ipotetico, ad esempio 5)
      - review_count (logaritmicamente trasformato e normalizzato)
      - presenza di telefono, email e sito web (feature binarie)
    I pesi sono definiti in modo arbitrario e potranno essere ottimizzati in un secondo momento.
    """
    # Convertiamo rating e review_count in numerici
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df['review_count'] = pd.to_numeric(df['review_count'], errors='coerce')
    
    # Normalizzazione del rating: assumiamo 5 come rating massimo
    df['norm_rating'] = df['rating'] / 5.0
    
    # Trasformazione logaritmica del review_count per gestire asimmetrie
    df['log_review_count'] = np.log1p(df['review_count'])
    max_log_review = df['log_review_count'].max()
    if max_log_review > 0:
        df['norm_review_count'] = df['log_review_count'] / max_log_review
    else:
        df['norm_review_count'] = 0
    
    # Feature binarie: presenza di telefono, email e sito web
    df['has_phone'] = df['telefono'].apply(lambda x: 1 if isinstance(x, list) and len(x) > 0 else 0)
    df['has_email'] = df['email'].apply(lambda x: 1 if isinstance(x, list) and len(x) > 0 else 0)
    df['has_website'] = df['sito_web'].apply(lambda x: 1 if pd.notnull(x) and x != "" else 0)
    
    # Definizione dei pesi (da tarare sulla base di analisi successive)
    weight_rating = 0.5
    weight_review = 0.3
    weight_phone = 0.1
    weight_email = 0.05
    weight_website = 0.05
    
    # Calcolo del lead score come somma pesata delle feature
    df['lead_score'] = (df['norm_rating'] * weight_rating +
                        df['norm_review_count'] * weight_review +
                        df['has_phone'] * weight_phone +
                        df['has_email'] * weight_email +
                        df['has_website'] * weight_website)
    
    return df

def analyze_lead_scoring(df):
    """
    Visualizza e analizza il lead score:
      - Distribuzione del lead score
      - Statistiche descrittive
      - Relazione tra lead score e variabili chiave (rating e review_count)
    """
    # Distribuzione del lead score
    plt.figure(figsize=(8,6))
    sns.histplot(df['lead_score'].dropna(), bins=20, kde=True, color='teal')
    plt.title("Distribuzione del Lead Score")
    plt.xlabel("Lead Score")
    plt.ylabel("Frequenza")
    plt.grid(True)
    plt.show()
    
    # Statistiche descrittive
    print("Statistiche del Lead Score:")
    print(df['lead_score'].describe(), "\n")
    
    # Relazione tra rating e lead score
    plt.figure(figsize=(8,6))
    plt.scatter(df['rating'], df['lead_score'], alpha=0.5, color='orange', edgecolor='k')
    plt.title("Relazione tra Rating e Lead Score")
    plt.xlabel("Rating")
    plt.ylabel("Lead Score")
    plt.grid(True)
    plt.show()
    
    # Relazione tra review_count e lead score
    plt.figure(figsize=(8,6))
    plt.scatter(df['review_count'], df['lead_score'], alpha=0.5, color='green', edgecolor='k')
    plt.title("Relazione tra Review Count e Lead Score")
    plt.xlabel("Review Count")
    plt.ylabel("Lead Score")
    plt.grid(True)
    plt.show()

def main():
    # Specifica il percorso del file JSON
    file_path = '../processed_data/emilia_romagna/mangiare/cleaned_data.json'
    data = load_data(file_path)
    
    # Creazione del DataFrame originale e appiattito
    df = pd.DataFrame(data)
    print("Colonne del DataFrame originale:")
    print(df.columns.tolist(), "\n")
    
    flattened_data = flatten_strutture(data)
    df_flat = pd.DataFrame(flattened_data)
    
    print("Colonne del DataFrame appiattito:")
    print(df_flat.columns.tolist(), "\n")
    
    # Conversione in numerico per rating e review_count
    df_flat['rating'] = pd.to_numeric(df_flat['rating'], errors='coerce')
    df_flat['review_count'] = pd.to_numeric(df_flat['review_count'], errors='coerce')
    
    # Calcolo del lead score
    df_scored = compute_lead_score(df_flat)
    
    # Visualizzazione di statistiche di base sui campi utilizzati
    print("Statistiche principali dei dati (rating, review_count, lead_score):")
    print(df_scored[['rating', 'review_count', 'lead_score']].describe(), "\n")
    
    # Analisi specifica del lead scoring
    analyze_lead_scoring(df_scored)
    
    # Ordinamento in base al lead score (decrescente) e stampa delle prime 20 aziende
    df_top20 = df_scored.sort_values('lead_score', ascending=False).head(20)
    print("Le prime 20 aziende con più propensione (lead score più alto):")
    print(df_top20[['nome', 'città', 'provincia', 'lead_score']])

if __name__ == '__main__':
    main()
