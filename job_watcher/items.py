import datetime as dt

from pydantic import BaseModel

from job_watcher.model import Compensation, JobType, Location, Site


class JobPost(BaseModel):
    class Config:
        validate_assignment = True

    id: str | None = None
    title: str
    site: Site
    job_url: str
    company_name: str | None = None
    job_url_direct: str | None = None
    location: Location | None = None

    description: str | None = None
    company_url: str | None = None
    company_url_direct: str | None = None

    job_type: list[JobType] | None = None
    compensation: Compensation | None = None
    date_posted: dt.date | None = None
    emails: list[str] | None = None
    is_remote: bool | None = None
    listing_type: str | None = None

    # LinkedIn specific
    job_level: str | None = None
    job_function: str | None = None

    # LinkedIn and Indeed specific
    company_industry: str | None = None

    # Indeed specific
    company_addresses: str | None = None
    company_num_employees: str | None = None
    company_revenue: str | None = None
    company_description: str | None = None
    company_logo: str | None = None
    banner_photo_url: str | None = None

    # Naukri specific
    skills: list[str] | None = None  # from tagsAndSkills
    experience_range: str | None = None  # from experienceText
    company_rating: float | None = None  # from ambitionBoxData.AggregateRating
    company_reviews_count: int | None = None  # from ambitionBoxData.ReviewsCount
    vacancy_count: int | None = None  # from vacancy
    work_from_home_type: str | None = (
        None  # from clusters.wfhType (e.g., "Hybrid", "Remote")
    )
