# Detailed Documentation: Scraping System and Data Processing Pipeline

## Project Overview

This project implements a comprehensive web scraping system designed to extract and process structured data from two major sources:

1. **Pagine Gialle (Italian Yellow Pages)**: extracts detailed information about commercial activities in Italy, categorized by region and type.
2. **Google Maps/Reviews**: enriches business data with ratings and reviews from Google Maps.

The architecture is based on the Scrapy framework with custom extensions to handle JavaScript rendering through Selenium for Google Maps dynamic content, implementing an end-to-end processing pipeline.

## System Architecture

The system is organized with clear separation of components:

```
/
├── src/
│   ├── scrapers/
│   │   ├── pagine_gialle_scraper/    # Pagine Gialle scraper
│   │   └── google_reviews/           # Google Maps/Reviews scraper
│   ├── data_processing/              # Data processing
│   │   ├── data_cleaning_pagine_gialle/
│   │   └── data_cleaning_reviews/
│   └── pipeline/                     # Workflow orchestration
│       └── pipeline_executor.py
├── data/
│   ├── raw/                          # Raw data
│   │   ├── raw_post_pagine_gialle/
│   │   └── raw_post_google_reviews/
│   └── processed_data/               # Processed data
│       ├── clean_post_pagine_gialle/
│       └── clean_post_google_reviews/
├── config/                           # Configuration files
│   └── regioni_paesi.json
├── logs/                             # Logs and reports
│   └── pipeline_reports/
└── temp/                             # Temporary files
```

## Pipeline Executor

The `PipelineExecutor` class coordinates the entire processing pipeline, ensuring consistent workflow and managing errors at each stage.

### Key Features

- **Modularity**: Divides the process into distinct and well-defined steps
- **Error Handling**: Detailed logging and error recovery
- **Configurability**: Parameterized by region and category
- **Reporting**: Generates comprehensive execution reports

### Execution Flow

1. **Initialization and Verification**: Project structure validation and necessary directory creation
2. **Pagine Gialle Data Collection**: Systematic extraction for each locality in the region
3. **Pagine Gialle Data Normalization**: Cleaning and standardization
4. **Google Maps Rating and Review Collection**: Data enrichment with Google data
5. **Review Data Normalization**: Final processing and integration

## 1. Pagine Gialle Scraper

### Main Components

- **Spider (`pagine_gialle.py`)**: coordinates data extraction from Pagine Gialle
- **Items (`items.py`)**: defines the structure of extracted data
- **Middlewares (`middlewares.py`)**: provides hooks for customizing Scrapy behavior
- **Pipelines (`pipelines.py`)**: handles post-processing and data saving
- **Settings (`settings.py`)**: configures spider operational parameters

### Operation

The spider systematically extracts business information from Pagine Gialle JSON pages using a paginated method. For each commercial activity, it collects:

- Company name
- Complete address (street, city, province, ZIP code)
- Contact information (phone, email)
- Website
- Category
- Description
- Geographic coordinates (latitude and longitude)
- Region and category metadata

### Technical Features

1. **State Management**: Implements a state persistence system to allow resumption after interruption, saving progress to JSON files.

2. **User-Agent Rotation**: Uses `fake_useragent` to dynamically vary User-Agents and minimize detection risk.

3. **Rotating Proxy System**: Configures middleware for proxy rotation, improving resilience against IP blocks.

4. **Intelligent Throttling**: Implements randomized delays and auto-throttling to avoid target server overload.

5. **Error Handling**: Includes error handling mechanisms and specific callbacks to manage HTTP request failures.

6. **Robust Data Processing**: The `clean_value()` function handles various data types (strings, lists, null) ensuring consistent output.

## 2. Google Reviews Scraper

### Main Components

- **Spider (`google_maps_spider.py`)**: coordinates data extraction from Google Maps
- **Custom Selenium Middleware**: handles JavaScript rendering and browser automation
- **Persistence and Recovery System**: implements state saving and automatic backups

### Operation

This scraper takes normalized data from the first spider (Pagine Gialle) as input and:

1. Searches for each business on Google Maps using name and city
2. Analyzes results and selects the best match using text similarity algorithms
3. Extracts ratings and review counts
4. Verifies address correspondence to ensure data accuracy

### Technical Features

1. **Selenium-Scrapy Integration**: Implements a custom middleware (`CustomSeleniumMiddleware`) that integrates Selenium with Scrapy to handle JavaScript rendering.

2. **Browser Resource Management**:
   - Automatic Chrome driver management through `webdriver_manager`
   - Temporary browser profile cleanup
   - Memory optimization through controlled browser instance closure

3. **Advanced Matching Algorithms**:
   - Uses `SequenceMatcher` to calculate string similarity
   - Implements custom functions like `check_location_similarity()` and `normalize_address()`
   - Applies different weights to name and city to improve matching accuracy

4. **Advanced Recovery System**:
   - Automatic backup every 10 processed items
   - Separate state files for each region/category combination
   - Signal handling (e.g., SIGINT) for controlled shutdowns

5. **Advanced Debugging**:
   - Automatic page screenshots for debugging
   - Detailed logging with configurable verbosity levels
   - Complete error tracing

