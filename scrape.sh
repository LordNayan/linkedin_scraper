#!/bin/bash
# Quick Start: LinkedIn Profile for AI Analysis
# This script helps you quickly scrape a LinkedIn profile for AI analysis

echo "🚀 LinkedIn Profile Scraper for AI Analysis"
echo "==========================================="
echo ""

# Check if session file exists
if [ ! -f "linkedin_session.json" ]; then
    echo "❌ Error: linkedin_session.json not found"
    echo ""
    echo "Please create a session first:"
    echo "  python samples/create_session.py"
    echo ""
    exit 1
fi

echo "✓ Session file found"
echo ""

# Get profile URL from user
echo "Enter the LinkedIn profile URL to scrape:"
echo "Example: https://www.linkedin.com/in/williamhgates/"
read -p "Profile URL: " PROFILE_URL

if [ -z "$PROFILE_URL" ]; then
    echo "❌ Error: No URL provided"
    exit 1
fi

echo ""
echo "📝 Creating custom scraper script..."

# Create temporary Python script
cat > temp_scrape.py << EOF
import asyncio
from pathlib import Path
from linkedin_scraper.scrapers.person import PersonScraper
from linkedin_scraper.core.browser import BrowserManager

async def main():
    profile_url = "${PROFILE_URL}"
    import re
    from pathlib import Path
    
    # Extract username from profile URL for unique filename
    match = re.search(r"linkedin.com/in/([\w\-]+)", profile_url)
    username = match.group(1) if match else "profile"
    
    # Ensure output directory exists
    output_dir = Path("scraped_profiles")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    async with BrowserManager(headless=False) as browser:
        await browser.load_session("linkedin_session.json")
        print("✓ Session loaded")
        
        scraper = PersonScraper(browser.page)
        print(f"🔍 Scraping: {profile_url}")
        
        person = await scraper.scrape(profile_url)
        
        print(f"✓ Profile scraped: {person.name}")
        
        # Generate markdown
        markdown = PersonScraper.generate_markdown_profile(person)
        
        # Save to unique file in scraped_profiles
        output_file = output_dir / f"{username}_profile_analysis.md"
        output_file.write_text(markdown, encoding='utf-8')
        
        print(f"✓ Markdown saved to: {output_file.absolute()}")
        print(f"✓ File size: {len(markdown):,} characters")

asyncio.run(main())
EOF

echo "✓ Script created"
echo ""
echo "🏃 Running scraper..."
echo ""

# Run the scraper
python temp_scrape.py

# Clean up
rm temp_scrape.py

echo ""
echo "✅ Done!"
echo ""
echo "📄 Output file: scraped_profiles/<username>_profile_analysis.md"
echo ""
echo "💡 Next steps:"
echo "   1. Open scraped_profiles/<username>_profile_analysis.md"
echo "   2. Copy all content"
echo "   3. Paste into ChatGPT, Claude, or any AI"
echo "   4. Ask for insights!"
echo ""
echo "Example prompts:"
echo '   - "Analyze this LinkedIn profile"'
echo '   - "What are the key themes in their posts?"'
echo '   - "Summarize their professional focus"'
echo ""
