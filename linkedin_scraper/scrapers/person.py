"""Person/Profile scraper for LinkedIn."""

import logging
import re
from typing import Optional, List
from urllib.parse import urljoin
from playwright.async_api import Page

from .base import BaseScraper
from ..models import Person, Experience, Education, Accomplishment, Interest, Contact
from ..models.person import PersonActivity, PersonComment
from ..callbacks import ProgressCallback, SilentCallback
from ..core.exceptions import ScrapingError

logger = logging.getLogger(__name__)


class PersonScraper(BaseScraper):
    """Async scraper for LinkedIn person profiles."""

    def __init__(self, page: Page, callback: Optional[ProgressCallback] = None):
        """
        Initialize person scraper.

        Args:
            page: Playwright page object
            callback: Progress callback
        """
        super().__init__(page, callback)

    async def scrape(self, linkedin_url: str) -> Person:
        """
        Scrape a LinkedIn person profile.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            Person object with all scraped data

        Raises:
            AuthenticationError: If not logged in
            ScrapingError: If scraping fails
        """
        await self.callback.on_start("person", linkedin_url)

        try:
            # Navigate to profile first (this loads the page with our session)
            await self.navigate_and_wait(linkedin_url)
            await self.callback.on_progress("Navigated to profile", 10)

            # Now check if logged in
            await self.ensure_logged_in()

            # Wait for main content
            await self.page.wait_for_selector("main", timeout=10000)
            await self.wait_and_focus(1)

            # Get name and location
            name, location = await self._get_name_and_location()
            await self.callback.on_progress(f"Got name: {name}", 20)

            # Get headline
            headline = await self._get_headline()
            await self.callback.on_progress("Got headline", 25)

            # Check open to work
            open_to_work = await self._check_open_to_work()

            # Get about
            about = await self._get_about()
            await self.callback.on_progress("Got about section", 30)

            # Scroll to load content
            await self.scroll_page_to_half()
            await self.scroll_page_to_bottom(pause_time=0.5, max_scrolls=3)

            # Get only current experience (first one)
            experiences = await self._get_experiences(linkedin_url)
            current_experience = experiences[0] if experiences else None
            await self.callback.on_progress(f"Got current experience", 50)

            # Get current company details if there's a current experience
            current_company = None
            if current_experience and current_experience.linkedin_url:
                try:
                    from .company import CompanyScraper
                    from .company_posts import CompanyPostsScraper
                    
                    company_scraper = CompanyScraper(self.page)
                    current_company = await company_scraper.scrape(current_experience.linkedin_url)
                    await self.callback.on_progress(f"Got company details", 60)
                    
                    # Also get company's recent posts (last 3)
                    try:
                        posts_scraper = CompanyPostsScraper(self.page)
                        company_posts = await posts_scraper.scrape(current_experience.linkedin_url, limit=3)
                        current_company.recent_posts = company_posts
                        await self.callback.on_progress(f"Got {len(company_posts)} company posts", 70)
                    except Exception as e:
                        logger.warning(f"Could not scrape company posts: {e}")
                        
                except Exception as e:
                    logger.warning(f"Could not scrape company details: {e}")

            # Comment out other scraping
            # educations = await self._get_educations(linkedin_url)
            # await self.callback.on_progress(f"Got {len(educations)} educations", 50)

            # interests = await self._get_interests(linkedin_url)
            # await self.callback.on_progress(f"Got {len(interests)} interests", 65)

            # accomplishments = await self._get_accomplishments(linkedin_url)
            # await self.callback.on_progress(
            #     f"Got {len(accomplishments)} accomplishments", 85
            # )

            # contacts = await self._get_contacts(linkedin_url)
            # await self.callback.on_progress(f"Got {len(contacts)} contacts", 90)

            # Get recent posts and reposts (last 3)
            recent_posts = await self._get_recent_posts(linkedin_url, limit=3)
            await self.callback.on_progress(f"Got {len(recent_posts)} recent posts", 95)

            # Get recent comments (last 3)
            recent_comments = await self._get_recent_comments(linkedin_url, limit=3)
            await self.callback.on_progress(f"Got {len(recent_comments)} recent comments", 98)

            person = Person(
                linkedin_url=linkedin_url,
                name=name,
                headline=headline,
                location=location,
                about=about,
                open_to_work=open_to_work,
                experiences=[current_experience] if current_experience else [],
                educations=[],  # Commented out
                interests=[],  # Commented out
                accomplishments=[],  # Commented out
                contacts=[],  # Commented out
                recent_posts=recent_posts,
                recent_comments=recent_comments,
                current_company=current_company,  # Include in initialization
            )

            await self.callback.on_progress("Scraping complete", 100)
            await self.callback.on_complete("person", person)

            return person

        except Exception as e:
            await self.callback.on_error(e)
            raise ScrapingError(f"Failed to scrape person profile: {e}")

    async def scrape_recent_posts(self, linkedin_url: str, limit: int = 3) -> List[PersonActivity]:
        """
        Scrape only the recent posts and reposts from a LinkedIn profile.
        
        Args:
            linkedin_url: LinkedIn profile URL
            limit: Number of posts to retrieve (default 3)
            
        Returns:
            List of PersonActivity objects
            
        Raises:
            AuthenticationError: If not logged in
            ScrapingError: If scraping fails
        """
        await self.callback.on_start("person_posts", linkedin_url)
        
        try:
            await self.navigate_and_wait(linkedin_url)
            await self.ensure_logged_in()
            
            posts = await self._get_recent_posts(linkedin_url, limit=limit)
            await self.callback.on_progress(f"Got {len(posts)} recent posts", 100)
            await self.callback.on_complete("person_posts", posts)
            
            return posts
            
        except Exception as e:
            await self.callback.on_error(e)
            raise ScrapingError(f"Failed to scrape person posts: {e}")

    async def scrape_recent_comments(self, linkedin_url: str, limit: int = 3) -> List[PersonComment]:
        """
        Scrape only the recent comments from a LinkedIn profile.
        
        Args:
            linkedin_url: LinkedIn profile URL
            limit: Number of comments to retrieve (default 3)
            
        Returns:
            List of PersonComment objects
            
        Raises:
            AuthenticationError: If not logged in
            ScrapingError: If scraping fails
        """
        await self.callback.on_start("person_comments", linkedin_url)
        
        try:
            await self.navigate_and_wait(linkedin_url)
            await self.ensure_logged_in()
            
            comments = await self._get_recent_comments(linkedin_url, limit=limit)
            await self.callback.on_progress(f"Got {len(comments)} recent comments", 100)
            await self.callback.on_complete("person_comments", comments)
            
            return comments
            
        except Exception as e:
            await self.callback.on_error(e)
            raise ScrapingError(f"Failed to scrape person comments: {e}")

    async def _get_name_and_location(self) -> tuple[str, Optional[str]]:
        """Extract name and location from profile."""
        try:
            name = await self.safe_extract_text("h1", default="Unknown")
            location = await self.safe_extract_text(
                ".text-body-small.inline.t-black--light.break-words", default=""
            )
            return name, location if location else None
        except Exception as e:
            logger.warning(f"Error getting name/location: {e}")
            return "Unknown", None

    async def _get_headline(self) -> Optional[str]:
        """Extract professional headline from profile."""
        try:
            # The headline is typically in a div with class containing 'headline'
            # or in the text-body-medium class near the top card
            headline = await self.safe_extract_text(
                ".text-body-medium.break-words", default=""
            )
            if headline:
                return headline.strip()
            
            # Fallback: try alternative selector
            headline = await self.safe_extract_text(
                ".pv-top-card--list-bullet li", default=""
            )
            return headline.strip() if headline else None
        except Exception as e:
            logger.debug(f"Error getting headline: {e}")
            return None

    async def _check_open_to_work(self) -> bool:
        """Check if profile has open to work badge."""
        try:
            # Look for open to work indicator
            img_title = await self.get_attribute_safe(
                ".pv-top-card-profile-picture img", "title", default=""
            )
            return "#OPEN_TO_WORK" in img_title.upper()
        except:
            return False

    async def _get_about(self) -> Optional[str]:
        """Extract about section."""
        try:
            # Find the profile card that contains "About"
            profile_cards = await self.page.locator(
                '[data-view-name="profile-card"]'
            ).all()

            for card in profile_cards:
                card_text = await card.inner_text()
                # Check if this card contains "About" heading
                if card_text.strip().startswith("About"):
                    # Get the span with aria-hidden to avoid duplication
                    about_spans = await card.locator('span[aria-hidden="true"]').all()
                    # Skip the first span (it's the "About" heading), get the content
                    if len(about_spans) > 1:
                        about_text = await about_spans[1].text_content()
                        return about_text.strip() if about_text else None

            return None
        except Exception as e:
            logger.debug(f"Error getting about section: {e}")
            return None

    async def _get_experiences(self, base_url: str) -> list[Experience]:
        """Extract experiences from the main profile page Experience section."""
        experiences = []

        try:
            experience_heading = self.page.locator('h2:has-text("Experience")').first
            
            if await experience_heading.count() > 0:
                experience_section = experience_heading.locator('xpath=ancestor::*[.//ul or .//ol][1]')
                if await experience_section.count() == 0:
                    experience_section = experience_heading.locator('xpath=ancestor::*[4]')
                
                if await experience_section.count() > 0:
                    items = await experience_section.locator('ul > li, ol > li').all()
                    
                    for item in items:
                        try:
                            exp = await self._parse_main_page_experience(item)
                            if exp:
                                experiences.append(exp)
                        except Exception as e:
                            logger.debug(f"Error parsing experience from main page: {e}")
                            continue
            
            if not experiences:
                exp_url = urljoin(base_url, "details/experience")
                await self.navigate_and_wait(exp_url)
                await self.page.wait_for_selector("main", timeout=10000)
                await self.wait_and_focus(1.5)
                await self.scroll_page_to_half()
                await self.scroll_page_to_bottom(pause_time=0.5, max_scrolls=5)

                items = []
                main_element = self.page.locator('main')
                if await main_element.count() > 0:
                    list_items = await main_element.locator('list > listitem, ul > li').all()
                    if list_items:
                        items = list_items
                
                if not items:
                    old_list = self.page.locator(".pvs-list__container").first
                    if await old_list.count() > 0:
                        items = await old_list.locator(".pvs-list__paged-list-item").all()

                for item in items:
                    try:
                        result = await self._parse_experience_item(item)
                        if result:
                            if isinstance(result, list):
                                experiences.extend(result)
                            else:
                                experiences.append(result)
                    except Exception as e:
                        logger.debug(f"Error parsing experience item: {e}")
                        continue

        except Exception as e:
            logger.warning(
                f"Error getting experiences: {e}. The experience section may not be available or the page structure has changed."
            )

        return experiences
    
    async def _parse_main_page_experience(self, item) -> Optional[Experience]:
        """Parse experience from main profile page list item with [logo_link, details_link] structure."""
        try:
            links = await item.locator('a').all()
            if len(links) < 2:
                return None
            
            company_url = await links[0].get_attribute('href')
            detail_link = links[1]
            
            unique_texts = await self._extract_unique_texts_from_element(detail_link)
            
            if len(unique_texts) < 2:
                return None
            
            position_title = unique_texts[0]
            company_name = unique_texts[1]
            work_times = unique_texts[2] if len(unique_texts) > 2 else ""
            
            from_date, to_date, duration = self._parse_work_times(work_times)
            
            return Experience(
                position_title=position_title,
                institution_name=company_name,
                linkedin_url=company_url,
                from_date=from_date,
                to_date=to_date,
                duration=duration,
                location=None,
                description=None,
            )
            
        except Exception as e:
            logger.debug(f"Error parsing main page experience: {e}")
            return None
    
    async def _extract_unique_texts_from_element(self, element) -> list[str]:
        """Extract unique text content from nested elements, avoiding duplicates from parent/child overlap."""
        text_elements = await element.locator('span[aria-hidden="true"], div > span').all()
        
        if not text_elements:
            text_elements = await element.locator('span, div').all()
        
        seen_texts = set()
        unique_texts = []
        
        for el in text_elements:
            text = await el.text_content()
            if text and text.strip():
                text = text.strip()
                if text not in seen_texts and len(text) < 200 and not any(text in t or t in text for t in seen_texts if len(t) > 3):
                    seen_texts.add(text)
                    unique_texts.append(text)
        
        return unique_texts

    async def _parse_experience_item(self, item):
        """Parse experience item. Returns Experience or list for nested positions."""
        try:
            links = await item.locator('a, link').all()
            if len(links) >= 2:
                company_url = await links[0].get_attribute('href')
                detail_link = links[1]
                
                generics = await detail_link.locator('generic, span, div').all()
                texts = []
                for g in generics:
                    text = await g.text_content()
                    if text and text.strip() and len(text.strip()) < 200:
                        texts.append(text.strip())
                
                unique_texts = list(dict.fromkeys(texts))
                
                if len(unique_texts) >= 2:
                    position_title = unique_texts[0]
                    company_name = unique_texts[1]
                    work_times = unique_texts[2] if len(unique_texts) > 2 else ""
                    location = unique_texts[3] if len(unique_texts) > 3 else ""
                    
                    from_date, to_date, duration = self._parse_work_times(work_times)
                    
                    return Experience(
                        position_title=position_title,
                        institution_name=company_name,
                        linkedin_url=company_url,
                        from_date=from_date,
                        to_date=to_date,
                        duration=duration,
                        location=location,
                        description=None,
                    )
            
            entity = item.locator('div[data-view-name="profile-component-entity"]').first
            if await entity.count() == 0:
                return None

            children = await entity.locator("> *").all()
            if len(children) < 2:
                return None

            company_link = children[0].locator("a").first
            company_url = await company_link.get_attribute("href")

            detail_container = children[1]
            detail_children = await detail_container.locator("> *").all()

            if len(detail_children) == 0:
                return None

            has_nested_positions = False
            if len(detail_children) > 1:
                nested_list = await detail_children[1].locator(".pvs-list__container").count()
                has_nested_positions = nested_list > 0

            if has_nested_positions:
                return await self._parse_nested_experience(item, company_url, detail_children)
            else:
                first_detail = detail_children[0]
                nested_elements = await first_detail.locator("> *").all()

                if len(nested_elements) == 0:
                    return None

                span_container = nested_elements[0]
                outer_spans = await span_container.locator("> *").all()

                position_title = ""
                company_name = ""
                work_times = ""
                location = ""

                if len(outer_spans) >= 1:
                    aria_span = outer_spans[0].locator('span[aria-hidden="true"]').first
                    position_title = await aria_span.text_content()
                if len(outer_spans) >= 2:
                    aria_span = outer_spans[1].locator('span[aria-hidden="true"]').first
                    company_name = await aria_span.text_content()
                if len(outer_spans) >= 3:
                    aria_span = outer_spans[2].locator('span[aria-hidden="true"]').first
                    work_times = await aria_span.text_content()
                if len(outer_spans) >= 4:
                    aria_span = outer_spans[3].locator('span[aria-hidden="true"]').first
                    location = await aria_span.text_content()

                from_date, to_date, duration = self._parse_work_times(work_times)

                description = ""
                if len(detail_children) > 1:
                    description = await detail_children[1].inner_text()

                return Experience(
                    position_title=position_title.strip(),
                    institution_name=company_name.strip(),
                    linkedin_url=company_url,
                    from_date=from_date,
                    to_date=to_date,
                    duration=duration,
                    location=location.strip(),
                    description=description.strip() if description else None,
                )

        except Exception as e:
            logger.debug(f"Error parsing experience: {e}")
            return None

    async def _parse_nested_experience(
        self, item, company_url: str, detail_children
    ) -> list[Experience]:
        """
        Parse nested experience positions (multiple roles at the same company).
        Returns a list of Experience objects.
        """
        experiences = []

        try:
            # Get company name from first detail
            first_detail = detail_children[0]
            nested_elements = await first_detail.locator("> *").all()
            if len(nested_elements) == 0:
                return []

            span_container = nested_elements[0]
            outer_spans = await span_container.locator("> *").all()

            # First span is company name for nested positions
            company_name = ""
            if len(outer_spans) >= 1:
                aria_span = outer_spans[0].locator('span[aria-hidden="true"]').first
                company_name = await aria_span.text_content()

            # Get the nested list from detail_children[1]
            nested_container = detail_children[1].locator(".pvs-list__container").first
            nested_items = await nested_container.locator(
                ".pvs-list__paged-list-item"
            ).all()

            for nested_item in nested_items:
                try:
                    # Each nested item has a link with position details
                    link = nested_item.locator("a").first
                    link_children = await link.locator("> *").all()

                    if len(link_children) == 0:
                        continue

                    # Navigate to get the spans
                    first_child = link_children[0]
                    nested_els = await first_child.locator("> *").all()
                    if len(nested_els) == 0:
                        continue

                    spans_container = nested_els[0]
                    position_spans = await spans_container.locator("> *").all()

                    # Extract position details
                    position_title = ""
                    work_times = ""
                    location = ""

                    if len(position_spans) >= 1:
                        aria_span = (
                            position_spans[0].locator('span[aria-hidden="true"]').first
                        )
                        position_title = await aria_span.text_content()
                    if len(position_spans) >= 2:
                        aria_span = (
                            position_spans[1].locator('span[aria-hidden="true"]').first
                        )
                        work_times = await aria_span.text_content()
                    if len(position_spans) >= 3:
                        aria_span = (
                            position_spans[2].locator('span[aria-hidden="true"]').first
                        )
                        location = await aria_span.text_content()

                    # Parse dates
                    from_date, to_date, duration = self._parse_work_times(work_times)

                    # Get description if available
                    description = ""
                    if len(link_children) > 1:
                        description = await link_children[1].inner_text()

                    experiences.append(
                        Experience(
                            position_title=position_title.strip(),
                            institution_name=company_name.strip(),
                            linkedin_url=company_url,
                            from_date=from_date,
                            to_date=to_date,
                            duration=duration,
                            location=location.strip(),
                            description=description.strip() if description else None,
                        )
                    )

                except Exception as e:
                    logger.debug(f"Error parsing nested position: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error parsing nested experience: {e}")

        return experiences

    def _parse_work_times(
        self, work_times: str
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse work times string into from_date, to_date, duration.

        Examples:
        - "2000 - Present · 26 yrs 1 mo" -> ("2000", "Present", "26 yrs 1 mo")
        - "Jan 2020 - Dec 2022 · 2 yrs" -> ("Jan 2020", "Dec 2022", "2 yrs")
        - "2015 - Present" -> ("2015", "Present", None)
        """
        if not work_times:
            return None, None, None

        try:
            # Split by · to separate date range from duration
            parts = work_times.split("·")
            times = parts[0].strip() if len(parts) > 0 else ""
            duration = parts[1].strip() if len(parts) > 1 else None

            # Parse dates - split by " - " to get from and to
            if " - " in times:
                date_parts = times.split(" - ")
                from_date = date_parts[0].strip()
                to_date = date_parts[1].strip() if len(date_parts) > 1 else ""
            else:
                from_date = times
                to_date = ""

            return from_date, to_date, duration
        except Exception as e:
            logger.debug(f"Error parsing work times '{work_times}': {e}")
            return None, None, None

    async def _get_educations(self, base_url: str) -> list[Education]:
        """Extract educations from the main profile page Education section."""
        educations = []

        try:
            education_heading = self.page.locator('h2:has-text("Education")').first
            
            if await education_heading.count() > 0:
                education_section = education_heading.locator('xpath=ancestor::*[.//ul or .//ol][1]')
                if await education_section.count() == 0:
                    education_section = education_heading.locator('xpath=ancestor::*[4]')
                
                if await education_section.count() > 0:
                    items = await education_section.locator('ul > li, ol > li').all()
                    
                    for item in items:
                        try:
                            edu = await self._parse_main_page_education(item)
                            if edu:
                                educations.append(edu)
                        except Exception as e:
                            logger.debug(f"Error parsing education from main page: {e}")
                            continue
            
            if not educations:
                edu_url = urljoin(base_url, "details/education")
                await self.navigate_and_wait(edu_url)
                await self.page.wait_for_selector("main", timeout=10000)
                await self.wait_and_focus(2)
                await self.scroll_page_to_half()
                await self.scroll_page_to_bottom(pause_time=0.5, max_scrolls=5)

                items = []
                main_element = self.page.locator('main')
                if await main_element.count() > 0:
                    list_items = await main_element.locator('ul > li, ol > li').all()
                    if list_items:
                        items = list_items
                
                if not items:
                    old_list = self.page.locator(".pvs-list__container").first
                    if await old_list.count() > 0:
                        items = await old_list.locator(".pvs-list__paged-list-item").all()

                for item in items:
                    try:
                        edu = await self._parse_education_item(item)
                        if edu:
                            educations.append(edu)
                    except Exception as e:
                        logger.debug(f"Error parsing education item: {e}")
                        continue

        except Exception as e:
            logger.warning(
                f"Error getting educations: {e}. The education section may not be publicly visible or the page structure has changed."
            )

        return educations
    
    async def _parse_main_page_education(self, item) -> Optional[Education]:
        """Parse education from main profile page list item with [logo_link, details_link] structure."""
        try:
            links = await item.locator('a').all()
            if not links:
                return None
            
            institution_url = await links[0].get_attribute('href')
            detail_link = links[1] if len(links) > 1 else links[0]
            
            unique_texts = await self._extract_unique_texts_from_element(detail_link)
            
            if not unique_texts:
                return None
            
            institution_name = unique_texts[0]
            degree = None
            times = ""
            
            if len(unique_texts) == 3:
                degree = unique_texts[1]
                times = unique_texts[2]
            elif len(unique_texts) == 2:
                second = unique_texts[1]
                if " - " in second or any(c.isdigit() for c in second):
                    times = second
                else:
                    degree = second
            
            from_date, to_date = self._parse_education_times(times)
            
            return Education(
                institution_name=institution_name,
                degree=degree.strip() if degree else None,
                linkedin_url=institution_url,
                from_date=from_date,
                to_date=to_date,
                description=None,
            )
            
        except Exception as e:
            logger.debug(f"Error parsing main page education: {e}")
            return None

    async def _parse_education_item(self, item) -> Optional[Education]:
        """Parse a single education item."""
        try:
            links = await item.locator('a, link').all()
            if len(links) >= 1:
                institution_url = await links[0].get_attribute('href')
                
                detail_link = links[1] if len(links) >= 2 else links[0]
                generics = await detail_link.locator('generic, span, div').all()
                texts = []
                for g in generics:
                    text = await g.text_content()
                    if text and text.strip() and len(text.strip()) < 200:
                        texts.append(text.strip())
                
                unique_texts = list(dict.fromkeys(texts))
                
                if unique_texts:
                    institution_name = unique_texts[0]
                    degree = None
                    times = ""
                    
                    if len(unique_texts) == 3:
                        degree = unique_texts[1]
                        times = unique_texts[2]
                    elif len(unique_texts) == 2:
                        second = unique_texts[1]
                        if " - " in second or second.isdigit() or any(c.isdigit() for c in second):
                            times = second
                        else:
                            degree = second
                    
                    from_date, to_date = self._parse_education_times(times)
                    
                    return Education(
                        institution_name=institution_name,
                        degree=degree.strip() if degree else None,
                        linkedin_url=institution_url,
                        from_date=from_date,
                        to_date=to_date,
                        description=None,
                    )
            
            entity = item.locator('div[data-view-name="profile-component-entity"]').first
            if await entity.count() == 0:
                return None

            children = await entity.locator("> *").all()
            if len(children) < 2:
                return None

            institution_link = children[0].locator("a").first
            institution_url = await institution_link.get_attribute("href")

            detail_container = children[1]
            detail_children = await detail_container.locator("> *").all()

            if len(detail_children) == 0:
                return None

            first_detail = detail_children[0]
            nested_elements = await first_detail.locator("> *").all()

            if len(nested_elements) == 0:
                return None

            span_container = nested_elements[0]
            outer_spans = await span_container.locator("> *").all()

            institution_name = ""
            degree = None
            times = ""

            if len(outer_spans) >= 1:
                aria_span = outer_spans[0].locator('span[aria-hidden="true"]').first
                institution_name = await aria_span.text_content()

            if len(outer_spans) == 3:
                aria_span = outer_spans[1].locator('span[aria-hidden="true"]').first
                degree = await aria_span.text_content()
                aria_span = outer_spans[2].locator('span[aria-hidden="true"]').first
                times = await aria_span.text_content()
            elif len(outer_spans) == 2:
                aria_span = outer_spans[1].locator('span[aria-hidden="true"]').first
                times = await aria_span.text_content()

            from_date, to_date = self._parse_education_times(times)

            description = ""
            if len(detail_children) > 1:
                description = await detail_children[1].inner_text()

            return Education(
                institution_name=institution_name.strip(),
                degree=degree.strip() if degree else None,
                linkedin_url=institution_url,
                from_date=from_date,
                to_date=to_date,
                description=description.strip() if description else None,
            )

        except Exception as e:
            logger.debug(f"Error parsing education: {e}")
            return None

    def _parse_education_times(self, times: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse education times string into from_date, to_date.

        Examples:
        - "1973 - 1977" -> ("1973", "1977")
        - "2015" -> ("2015", "2015")
        - "" -> (None, None)
        """
        if not times:
            return None, None

        try:
            # Split by " - " to get from and to dates
            if " - " in times:
                parts = times.split(" - ")
                from_date = parts[0].strip()
                to_date = parts[1].strip() if len(parts) > 1 else ""
            else:
                # Single year
                from_date = times.strip()
                to_date = times.strip()

            return from_date, to_date
        except Exception as e:
            logger.debug(f"Error parsing education times '{times}': {e}")
            return None, None

    async def _get_interests(self, base_url: str) -> list[Interest]:
        """Extract interests from the main profile page Interests section with tablist."""
        interests = []

        try:
            interests_heading = self.page.locator('h2:has-text("Interests")').first
            
            if await interests_heading.count() > 0:
                interests_section = interests_heading.locator('xpath=ancestor::*[.//tablist or .//*[@role="tablist"]][1]')
                if await interests_section.count() == 0:
                    interests_section = interests_heading.locator('xpath=ancestor::*[4]')
                
                tabs = await interests_section.locator('[role="tab"], tab').all() if await interests_section.count() > 0 else []
                
                if tabs:
                    for tab in tabs:
                        try:
                            tab_name = await tab.text_content()
                            if not tab_name:
                                continue
                            tab_name = tab_name.strip()
                            category = self._map_interest_tab_to_category(tab_name)

                            await tab.click()
                            await self.wait_and_focus(0.5)

                            tabpanel = interests_section.locator('[role="tabpanel"]').first
                            if await tabpanel.count() > 0:
                                list_items = await tabpanel.locator('li, listitem').all()
                                
                                for item in list_items:
                                    try:
                                        interest = await self._parse_interest_item(item, category)
                                        if interest:
                                            interests.append(interest)
                                    except Exception as e:
                                        logger.debug(f"Error parsing interest item: {e}")
                                        continue
                        except Exception as e:
                            logger.debug(f"Error processing interest tab: {e}")
                            continue
            
            if not interests:
                interests_url = urljoin(base_url, "details/interests/")
                await self.navigate_and_wait(interests_url)
                await self.page.wait_for_selector("main", timeout=10000)
                await self.wait_and_focus(1.5)

                tabs = await self.page.locator('[role="tab"], tab').all()

                if not tabs:
                    logger.debug("No interests tabs found on profile")
                    return interests

                for tab in tabs:
                    try:
                        tab_name = await tab.text_content()
                        if not tab_name:
                            continue
                        tab_name = tab_name.strip()
                        category = self._map_interest_tab_to_category(tab_name)

                        await tab.click()
                        await self.wait_and_focus(0.8)

                        tabpanel = self.page.locator('[role="tabpanel"], tabpanel').first
                        list_items = await tabpanel.locator("listitem, li, .pvs-list__paged-list-item").all()

                        for item in list_items:
                            try:
                                interest = await self._parse_interest_item(item, category)
                                if interest:
                                    interests.append(interest)
                            except Exception as e:
                                logger.debug(f"Error parsing interest item: {e}")
                                continue

                    except Exception as e:
                        logger.debug(f"Error processing interest tab: {e}")
                        continue

        except Exception as e:
            logger.warning(f"Error getting interests: {e}")

        return interests
    
    async def _parse_interest_item(self, item, category: str) -> Optional[Interest]:
        """Parse a single interest item from profile or details page."""
        try:
            link = item.locator("a, link").first
            if await link.count() == 0:
                return None
            href = await link.get_attribute("href")

            unique_texts = await self._extract_unique_texts_from_element(item)
            name = unique_texts[0] if unique_texts else None

            if name and href:
                return Interest(
                    name=name,
                    category=category,
                    linkedin_url=href,
                )
            return None
        except Exception as e:
            logger.debug(f"Error parsing interest: {e}")
            return None

    def _map_interest_tab_to_category(self, tab_name: str) -> str:
        tab_lower = tab_name.lower()
        if "compan" in tab_lower:
            return "company"
        elif "group" in tab_lower:
            return "group"
        elif "school" in tab_lower:
            return "school"
        elif "newsletter" in tab_lower:
            return "newsletter"
        elif "voice" in tab_lower or "influencer" in tab_lower:
            return "influencer"
        else:
            return tab_lower

    async def _get_accomplishments(self, base_url: str) -> list[Accomplishment]:
        accomplishments = []

        accomplishment_sections = [
            ("certifications", "certification"),
            ("honors", "honor"),
            ("publications", "publication"),
            ("patents", "patent"),
            ("courses", "course"),
            ("projects", "project"),
            ("languages", "language"),
            ("organizations", "organization"),
        ]

        for url_path, category in accomplishment_sections:
            try:
                section_url = urljoin(base_url, f"details/{url_path}/")
                await self.navigate_and_wait(section_url)
                await self.page.wait_for_selector("main", timeout=10000)
                await self.wait_and_focus(1)

                nothing_to_see = await self.page.locator(
                    'text="Nothing to see for now"'
                ).count()
                if nothing_to_see > 0:
                    continue

                main_list = self.page.locator(
                    ".pvs-list__container, main ul, main ol"
                ).first
                if await main_list.count() == 0:
                    continue

                items = await main_list.locator(".pvs-list__paged-list-item").all()
                if not items:
                    items = await main_list.locator("> li").all()

                seen_titles = set()
                for item in items:
                    try:
                        accomplishment = await self._parse_accomplishment_item(
                            item, category
                        )
                        if accomplishment and accomplishment.title not in seen_titles:
                            seen_titles.add(accomplishment.title)
                            accomplishments.append(accomplishment)
                    except Exception as e:
                        logger.debug(f"Error parsing {category} item: {e}")
                        continue

            except Exception as e:
                logger.debug(f"Error getting {category}s: {e}")
                continue

        return accomplishments

    async def _parse_accomplishment_item(
        self, item, category: str
    ) -> Optional[Accomplishment]:
        try:
            entity = item.locator(
                'div[data-view-name="profile-component-entity"]'
            ).first
            if await entity.count() > 0:
                spans = await entity.locator('span[aria-hidden="true"]').all()
            else:
                spans = await item.locator('span[aria-hidden="true"]').all()

            title = ""
            issuer = ""
            issued_date = ""
            credential_id = ""

            for i, span in enumerate(spans[:5]):
                text = await span.text_content()
                if not text:
                    continue
                text = text.strip()

                if len(text) > 500:
                    continue

                if i == 0:
                    title = text
                elif "Issued by" in text:
                    parts = text.split("·")
                    issuer = parts[0].replace("Issued by", "").strip()
                    if len(parts) > 1:
                        issued_date = parts[1].strip()
                elif "Issued " in text and not issued_date:
                    issued_date = text.replace("Issued ", "")
                elif "Credential ID" in text:
                    credential_id = text.replace("Credential ID ", "")
                elif i == 1 and not issuer:
                    issuer = text
                elif (
                    any(
                        month in text
                        for month in [
                            "Jan",
                            "Feb",
                            "Mar",
                            "Apr",
                            "May",
                            "Jun",
                            "Jul",
                            "Aug",
                            "Sep",
                            "Oct",
                            "Nov",
                            "Dec",
                        ]
                    )
                    and not issued_date
                ):
                    if "·" in text:
                        parts = text.split("·")
                        issued_date = parts[0].strip()
                    else:
                        issued_date = text

            link = item.locator('a[href*="credential"], a[href*="verify"]').first
            credential_url = (
                await link.get_attribute("href") if await link.count() > 0 else None
            )

            if not title or len(title) > 200:
                return None

            return Accomplishment(
                category=category,
                title=title,
                issuer=issuer if issuer else None,
                issued_date=issued_date if issued_date else None,
                credential_id=credential_id if credential_id else None,
                credential_url=credential_url,
            )

        except Exception as e:
            logger.debug(f"Error parsing accomplishment: {e}")
            return None

    async def _get_contacts(self, base_url: str) -> list[Contact]:
        """Extract contact info from the contact-info overlay dialog."""
        contacts = []

        try:
            contact_url = urljoin(base_url, "overlay/contact-info/")
            await self.navigate_and_wait(contact_url)
            await self.wait_and_focus(1)

            dialog = self.page.locator('dialog, [role="dialog"]').first
            if await dialog.count() == 0:
                logger.warning("Contact info dialog not found")
                return contacts

            contact_sections = await dialog.locator('h3').all()
            
            for section_heading in contact_sections:
                try:
                    heading_text = await section_heading.text_content()
                    if not heading_text:
                        continue
                    heading_text = heading_text.strip().lower()
                    
                    section_container = section_heading.locator('xpath=ancestor::*[1]')
                    if await section_container.count() == 0:
                        continue
                    
                    contact_type = self._map_contact_heading_to_type(heading_text)
                    if not contact_type:
                        continue
                    
                    links = await section_container.locator('a').all()
                    for link in links:
                        href = await link.get_attribute('href')
                        text = await link.text_content()
                        if href and text:
                            text = text.strip()
                            label = None
                            sibling_text = await section_container.locator('span, generic').all()
                            for sib in sibling_text:
                                sib_text = await sib.text_content()
                                if sib_text and sib_text.strip().startswith('(') and sib_text.strip().endswith(')'):
                                    label = sib_text.strip()[1:-1]
                                    break
                            
                            if contact_type == "linkedin":
                                contacts.append(Contact(type=contact_type, value=href, label=label))
                            elif contact_type == "email" and "mailto:" in href:
                                contacts.append(Contact(type=contact_type, value=href.replace("mailto:", ""), label=label))
                            else:
                                contacts.append(Contact(type=contact_type, value=text, label=label))
                    
                    if contact_type == "birthday" and not links:
                        birthday_text = await section_container.text_content()
                        if birthday_text:
                            birthday_value = birthday_text.replace(heading_text, "").replace("Birthday", "").strip()
                            if birthday_value:
                                contacts.append(Contact(type="birthday", value=birthday_value))
                    
                    if contact_type == "phone" and not links:
                        phone_text = await section_container.text_content()
                        if phone_text:
                            phone_value = phone_text.replace(heading_text, "").replace("Phone", "").strip()
                            if phone_value:
                                contacts.append(Contact(type="phone", value=phone_value))
                    
                    if contact_type == "address" and not links:
                        address_text = await section_container.text_content()
                        if address_text:
                            address_value = address_text.replace(heading_text, "").replace("Address", "").strip()
                            if address_value:
                                contacts.append(Contact(type="address", value=address_value))
                                
                except Exception as e:
                    logger.debug(f"Error parsing contact section: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error getting contacts: {e}")

        return contacts
    
    def _map_contact_heading_to_type(self, heading: str) -> Optional[str]:
        """Map contact section heading to contact type."""
        heading = heading.lower()
        if "profile" in heading:
            return "linkedin"
        elif "website" in heading:
            return "website"
        elif "email" in heading:
            return "email"
        elif "phone" in heading:
            return "phone"
        elif "twitter" in heading or "x.com" in heading:
            return "twitter"
        elif "birthday" in heading:
            return "birthday"
        elif "address" in heading:
            return "address"
        return None

    async def _get_recent_posts(self, base_url: str, limit: int = 3) -> List[PersonActivity]:
        """
        Extract the last N posts and reposts from a person's activity page.
        
        Args:
            base_url: The person's LinkedIn profile URL
            limit: Number of posts to retrieve (default 3)
            
        Returns:
            List of PersonActivity objects
        """
        posts: List[PersonActivity] = []
        
        try:
            # Ensure base_url ends with / for proper URL joining
            if not base_url.endswith('/'):
                base_url = base_url + '/'
            
            # Navigate to the recent activity/posts page
            activity_url = urljoin(base_url, "recent-activity/all/")
            logger.info(f"Navigating to posts activity page: {activity_url}")
            await self.navigate_and_wait(activity_url)
            logger.info(f"Successfully navigated to: {self.page.url}")
            
            # Try to wait for main, but continue if it times out
            try:
                logger.debug("Waiting for main selector...")
                await self.page.wait_for_selector("main", timeout=5000)
                logger.debug("Main selector found")
            except Exception as e:
                logger.warning(f"Main selector timeout, continuing anyway: {e}")
            
            await self.wait_and_focus(2)
            logger.debug("Completed wait and focus")
            logger.debug("Completed wait and focus")
            
            # Scroll to load content
            logger.debug("Starting to scroll page...")
            await self.scroll_page_to_half()
            await self.scroll_page_to_bottom(pause_time=0.5, max_scrolls=3)
            logger.debug("Completed scrolling")
            
            # Extract posts using JavaScript
            logger.info(f"Extracting posts data via JavaScript (limit: {limit})...")
            posts_data = await self.page.evaluate('''(limit) => {
                const posts = [];
                const html = document.body.innerHTML;
                
                // Find all activity URNs in the page
                const urnMatches = html.matchAll(/urn:li:activity:(\\d+)/g);
                const seenUrns = new Set();
                
                for (const match of urnMatches) {
                    if (posts.length >= limit) break;
                    
                    const urn = match[0];
                    if (seenUrns.has(urn)) continue;
                    seenUrns.add(urn);
                    
                    // Find the element with this URN
                    const el = document.querySelector(`[data-urn="${urn}"]`);
                    if (!el) continue;
                    
                    // Check if it's a repost
                    const headerText = el.querySelector('.update-components-header, .feed-shared-update-v2__description-wrapper')?.innerText || '';
                    const isRepost = headerText.toLowerCase().includes('reposted') || 
                                     headerText.toLowerCase().includes('shared');
                    
                    // Get original author if repost
                    let originalAuthor = null;
                    if (isRepost) {
                        const actorEl = el.querySelector('.update-components-actor__name, .feed-shared-actor__name');
                        if (actorEl) {
                            originalAuthor = actorEl.innerText?.trim() || null;
                        }
                    }
                    
                    // Get text content
                    let text = '';
                    const textSelectors = [
                        '.feed-shared-update-v2__description',
                        '.update-components-text',
                        '.feed-shared-text',
                        '.break-words.whitespace-pre-wrap'
                    ];
                    
                    for (const sel of textSelectors) {
                        const textEl = el.querySelector(sel);
                        if (textEl) {
                            const t = textEl.innerText?.trim() || '';
                            if (t.length > text.length && t.length > 10) {
                                text = t;
                            }
                        }
                    }
                    
                    // Get time
                    const timeEl = el.querySelector('[class*="actor__sub-description"], [class*="update-components-actor__sub-description"]');
                    const timeText = timeEl ? timeEl.innerText : '';
                    
                    // Get reactions
                    const reactionsEl = el.querySelector('button[aria-label*="reaction"], [class*="social-details-social-counts__reactions"]');
                    const reactions = reactionsEl ? reactionsEl.innerText : '';
                    
                    // Get comments
                    const commentsEl = el.querySelector('button[aria-label*="comment"]');
                    const comments = commentsEl ? commentsEl.innerText : '';
                    
                    // Get reposts count
                    const repostsEl = el.querySelector('button[aria-label*="repost"]');
                    const reposts = repostsEl ? repostsEl.innerText : '';
                    
                    // Get images
                    const images = [];
                    el.querySelectorAll('img[src*="media"]').forEach(img => {
                        if (img.src && !img.src.includes('profile') && !img.src.includes('logo')) {
                            images.push(img.src);
                        }
                    });
                    
                    posts.push({
                        urn: urn,
                        text: text.substring(0, 2000),
                        timeText: timeText,
                        isRepost: isRepost,
                        originalAuthor: originalAuthor,
                        reactions: reactions,
                        comments: comments,
                        reposts: reposts,
                        images: images
                    });
                }
                
                return posts;
            }''', limit)
            
            logger.info(f"JavaScript returned {len(posts_data)} posts")
            
            for idx, data in enumerate(posts_data):
                logger.debug(f"Processing post {idx + 1}/{len(posts_data)}: URN={data.get('urn')}")
                activity_id = data['urn'].replace('urn:li:activity:', '')
                post = PersonActivity(
                    linkedin_url=f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/",
                    urn=data['urn'],
                    text=data['text'],
                    posted_date=self._extract_time_from_text(data.get('timeText', '')),
                    is_repost=data.get('isRepost', False),
                    original_author=data.get('originalAuthor'),
                    reactions_count=self._parse_count(data.get('reactions', '')),
                    comments_count=self._parse_count(data.get('comments', '')),
                    reposts_count=self._parse_count(data.get('reposts', '')),
                    image_urls=data.get('images', [])
                )
                posts.append(post)
                logger.debug(f"Post {idx + 1} parsed: {post.text[:50] if post.text else 'No text'}...")
            
            logger.info(f"Successfully extracted {len(posts)} posts")
            
        except Exception as e:
            logger.error(f"Error getting recent posts: {e}", exc_info=True)
        
        return posts[:limit]

    async def _get_recent_comments(self, base_url: str, limit: int = 3) -> List[PersonComment]:
        """
        Extract the last N comments made by a person.
        
        Args:
            base_url: The person's LinkedIn profile URL
            limit: Number of comments to retrieve (default 3)
            
        Returns:
            List of PersonComment objects
        """
        comments: List[PersonComment] = []
        
        try:
            # Ensure base_url ends with / for proper URL joining
            if not base_url.endswith('/'):
                base_url = base_url + '/'
            
            # Navigate to the comments activity page
            comments_url = urljoin(base_url, "recent-activity/comments/")
            logger.info(f"Navigating to comments activity page: {comments_url}")
            await self.navigate_and_wait(comments_url)
            logger.info(f"Successfully navigated to: {self.page.url}")
            
            # Try to wait for main, but continue if it times out
            try:
                logger.debug("Waiting for main selector...")
                await self.page.wait_for_selector("main", timeout=5000)
                logger.debug("Main selector found")
            except Exception as e:
                logger.warning(f"Main selector timeout, continuing anyway: {e}")
            
            await self.wait_and_focus(2)
            logger.debug("Completed wait and focus")
            
            # Scroll to load content
            logger.debug("Starting to scroll page...")
            await self.scroll_page_to_half()
            await self.scroll_page_to_bottom(pause_time=0.5, max_scrolls=3)
            logger.debug("Completed scrolling")
            
            # Debug: Check page content
            page_text = await self.page.content()
            logger.debug(f"Page content length: {len(page_text)} characters")
            
            # First, let's see what's on the page
            logger.info("Analyzing page structure...")
            all_text = await self.page.evaluate('''() => {
                return document.body.innerText.substring(0, 500);
            }''')
            logger.debug(f"Page text preview: {all_text}")
            
            # Extract comments using JavaScript with extensive logging
            logger.info(f"Extracting comments data via JavaScript (limit: {limit})...")
            comments_data = await self.page.evaluate('''(limit) => {
                const comments = [];
                const debugLog = [];
                
                debugLog.push('Starting comment extraction...');
                
                // Strategy 1: Look for feed items that indicate commenting activity
                const feedItems = document.querySelectorAll('[data-urn], .feed-shared-update-v2, .profile-creator-shared-feed-update__container');
                debugLog.push(`Found ${feedItems.length} potential feed items`);
                
                for (let i = 0; i < feedItems.length && comments.length < limit; i++) {
                    const el = feedItems[i];
                    
                    // Check if this is a comment activity
                    const activityText = el.innerText || '';
                    const hasCommentIndicator = activityText.toLowerCase().includes('commented') ||
                                               activityText.toLowerCase().includes('comment on this');
                    
                    if (!hasCommentIndicator) {
                        continue;
                    }
                    
                    debugLog.push(`Item ${i}: Found comment indicator`);
                    
                    const urn = el.getAttribute('data-urn') || '';
                    
                    // Try to find the actual comment text
                    let commentText = '';
                    let commentedDate = '';
                    let postAuthor = '';
                    let postTextPreview = '';
                    
                    // Look for comment text in various possible locations
                    const commentSelectors = [
                        '.comments-comment-item__main-content',
                        '.comments-comment-item-content-body',
                        '.comment-text',
                        '[class*="comment"][class*="content"]',
                        '.feed-shared-text',
                        '.update-components-text'
                    ];
                    
                    for (const selector of commentSelectors) {
                        const commentEl = el.querySelector(selector);
                        if (commentEl) {
                            const text = commentEl.innerText?.trim();
                            if (text && text.length > 10) {
                                commentText = text;
                                debugLog.push(`Found comment text with ${selector}: ${text.substring(0, 50)}...`);
                                break;
                            }
                        }
                    }
                    
                    // If still no comment text, try to extract from the main text
                    if (!commentText) {
                        // Sometimes the comment is in the description area
                        const descEl = el.querySelector('.feed-shared-update-v2__description, .feed-shared-text');
                        if (descEl) {
                            commentText = descEl.innerText?.trim() || '';
                            debugLog.push(`Extracted from description: ${commentText.substring(0, 50)}...`);
                        }
                    }
                    
                    // Get timestamp
                    const timeEl = el.querySelector('time, [class*="time"], [class*="timestamp"]');
                    if (timeEl) {
                        commentedDate = timeEl.innerText?.trim() || timeEl.getAttribute('datetime') || '';
                    }
                    
                    // Get post author
                    const authorEl = el.querySelector('.update-components-actor__name, .feed-shared-actor__name, [class*="actor"][class*="name"]');
                    if (authorEl) {
                        postAuthor = authorEl.innerText?.trim() || '';
                    }
                    
                    // Get full post text (not just preview)
                    // Look for the main post content, excluding comment text and author info
                    let postText = '';
                    
                    // Strategy 1: Look for feed-shared-update-v2__description (main post content)
                    const postContentEl = el.querySelector('.feed-shared-update-v2__description, .feed-shared-inline-show-more-text');
                    if (postContentEl) {
                        const text = postContentEl.innerText?.trim();
                        if (text && text.length > 20 && text !== commentText && text !== postAuthor) {
                            postText = text;
                            postTextPreview = text.substring(0, 150);
                            debugLog.push(`Found post text via description: ${text.substring(0, 50)}...`);
                        }
                    }
                    
                    // Strategy 2: If not found, look for update-components-text that's not the comment
                    if (!postText) {
                        const textEls = el.querySelectorAll('.update-components-text, .feed-shared-text');
                        for (const textEl of textEls) {
                            const text = textEl.innerText?.trim();
                            // Make sure it's not the comment, not the author, and has substantial content
                            if (text && text.length > 30 && 
                                text !== commentText && 
                                text !== postAuthor &&
                                !text.includes('commented on this')) {
                                postText = text;
                                postTextPreview = text.substring(0, 150);
                                debugLog.push(`Found post text via text elements: ${text.substring(0, 50)}...`);
                                break;
                            }
                        }
                    }
                    
                    if (commentText && commentText.length > 5) {
                        debugLog.push(`Adding comment: ${commentText.substring(0, 30)}...`);
                        comments.push({
                            postUrn: urn,
                            commentText: commentText.substring(0, 1000),
                            commentedDate: commentedDate,
                            postAuthor: postAuthor,
                            postText: postText,
                            postTextPreview: postTextPreview
                        });
                    } else {
                        debugLog.push(`Skipped - no valid comment text found`);
                    }
                }
                
                debugLog.push(`Total comments found: ${comments.length}`);
                
                return { comments: comments, debug: debugLog };
            }''', limit)
            
            # Log debug info from JavaScript
            if 'debug' in comments_data:
                for log_line in comments_data['debug']:
                    logger.debug(f"[JS] {log_line}")
            
            actual_comments = comments_data.get('comments', [])
            logger.info(f"JavaScript returned {len(actual_comments)} comments")
            
            for idx, data in enumerate(actual_comments):
                logger.debug(f"Processing comment {idx + 1}/{len(actual_comments)}: URN={data.get('postUrn')}")
                post_urn = data.get('postUrn', '')
                activity_id = post_urn.replace('urn:li:activity:', '') if post_urn else ''
                
                comment = PersonComment(
                    linkedin_url=f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}/" if activity_id else None,
                    post_urn=post_urn if post_urn else None,
                    comment_text=data.get('commentText'),
                    commented_date=data.get('commentedDate'),
                    post_author=data.get('postAuthor'),
                    post_text=data.get('postText'),
                    post_text_preview=data.get('postTextPreview')
                )
                comments.append(comment)
                logger.debug(f"Comment {idx + 1} parsed: {comment.comment_text[:50] if comment.comment_text else 'No text'}...")
            
            logger.info(f"Successfully extracted {len(comments)} comments")
            
        except Exception as e:
            logger.error(f"Error getting recent comments: {e}", exc_info=True)
        
        return comments[:limit]

    def _extract_time_from_text(self, text: str) -> Optional[str]:
        """Extract time/date from text."""
        if not text:
            return None
        match = re.search(r'(\d+[hdwmy]|\d+\s*(?:hour|day|week|month|year)s?\s*ago)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        parts = text.split('•')
        if parts:
            return parts[0].strip()
        return None

    def _parse_count(self, text: str) -> Optional[int]:
        """Parse count from text like '123 reactions'."""
        if not text:
            return None
        try:
            numbers = re.findall(r'[\d,]+', text.replace(',', ''))
            if numbers:
                return int(numbers[0])
        except:
            pass
        return None

    @staticmethod
    def generate_markdown_profile(person, current_company=None) -> str:
        """
        Generate a markdown document with LinkedIn profile details for AI analysis.
        
        Args:
            person: Person object with profile data
            current_company: Optional Company object with current company details
                           (if None, will try to use person.current_company)
            
        Returns:
            Markdown formatted string
        """
        # Use company from person object if not provided
        if current_company is None:
            current_company = getattr(person, 'current_company', None)
        
        md = []
        md.append("# LinkedIn Profile Analysis\n")
        
        # 1. LinkedIn Profile URL
        md.append("## 1. LinkedIn Profile URL")
        md.append(f"{person.linkedin_url}\n")
        
        # 2. Name
        md.append("## 2. Name")
        md.append(f"{person.name}\n")
        
        # 3. Headline
        md.append("## 3. Headline")
        md.append(f"{person.headline if person.headline else 'Not specified'}\n")
        
        # 4. Location
        md.append("## 4. Location")
        md.append(f"{person.location if person.location else 'Not specified'}\n")
        
        # 5. About
        md.append("## 5. About")
        if person.about:
            md.append(f"{person.about}\n")
        else:
            md.append("Not provided\n")
        
        # 6. Current Company Details
        md.append("## 6. Current Company Details")
        if person.experiences and len(person.experiences) > 0:
            current_exp = person.experiences[0]
            md.append(f"**Company Name:** {current_exp.institution_name}")
            if current_exp.linkedin_url:
                md.append(f"**Company LinkedIn:** {current_exp.linkedin_url}")
            
            # Add company description if available
            if current_company:
                md.append(f"\n**What the company does:**")
                if current_company.about_us:
                    md.append(f"{current_company.about_us}")
                else:
                    md.append("Company description not available")
                if current_company.website:
                    md.append(f"\n**Website:** {current_company.website}")
                if current_company.industry:
                    md.append(f"**Industry:** {current_company.industry}")
                if current_company.company_size:
                    md.append(f"**Company Size:** {current_company.company_size}")
                if current_company.headquarters:
                    md.append(f"**Headquarters:** {current_company.headquarters}")
                if current_company.founded:
                    md.append(f"**Founded:** {current_company.founded}")
            
            # Add company recent posts if available
            if current_company and hasattr(current_company, 'recent_posts') and current_company.recent_posts:
                md.append(f"\n**Recent Company Posts/Activity:**")
                for i, post in enumerate(current_company.recent_posts[:3], 1):
                    md.append(f"\n*Post {i}:*")
                    if post.posted_date:
                        md.append(f"- Posted: {post.posted_date}")
                    if post.text:
                        preview = post.text[:200] + "..." if len(post.text) > 200 else post.text
                        md.append(f"- Content: {preview}")
                    if post.linkedin_url:
                        md.append(f"- Link: {post.linkedin_url}")
                    if post.reactions_count or post.comments_count:
                        engagement = []
                        if post.reactions_count:
                            engagement.append(f"{post.reactions_count} reactions")
                        if post.comments_count:
                            engagement.append(f"{post.comments_count} comments")
                        md.append(f"- Engagement: {', '.join(engagement)}")
            md.append("")
        else:
            md.append("No current company information available\n")
        
        # 7. Current Designation and Work Description
        md.append("## 7. Current Designation and Work Description")
        if person.experiences and len(person.experiences) > 0:
            current_exp = person.experiences[0]
            md.append(f"**Position:** {current_exp.position_title}")
            if current_exp.from_date or current_exp.to_date:
                date_str = f"{current_exp.from_date or ''} - {current_exp.to_date or 'Present'}"
                if current_exp.duration:
                    date_str += f" ({current_exp.duration})"
                md.append(f"**Duration:** {date_str}")
            if current_exp.location:
                md.append(f"**Location:** {current_exp.location}")
            if current_exp.description:
                md.append(f"\n**Work Description:**")
                md.append(f"{current_exp.description}")
            md.append("")
        else:
            md.append("No current position information available\n")
        
        # 8. Last 3 Posts/Reposts
        md.append("## 8. Last 3 Posts/Reposts")
        if person.recent_posts and len(person.recent_posts) > 0:
            for i, post in enumerate(person.recent_posts, 1):
                post_type = "Repost" if post.is_repost else "Post"
                md.append(f"\n### {post_type} {i}")
                if post.posted_date:
                    md.append(f"**Posted:** {post.posted_date}")
                if post.is_repost and post.original_author:
                    md.append(f"**Original Author:** {post.original_author}")
                if post.linkedin_url:
                    md.append(f"**Link:** {post.linkedin_url}")
                md.append(f"\n**Content:**")
                md.append(f"{post.text if post.text else 'No text content'}")
                if post.reactions_count or post.comments_count or post.reposts_count:
                    engagement = []
                    if post.reactions_count:
                        engagement.append(f"👍 {post.reactions_count} reactions")
                    if post.comments_count:
                        engagement.append(f"💬 {post.comments_count} comments")
                    if post.reposts_count:
                        engagement.append(f"🔄 {post.reposts_count} reposts")
                    md.append(f"\n**Engagement:** {' | '.join(engagement)}")
                md.append("")
        else:
            md.append("No recent posts available\n")
        
        # 9. Last 3 Comments
        md.append("## 9. Last 3 Comments Made")
        if person.recent_comments and len(person.recent_comments) > 0:
            for i, comment in enumerate(person.recent_comments, 1):
                md.append(f"\n### Comment {i}")
                if comment.commented_date:
                    md.append(f"**Commented on:** {comment.commented_date}")
                if comment.post_author:
                    md.append(f"**Post by:** {comment.post_author}")
                if comment.linkedin_url:
                    md.append(f"**Link:** {comment.linkedin_url}")
                
                md.append(f"\n**Comment Text:**")
                md.append(f"{comment.comment_text if comment.comment_text else 'No comment text'}")
                
                if comment.post_text:
                    md.append(f"\n**Original Post:**")
                    md.append(f"{comment.post_text}")
                elif comment.post_text_preview:
                    md.append(f"\n**Original Post (preview):**")
                    md.append(f"{comment.post_text_preview}")
                md.append("")
        else:
            md.append("No recent comments available\n")
        
        # Footer
        md.append("---")
        md.append("*This profile summary was generated for AI analysis purposes.*")
        
        return "\n".join(md)
