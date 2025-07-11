#!/usr/bin/env python3

import pandas as pd
import json
import os
import argparse
import logging
import sys
import re
from pathlib import Path

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_cleaning.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def flatten_list(nested_list):
    """Flattens nested lists and removes duplicates"""
    if isinstance(nested_list, pd.Series):
        nested_list = nested_list.dropna().tolist()
    elif not isinstance(nested_list, list):
        if pd.isna(nested_list):
            return []
        nested_list = [nested_list]
    
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(item)
        elif item is not None and not pd.isna(item):
            flat_list.append(item)
    
    # Remove duplicates and sort
    return sorted(list(set(str(item).strip() for item in flat_list if str(item).strip() and str(item) != "N/A")))

def process_keywords_pg(keyword_series):
    """
    Processes keywords_pg field by flattening, deduplicating and cleaning
    """
    if isinstance(keyword_series, pd.Series):
        all_keywords = []
        for item in keyword_series.dropna():
            if isinstance(item, list):
                all_keywords.extend(item)
            elif isinstance(item, str) and item.strip() and item != "N/A":
                all_keywords.append(item.strip())
        
        # Remove duplicates while preserving order and clean up
        unique_keywords = []
        seen = set()
        for kw in all_keywords:
            kw_clean = str(kw).strip()
            if kw_clean and kw_clean != "N/A" and kw_clean.lower() not in seen:
                unique_keywords.append(kw_clean)
                seen.add(kw_clean.lower())
        
        return unique_keywords
    
    return []

def process_keywords_processed_pg(keyword_series):
    """
    Processes keywords_processed_pg field by flattening, deduplicating and cleaning
    Handles both string representations of dictionaries and actual dictionaries
    """
    if isinstance(keyword_series, pd.Series):
        all_processed_keywords = []
        seen_labels = set()
        
        for item in keyword_series.dropna():
            if isinstance(item, list):
                for subitem in item:
                    processed_kw = _parse_processed_keyword(subitem)
                    if processed_kw and processed_kw['lbl'].lower() not in seen_labels:
                        all_processed_keywords.append(processed_kw)
                        seen_labels.add(processed_kw['lbl'].lower())
            else:
                processed_kw = _parse_processed_keyword(item)
                if processed_kw and processed_kw['lbl'].lower() not in seen_labels:
                    all_processed_keywords.append(processed_kw)
                    seen_labels.add(processed_kw['lbl'].lower())
        
        # Convert back to string representation as in your example
        return [str(kw) for kw in all_processed_keywords]
    
    return []

def _parse_processed_keyword(item):
    """
    Helper function to parse processed keywords from various formats
    """
    if not item or pd.isna(item) or str(item).strip() == "N/A":
        return None
    
    item_str = str(item).strip()
    
    # If it's already in the expected format: "{'lbl': 'text', 'tot_chars': number}"
    if item_str.startswith("{'lbl':") or item_str.startswith('{"lbl":'):
        try:
            # Try to evaluate as dictionary
            if item_str.startswith("{'lbl':"):
                # Replace single quotes with double quotes for JSON parsing
                json_str = item_str.replace("'", '"')
                parsed = json.loads(json_str)
            else:
                parsed = json.loads(item_str)
            
            if 'lbl' in parsed:
                return {
                    'lbl': parsed['lbl'],
                    'tot_chars': parsed.get('tot_chars', len(parsed['lbl']))
                }
        except (json.JSONDecodeError, SyntaxError):
            pass
    
    # If it's a plain string, create the processed format
    if isinstance(item_str, str) and item_str:
        return {
            'lbl': item_str,
            'tot_chars': len(item_str)
        }
    
    return None

def first_valid(lst):
    """Gets the first valid value (avoids 'N/A' and null values)"""
    if isinstance(lst, pd.Series):
        lst = lst.dropna().tolist()
    if isinstance(lst, list):
        for x in lst:
            if x is not None and not pd.isna(x) and isinstance(x, (str, int, float)):
                x_str = str(x).strip()
                if x_str and x_str not in ["N/A", "nan", "None"]:
                    return x if not isinstance(x, str) else x_str
    elif lst is not None and not pd.isna(lst):
        lst_str = str(lst).strip()
        if lst_str and lst_str not in ["N/A", "nan", "None"]:
            return lst if not isinstance(lst, str) else lst_str
    return None

def normalize_string(text):
    """
    Normalizes a string for better duplicate matching:
    - Converts to lowercase
    - Removes multiple spaces
    - Removes non-alphanumeric characters (except spaces and accented letters)
    - Removes common articles and words (Italian)
    """
    if not isinstance(text, str) or not text or text == "N/A":
        return ""
    
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\àèéìòù]', '', text) # Keep accented characters for Italian
    text = re.sub(r'^(il|lo|la|i|gli|le|un|uno|una|di|a|da|in|con|su|per|tra|fra) ', '', text) # Italian articles
    
    return text.strip()