6. **Cookie and Consent Management**: Implements functions to automatically handle cookie consent and GDPR popups.

## 3. Data Normalization Process

### Pagine Gialle Data Normalization

The `cleanData.py` script performs cleaning and standardization operations on raw data extracted from Pagine Gialle:

1. Removes duplicates based on unique identifiers
2. Standardizes data formats (addresses, phone numbers, etc.)
3. Separates composite fields (e.g., complete address into separate components)
4. Adds metadata to facilitate integration with other sources
5. Handles missing values and data anomalies

### Google Reviews Data Normalization

The `cleanDataReviews.py` script processes and integrates review data:

1. Integrates ratings with main business data
2. Standardizes rating value formats
3. Calculates additional metrics based on reviews
4. Handles cases of mismatch between different sources
5. Produces an enriched dataset ready for analysis

## Pipeline Orchestration

The `PipelineExecutor` coordinates the complete workflow using a modular approach:

### Initialization

```python
def __init__(self, region, category, base_path=None):
    """
    Initialize the pipeline executor
    
    Args:
        region (str): Target region (e.g., 'emilia_romagna')
        category (str): Target category (e.g., 'ristoranti')
        base_path (str, optional): Project base path
    """
    # Initialize attributes and directory structure
```

### Command Execution Management

```python
def execute_command(self, command, cwd=None, description="", capture_output=True):
    """
    Execute a system command with error handling
    
    Args:
        command (str): Command to execute
        cwd (str, optional): Working directory
        description (str, optional): Command description for logs
        capture_output (bool): Whether to capture output or show directly on terminal
        
    Returns:
        bool: True if execution succeeded, False otherwise
    """
    # Command handling implementation
```

### Pipeline Steps

1. **Pagine Gialle Data Collection**:
   ```python
   def step1_collect_pagine_gialle(self):
       """Execute the Pagine Gialle spider to collect raw data into a single file"""
       # Step 1 implementation
   ```

2. **Pagine Gialle Data Normalization**:
   ```python
   def step2_normalize_pagine_gialle_data(self):
       """Normalize raw Pagine Gialle data"""
       # Step 2 implementation
   ```

3. **Google Maps Data Collection**:
   ```python
   def step3_collect_google_reviews(self):
       """Collect ratings and reviews from Google Maps"""
       # Step 3 implementation
   ```

4. **Review Data Normalization**:
   ```python
   def step4_normalize_review_data(self):
       """Normalize data with reviews and ratings"""
       # Step 4 implementation
   ```

### Full Pipeline Execution

```python
def execute_pipeline(self):
    """Execute the entire pipeline from start to finish"""
    logger.info(f"PIPELINE START for {self.region} - {self.category}")
    self.verify_project_structure()
    # Sequential step execution
    # Final report generation
```

## Configuration and Parameters

### Pagine Gialle Scraper

Main parameters in `settings.py`:

```python
# Throttling and concurrency
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 3
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 1
AUTOTHROTTLE_ENABLED = True
```

### Google Reviews Scraper

Main parameters in `settings.py`:

```python
# Reduce concurrency to avoid too many open browsers
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# Selenium arguments
SELENIUM_DRIVER_ARGUMENTS = [
    # '--headless=new',  # Commented for debugging
    '--disable-gpu',
    '--no-sandbox',
    '--disable-dev-shm-usage',
    '--disable-notifications',
    # other parameters...
]
```

## Data Structure

### Input for Google Reviews

The system expects data in this JSON format from Pagine Gialle (already processed):

```json
[
  {
    "strutture": [
      {
        "nome": "Business Name",
        "città": "City Name",
        "indirizzo": "Via Example 123",
        // other fields...
      }
    ]
  }
]
```

### Google Reviews Output

Data is enriched with:

```json
{
  "nome": "Business Name",
  "città": "City Name",
  "indirizzo": "Via Example 123",
  "rating": "4.5",
  "review_count": "125",
  "google_url": "https://www.google.com/maps/place/...",
  // original fields preserved...
}
```

## Resilience Mechanisms

### 1. Exception Handling

Implementation of detailed try-catch blocks on all critical components:

```python
try:
    # Critical operations
except Exception as e:
    logger.error(f"Exception during: {description}: {e}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    return False
```

### 2. Exponential Backoff

Implementation of increasing delays between failed attempts, with randomization to avoid synchronization:

```python
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED = True
```

### 3. State Saving

Periodic state saving mechanism to allow resumption:

```python
def _save_state(self, idx):
    state = {
        "last_index": idx,
        "region": self.region,
        "category": self.category,
        "timestamp": time.time(),
        "items_processed": idx,
        "total_items": len(self.aziende),
        "progress_percentage": round((idx / len(self.aziende) * 100), 2)
    }
    with open(self.state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
```

### 4. Automatic Backup

Periodic backup system to prevent data loss:

```python
def _manual_save_results(self):
    backup_file = os.path.join(
        backup_dir, 
        f"{self.region}_{self.category}_backup_{int(time.time())}.json"
    )
    
    # Data saving
    with open(self.raw_path, 'w', encoding='utf-8') as f:
        json.dump(self.results, f, ensure_ascii=False, indent=2)
```

