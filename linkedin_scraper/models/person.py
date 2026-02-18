"""Pydantic models for LinkedIn Person/Profile data."""

from typing import List, Optional, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Interest(BaseModel):
    name: str
    category: str
    linkedin_url: Optional[str] = None


class Contact(BaseModel):
    type: str
    value: str
    label: Optional[str] = None


class Experience(BaseModel):
    """Work experience model."""

    position_title: Optional[str] = None
    institution_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None


class Education(BaseModel):
    """Education model."""

    institution_name: Optional[str] = None
    degree: Optional[str] = None
    linkedin_url: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    description: Optional[str] = None


class Accomplishment(BaseModel):
    category: str
    title: str
    issuer: Optional[str] = None
    issued_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    description: Optional[str] = None


class PersonActivity(BaseModel):
    """Model for a person's post or repost."""

    linkedin_url: Optional[str] = None
    urn: Optional[str] = None
    text: Optional[str] = None
    posted_date: Optional[str] = None
    is_repost: bool = False
    original_author: Optional[str] = None
    reactions_count: Optional[int] = None
    comments_count: Optional[int] = None
    reposts_count: Optional[int] = None
    image_urls: List[str] = Field(default_factory=list)


class PersonComment(BaseModel):
    """Model for a comment made by a person."""

    linkedin_url: Optional[str] = None
    post_urn: Optional[str] = None
    comment_text: Optional[str] = None
    commented_date: Optional[str] = None
    post_author: Optional[str] = None
    post_text: Optional[str] = None
    post_text_preview: Optional[str] = None


class Person(BaseModel):
    """
    LinkedIn Person/Profile model with validation.

    Represents a complete LinkedIn profile with all scraped data.
    """

    linkedin_url: str
    name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    about: Optional[str] = None
    open_to_work: bool = False
    experiences: List[Experience] = Field(default_factory=list)
    educations: List[Education] = Field(default_factory=list)
    interests: List[Interest] = Field(default_factory=list)
    accomplishments: List[Accomplishment] = Field(default_factory=list)
    contacts: List[Contact] = Field(default_factory=list)
    recent_posts: List["PersonActivity"] = Field(default_factory=list)
    recent_comments: List["PersonComment"] = Field(default_factory=list)
    current_company: Optional[Any] = None  # Stores Company object for AI analysis

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: str) -> str:
        """Validate that URL is a LinkedIn profile URL."""
        if "linkedin.com/in/" not in v:
            raise ValueError("Must be a valid LinkedIn profile URL (contains /in/)")
        return v

    def to_dict(self) -> dict:
        """
        Convert to dictionary.

        Returns:
            Dictionary representation of the person
        """
        return self.model_dump()

    def to_json(self, **kwargs) -> str:
        """
        Convert to JSON string.

        Args:
            **kwargs: Additional arguments for model_dump_json (e.g., indent=2)

        Returns:
            JSON string representation
        """
        return self.model_dump_json(**kwargs)

    @property
    def company(self) -> Optional[str]:
        """
        Get the most recent company.

        Returns:
            Company name from most recent experience or None
        """
        if self.experiences:
            return self.experiences[0].institution_name
        return None

    @property
    def job_title(self) -> Optional[str]:
        """
        Get the most recent job title.

        Returns:
            Job title from most recent experience or None
        """
        if self.experiences:
            return self.experiences[0].position_title
        return None

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Person {self.name}\n"
            f"  Company: {self.company}\n"
            f"  Title: {self.job_title}\n"
            f"  Location: {self.location}\n"
            f"  Experiences: {len(self.experiences)}\n"
            f"  Education: {len(self.educations)}\n"
            f"  Recent Posts: {len(self.recent_posts)}\n"
            f"  Recent Comments: {len(self.recent_comments)}>"
        )
