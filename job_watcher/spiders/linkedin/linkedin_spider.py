import datetime as dt
import re
from urllib.parse import unquote, urlparse, urlunparse

from scrapy import Spider
from scrapy.http.response import Response
from scrapy_spider_metadata import Args

from job_watcher.custom import WrappedRequest
from job_watcher.items import JobPost
from job_watcher.model import Compensation, Country, Location, Site
from job_watcher.spiders.linkedin.model import LinkedinParams
from job_watcher.spiders.utils import (
    currency_parser,
    extract_emails_from_text,
    get_enum_from_job_type,
    get_full_text,
    markdown_converter,
)


class LinkedinSpider(Args[LinkedinParams], Spider):
    name = "linkedin_spider"
    base_url = "https://www.linkedin.com"
    init_search_endpoint = "/jobs-guest/jobs/search"
    more_search_endpoint = "/jobs-guest/jobs/api/seeMoreJobPostings/search"
    job_detail_endpoint = "/jobs/view"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_req_params = self.gen_base_request_params()
        self.seen_ids = set()
        self.start_param = self.args.starting_point
        self.job_url_direct_regex = re.compile(r'(?<=\?url=)[^"]+')

    def gen_base_request_params(self):
        params = {
            "keywords": self.args.search_term,
            "location": self.args.location,
            "distance": self.args.distance,
            "f_WT": self.args.remote_code,
            "f_JT": self.args.job_type_code,
            "pageNum": 0,
            "f_AL": self.args.easy_apply_code,
            "f_C": (
                ",".join(map(str, self.args.linkedin_company_ids))
                if self.args.linkedin_company_ids
                else None
            ),
            "f_TPR": self.args.seconds_old,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return params

    async def start(self):
        params = {**self.base_req_params, "start": self.start_param}
        yield WrappedRequest(
            url=f"{self.base_url}{self.init_search_endpoint}",
            method="GET",
            params=params,
            callback=self.parse_job_posts,
        )

    def parse_job_posts(self, response: Response):
        job_cards = response.css("div.base-search-card")
        if not job_cards:
            return

        for job_card in job_cards:
            href = job_card.css("a.base-card__full-link::attr(href)").get()
            job_id = href.split("?")[0].rsplit("-", 1)[-1]
            if job_id in self.seen_ids:
                continue

            self.logger.info(f"Found job: {job_id}")

            # -- Compensation
            salary_text = get_full_text(
                job_card.css("span.job-search-card__salary-info"), seperator=" "
            )
            compensation = None
            if salary_text:
                # e.g. "$70,000 - $90,000" → ["$70,000", " $90,000"]
                parts = [currency_parser(p) for p in salary_text.split("-")]
                if len(parts) >= 2:
                    salary_min = parts[0]
                    salary_max = parts[1]
                    currency = salary_text[0] if salary_text[0] != "$" else "USD"
                    compensation = Compensation(
                        min_amount=int(salary_min),
                        max_amount=int(salary_max),
                        currency=currency,
                    )

            # --- Title ---
            title = get_full_text(job_card.css("span.sr-only"), default="N/A")

            # --- Company & URL ---
            company_sel = job_card.css("h4.base-search-card__subtitle a")
            company_name = get_full_text(company_sel, default="N/A")
            company_href = company_sel.attrib.get("href", "")
            if company_href:
                # strip query params
                u = urlparse(company_href)
                company_url = urlunparse(u._replace(query=""))
            else:
                company_url = ""

            metadata_card = job_card.css("div.base-search-card__metadata")

            # --- Location ---
            loc_text = (
                metadata_card.css("span.job-search-card__location::text")
                .get(default="N/A")
                .strip()
            )
            # parse city/state/country
            parts = [p.strip() for p in loc_text.split(",")]
            if len(parts) == 3:
                city, state, country_str = parts
                country = Country.from_string(country_str)
                location = Location(city=city, state=state, country=country)
            elif len(parts) == 2:
                city, state = parts
                location = Location(
                    city=city, state=state, country=Country.from_string("worldwide")
                )
            else:
                location = Location(country=Country.from_string("worldwide"))

            # --- Date Posted ---
            datetime_str = metadata_card.css("time::attr(datetime)").get()
            date_posted = None
            if datetime_str:
                try:
                    date_posted = dt.datetime.strptime(datetime_str, "%Y-%m-%d")
                except ValueError:
                    self.logger.debug(f"Failed to parse date: {datetime_str}")

            # --- Optional Full Description & Details ---
            detail_job_url = f"{self.base_url}{self.job_detail_endpoint}/{job_id}"
            job_post = JobPost(
                id=f"li-{job_id}",
                title=title,
                site=Site.LINKEDIN,
                company_name=company_name,
                company_url=company_url,
                location=location,
                date_posted=date_posted,
                job_url=detail_job_url,
                compensation=compensation,
            )
            if not self.args.linkedin_fetch_description:
                yield job_post
                continue

            yield WrappedRequest(
                url=detail_job_url,
                method="GET",
                callback=self.parse_job_detail,
                cb_kwargs={"job_post": job_post},
            )
            self.seen_ids.add(job_id)

        if len(self.seen_ids) >= self.args.results_wanted:
            self.logger.info("Reached max results, stopping.")
            return

        self.start_param += 25
        yield WrappedRequest(
            url=f"{self.base_url}{self.more_search_endpoint}",
            method="GET",
            params={**self.base_req_params, "start": self.start_param},
            callback=self.parse_job_posts,
        )

    def parse_job_detail(self, response: Response, job_post: JobPost):
        if "linkedin.com/signup" in response.url:
            yield job_post
            return

        # --- Description ---
        description = markdown_converter(
            response.css('div[class*="show-more-less-html__markup"]').get()
        )

        # --- job function: find <h3> containing "Job function", then next <span> ---
        job_function = response.xpath(
            '//h3[contains(normalize-space(.),"Job function")]'
            '/following-sibling::span[contains(@class,"description__job-criteria-text")][1]/text()'
        ).get()
        if job_function:
            job_function = job_function.strip()

        # --- company logo URL from <img class="artdeco-entity-image" data-delayed-url=...> ---
        company_logo = response.css(
            "img.artdeco-entity-image::attr(data-delayed-url)"
        ).get()

        # 1. Seniority level → job_level
        job_level = response.xpath(
            "//h3[contains(@class,'description__job-criteria-subheader')"
            " and contains(normalize-space(.),'Seniority level')]"
            "/following-sibling::span"
            "[contains(@class,'description__job-criteria-text')][1]/text()"
        ).get()  # find the <h3> containing "Seniority level", then next <span>
        if job_level:
            job_level = job_level.strip()

        # 2. Industries → industry
        industry = response.xpath(
            "//h3[contains(@class,'description__job-criteria-subheader')"
            " and contains(normalize-space(.),'Industries')]"
            "/following-sibling::span"
            "[contains(@class,'description__job-criteria-text')][1]/text()"
        ).get()  # find the <h3> containing "Industries", then next <span>
        if industry:
            industry = industry.strip()

        # 3. Employment type → employment_type
        employment_type = response.xpath(
            "//h3[contains(@class,'description__job-criteria-subheader')"
            " and contains(normalize-space(.),'Employment type')]"
            "/following-sibling::span"
            "[contains(@class,'description__job-criteria-text')][1]/text()"
        ).get()  # find the <h3> containing "Employment type", then next <span>

        if employment_type:
            employment_type = employment_type.strip().lower().replace("-", "")
            job_type_enum = [get_enum_from_job_type(employment_type)]
        else:
            job_type_enum = []

        # 4. Direct apply URL → job_url_direct
        raw = response.css("code#applyUrl").get()
        job_url_direct = None
        if raw:
            m = self.job_url_direct_regex.search(raw)
            if m:
                job_url_direct = unquote(m.group())

        # 5. Emails → emails
        emails = extract_emails_from_text(description)

        # 6. Is remote
        remote_keywords = ["remote", "work from home", "wfh"]
        location = job_post.location.display_location()
        full_string = f"{job_post.title} {description} {location}".lower()
        is_remote = any(keyword in full_string for keyword in remote_keywords)

        job_post.description = description
        job_post.job_function = job_function
        job_post.job_level = job_level
        job_post.company_industry = industry
        job_post.job_type = job_type_enum
        job_post.company_logo = company_logo
        job_post.job_url_direct = job_url_direct
        job_post.emails = emails
        job_post.is_remote = is_remote
        yield job_post
