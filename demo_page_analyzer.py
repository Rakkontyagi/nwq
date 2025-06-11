#!/usr/bin/env python3
"""
Demo script for the Page Ranking Analyzer
Tests the page-level analysis functionality
"""

import os
import sys
import time
from page_ranking_analyzer import PageRankingTracker, SearchConfig, setup_logging

def demo_page_analysis():
    """Demonstrate page-level ranking analysis"""
    
    # Setup logging
    setup_logging(verbose=True)
    
    # API key (replace with your actual key)
    api_key = "4ce37b02808e4325e42068eb815b03490a5519e5"
    
    print("🔍 PAGE RANKING ANALYZER DEMO")
    print("=" * 50)
    
    # Test 1: Single keyword analysis
    print("\n📊 TEST 1: Single Keyword Analysis")
    print("-" * 40)
    
    target_domain = "visiting-angels.co.uk"
    test_keyword = "home care services"
    
    config = SearchConfig(
        keywords=[test_keyword],
        target_domain=target_domain,
        google_domain='google.co.uk',
        country='GB',
        language='en',
        device='desktop',
        rate_limit_delay=0.5
    )
    
    tracker = PageRankingTracker(api_key, target_domain, config)
    
    print(f"Analyzing: '{test_keyword}' for domain: {target_domain}")
    
    start_time = time.time()
    page_rankings = tracker.track_keywords([test_keyword])
    end_time = time.time()
    
    print(f"\n✅ Analysis completed in {end_time - start_time:.1f} seconds")
    print(f"Found {len(page_rankings)} page(s) ranking for '{test_keyword}'")
    
    # Display results
    if page_rankings:
        print("\n📄 PAGES FOUND:")
        for ranking in page_rankings:
            print(f"  • Page: {ranking.page_path}")
            print(f"    Position: #{ranking.position}")
            print(f"    URL: {ranking.page_url}")
            print(f"    Title: {ranking.page_title[:60]}...")
            print()
    else:
        print("❌ No pages found ranking for this keyword")
    
    # Test 2: Multiple keywords analysis
    print("\n📊 TEST 2: Multiple Keywords Analysis")
    print("-" * 40)
    
    test_keywords = [
        "elderly care",
        "home care services", 
        "caregiver support",
        "senior care"
    ]
    
    config.keywords = test_keywords
    tracker2 = PageRankingTracker(api_key, target_domain, config)
    
    print(f"Analyzing {len(test_keywords)} keywords for domain: {target_domain}")
    
    start_time = time.time()
    all_rankings = tracker2.track_keywords(test_keywords, max_workers=2)
    end_time = time.time()
    
    print(f"\n✅ Analysis completed in {end_time - start_time:.1f} seconds")
    print(f"Found {len(all_rankings)} total page rankings")
    
    # Generate page summary
    summary = tracker2.generate_page_summary()
    
    if summary:
        print(f"\n📊 PAGE SUMMARY ({len(summary)} unique pages):")
        print("-" * 60)
        
        # Sort by total keywords
        sorted_pages = sorted(summary.items(), key=lambda x: x[1]['total_keywords'], reverse=True)
        
        for page_path, data in sorted_pages:
            print(f"\n📄 {page_path}")
            print(f"   Keywords: {data['total_keywords']} | Best: #{data['best_position']} | Avg: #{data['average_position']}")
            print(f"   URL: {data['page_url']}")
            
            # Show keywords
            for kw in data['keywords'][:3]:  # Show top 3
                print(f"   • {kw['keyword']} (#{kw['position']})")
            
            if len(data['keywords']) > 3:
                print(f"   ... and {len(data['keywords']) - 3} more")
    
    # Test 3: Export functionality
    print("\n📊 TEST 3: Export Functionality")
    print("-" * 40)
    
    try:
        # Export detailed results
        csv_file = tracker2.export_to_csv("demo_page_rankings.csv")
        print(f"✅ Detailed results exported to: {csv_file}")
        
        # Export page summary
        summary_file = tracker2.export_page_summary_to_csv("demo_page_summary.csv")
        print(f"✅ Page summary exported to: {summary_file}")
        
        # Show file sizes
        if os.path.exists(csv_file):
            size = os.path.getsize(csv_file)
            print(f"   Detailed file size: {size} bytes")
        
        if os.path.exists(summary_file):
            size = os.path.getsize(summary_file)
            print(f"   Summary file size: {size} bytes")
            
    except Exception as e:
        print(f"❌ Export failed: {e}")
    
    print("\n🎉 DEMO COMPLETED!")
    print("=" * 50)
    
    return len(all_rankings)

def demo_different_domains():
    """Test with different domains"""
    
    print("\n🌐 TESTING DIFFERENT DOMAINS")
    print("=" * 50)
    
    api_key = "4ce37b02808e4325e42068eb815b03490a5519e5"
    
    test_cases = [
        {
            'domain': 'balkland.com',
            'keyword': 'balkan tours',
            'country': 'US',
            'google_domain': 'google.com'
        },
        {
            'domain': 'visiting-angels.co.uk',
            'keyword': 'home care',
            'country': 'GB', 
            'google_domain': 'google.co.uk'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 TEST CASE {i}: {test_case['domain']}")
        print("-" * 40)
        
        config = SearchConfig(
            keywords=[test_case['keyword']],
            target_domain=test_case['domain'],
            google_domain=test_case['google_domain'],
            country=test_case['country'],
            language='en',
            rate_limit_delay=1.0
        )
        
        tracker = PageRankingTracker(api_key, test_case['domain'], config)
        
        try:
            rankings = tracker.track_keywords([test_case['keyword']])
            
            if rankings:
                print(f"✅ Found {len(rankings)} page(s) for '{test_case['keyword']}'")
                for ranking in rankings:
                    print(f"   • {ranking.page_path} (#{ranking.position})")
            else:
                print(f"❌ No pages found for '{test_case['keyword']}'")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Small delay between tests
        time.sleep(2)

if __name__ == "__main__":
    try:
        print("🚀 Starting Page Ranking Analyzer Demo...")
        
        # Run main demo
        total_rankings = demo_page_analysis()
        
        # Run domain comparison demo
        demo_different_domains()
        
        print(f"\n✅ Demo completed successfully!")
        print(f"Total page rankings found: {total_rankings}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)