def find_input_file(base_path, region, category):
    """
    Searches for the input file in the expected structure.
    """
    candidate = os.path.join(
        base_path,
        "data", "raw", "raw_post_pagine_gialle",
        region, category,
        f"{region}_{category}_data.json"
    )
    logger.debug(f"Checking path: {candidate}")
    if os.path.exists(candidate):
        logger.info(f"Input file found: {candidate}")
        return candidate
    
    logger.error("Input file not found in the expected path")
    return None

def determine_output_path(base_path, region, category):
    """
    Determines the correct output path.
    """
    output_dir = os.path.join(base_path, f"data/processed_data/clean_post_pagine_gialle/{region}/{category}")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{category}_categorized_{region}.json")
    
    return output_dir, output_file

def analyze_duplicates(df):
    """
    Analyzes duplicates to identify potential issues.
    """
    # Create a copy with only hashable columns for duplicate checking
    hashable_df = df.copy()
    
    for col in hashable_df.columns:
        if hashable_df[col].apply(lambda x: isinstance(x, list)).any():
            logger.debug(f"Column '{col}' contains lists, excluding from exact duplicate analysis")
            # We exclude only non-string, non-numeric list columns here.
            # 'name_pg' and 'address_pg' are usually strings, so they'd be included.
            if col not in ['phone_pg', 'email_pg', 'keywords_pg', 'keywords_processed_pg']:
                hashable_df = hashable_df.drop(columns=[col])
            else: # For list columns, convert to a hashable representation for a loose check
                hashable_df[col] = hashable_df[col].apply(lambda x: tuple(x) if isinstance(x, list) else x)

    try:
        exact_dupes = hashable_df.duplicated().sum()
        logger.info(f"Exact duplicates (hashable columns): {exact_dupes}")
    except Exception as e:
        logger.warning(f"Could not check for exact duplicates: {e}")
    
    # Check duplicates by name_pg and address_pg
    if "name_pg" in df.columns and "address_pg" in df.columns:
        name_address_dupes = df.duplicated(subset=["name_pg", "address_pg"]).sum()
        logger.info(f"Duplicates by name_pg and address_pg: {name_address_dupes}")
    
    return df

def process_dataframe_in_batches(df, batch_size=1000):
    """
    Processes a DataFrame in batches to reduce memory usage.
    """
    # Use the original column names for grouping
    if 'name_pg' not in df.columns or 'address_pg' not in df.columns:
        logger.error("Columns 'name_pg' and 'address_pg' are required but not found for grouping.")
        return []
    
    # Normalize address and name for grouping using their original names
    df["name_pg_normalized"] = df["name_pg"].astype(str).apply(normalize_string)
    df["address_pg_normalized"] = df["address_pg"].astype(str).apply(normalize_string)
    
    # Group by normalized fields
    grouped = df.groupby(["name_pg_normalized", "address_pg_normalized"])
    
    all_records = []
    
    # Define aggregations using the *original* column names with enhanced keyword processing
    agg_dict = {
        "name_pg": "first",
        "address_pg": "first",
        "city_pg": "first",
        "province_pg": "first",
        "postal_code_pg": "first",
        "phone_pg": lambda x: flatten_list(x),
        "email_pg": lambda x: flatten_list(x),
        "website_pg": lambda x: first_valid(x) or "N/A",
        "category_pg": "first", # This will be the main category for grouping
        "description_pg": lambda x: first_valid(x) or "N/A",
        "latitude_pg": "first",
        "longitude_pg": "first",
        "vat_number_pg": lambda x: first_valid(x) or "N/A",
        "average_rating_pg": "first",
        "reviews_count_pg": "first",
        "additional_info_pg": lambda x: first_valid(x) or "N/A",
        "free_text_pg": lambda x: first_valid(x) or "N/A",
        "keywords_pg": process_keywords_pg,  # Enhanced processing
        "keywords_processed_pg": process_keywords_processed_pg,  # Enhanced processing
        "quote_email_pg": lambda x: first_valid(x) or "N/A",
        "region_pg": "first",
        "category": "first",
        "page": "first"
    }

    # Filter aggregation dictionary to keep only columns present in the DataFrame
    final_agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    
    # Apply aggregation
    processed_df = grouped.agg(final_agg_dict)
    
    # Reset index to turn groups back into columns, then convert to dict
    all_records = processed_df.reset_index(drop=True).to_dict("records")

    logger.info(f"Total records after grouping process: {len(all_records)}")
    return all_records

