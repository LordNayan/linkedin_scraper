#!/usr/bin/env python3
"""
Example: Scrape person profile with detailed information

This example shows how to scrape a LinkedIn person profile including
work experience, education history, recent posts, and recent comments.
"""
import asyncio
from linkedin_scraper.scrapers.person import PersonScraper
from linkedin_scraper.core.browser import BrowserManager


async def main():
    """Scrape a person profile"""
    profile_url = "https://www.linkedin.com/in/williamhgates/"
    
    # Initialize and start browser using context manager
    async with BrowserManager(headless=False) as browser:
        # Load existing session (must be created first - see README for setup)
        await browser.load_session("linkedin_session.json")
        print("✓ Session loaded")
        
        # Initialize scraper with the browser page
        scraper = PersonScraper(browser.page)
        
        # Scrape the profile
        print(f"🚀 Scraping: {profile_url}")
        person = await scraper.scrape(profile_url)
        
        # Display person info
        print("\n" + "="*60)
        print(f"Person: {person.name}")
        print(f"Location: {person.location}")
        print(f"About: {person.about[:100] if person.about else 'N/A'}...")
        print("="*60)
        
        # Display work experience
        print(f"\n💼 Work Experience ({len(person.experiences)} positions):")
        for exp in person.experiences[:5]:  # Show first 5
            print(f"  - {exp.position_title} at {exp.institution_name}")
            print(f"    {exp.from_date} - {exp.to_date}")
        
        if len(person.experiences) > 5:
            print(f"  ... and {len(person.experiences) - 5} more positions")
        
        # Display education
        print(f"\n🎓 Education ({len(person.educations)} schools):")
        for edu in person.educations[:3]:  # Show first 3
            print(f"  - {edu.institution_name}")
            if edu.degree:
                print(f"    {edu.degree}")
        
        if len(person.educations) > 3:
            print(f"  ... and {len(person.educations) - 3} more schools")
        
        # Display recent posts and reposts
        print(f"\n📝 Recent Posts & Reposts ({len(person.recent_posts)}):")
        for post in person.recent_posts:
            post_type = "🔄 Repost" if post.is_repost else "📄 Post"
            text_preview = post.text[:80] + "..." if post.text and len(post.text) > 80 else post.text
            print(f"  {post_type}: {text_preview}")
            if post.is_repost and post.original_author:
                print(f"    Originally by: {post.original_author}")
            print(f"    Posted: {post.posted_date} | 👍 {post.reactions_count or 0} | 💬 {post.comments_count or 0}")
        
        # Display recent comments
        print(f"\n💬 Recent Comments ({len(person.recent_comments)}):")
        for comment in person.recent_comments:
            comment_preview = comment.comment_text[:80] + "..." if comment.comment_text and len(comment.comment_text) > 80 else comment.comment_text
            print(f"  - {comment_preview}")
            if comment.post_author:
                print(f"    On post by: {comment.post_author}")
            if comment.commented_date:
                print(f"    Date: {comment.commented_date}")
    
    print("\n✓ Done!")


if __name__ == "__main__":
    asyncio.run(main())
