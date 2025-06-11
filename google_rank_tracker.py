#!/usr/bin/env python3
"""
Google Keyword Ranking Tracker using Serper API
A comprehensive, production-ready script for tracking keyword rankings on Google.

Author: AI Assistant
Version: 1.0.0
License: MIT
"""

import os
import sys
import json
import csv
import time
import sqlite3
import logging
import argparse
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse
import concurrent.futures
import threading
from dataclasses import dataclass, asdict

try:
    import requests
    from colorama import init, Fore, Back, Style
    from tqdm import tqdm
    import pandas as pd
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

@dataclass
class RankingResult:
    """Data class for storing ranking results"""
    keyword: str
    position: Optional[int]
    url: str
    title: str
    snippet: str
    search_volume: Optional[int]
    difficulty: Optional[float]
    date: str
    google_domain: str
    country: str
    language: str
    device: str

@dataclass
class SearchConfig:
    """Configuration for search parameters"""
    keywords: List[str]
    target_domain: str
    google_domain: str = 'google.com'
    country: str = 'US'
    language: str = 'en'
    location: Optional[str] = None
    device: str = 'desktop'
    results_per_page: int = 100
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_delay: float = 0.1

class SerperAPIClient:
    """Client for interacting with the Serper API"""
    
    def __init__(self, api_key: str, rate_limit_delay: float = 0.1):
        self.api_key = api_key
        self.base_url = "https://google.serper.dev"
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-KEY': api_key,
            'Content-Type': 'application/json'
        })
        self._last_request_time = 0
        self._lock = threading.Lock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _rate_limit(self):
        """Implement rate limiting"""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - time_since_last
                time.sleep(sleep_time)
            self._last_request_time = time.time()
    
    def search(self, query: str, config: SearchConfig, max_retries: int = 3) -> Dict[str, Any]:
        """
        Perform a search query using the Serper API
        
        Args:
            query: Search query string
            config: Search configuration
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary containing search results
            
        Raises:
            requests.RequestException: If API request fails after retries
        """
        self._rate_limit()
        
        # Prepare search parameters
        params = {
            'q': query,
            'gl': config.country.lower(),
            'hl': config.language.lower(),
            'num': min(config.results_per_page, 100),  # Serper max is 100
            'autocorrect': True,
            'type': 'search'
        }
        
        # Add location if specified
        if config.location:
            params['location'] = config.location
        
        # Add device type if mobile
        if config.device.lower() == 'mobile':
            params['device'] = 'mobile'
        
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"Searching for '{query}' (attempt {attempt + 1})")
                
                response = self.session.post(
                    f"{self.base_url}/search",
                    json=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit exceeded
                    wait_time = (2 ** attempt) * config.retry_delay
                    self.logger.warning(f"Rate limit exceeded. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 401:
                    raise requests.RequestException("Invalid API key")
                elif response.status_code == 403:
                    raise requests.RequestException("API access forbidden")
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Request timeout for query '{query}' (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(config.retry_delay * (attempt + 1))
                    continue
                else:
                    raise requests.RequestException(f"Request timeout after {max_retries} attempts")
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed for query '{query}': {e}")
                if attempt < max_retries - 1:
                    time.sleep(config.retry_delay * (attempt + 1))
                    continue
                else:
                    raise
        
        raise requests.RequestException(f"Failed to get results after {max_retries} attempts")

class RankingParser:
    """Parser for extracting ranking information from search results"""
    
    def __init__(self, target_domain: str):
        self.target_domain = target_domain.lower().strip()
        if self.target_domain.startswith('http'):
            self.target_domain = urlparse(self.target_domain).netloc
        if self.target_domain.startswith('www.'):
            self.target_domain = self.target_domain[4:]
        
        self.logger = logging.getLogger(__name__)
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url if url.startswith('http') else f'http://{url}')
            domain = parsed.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return url.lower()
    
    def find_rankings(self, search_results: Dict[str, Any], keyword: str, config: SearchConfig) -> List[RankingResult]:
        """
        Find rankings for the target domain in search results
        
        Args:
            search_results: Raw search results from Serper API
            keyword: The search keyword
            config: Search configuration
            
        Returns:
            List of RankingResult objects
        """
        rankings = []
        current_date = datetime.now().isoformat()
        
        # Check organic results
        organic_results = search_results.get('organic', [])
        
        for result in organic_results:
            try:
                url = result.get('link', '')
                title = result.get('title', '')
                snippet = result.get('snippet', '')
                position = result.get('position', 0)

                # Extract domain from URL
                result_domain = self.extract_domain(url)

                # Check if this result matches our target domain
                if self.target_domain in result_domain or result_domain in self.target_domain:
                    ranking = RankingResult(
                        keyword=keyword,
                        position=position,
                        url=url,
                        title=title,
                        snippet=snippet,
                        search_volume=None,  # Not available from Serper
                        difficulty=None,     # Not available from Serper
                        date=current_date,
                        google_domain=config.google_domain,
                        country=config.country,
                        language=config.language,
                        device=config.device
                    )
                    rankings.append(ranking)
                    self.logger.info(f"Found ranking for '{keyword}': Position {position}")
            except Exception as e:
                self.logger.warning(f"Error processing search result: {e}")
                continue
        
        # If no rankings found, create a "not found" entry
        if not rankings:
            ranking = RankingResult(
                keyword=keyword,
                position=None,
                url='',
                title='',
                snippet='',
                search_volume=None,
                difficulty=None,
                date=current_date,
                google_domain=config.google_domain,
                country=config.country,
                language=config.language,
                device=config.device
            )
            rankings.append(ranking)
            self.logger.info(f"No ranking found for '{keyword}' in top {config.results_per_page} results")
        
        return rankings

class DatabaseManager:
    """Manager for SQLite database operations"""
    
    def __init__(self, db_path: str = 'ranking_history.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS rankings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keyword TEXT NOT NULL,
                        position INTEGER,
                        url TEXT,
                        title TEXT,
                        snippet TEXT,
                        search_volume INTEGER,
                        difficulty REAL,
                        date TEXT NOT NULL,
                        google_domain TEXT,
                        country TEXT,
                        language TEXT,
                        device TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_keyword_date 
                    ON rankings(keyword, date)
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    def save_rankings(self, rankings: List[RankingResult]) -> bool:
        """Save ranking results to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for ranking in rankings:
                    cursor.execute('''
                        INSERT INTO rankings (
                            keyword, position, url, title, snippet, search_volume,
                            difficulty, date, google_domain, country, language, device
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ranking.keyword, ranking.position, ranking.url, ranking.title,
                        ranking.snippet, ranking.search_volume, ranking.difficulty,
                        ranking.date, ranking.google_domain, ranking.country,
                        ranking.language, ranking.device
                    ))
                
                conn.commit()
                self.logger.info(f"Saved {len(rankings)} ranking results to database")
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save rankings to database: {e}")
            return False
    
    def get_historical_rankings(self, keyword: str, days: int = 30) -> List[Dict]:
        """Get historical rankings for a keyword"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM rankings 
                    WHERE keyword = ? 
                    AND date >= date('now', '-{} days')
                    ORDER BY date DESC
                '''.format(days), (keyword,))
                
                columns = [description[0] for description in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return results
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get historical rankings: {e}")
            return []

class ReportGenerator:
    """Generator for various output formats and reports"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def print_console_results(self, rankings: List[RankingResult], target_domain: str):
        """Print results to console with colored formatting"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}GOOGLE RANKING RESULTS FOR: {Fore.YELLOW}{target_domain}")
        print(f"{Fore.CYAN}{'='*80}")

        if not rankings:
            print(f"{Fore.RED}No results found.")
            return

        # Group by keyword
        keyword_groups = {}
        for ranking in rankings:
            if ranking.keyword not in keyword_groups:
                keyword_groups[ranking.keyword] = []
            keyword_groups[ranking.keyword].append(ranking)

        for keyword, keyword_rankings in keyword_groups.items():
            print(f"\n{Fore.WHITE}Keyword: {Fore.GREEN}{keyword}")
            print(f"{Fore.WHITE}{'─' * 60}")

            for ranking in keyword_rankings:
                if ranking.position:
                    color = Fore.GREEN if ranking.position <= 10 else Fore.YELLOW if ranking.position <= 50 else Fore.RED
                    print(f"{Fore.WHITE}Position: {color}{ranking.position}")
                    print(f"{Fore.WHITE}URL: {Fore.BLUE}{ranking.url}")
                    print(f"{Fore.WHITE}Title: {ranking.title[:80]}...")
                    print(f"{Fore.WHITE}Snippet: {ranking.snippet[:100]}...")
                else:
                    print(f"{Fore.RED}Not found in top {100} results")

                print(f"{Fore.WHITE}Date: {ranking.date}")
                print(f"{Fore.WHITE}Country: {ranking.country} | Language: {ranking.language} | Device: {ranking.device}")
                print()

    def export_to_csv(self, rankings: List[RankingResult], filename: str) -> bool:
        """Export rankings to CSV file"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'keyword', 'position', 'url', 'title', 'snippet', 'search_volume',
                    'difficulty', 'date', 'google_domain', 'country', 'language', 'device'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for ranking in rankings:
                    writer.writerow(asdict(ranking))

            self.logger.info(f"Results exported to CSV: {filename}")
            print(f"{Fore.GREEN}Results exported to CSV: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")
            print(f"{Fore.RED}Failed to export to CSV: {e}")
            return False

    def export_to_json(self, rankings: List[RankingResult], filename: str) -> bool:
        """Export rankings to JSON file"""
        try:
            data = [asdict(ranking) for ranking in rankings]
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(data, jsonfile, indent=2, ensure_ascii=False)

            self.logger.info(f"Results exported to JSON: {filename}")
            print(f"{Fore.GREEN}Results exported to JSON: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}")
            print(f"{Fore.RED}Failed to export to JSON: {e}")
            return False

    def export_to_excel(self, rankings: List[RankingResult], filename: str) -> bool:
        """Export rankings to Excel file"""
        try:
            data = [asdict(ranking) for ranking in rankings]
            df = pd.DataFrame(data)

            # Create Excel writer with formatting
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Rankings', index=False)

                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Rankings']

                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            self.logger.info(f"Results exported to Excel: {filename}")
            print(f"{Fore.GREEN}Results exported to Excel: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to export to Excel: {e}")
            print(f"{Fore.RED}Failed to export to Excel: {e}")
            return False

class ConfigurationManager:
    """Manager for handling configuration and settings"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def load_keywords_from_file(self, filepath: str) -> List[str]:
        """Load keywords from a text or CSV file"""
        keywords = []
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                if filepath.lower().endswith('.csv'):
                    reader = csv.reader(file)
                    for row in reader:
                        if row:  # Skip empty rows
                            keywords.extend([kw.strip() for kw in row if kw.strip()])
                else:
                    # Treat as text file with one keyword per line
                    for line in file:
                        keyword = line.strip()
                        if keyword and not keyword.startswith('#'):  # Skip empty lines and comments
                            keywords.append(keyword)

            # Remove duplicates while preserving order
            seen = set()
            unique_keywords = []
            for kw in keywords:
                if kw not in seen:
                    seen.add(kw)
                    unique_keywords.append(kw)

            self.logger.info(f"Loaded {len(unique_keywords)} keywords from {filepath}")
            return unique_keywords

        except FileNotFoundError:
            self.logger.error(f"Keywords file not found: {filepath}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load keywords from {filepath}: {e}")
            raise

    def load_config_from_file(self, filepath: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                config = json.load(file)

            self.logger.info(f"Configuration loaded from {filepath}")
            return config

        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {filepath}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def validate_config(self, config: SearchConfig) -> bool:
        """Validate search configuration"""
        errors = []

        if not config.keywords:
            errors.append("No keywords provided")

        if not config.target_domain:
            errors.append("No target domain provided")

        if config.results_per_page < 1 or config.results_per_page > 100:
            errors.append("Results per page must be between 1 and 100")

        if config.max_retries < 1 or config.max_retries > 10:
            errors.append("Max retries must be between 1 and 10")

        if config.retry_delay < 0:
            errors.append("Retry delay must be non-negative")

        if config.device not in ['desktop', 'mobile']:
            errors.append("Device must be 'desktop' or 'mobile'")

        if errors:
            for error in errors:
                self.logger.error(f"Configuration error: {error}")
            return False

        return True

class GoogleRankTracker:
    """Main class for Google keyword ranking tracking"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = SerperAPIClient(api_key)
        self.db_manager = DatabaseManager()
        self.report_generator = ReportGenerator()
        self.config_manager = ConfigurationManager()
        self.logger = logging.getLogger(__name__)

    def track_keywords(self, config: SearchConfig, save_to_db: bool = True,
                      export_csv: str = None, export_json: str = None,
                      export_excel: str = None) -> List[RankingResult]:
        """
        Track keyword rankings for the specified configuration

        Args:
            config: Search configuration
            save_to_db: Whether to save results to database
            export_csv: CSV filename for export (optional)
            export_json: JSON filename for export (optional)
            export_excel: Excel filename for export (optional)

        Returns:
            List of ranking results
        """
        if not self.config_manager.validate_config(config):
            raise ValueError("Invalid configuration")

        parser = RankingParser(config.target_domain)
        all_rankings = []

        print(f"{Fore.CYAN}Starting keyword ranking tracking...")
        print(f"{Fore.WHITE}Target Domain: {Fore.YELLOW}{config.target_domain}")
        print(f"{Fore.WHITE}Keywords: {len(config.keywords)}")
        print(f"{Fore.WHITE}Google Domain: {config.google_domain}")
        print(f"{Fore.WHITE}Country: {config.country} | Language: {config.language}")
        print(f"{Fore.WHITE}Device: {config.device}")
        print()

        # Process keywords with progress bar
        with tqdm(total=len(config.keywords), desc="Processing keywords",
                 bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:

            for keyword in config.keywords:
                try:
                    pbar.set_description(f"Processing: {keyword[:30]}...")

                    # Perform search
                    search_results = self.client.search(keyword, config)

                    # Parse rankings
                    rankings = parser.find_rankings(search_results, keyword, config)
                    all_rankings.extend(rankings)

                    pbar.update(1)

                except Exception as e:
                    self.logger.error(f"Failed to process keyword '{keyword}': {e}")
                    print(f"{Fore.RED}Error processing '{keyword}': {e}")
                    pbar.update(1)
                    continue

        print(f"\n{Fore.GREEN}Completed processing {len(config.keywords)} keywords")
        print(f"{Fore.WHITE}Found {len([r for r in all_rankings if r.position])} rankings")

        # Save to database
        if save_to_db and all_rankings:
            self.db_manager.save_rankings(all_rankings)

        # Export results
        if export_csv and all_rankings:
            self.report_generator.export_to_csv(all_rankings, export_csv)

        if export_json and all_rankings:
            self.report_generator.export_to_json(all_rankings, export_json)

        if export_excel and all_rankings:
            self.report_generator.export_to_excel(all_rankings, export_excel)

        # Display console results
        self.report_generator.print_console_results(all_rankings, config.target_domain)

        return all_rankings

    def track_keywords_concurrent(self, config: SearchConfig, max_workers: int = 5,
                                save_to_db: bool = True, export_csv: str = None,
                                export_json: str = None, export_excel: str = None) -> List[RankingResult]:
        """
        Track keyword rankings using concurrent processing

        Args:
            config: Search configuration
            max_workers: Maximum number of concurrent workers
            save_to_db: Whether to save results to database
            export_csv: CSV filename for export (optional)
            export_json: JSON filename for export (optional)
            export_excel: Excel filename for export (optional)

        Returns:
            List of ranking results
        """
        if not self.config_manager.validate_config(config):
            raise ValueError("Invalid configuration")

        parser = RankingParser(config.target_domain)
        all_rankings = []

        print(f"{Fore.CYAN}Starting concurrent keyword ranking tracking...")
        print(f"{Fore.WHITE}Target Domain: {Fore.YELLOW}{config.target_domain}")
        print(f"{Fore.WHITE}Keywords: {len(config.keywords)}")
        print(f"{Fore.WHITE}Max Workers: {max_workers}")
        print(f"{Fore.WHITE}Google Domain: {config.google_domain}")
        print(f"{Fore.WHITE}Country: {config.country} | Language: {config.language}")
        print()

        def process_keyword(keyword: str) -> List[RankingResult]:
            """Process a single keyword"""
            try:
                search_results = self.client.search(keyword, config)
                return parser.find_rankings(search_results, keyword, config)
            except Exception as e:
                self.logger.error(f"Failed to process keyword '{keyword}': {e}")
                return []

        # Process keywords concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            with tqdm(total=len(config.keywords), desc="Processing keywords",
                     bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") as pbar:

                # Submit all tasks
                future_to_keyword = {
                    executor.submit(process_keyword, keyword): keyword
                    for keyword in config.keywords
                }

                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_keyword):
                    keyword = future_to_keyword[future]
                    try:
                        rankings = future.result()
                        all_rankings.extend(rankings)
                    except Exception as e:
                        self.logger.error(f"Failed to get results for '{keyword}': {e}")
                    finally:
                        pbar.update(1)

        print(f"\n{Fore.GREEN}Completed processing {len(config.keywords)} keywords")
        print(f"{Fore.WHITE}Found {len([r for r in all_rankings if r.position])} rankings")

        # Save to database
        if save_to_db and all_rankings:
            self.db_manager.save_rankings(all_rankings)

        # Export results
        if export_csv and all_rankings:
            self.report_generator.export_to_csv(all_rankings, export_csv)

        if export_json and all_rankings:
            self.report_generator.export_to_json(all_rankings, export_json)

        if export_excel and all_rankings:
            self.report_generator.export_to_excel(all_rankings, export_excel)

        # Display console results
        self.report_generator.print_console_results(all_rankings, config.target_domain)

        return all_rankings

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)

def validate_api_key(api_key: str) -> bool:
    """Validate Serper API key by making a test request"""
    try:
        client = SerperAPIClient(api_key)
        test_config = SearchConfig(
            keywords=['test'],
            target_domain='example.com',
            results_per_page=1
        )
        client.search('test query', test_config)
        return True
    except requests.RequestException as e:
        if "Invalid API key" in str(e) or "401" in str(e):
            return False
        # Other errors might be temporary, so we assume the key is valid
        return True
    except Exception:
        return True  # Assume valid if we can't test

def create_sample_files():
    """Create sample configuration and keywords files"""

    # Sample configuration file
    sample_config = {
        "keywords": ["python tutorial", "web development", "SEO tips"],
        "target_domain": "example.com",
        "google_domain": "google.com",
        "country": "US",
        "language": "en",
        "location": "New York, NY",
        "device": "desktop",
        "results_per_page": 100,
        "max_retries": 3,
        "retry_delay": 1.0,
        "rate_limit_delay": 0.1
    }

    try:
        with open('config.json', 'w') as f:
            json.dump(sample_config, f, indent=2)
        print(f"{Fore.GREEN}Sample configuration file created: config.json")
    except Exception as e:
        print(f"{Fore.RED}Failed to create config.json: {e}")

    # Sample keywords file
    sample_keywords = [
        "python programming",
        "web development tutorial",
        "SEO best practices",
        "digital marketing",
        "keyword research tools",
        "google ranking factors",
        "content marketing strategy",
        "social media marketing",
        "email marketing tips",
        "conversion rate optimization"
    ]

    try:
        with open('keywords.txt', 'w') as f:
            for keyword in sample_keywords:
                f.write(f"{keyword}\n")
        print(f"{Fore.GREEN}Sample keywords file created: keywords.txt")
    except Exception as e:
        print(f"{Fore.RED}Failed to create keywords.txt: {e}")

def main():
    """Main function for command-line interface"""
    parser = argparse.ArgumentParser(
        description='Google Keyword Ranking Tracker using Serper API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single keyword check
  python google_rank_tracker.py --keyword "python tutorial" --domain "example.com"

  # Multiple keywords from file
  python google_rank_tracker.py --keywords keywords.txt --domain "example.com" --country "UK"

  # Using configuration file
  python google_rank_tracker.py --config config.json

  # Export results to multiple formats
  python google_rank_tracker.py --keyword "SEO tips" --domain "example.com" --csv results.csv --json results.json --excel results.xlsx

  # Concurrent processing
  python google_rank_tracker.py --keywords keywords.txt --domain "example.com" --concurrent --workers 10
        """
    )

    # API Configuration
    parser.add_argument('--api-key', type=str,
                       help='Serper API key (or set SERPER_API_KEY environment variable)')

    # Input options
    parser.add_argument('--keyword', type=str,
                       help='Single keyword to track')
    parser.add_argument('--keywords', type=str,
                       help='File containing keywords (one per line or CSV)')
    parser.add_argument('--config', type=str,
                       help='JSON configuration file')

    # Search configuration
    parser.add_argument('--domain', type=str, required=False,
                       help='Target domain to track rankings for')
    parser.add_argument('--google-domain', type=str, default='google.com',
                       help='Google domain to search (default: google.com)')
    parser.add_argument('--country', type=str, default='US',
                       help='Country code for search (default: US)')
    parser.add_argument('--language', type=str, default='en',
                       help='Language code for search (default: en)')
    parser.add_argument('--location', type=str,
                       help='Specific location for local search')
    parser.add_argument('--device', type=str, choices=['desktop', 'mobile'], default='desktop',
                       help='Device type for search (default: desktop)')
    parser.add_argument('--results', type=int, default=100,
                       help='Number of results to check (max 100, default: 100)')

    # Processing options
    parser.add_argument('--concurrent', action='store_true',
                       help='Use concurrent processing for faster results')
    parser.add_argument('--workers', type=int, default=5,
                       help='Number of concurrent workers (default: 5)')
    parser.add_argument('--max-retries', type=int, default=3,
                       help='Maximum number of retries for failed requests (default: 3)')
    parser.add_argument('--retry-delay', type=float, default=1.0,
                       help='Delay between retries in seconds (default: 1.0)')
    parser.add_argument('--rate-limit', type=float, default=0.1,
                       help='Delay between API requests in seconds (default: 0.1)')

    # Output options
    parser.add_argument('--csv', type=str,
                       help='Export results to CSV file')
    parser.add_argument('--json', type=str,
                       help='Export results to JSON file')
    parser.add_argument('--excel', type=str,
                       help='Export results to Excel file')
    parser.add_argument('--no-db', action='store_true',
                       help='Do not save results to database')

    # Utility options
    parser.add_argument('--create-samples', action='store_true',
                       help='Create sample configuration and keywords files')
    parser.add_argument('--validate-key', action='store_true',
                       help='Validate API key and exit')
    parser.add_argument('--log-level', type=str, default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    parser.add_argument('--log-file', type=str,
                       help='Log file path (optional)')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)

    # Create sample files if requested
    if args.create_samples:
        create_sample_files()
        return

    # Get API key
    api_key = args.api_key or os.getenv('SERPER_API_KEY')
    if not api_key:
        print(f"{Fore.RED}Error: Serper API key is required.")
        print(f"{Fore.WHITE}Set SERPER_API_KEY environment variable or use --api-key argument.")
        print(f"{Fore.WHITE}Get your API key from: https://serper.dev/")
        sys.exit(1)

    # Validate API key if requested
    if args.validate_key:
        print(f"{Fore.CYAN}Validating API key...")
        if validate_api_key(api_key):
            print(f"{Fore.GREEN}API key is valid!")
        else:
            print(f"{Fore.RED}API key is invalid!")
            sys.exit(1)
        return

    try:
        # Initialize tracker
        tracker = GoogleRankTracker(api_key)

        # Load configuration
        if args.config:
            # Load from configuration file
            config_data = tracker.config_manager.load_config_from_file(args.config)
            config = SearchConfig(**config_data)
        else:
            # Build configuration from arguments
            keywords = []

            if args.keyword:
                keywords = [args.keyword]
            elif args.keywords:
                keywords = tracker.config_manager.load_keywords_from_file(args.keywords)
            else:
                print(f"{Fore.RED}Error: No keywords specified.")
                print(f"{Fore.WHITE}Use --keyword for single keyword or --keywords for file.")
                sys.exit(1)

            if not args.domain:
                print(f"{Fore.RED}Error: Target domain is required.")
                print(f"{Fore.WHITE}Use --domain argument to specify target domain.")
                sys.exit(1)

            config = SearchConfig(
                keywords=keywords,
                target_domain=args.domain,
                google_domain=args.google_domain,
                country=args.country,
                language=args.language,
                location=args.location,
                device=args.device,
                results_per_page=args.results,
                max_retries=args.max_retries,
                retry_delay=args.retry_delay,
                rate_limit_delay=args.rate_limit
            )

        # Track keywords
        if args.concurrent:
            results = tracker.track_keywords_concurrent(
                config=config,
                max_workers=args.workers,
                save_to_db=not args.no_db,
                export_csv=args.csv,
                export_json=args.json,
                export_excel=args.excel
            )
        else:
            results = tracker.track_keywords(
                config=config,
                save_to_db=not args.no_db,
                export_csv=args.csv,
                export_json=args.json,
                export_excel=args.excel
            )

        print(f"\n{Fore.GREEN}Tracking completed successfully!")
        print(f"{Fore.WHITE}Total results: {len(results)}")
        print(f"{Fore.WHITE}Rankings found: {len([r for r in results if r.position])}")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"{Fore.RED}Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

