#!/usr/bin/env python3
"""
Example: Scrape a single LinkedIn profile and generate markdown for AI analysis

This example shows how to use the PersonScraper to scrape a LinkedIn profile
and generate a markdown document suitable for AI analysis.
"""
import asyncio
from pathlib import Path
from linkedin_scraper.scrapers.person import PersonScraper
from linkedin_scraper.core.browser import BrowserManager


async def main():
    """Scrape a single person profile and generate markdown"""
    profile_url = "https://www.linkedin.com/in/williamhgates/"
    
    # Initialize and start browser using context manager
    async with BrowserManager(headless=True) as browser:
        # Load existing session (must be created first - see README for setup)
        await browser.load_session("linkedin_session.json")
        print("✓ Session loaded")
        
        # Initialize scraper with the browser page
        scraper = PersonScraper(browser.page)
        
        # Scrape the profile
        print(f"🚀 Scraping: {profile_url}")
        person = await scraper.scrape(profile_url)
        
        # Display brief results
        print("\n" + "="*60)
        print(f"Name: {person.name}")
        print(f"Location: {person.location}")
        print(f"Current Position: {person.experiences[0].position_title if person.experiences else 'N/A'}")
        print(f"Current Company: {person.experiences[0].institution_name if person.experiences else 'N/A'}")
        print(f"Recent Posts: {len(person.recent_posts)}")
        print(f"Recent Comments: {len(person.recent_comments)}")
        print("="*60)
        
        # Generate markdown document
        print("\n📝 Generating markdown document...")
        markdown_content = PersonScraper.generate_markdown_profile(person)
        
        # Save to file
        output_file = Path("linkedin_profile_analysis.md")
        output_file.write_text(markdown_content, encoding='utf-8')
        
        print(f"✅ Markdown document saved to: {output_file.absolute()}")
        print(f"   File size: {len(markdown_content)} characters")
    
    print("\n✓ Done! You can now feed the markdown file to an AI for insights.")


if __name__ == "__main__":
    asyncio.run(main())