### 5. Resource Management

Systematic cleanup of used resources:
- Controlled closure of Selenium drivers
- Removal of temporary Chrome profiles
- Cleanup of temporary files no longer needed

## Logging and Debugging

The system implements an extensive multi-level logging system:

```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline_execution.log'),
        logging.StreamHandler()
    ]
)
```

### Logging System Features

1. **Hierarchical Logging**: Different detail levels (DEBUG, INFO, WARNING, ERROR)
2. **File and Console Logging**: Duplicated output to facilitate monitoring
3. **Precise Timestamps**: Each entry includes exact date and time
4. **Complete Tracebacks**: Errors include complete traceback
5. **Structured Reporting**: JSON report generation at execution end

### Debug Mode

Activatable via command line flag:

```bash
python pipeline_executor.py --region lombardia --category ristoranti --debug
```

When activated, provides:
- More detailed logs on each step
- Enhanced diagnostic information
- Detailed tracking of internal operations

## Command Line Arguments

The `PipelineExecutor` can be controlled through CLI interface:

```python
parser = argparse.ArgumentParser(description="Scraping and data processing pipeline executor")
parser.add_argument("--region", required=True, help="Target region (e.g., emilia_romagna)")
parser.add_argument("--category", required=True, help="Target category (e.g., ristoranti)")
parser.add_argument("--base-path", help="Project base path")
parser.add_argument("--step", type=int, choices=[1, 2, 3, 4], help="Execute only a specific step")
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
```

### Usage Examples

To run the entire pipeline:
```bash
python src/pipeline/pipeline_executor.py --region lombardia --category ristoranti
```

To execute only a specific step:
```bash
python src/pipeline/pipeline_executor.py --region lombardia --category ristoranti --step 2
```

To enable debug mode:
```bash
python src/pipeline/pipeline_executor.py --region lombardia --category ristoranti --debug
```

## Performance Management

### Pagine Gialle Optimizations

- Use of `RANDOMIZE_DOWNLOAD_DELAY` and `AUTOTHROTTLE_ENABLED`
- Concurrent request limitation with `CONCURRENT_REQUESTS` and `CONCURRENT_REQUESTS_PER_DOMAIN`
- User-Agent rotation to minimize detection
- Efficient resource management with timely cleanup of temporary files

### Google Reviews Optimizations

- Image loading disabling
   ```python
   prefs = {"profile.managed_default_content_settings.images": 2}
   options.add_experimental_option("prefs", prefs)
   ```
- Precise browser resource management with controlled closure
- Separate temporary user profiles for each browser instance
- Parameterized concurrent requests to avoid overload

## Verification and Quality Assurance

The system implements various checks to ensure process integrity:

### Project Structure Verification

```python
def verify_project_structure(self):
    """Verify project structure and show detailed information for debugging"""
    logger.info("Verifying project structure...")
    
    key_directories = [
        "src/scrapers/pagine_gialle_scraper",
        "src/scrapers/google_reviews",
        # other directories...
    ]
    
    for directory in key_directories:
        path = os.path.join(self.base_path, directory)
        if os.path.exists(path):
            logger.info(f"Directory found: {path}")
            # Further checks...
        else:
            logger.warning(f"Missing directory: {path}")
    
    # Verify crucial configuration files
    # ...
```

### Dependency Verification

```python
def check_scrapy_installation(self):
    """Verify that Scrapy is installed and working."""
    logger.info("Verifying Scrapy installation...")
    
    # Check Scrapy version
    return self.execute_command(
        "scrapy version",
        description="Verify Scrapy version",
        capture_output=True
    )
```

## Known Limitations and Issues

1. **Google Maps DOM Dependency**: Changes in Google Maps interface might require updates to CSS/XPath selectors.

2. **Bot Detection**: Google Maps implements advanced bot detection systems that might block requests despite countermeasures.

3. **Cookie Management**: Cookie consent popups require specific interaction that might change over time.

4. **Computational Resources**: Selenium usage requires significant resources, particularly memory and CPU.

5. **Scraping Stagnation**: The spider might get stuck on certain requests (handled through timeout and retry).

6. **Regional Configuration Dependency**: The `regioni_paesi.json` file must be accurately maintained and updated.

## Implemented Best Practices

1. **Detailed Logging**: Every phase of the process is logged with appropriate verbosity levels.

2. **Resource Cleanup**: Careful management of browser and temporary file closure.

3. **Data Verification**: Quality checks on extracted data through similarity algorithms.

4. **Respectful Throttling**: Implementation of delays and concurrency limits to reduce load on target servers.

5. **Error Resilience**: Recovery and backup mechanisms to ensure extraction continuity.

6. **Modularity**: Clear separation of responsibilities between different components.

7. **Documentation**: Well-documented code with docstrings and explanatory comments.

## Ethical and Legal Considerations

- The system implements delays and throttling to minimize impact on target servers
- Respect for robots.txt policies is configurable through `ROBOTSTXT_OBEY`
- Use of this tool must comply with target platform terms of service
- User-Agent and proxy rotation should be used responsibly
