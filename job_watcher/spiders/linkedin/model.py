from enum import Enum

from pydantic import BaseModel, computed_field


class JobType(Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    INTERNSHIP = "INTERNSHIP"
    CONTRACT = "CONTRACT"
    TEMPORARY = "TEMPORARY"


class LinkedinParams(BaseModel):
    search_term: str | None = None
    location: str | None = None
    distance: int | None = None
    is_remote: bool = False
    job_type: JobType | None = None
    easy_apply: bool | None = None
    offset: int = 0
    linkedin_fetch_description: bool = False
    linkedin_company_ids: list[int] | None = None
    # description_format: DescriptionFormat | None = DescriptionFormat.MARKDOWN

    results_wanted: int = 15
    hours_old: int | None = None

    @computed_field
    @property
    def job_type_code(self) -> str | None:
        return {
            JobType.FULL_TIME: "F",
            JobType.PART_TIME: "P",
            JobType.INTERNSHIP: "I",
            JobType.CONTRACT: "C",
            JobType.TEMPORARY: "T",
        }.get(self.job_type, None)

    @computed_field
    @property
    def seconds_old(self) -> int | None:
        if self.hours_old is not None:
            return self.hours_old * 3600
        return None

    @computed_field
    @property
    def remote_code(self) -> int | None:
        return 2 if self.is_remote else None

    @computed_field
    @property
    def easy_apply_code(self) -> str | None:
        return "true" if self.easy_apply else None

    @computed_field
    @property
    def starting_point(self) -> int:
        return self.offset // 10 * 10 if self.offset else 0
