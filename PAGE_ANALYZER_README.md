# 📊 Website Page Ranking Analyzer

**Analyze which specific pages of your website rank for each keyword - Perfect for content strategy and SEO optimization!**

## 🎯 **What This Tool Does**

Instead of just showing you **position numbers**, this analyzer shows you **which specific pages** of your website are ranking for each keyword. This is incredibly valuable for:

- ✅ **Content Strategy** - See which pages are performing well
- ✅ **SEO Optimization** - Identify pages that need improvement  
- ✅ **Content Gaps** - Find keywords with no ranking pages
- ✅ **Page Performance** - Track which pages rank for multiple keywords
- ✅ **Competitive Analysis** - Understand your content landscape

## 🚀 **Key Features**

### **Page-Focused Analysis**
- Shows **exact page paths** ranking for each keyword
- Groups results by **page** rather than keyword
- Identifies **high-performing pages** with multiple keyword rankings
- Finds **content gaps** where no pages rank

### **Comprehensive Reporting**
- **Detailed CSV** - Every keyword-to-page mapping
- **Page Summary CSV** - Pages grouped with all their keywords
- **Console Output** - Formatted summary with statistics
- **SQLite Database** - Historical tracking and analysis

### **Smart Domain Matching**
- Automatically handles www/non-www variations
- Supports subdomains and complex URL structures
- Flexible domain matching for accurate results

## 📋 **Installation & Setup**

### **1. Install Dependencies**
```bash
pip install requests colorama tqdm pandas python-dotenv openpyxl
```

