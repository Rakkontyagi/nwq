#!/usr/bin/env python3
"""
Test script for Google Keyword Ranking Tracker
Tests core functionality without making actual API calls
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

# Add the current directory to the path to import our module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_rank_tracker import (
    RankingResult, SearchConfig, SerperAPIClient, RankingParser,
    DatabaseManager, ReportGenerator, ConfigurationManager, GoogleRankTracker
)

class TestRankTracker(unittest.TestCase):
    """Test cases for the rank tracker components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_keywords = ["test keyword 1", "test keyword 2"]
        self.test_domain = "example.com"
        
        # Sample search results from Serper API
        self.sample_search_results = {
            "organic": [
                {
                    "title": "Example Domain",
                    "link": "https://example.com/page1",
                    "snippet": "This is a test snippet for example.com",
                    "position": 1
                },
                {
                    "title": "Another Site",
                    "link": "https://another-site.com/page",
                    "snippet": "This is another site",
                    "position": 2
                },
                {
                    "title": "Example Subdomain",
                    "link": "https://blog.example.com/article",
                    "snippet": "This is from a subdomain",
                    "position": 5
                }
            ],
            "searchParameters": {
                "q": "test keyword",
                "gl": "us",
                "hl": "en"
            }
        }
    
    def test_search_config_creation(self):
        """Test SearchConfig creation and validation"""
        config = SearchConfig(
            keywords=self.test_keywords,
            target_domain=self.test_domain,
            country="US",
            language="en"
        )
        
        self.assertEqual(config.keywords, self.test_keywords)
        self.assertEqual(config.target_domain, self.test_domain)
        self.assertEqual(config.country, "US")
        self.assertEqual(config.language, "en")
        self.assertEqual(config.device, "desktop")  # default value
    
    def test_ranking_result_creation(self):
        """Test RankingResult creation"""
        result = RankingResult(
            keyword="test keyword",
            position=1,
            url="https://example.com",
            title="Test Title",
            snippet="Test snippet",
            search_volume=None,
            difficulty=None,
            date=datetime.now().isoformat(),
            google_domain="google.com",
            country="US",
            language="en",
            device="desktop"
        )
        
        self.assertEqual(result.keyword, "test keyword")
        self.assertEqual(result.position, 1)
        self.assertEqual(result.url, "https://example.com")
    
    def test_ranking_parser_domain_extraction(self):
        """Test domain extraction from URLs"""
        parser = RankingParser("example.com")
        
        # Test various URL formats
        self.assertEqual(parser.extract_domain("https://example.com/page"), "example.com")
        self.assertEqual(parser.extract_domain("http://www.example.com/page"), "example.com")
        self.assertEqual(parser.extract_domain("https://blog.example.com"), "blog.example.com")
        self.assertEqual(parser.extract_domain("example.com"), "example.com")
    
    def test_ranking_parser_find_rankings(self):
        """Test ranking detection in search results"""
        parser = RankingParser("example.com")
        config = SearchConfig(
            keywords=["test keyword"],
            target_domain="example.com"
        )
        
        rankings = parser.find_rankings(self.sample_search_results, "test keyword", config)
        
        # Should find 2 rankings (position 1 and 5)
        found_rankings = [r for r in rankings if r.position is not None]
        self.assertEqual(len(found_rankings), 2)
        
        # Check positions
        positions = [r.position for r in found_rankings]
        self.assertIn(1, positions)
        self.assertIn(5, positions)
    
    def test_configuration_manager_keyword_loading(self):
        """Test loading keywords from file"""
        config_manager = ConfigurationManager()
        
        # Create temporary keyword file
        keyword_file = os.path.join(self.temp_dir, "test_keywords.txt")
        with open(keyword_file, 'w') as f:
            f.write("keyword 1\n")
            f.write("keyword 2\n")
            f.write("# This is a comment\n")
            f.write("\n")  # Empty line
            f.write("keyword 3\n")
        
        keywords = config_manager.load_keywords_from_file(keyword_file)
        
        self.assertEqual(len(keywords), 3)
        self.assertIn("keyword 1", keywords)
        self.assertIn("keyword 2", keywords)
        self.assertIn("keyword 3", keywords)
        self.assertNotIn("# This is a comment", keywords)
    
    def test_configuration_manager_csv_loading(self):
        """Test loading keywords from CSV file"""
        config_manager = ConfigurationManager()
        
        # Create temporary CSV file
        csv_file = os.path.join(self.temp_dir, "test_keywords.csv")
        with open(csv_file, 'w') as f:
            f.write("keyword 1,keyword 2,keyword 3\n")
            f.write("keyword 4,keyword 5\n")
        
        keywords = config_manager.load_keywords_from_file(csv_file)
        
        self.assertEqual(len(keywords), 5)
        for i in range(1, 6):
            self.assertIn(f"keyword {i}", keywords)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        config_manager = ConfigurationManager()
        
        # Valid configuration
        valid_config = SearchConfig(
            keywords=["test"],
            target_domain="example.com"
        )
        self.assertTrue(config_manager.validate_config(valid_config))
        
        # Invalid configuration - no keywords
        invalid_config = SearchConfig(
            keywords=[],
            target_domain="example.com"
        )
        self.assertFalse(config_manager.validate_config(invalid_config))
        
        # Invalid configuration - no domain
        invalid_config2 = SearchConfig(
            keywords=["test"],
            target_domain=""
        )
        self.assertFalse(config_manager.validate_config(invalid_config2))
    
    def test_database_operations(self):
        """Test database creation and operations"""
        db_file = os.path.join(self.temp_dir, "test_rankings.db")
        db_manager = DatabaseManager(db_file)
        
        # Create test ranking
        ranking = RankingResult(
            keyword="test keyword",
            position=1,
            url="https://example.com",
            title="Test Title",
            snippet="Test snippet",
            search_volume=None,
            difficulty=None,
            date=datetime.now().isoformat(),
            google_domain="google.com",
            country="US",
            language="en",
            device="desktop"
        )
        
        # Test saving
        success = db_manager.save_rankings([ranking])
        self.assertTrue(success)
        
        # Test retrieval
        historical = db_manager.get_historical_rankings("test keyword", 30)
        self.assertEqual(len(historical), 1)
        self.assertEqual(historical[0]['keyword'], "test keyword")
    
    def test_report_generation(self):
        """Test report generation functionality"""
        report_generator = ReportGenerator()
        
        # Create test ranking
        ranking = RankingResult(
            keyword="test keyword",
            position=1,
            url="https://example.com",
            title="Test Title",
            snippet="Test snippet",
            search_volume=None,
            difficulty=None,
            date=datetime.now().isoformat(),
            google_domain="google.com",
            country="US",
            language="en",
            device="desktop"
        )
        
        # Test CSV export
        csv_file = os.path.join(self.temp_dir, "test_results.csv")
        success = report_generator.export_to_csv([ranking], csv_file)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(csv_file))
        
        # Test JSON export
        json_file = os.path.join(self.temp_dir, "test_results.json")
        success = report_generator.export_to_json([ranking], json_file)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(json_file))
        
        # Verify JSON content
        with open(json_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['keyword'], "test keyword")
    
    @patch('google_rank_tracker.SerperAPIClient.search')
    def test_google_rank_tracker_integration(self, mock_search):
        """Test the main GoogleRankTracker class"""
        # Mock the API response
        mock_search.return_value = self.sample_search_results
        
        # Create tracker with dummy API key
        tracker = GoogleRankTracker("dummy_api_key")
        
        # Create configuration
        config = SearchConfig(
            keywords=["test keyword"],
            target_domain="example.com"
        )
        
        # Test tracking (with mocked API)
        results = tracker.track_keywords(config, save_to_db=False)
        
        # Verify results
        self.assertGreater(len(results), 0)
        found_rankings = [r for r in results if r.position is not None]
        self.assertGreater(len(found_rankings), 0)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

def run_comprehensive_tests():
    """Run all tests and provide detailed output"""
    print("🧪 Running comprehensive tests for Google Rank Tracker...")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRankTracker)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED! The script is fully functional.")
        print(f"✅ Ran {result.testsRun} tests successfully")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
