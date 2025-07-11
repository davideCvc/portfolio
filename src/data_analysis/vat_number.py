import json

# Percorso al file
file_path = "../../data/processed_data/clean_post_pagine_gialle/emilia_romagna/ristoranti/ristoranti_categorized_emilia_romagna.json"  # Sostituisci col nome del tuo file

# Carica il file JSON
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Lista completa di tutte le entries da tutte le sezioni
all_entries = []

for categoria in data:
    entries = categoria.get("entries", [])
    all_entries.extend(entries)

# Filtra solo quelle con partita IVA valida
valid_vat_entries = [
    entry for entry in all_entries
    if entry.get("vat_number_pg") not in [None, "", "N/A"]
]

# Output
print(f"Totale aziende: {len(all_entries)}")
print(f"Con partita IVA valida: {len(valid_vat_entries)}")
print(f"Senza partita IVA valida: {len(all_entries) - len(valid_vat_entries)}")