### **2. Get Serper API Key**
1. Visit [serper.dev](https://serper.dev)
2. Sign up for free account
3. Get your API key from dashboard

### **3. Download the Script**
```bash
# Clone from GitHub
git clone https://github.com/Rakkontyagi/nwq.git
cd nwq

# Or download directly
wget https://raw.githubusercontent.com/Rakkontyagi/nwq/feature/initial-backend-setup/page_ranking_analyzer.py
```

## 🎮 **Usage Examples**

### **Basic Usage - Single Keyword**
```bash
python page_ranking_analyzer.py \
  --api-key "your_serper_api_key" \
  --keyword "home care services" \
  --domain "your-website.com"
```

### **Multiple Keywords from File**
```bash
python page_ranking_analyzer.py \
  --api-key "your_serper_api_key" \
  --keywords-file keywords.txt \
  --domain "your-website.com" \
  --export-csv results.csv \
  --export-summary summary.csv
```

### **UK Market Analysis**
```bash
python page_ranking_analyzer.py \
  --api-key "your_serper_api_key" \
  --keywords-file uk_keywords.txt \
  --domain "your-site.co.uk" \
  --country GB \
  --google-domain google.co.uk \
  --export-summary uk_page_analysis.csv
```

### **Advanced Configuration**
```bash
python page_ranking_analyzer.py \
  --api-key "your_serper_api_key" \
  --keywords-file keywords.txt \
  --domain "your-website.com" \
  --country US \
  --language en \
  --device desktop \
  --max-workers 3 \
  --rate-limit 0.5 \
  --export-csv detailed_results.csv \
  --export-summary page_summary.csv \
  --verbose
```

## 📊 **Output Examples**

### **Console Output**
```
📊 PAGE RANKING SUMMARY
================================================================================

📄 Page: Homepage
   URL: https://www.visiting-angels.co.uk/
   Title: Visiting Angels: Home Care Services | Elderly and Respite Care...
   Keywords: 3 | Best Position: #33 | Avg Position: #38.7
   1. elderly care (#33)
   2. home health care (#41)
   3. senior care (#42)

📄 Page: westlondon
   URL: https://www.visiting-angels.co.uk/westlondon/
   Title: Home Care Service in West London - Visiting Angels...
   Keywords: 1 | Best Position: #17 | Avg Position: #17.0
   1. home care london (#17)
```

### **Page Summary CSV**
```csv
page_path,page_url,page_title,total_keywords,best_position,average_position,keywords_list
Homepage,https://www.visiting-angels.co.uk/,Visiting Angels: Home Care Services,3,33,38.7,"elderly care (#33); home health care (#41); senior care (#42)"
westlondon,https://www.visiting-angels.co.uk/westlondon/,Home Care Service in West London,1,17,17.0,"home care london (#17)"
```

### **Detailed Results CSV**
```csv
keyword,page_path,page_url,page_title,position,snippet,date,google_domain,country,language,device
elderly care,Homepage,https://www.visiting-angels.co.uk/,Visiting Angels: Home Care Services,33,"Exceptional Care Services...",2025-06-11T16:50:06,google.co.uk,GB,en,desktop
home care london,westlondon,https://www.visiting-angels.co.uk/westlondon/,Home Care Service in West London,17,"Professional home care...",2025-06-11T16:50:06,google.co.uk,GB,en,desktop
```

## 🎯 **Real-World Use Cases**

### **1. Content Strategy Planning**
**Question:** "Which pages should I optimize first?"
**Answer:** Pages with multiple keyword rankings but lower positions

### **2. Content Gap Analysis**
**Question:** "What keywords have no ranking pages?"
**Answer:** Keywords that return zero results - content opportunities

### **3. Page Performance Audit**
**Question:** "Which pages are my top performers?"
**Answer:** Pages ranking for multiple keywords with good positions

### **4. Location-Based SEO**
**Question:** "How are my location pages performing?"
**Answer:** Compare rankings across different location-specific pages

## 🔧 **Command Line Options**

### **Required Arguments**
- `--api-key` - Your Serper API key
- `--domain` - Target domain to analyze (e.g., your-website.com)
- `--keyword` OR `--keywords-file` - Single keyword or file with keywords

### **Search Configuration**
- `--country` - Country code (default: US)
- `--language` - Language code (default: en)  
- `--google-domain` - Google domain (default: google.com)
- `--location` - Specific location for search
- `--device` - desktop or mobile (default: desktop)

### **Output Options**
- `--export-csv` - Export detailed results to CSV
- `--export-summary` - Export page summary to CSV
- `--no-summary` - Skip console summary

### **Performance Options**
- `--max-workers` - Concurrent workers (default: 5)
- `--rate-limit` - Delay between requests (default: 0.1s)

### **Utility Options**
- `--validate-key` - Test API key and exit
- `--verbose` - Enable detailed logging

## 📈 **Performance & Limits**

### **Speed**
- **Single keyword:** ~1-2 seconds
- **10 keywords:** ~10-15 seconds  
- **50 keywords:** ~45-60 seconds
- **100+ keywords:** ~2-3 minutes

### **API Limits**
- **Free Serper Plan:** 2,500 searches/month
- **Pro Plan:** 10,000+ searches/month
- **Rate limiting:** Built-in delays prevent API errors

### **Accuracy**
- **Search Results:** Top 100 positions tracked
- **Domain Matching:** Handles www, subdomains, URL variations
- **Real-time Data:** Fresh results from Google

## 🎯 **Strategic Insights You'll Get**

### **Page Performance Ranking**
1. **Top Performers** - Pages ranking for multiple keywords
2. **Underperformers** - Pages with poor average positions
3. **Specialists** - Pages ranking for specific keyword types
4. **Opportunities** - Pages that could rank for more keywords

### **Content Strategy Insights**
1. **Content Gaps** - Keywords with no ranking pages
2. **Cannibalization** - Multiple pages competing for same keywords
3. **Optimization Targets** - Pages close to top 10 rankings
4. **Content Expansion** - Successful pages that could target more keywords

### **SEO Action Items**
1. **Immediate Wins** - Pages ranking 11-20 that could reach top 10
2. **Content Creation** - Keywords with no ranking pages
3. **Page Optimization** - Underperforming pages with potential
4. **Internal Linking** - Connect related high-performing pages

## 🚀 **Getting Started**

1. **Get your API key** from [serper.dev](https://serper.dev)
2. **Create keywords file** with your target keywords
3. **Run the analyzer** with your domain
4. **Analyze the results** to identify opportunities
5. **Take action** based on insights

**Ready to discover which pages are driving your SEO success?** 🎯
