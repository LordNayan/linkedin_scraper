#!/usr/bin/env python3
"""
Example: Scrape LinkedIn profile for AI analysis

This script scrapes specific LinkedIn profile details and generates a markdown
document that can be directly fed to an AI for insights and analysis.

The script scrapes:
1. Profile URL
2. Name
3. Location
4. About section
5. Current company details (including what the company does)
6. Current designation and work description
7. Last 3 posts/reposts (complete text)
8. Last 3 comments with the post they commented on

Usage:
    python scrape_for_ai_analysis.py [profile_url]
    
If no profile URL is provided, defaults to Bill Gates' profile.
"""
import asyncio
import sys
from pathlib import Path
from linkedin_scraper.scrapers.person import PersonScraper
from linkedin_scraper.core.browser import BrowserManager


async def main():
    """Scrape profile and generate AI-ready markdown"""
    
    # Profile to scrape - accept from command line or use default
    if len(sys.argv) > 1:
        profile_url = sys.argv[1]
    else:
        profile_url = "https://www.linkedin.com/in/williamhgates/"
    
    # Initialize browser
    async with BrowserManager(headless=False) as browser:
        # Load your LinkedIn session
        await browser.load_session("linkedin_session.json")
        print("✓ Session loaded")
        
        # Initialize scraper
        scraper = PersonScraper(browser.page)
        
        # Scrape the profile (only gets required details)
        print(f"\n🔍 Scraping profile: {profile_url}")
        print("   Fetching: Name, Location, About, Current Job, Company, Posts, Comments...")
        
        person = await scraper.scrape(profile_url)
        
        # Show what was scraped
        print("\n" + "="*70)
        print("✅ Profile Scraped Successfully")
        print("="*70)
        print(f"Name:             {person.name}")
        print(f"Location:         {person.location or 'Not specified'}")
        print(f"Current Role:     {person.experiences[0].position_title if person.experiences else 'N/A'}")
        print(f"Current Company:  {person.experiences[0].institution_name if person.experiences else 'N/A'}")
        print(f"Recent Posts:     {len(person.recent_posts)} collected")
        print(f"Recent Comments:  {len(person.recent_comments)} collected")
        print("="*70)
        
        # Generate markdown for AI
        print("\n📝 Generating markdown document for AI analysis...")
        markdown_content = PersonScraper.generate_markdown_profile(person)
        
        # Save to file
        output_file = Path("linkedin_profile_analysis.md")
        output_file.write_text(markdown_content, encoding='utf-8')
        
        print(f"\n✅ Success!")
        print(f"   📄 File: {output_file.absolute()}")
        print(f"   📊 Size: {len(markdown_content):,} characters")
        print(f"\n💡 Next Steps:")
        print(f"   1. Open '{output_file.name}' in a text editor")
        print(f"   2. Copy the content")
        print(f"   3. Feed it to an AI (ChatGPT, Claude, etc.) for insights")
        print(f"   4. Ask questions like:")
        print(f"      - 'Analyze this LinkedIn profile'")
        print(f"      - 'What are the key themes in their posts?'")
        print(f"      - 'What can you tell about their professional interests?'")
    
    print("\n✓ Done!")


if __name__ == "__main__":
    asyncio.run(main())