def clean_data(region, category, base_path=None, batch_size=1000):
    """
    Normalizes and cleans raw Pagine Gialle data, preserving original JSON field names.
    """
    try:
        if not base_path:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logger.debug(f"Base path determined: {base_path}")

        input_file = find_input_file(base_path, region, category)
        if not input_file:
            return False
        
        output_dir, output_file = determine_output_path(base_path, region, category)
        
        logger.info(f"Processing data from: {input_file}")
        logger.info(f"Output destination: {output_file}")
        
        try:
            df = pd.read_json(input_file)
            logger.info(f"Total records loaded: {len(df)}")
        except (pd.errors.EmptyDataError, json.JSONDecodeError) as e:
            logger.error(f"Error loading JSON file: {e}")
            return False
        
        if len(df) == 0:
            logger.warning(f"No records to process in file: {input_file}")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            return True
        
        # Column mapping (identity mapping to preserve original names)
        column_mapping = {
            "name_pg": "name_pg",
            "address_pg": "address_pg",
            "city_pg": "city_pg",
            "province_pg": "province_pg",
            "region_pg": "region_pg",
            "postal_code_pg": "postal_code_pg",
            "phone_pg": "phone_pg",
            "email_pg": "email_pg",
            "website_pg": "website_pg",
            "category_pg": "category_pg",
            "description_pg": "description_pg",
            "latitude_pg": "latitude_pg",
            "longitude_pg": "longitude_pg",
            "vat_number_pg": "vat_number_pg",
            "average_rating_pg": "average_rating_pg",
            "reviews_count_pg": "reviews_count_pg",
            "additional_info_pg": "additional_info_pg",
            "free_text_pg": "free_text_pg",
            "keywords_pg": "keywords_pg",
            "keywords_processed_pg": "keywords_processed_pg",
            "quote_email_pg": "quote_email_pg",
            "category": "category",
            "page": "page"
        }
        
        # Apply the mapping
        df.rename(columns=column_mapping, inplace=True, errors='ignore')
        logger.info("Column names aligned with raw JSON structure.")
        logger.debug(f"Current column names: {df.columns.tolist()}")

        # Handle missing values and ensure all expected columns are present
        expected_columns = [
            "name_pg", "address_pg", "city_pg", "province_pg", "postal_code_pg", 
            "phone_pg", "email_pg", "website_pg", "category_pg", "description_pg", 
            "latitude_pg", "longitude_pg", "vat_number_pg", "average_rating_pg", 
            "reviews_count_pg", "additional_info_pg", "free_text_pg", 
            "keywords_pg", "keywords_processed_pg", "quote_email_pg",
            "region_pg", "category", "page"
        ]
        
        for col in expected_columns:
            if col not in df.columns:
                logger.warning(f"Column '{col}' missing in the dataset. It will be created with default values.")
                if col in ["phone_pg", "email_pg", "keywords_pg", "keywords_processed_pg"]:
                    df[col] = [[] for _ in range(len(df))]
                elif col in ["latitude_pg", "longitude_pg"]:
                    df[col] = None
                elif col in ["average_rating_pg", "reviews_count_pg"]:
                    df[col] = 0.0
                else:
                    df[col] = "N/A"
        
        # Analyze duplicates for diagnostics
        df = analyze_duplicates(df)
        
        # Process the DataFrame
        all_records = process_dataframe_in_batches(df, batch_size)
        
        # Organize data by category
        categorized_data = {}
        for record in all_records:
            category_key = record.get("category", "Unknown")
            if pd.isna(category_key) or category_key == "N/A": 
                category_key = "Unknown"
            if category_key not in categorized_data:
                categorized_data[category_key] = []
            
            # Ensure the output record exactly matches the desired structure
            output_record = {}
            for key in expected_columns:
                if key in record:
                    output_record[key] = record[key]
                else:
                    output_record[key] = "N/A"
            
            # Remove the normalized columns used for grouping, if they exist
            output_record.pop("name_pg_normalized", None)
            output_record.pop("address_pg_normalized", None)

            categorized_data[category_key].append(output_record)
        
        # Final output structure
        final_output = [{"category": cat, "entries": items} for cat, items in categorized_data.items()]
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Cleaned data saved: {len(all_records)} records in '{output_file}'")
        
        # Log sample of processed keywords for verification
        if all_records:
            sample_record = all_records[0]
            logger.info(f"Sample keywords_pg: {sample_record.get('keywords_pg', [])}")
            logger.info(f"Sample keywords_processed_pg: {sample_record.get('keywords_processed_pg', [])}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during data cleaning: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pagine Gialle Data Cleaning Script")
    parser.add_argument("--region", required=True, help="Target region (e.g., lombardia)")
    parser.add_argument("--category", required=True, help="Target category (e.g., ristoranti)")
    parser.add_argument("--base-path", help="Base project path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("DEBUG mode activated")
    
    success = clean_data(args.region, args.category, args.base_path, args.batch_size)
    sys.exit(0 if success else 1)