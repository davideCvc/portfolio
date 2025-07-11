import pandas as pd
import json
import numpy as np

# Carica il file JSON
df = pd.read_json("../../google_reviews_scraper/data/emilia_romagna/mangiare/output.json")
print(f"Record totali caricati: {len(df)}")

# Normalizza indirizzo e nome (conversione in minuscolo, rimozione spazi multipli e strip)
df["indirizzo"] = df["indirizzo"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
df["nome"] = df["nome"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()

# Funzione per appiattire liste annidate ed eliminare duplicati
def flatten_list(nested_list):
    if isinstance(nested_list, pd.Series):
        nested_list = nested_list.dropna().tolist()
    elif not isinstance(nested_list, list):
        nested_list = [nested_list]
    return sorted(set(item for sublist in nested_list if isinstance(sublist, list) for item in sublist) | 
                  set(item for item in nested_list if not isinstance(item, list)))

# Funzione per ottenere il primo valore valido (evita "N/A")
def first_valid(lst):
    if isinstance(lst, pd.Series):
        lst = lst.dropna().tolist()
    if isinstance(lst, list):
        for x in lst:
            if isinstance(x, str) and x.strip() and x != "N/A":
                return x  
    elif isinstance(lst, str) and lst.strip() and lst != "N/A":
        return lst
    return None

# Se il rating è in formato stringa con la virgola come separatore decimale, sostituiscila con il punto
df["rating"] = df["rating"].astype(str).str.replace(",", ".")

# Converti rating in valori numerici: se non convertibile, restituisci None invece di NaN
df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
df["rating"] = df["rating"].apply(lambda x: x if pd.notnull(x) else None)

# Converti review_count in int; se non convertibile, impostalo a 0
df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").fillna(0).astype(int)

# Raggruppa per "nome" e "indirizzo" applicando le opportune funzioni di aggregazione
df = df.groupby(["nome", "indirizzo"], as_index=False).agg({
    "città": "first", 
    "provincia": "first",
    "cap": "first",
    "telefono": lambda x: flatten_list(x) if not x.isna().all() else [],
    "email": lambda x: flatten_list(x) if not x.isna().all() else [],
    "sito_web": lambda x: first_valid(x) or None,
    "categoria": "first",
    "descrizione": lambda x: first_valid(x) or None,
    "latitudine": "first",
    "longitudine": "first",
    "region": "first",
    "paese": lambda x: flatten_list(x)[:50] if not x.isna().all() else [None],
    "pagina": "first",
    "rating": "first",
    "review_count": "first",
})

print(f"Record dopo il raggruppamento: {len(df)}")

# Organizza i dati per categoria
categorized_data = {}
for record in df.to_dict("records"):
    categorized_data.setdefault(record["categoria"], []).append(record)

# Converti in formato JSON richiesto
final_output = [{"categoria": cat, "strutture": items} for cat, items in categorized_data.items()]

# Salva il dataset pulito in un nuovo file JSON
output_file = "../../data/processed_data/emilia_romagna/mangiare/cleaned_data.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=4)

print(f"Dati puliti e salvati: {len(df)} record in '{output_file}'")
