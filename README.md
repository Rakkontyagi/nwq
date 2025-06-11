# Google Keyword Ranking Tracker

A comprehensive, production-ready Python script for tracking keyword rankings on Google using the Serper API. This tool supports multiple keywords, different Google domains/regions, and provides comprehensive ranking data with various export options.

## Features

### Core Functionality
- ✅ **Multi-keyword support** - Process single keywords, keyword lists, or CSV files
- ✅ **Multi-region Google support** - Different Google domains, countries, and languages
- ✅ **Serper API integration** - Robust API client with rate limiting and error handling
- ✅ **Ranking detection** - Find target domain rankings in organic search results
- ✅ **Historical tracking** - SQLite database for storing ranking history
- ✅ **Multiple export formats** - CSV, JSON, and Excel export capabilities
- ✅ **Concurrent processing** - Fast processing with configurable worker threads
- ✅ **Comprehensive error handling** - Graceful handling of API errors and edge cases

### Advanced Features
- 🎯 **Precise targeting** - Track specific domains and subdomains
- 🌍 **Global search support** - Search across different countries and languages
- 📱 **Device-specific results** - Desktop and mobile search results
- 📊 **Rich reporting** - Colored console output and detailed reports
- ⚡ **Performance optimized** - Rate limiting, retries, and concurrent processing
- 🔧 **Highly configurable** - Command-line arguments and JSON configuration files

## Installation

### Prerequisites
- Python 3.7 or higher
- Serper API key (get one at [serper.dev](https://serper.dev/))

### Setup
1. Clone or download the script files
2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Set your Serper API key:
```bash
export SERPER_API_KEY="your_api_key_here"
```

Or create a `.env` file:
```
SERPER_API_KEY=your_api_key_here
```

## Quick Start

### 1. Create Sample Files
```bash
python google_rank_tracker.py --create-samples
```

### 2. Single Keyword Check
```bash
python google_rank_tracker.py --keyword "python tutorial" --domain "example.com"
```

### 3. Multiple Keywords from File
```bash
python google_rank_tracker.py --keywords keywords.txt --domain "example.com"
```

### 4. Using Configuration File
```bash
python google_rank_tracker.py --config config.json
```

## Usage Examples

### Basic Usage
```bash
# Track a single keyword
python google_rank_tracker.py --keyword "SEO tips" --domain "mysite.com"

# Track multiple keywords from file
python google_rank_tracker.py --keywords keywords.txt --domain "mysite.com"

# Specify country and language
python google_rank_tracker.py --keyword "marketing tips" --domain "mysite.com" --country "UK" --language "en"
```

### Advanced Usage
```bash
# Concurrent processing for faster results
python google_rank_tracker.py --keywords keywords.txt --domain "mysite.com" --concurrent --workers 10

# Export to multiple formats
python google_rank_tracker.py --keywords keywords.txt --domain "mysite.com" --csv results.csv --json results.json --excel results.xlsx

# Mobile search results
python google_rank_tracker.py --keyword "mobile app" --domain "mysite.com" --device mobile

# Local search with specific location
python google_rank_tracker.py --keyword "restaurant" --domain "mysite.com" --location "New York, NY"
```

### Configuration File Usage
Create a `config.json` file:
```json
{
  "keywords": ["keyword1", "keyword2", "keyword3"],
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
```

Then run:
```bash
python google_rank_tracker.py --config config.json
```

## Command Line Arguments

### Required Arguments
- `--keyword` - Single keyword to track
- `--keywords` - File containing keywords (one per line or CSV)
- `--config` - JSON configuration file
- `--domain` - Target domain to track rankings for

### Search Configuration
- `--google-domain` - Google domain to search (default: google.com)
- `--country` - Country code for search (default: US)
- `--language` - Language code for search (default: en)
- `--location` - Specific location for local search
- `--device` - Device type: desktop or mobile (default: desktop)
- `--results` - Number of results to check, max 100 (default: 100)

### Processing Options
- `--concurrent` - Use concurrent processing for faster results
- `--workers` - Number of concurrent workers (default: 5)
- `--max-retries` - Maximum retries for failed requests (default: 3)
- `--retry-delay` - Delay between retries in seconds (default: 1.0)
- `--rate-limit` - Delay between API requests in seconds (default: 0.1)

### Output Options
- `--csv` - Export results to CSV file
- `--json` - Export results to JSON file
- `--excel` - Export results to Excel file
- `--no-db` - Do not save results to database

### Utility Options
- `--api-key` - Serper API key (or set SERPER_API_KEY env var)
- `--create-samples` - Create sample configuration and keywords files
- `--validate-key` - Validate API key and exit
- `--log-level` - Logging level: DEBUG, INFO, WARNING, ERROR
- `--log-file` - Log file path (optional)

## Output Formats

### Console Output
The script provides colored console output showing:
- Keyword rankings with positions
- URLs, titles, and snippets
- Search parameters and metadata
- Progress indicators and status messages

### CSV Export
Columns include:
- keyword, position, url, title, snippet
- search_volume, difficulty, date
- google_domain, country, language, device

### JSON Export
Structured JSON format with all ranking data and metadata.

### Excel Export
Formatted Excel file with auto-adjusted column widths and proper data types.

### Database Storage
SQLite database (`ranking_history.db`) stores all historical ranking data for trend analysis.

## Error Handling

The script includes comprehensive error handling for:
- ✅ Invalid API keys
- ✅ Network timeouts and connection errors
- ✅ Rate limit exceeded (with automatic retry)
- ✅ Invalid keywords or domains
- ✅ File I/O errors
- ✅ Malformed configuration files
- ✅ API quota exceeded

## Performance Features

- **Rate Limiting**: Respects API rate limits with configurable delays
- **Retry Logic**: Automatic retries with exponential backoff
- **Concurrent Processing**: Multi-threaded processing for large keyword lists
- **Progress Tracking**: Real-time progress bars for long operations
- **Memory Efficient**: Processes keywords in batches to manage memory usage

## Supported Google Domains

The script supports all Google domains including:
- google.com (Global)
- google.co.uk (United Kingdom)
- google.ca (Canada)
- google.com.au (Australia)
- google.de (Germany)
- google.fr (France)
- And many more...

## API Key Setup

1. Visit [serper.dev](https://serper.dev/)
2. Sign up for a free account
3. Get your API key from the dashboard
4. Set the environment variable or use the `--api-key` argument

## Troubleshooting

### Common Issues

**"Invalid API key" error:**
- Verify your API key is correct
- Check that SERPER_API_KEY environment variable is set
- Use `--validate-key` to test your API key

**"Rate limit exceeded" error:**
- Increase `--rate-limit` delay (e.g., `--rate-limit 0.5`)
- Reduce `--workers` for concurrent processing
- Check your API plan limits

**"No rankings found" message:**
- Verify the target domain is correct
- Check if the domain actually ranks in top 100 results
- Try different keyword variations

**File not found errors:**
- Ensure keywords file exists and is readable
- Check file path and permissions
- Use absolute paths if needed

### Debug Mode
Enable debug logging for detailed troubleshooting:
```bash
python google_rank_tracker.py --keyword "test" --domain "example.com" --log-level DEBUG
```

## License

MIT License - feel free to use and modify as needed.

## Support

For issues, questions, or feature requests, please check the script's error messages and logs first. The script includes comprehensive error handling and logging to help diagnose issues.