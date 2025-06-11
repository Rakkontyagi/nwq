#!/usr/bin/env python3
"""
Website Page Ranking Analyzer using Serper API
Analyzes which specific pages of your website rank for each keyword

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
from collections import defaultdict

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
class PageRanking:
    """Data class for storing page ranking results"""
    keyword: str
    page_url: str
    page_path: str
    page_title: str
    snippet: str
    position: int
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
        """Perform a search query using the Serper API"""
        self._rate_limit()
        
        # Prepare search parameters
        params = {
            'q': query,
            'gl': config.country.lower(),
            'hl': config.language.lower(),
            'num': min(config.results_per_page, 100),
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

class PageAnalyzer:
    """Analyzer for extracting page-level ranking information"""
    
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
    
    def extract_page_path(self, url: str) -> str:
        """Extract the page path from URL"""
        try:
            parsed = urlparse(url if url.startswith('http') else f'http://{url}')
            path = parsed.path
            if path == '/':
                return 'Homepage'
            return path.strip('/')
        except Exception:
            return 'Unknown'
    
    def find_page_rankings(self, search_results: Dict[str, Any], keyword: str, config: SearchConfig) -> List[PageRanking]:
        """Find all pages from target domain ranking for the keyword"""
        page_rankings = []
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
                    page_path = self.extract_page_path(url)
                    
                    page_ranking = PageRanking(
                        keyword=keyword,
                        page_url=url,
                        page_path=page_path,
                        page_title=title,
                        snippet=snippet,
                        position=position,
                        date=current_date,
                        google_domain=config.google_domain,
                        country=config.country,
                        language=config.language,
                        device=config.device
                    )
                    page_rankings.append(page_ranking)
                    self.logger.info(f"Found page ranking for '{keyword}': {page_path} at position {position}")
            
            except Exception as e:
                self.logger.warning(f"Error processing search result: {e}")
                continue
        
        return page_rankings

class PageRankingDatabase:
    """Manager for SQLite database operations focused on page rankings"""
    
    def __init__(self, db_path: str = 'page_rankings.db'):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS page_rankings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        keyword TEXT NOT NULL,
                        page_url TEXT NOT NULL,
                        page_path TEXT NOT NULL,
                        page_title TEXT,
                        snippet TEXT,
                        position INTEGER,
                        date TEXT NOT NULL,
                        google_domain TEXT,
                        country TEXT,
                        language TEXT,
                        device TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_keyword_page 
                    ON page_rankings(keyword, page_path)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_page_path 
                    ON page_rankings(page_path)
                ''')
                
                conn.commit()
                self.logger.info("Page rankings database initialized successfully")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    def save_page_rankings(self, rankings: List[PageRanking]) -> bool:
        """Save page ranking results to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for ranking in rankings:
                    cursor.execute('''
                        INSERT INTO page_rankings (
                            keyword, page_url, page_path, page_title, snippet, position,
                            date, google_domain, country, language, device
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ranking.keyword, ranking.page_url, ranking.page_path, ranking.page_title,
                        ranking.snippet, ranking.position, ranking.date, ranking.google_domain,
                        ranking.country, ranking.language, ranking.device
                    ))
                
                conn.commit()
                self.logger.info(f"Saved {len(rankings)} page ranking results to database")
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save page rankings to database: {e}")
            return False

class PageRankingTracker:
    """Main class for tracking page rankings"""

    def __init__(self, api_key: str, target_domain: str, config: SearchConfig):
        self.api_client = SerperAPIClient(api_key, config.rate_limit_delay)
        self.page_analyzer = PageAnalyzer(target_domain)
        self.database = PageRankingDatabase()
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Results storage
        self.all_page_rankings: List[PageRanking] = []
        self.page_summary: Dict[str, List[str]] = defaultdict(list)

    def track_keyword(self, keyword: str) -> List[PageRanking]:
        """Track page rankings for a single keyword"""
        try:
            self.logger.info(f"Tracking page rankings for keyword: '{keyword}'")

            # Perform search
            search_results = self.api_client.search(keyword, self.config)

            # Extract page rankings
            page_rankings = self.page_analyzer.find_page_rankings(search_results, keyword, self.config)

            if page_rankings:
                self.logger.info(f"Found {len(page_rankings)} page(s) ranking for '{keyword}'")
                for ranking in page_rankings:
                    self.page_summary[ranking.page_path].append(f"{keyword} (#{ranking.position})")
            else:
                self.logger.info(f"No pages found ranking for '{keyword}'")

            return page_rankings

        except Exception as e:
            self.logger.error(f"Error tracking keyword '{keyword}': {e}")
            return []

    def track_keywords(self, keywords: List[str], max_workers: int = 5) -> List[PageRanking]:
        """Track page rankings for multiple keywords"""
        self.logger.info(f"Starting page ranking analysis for {len(keywords)} keywords")

        all_rankings = []

        # Use progress bar
        with tqdm(total=len(keywords), desc="Analyzing page rankings", unit="keyword") as pbar:
            if max_workers == 1:
                # Sequential processing
                for keyword in keywords:
                    rankings = self.track_keyword(keyword)
                    all_rankings.extend(rankings)
                    self.all_page_rankings.extend(rankings)
                    pbar.update(1)
            else:
                # Concurrent processing
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_keyword = {
                        executor.submit(self.track_keyword, keyword): keyword
                        for keyword in keywords
                    }

                    for future in concurrent.futures.as_completed(future_to_keyword):
                        keyword = future_to_keyword[future]
                        try:
                            rankings = future.result()
                            all_rankings.extend(rankings)
                            self.all_page_rankings.extend(rankings)
                        except Exception as e:
                            self.logger.error(f"Error processing keyword '{keyword}': {e}")
                        finally:
                            pbar.update(1)

        # Save to database
        if all_rankings:
            self.database.save_page_rankings(all_rankings)

        self.logger.info(f"Page ranking analysis completed. Found {len(all_rankings)} total page rankings")
        return all_rankings

    def generate_page_summary(self) -> Dict[str, Dict[str, Any]]:
        """Generate a summary of which pages rank for which keywords"""
        summary = {}

        for ranking in self.all_page_rankings:
            page_path = ranking.page_path

            if page_path not in summary:
                summary[page_path] = {
                    'page_url': ranking.page_url,
                    'page_title': ranking.page_title,
                    'keywords': [],
                    'total_keywords': 0,
                    'best_position': float('inf'),
                    'average_position': 0
                }

            summary[page_path]['keywords'].append({
                'keyword': ranking.keyword,
                'position': ranking.position,
                'snippet': ranking.snippet[:100] + '...' if len(ranking.snippet) > 100 else ranking.snippet
            })

            # Update statistics
            summary[page_path]['total_keywords'] += 1
            summary[page_path]['best_position'] = min(summary[page_path]['best_position'], ranking.position)

        # Calculate average positions
        for page_path, data in summary.items():
            if data['keywords']:
                avg_pos = sum(k['position'] for k in data['keywords']) / len(data['keywords'])
                data['average_position'] = round(avg_pos, 1)

                # Sort keywords by position
                data['keywords'].sort(key=lambda x: x['position'])

        return summary

    def export_to_csv(self, filename: str = None) -> str:
        """Export page rankings to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"page_rankings_{timestamp}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'keyword', 'page_path', 'page_url', 'page_title', 'position',
                    'snippet', 'date', 'google_domain', 'country', 'language', 'device'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for ranking in self.all_page_rankings:
                    writer.writerow({
                        'keyword': ranking.keyword,
                        'page_path': ranking.page_path,
                        'page_url': ranking.page_url,
                        'page_title': ranking.page_title,
                        'position': ranking.position,
                        'snippet': ranking.snippet,
                        'date': ranking.date,
                        'google_domain': ranking.google_domain,
                        'country': ranking.country,
                        'language': ranking.language,
                        'device': ranking.device
                    })

            self.logger.info(f"Page rankings exported to {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")
            raise

    def export_page_summary_to_csv(self, filename: str = None) -> str:
        """Export page summary to CSV"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"page_summary_{timestamp}.csv"

        try:
            summary = self.generate_page_summary()

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'page_path', 'page_url', 'page_title', 'total_keywords',
                    'best_position', 'average_position', 'keywords_list'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for page_path, data in summary.items():
                    keywords_list = '; '.join([f"{k['keyword']} (#{k['position']})" for k in data['keywords']])

                    writer.writerow({
                        'page_path': page_path,
                        'page_url': data['page_url'],
                        'page_title': data['page_title'],
                        'total_keywords': data['total_keywords'],
                        'best_position': data['best_position'] if data['best_position'] != float('inf') else 'N/A',
                        'average_position': data['average_position'],
                        'keywords_list': keywords_list
                    })

            self.logger.info(f"Page summary exported to {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"Failed to export page summary to CSV: {e}")
            raise

def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Setup file handler
    file_handler = logging.FileHandler('page_ranking_analyzer.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

def load_keywords_from_file(file_path: str) -> List[str]:
    """Load keywords from a text file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return keywords
    except FileNotFoundError:
        raise FileNotFoundError(f"Keywords file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading keywords file: {e}")

def validate_api_key(api_key: str) -> bool:
    """Validate the Serper API key"""
    try:
        client = SerperAPIClient(api_key)
        test_config = SearchConfig(
            keywords=["test"],
            target_domain="example.com",
            results_per_page=10
        )

        # Try a simple search
        result = client.search("test query", test_config)
        return 'organic' in result or 'answerBox' in result

    except Exception as e:
        print(f"API key validation failed: {e}")
        return False

def print_page_summary(tracker: PageRankingTracker) -> None:
    """Print a formatted summary of page rankings"""
    summary = tracker.generate_page_summary()

    if not summary:
        print(f"\n{Fore.YELLOW}No pages found ranking for the analyzed keywords.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.GREEN}📊 PAGE RANKING SUMMARY{Style.RESET_ALL}")
    print("=" * 80)

    # Sort pages by total keywords (descending)
    sorted_pages = sorted(summary.items(), key=lambda x: x[1]['total_keywords'], reverse=True)

    for page_path, data in sorted_pages:
        print(f"\n{Fore.CYAN}📄 Page: {page_path}{Style.RESET_ALL}")
        print(f"   URL: {data['page_url']}")
        print(f"   Title: {data['page_title'][:80]}...")
        print(f"   Keywords: {data['total_keywords']} | Best Position: #{data['best_position']} | Avg Position: #{data['average_position']}")

        # Show top 5 keywords
        top_keywords = data['keywords'][:5]
        for i, kw in enumerate(top_keywords, 1):
            print(f"   {i}. {kw['keyword']} (#{kw['position']})")

        if len(data['keywords']) > 5:
            print(f"   ... and {len(data['keywords']) - 5} more keywords")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Website Page Ranking Analyzer - Analyze which pages rank for keywords",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze single keyword
  python page_ranking_analyzer.py --api-key YOUR_KEY --keyword "home care services" --domain "visiting-angels.co.uk"

  # Analyze keywords from file
  python page_ranking_analyzer.py --api-key YOUR_KEY --keywords-file keywords.txt --domain "your-website.com"

  # UK market analysis
  python page_ranking_analyzer.py --api-key YOUR_KEY --keywords-file keywords.txt --domain "your-site.co.uk" --country GB --google-domain google.co.uk

  # Export results
  python page_ranking_analyzer.py --api-key YOUR_KEY --keyword "test" --domain "example.com" --export-csv results.csv
        """
    )

    # Required arguments
    parser.add_argument('--api-key', required=True, help='Serper API key')
    parser.add_argument('--domain', required=True, help='Target domain to analyze (e.g., your-website.com)')

    # Keyword input (mutually exclusive)
    keyword_group = parser.add_mutually_exclusive_group(required=True)
    keyword_group.add_argument('--keyword', help='Single keyword to analyze')
    keyword_group.add_argument('--keywords-file', help='File containing keywords (one per line)')

    # Search configuration
    parser.add_argument('--country', default='US', help='Country code (default: US)')
    parser.add_argument('--language', default='en', help='Language code (default: en)')
    parser.add_argument('--google-domain', default='google.com', help='Google domain (default: google.com)')
    parser.add_argument('--location', help='Specific location for search')
    parser.add_argument('--device', choices=['desktop', 'mobile'], default='desktop', help='Device type (default: desktop)')

    # Output options
    parser.add_argument('--export-csv', help='Export detailed results to CSV file')
    parser.add_argument('--export-summary', help='Export page summary to CSV file')
    parser.add_argument('--no-summary', action='store_true', help='Skip printing summary to console')

    # Performance options
    parser.add_argument('--max-workers', type=int, default=5, help='Maximum concurrent workers (default: 5)')
    parser.add_argument('--rate-limit', type=float, default=0.1, help='Rate limit delay in seconds (default: 0.1)')

    # Utility options
    parser.add_argument('--validate-key', action='store_true', help='Validate API key and exit')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # Validate API key if requested
        if args.validate_key:
            print("Validating API key...")
            if validate_api_key(args.api_key):
                print(f"{Fore.GREEN}✅ API key is valid!{Style.RESET_ALL}")
                return 0
            else:
                print(f"{Fore.RED}❌ API key is invalid!{Style.RESET_ALL}")
                return 1

        # Load keywords
        if args.keyword:
            keywords = [args.keyword]
        else:
            keywords = load_keywords_from_file(args.keywords_file)

        print(f"{Fore.BLUE}🔍 Starting page ranking analysis...{Style.RESET_ALL}")
        print(f"Domain: {args.domain}")
        print(f"Keywords: {len(keywords)}")
        print(f"Market: {args.country} ({args.google_domain})")

        # Create search configuration
        config = SearchConfig(
            keywords=keywords,
            target_domain=args.domain,
            google_domain=args.google_domain,
            country=args.country,
            language=args.language,
            location=args.location,
            device=args.device,
            rate_limit_delay=args.rate_limit
        )

        # Initialize tracker
        tracker = PageRankingTracker(args.api_key, args.domain, config)

        # Track keywords
        start_time = time.time()
        page_rankings = tracker.track_keywords(keywords, args.max_workers)
        end_time = time.time()

        # Print results
        print(f"\n{Fore.GREEN}✅ Analysis completed in {end_time - start_time:.1f} seconds{Style.RESET_ALL}")
        print(f"Found {len(page_rankings)} page rankings across {len(set(r.page_path for r in page_rankings))} unique pages")

        # Print summary unless disabled
        if not args.no_summary:
            print_page_summary(tracker)

        # Export results
        if args.export_csv:
            tracker.export_to_csv(args.export_csv)
            print(f"{Fore.GREEN}📄 Detailed results exported to: {args.export_csv}{Style.RESET_ALL}")

        if args.export_summary:
            tracker.export_page_summary_to_csv(args.export_summary)
            print(f"{Fore.GREEN}📊 Page summary exported to: {args.export_summary}{Style.RESET_ALL}")

        return 0

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Analysis interrupted by user{Style.RESET_ALL}")
        return 1
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
