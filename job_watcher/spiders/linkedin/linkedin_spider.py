from scrapy import Spider
from scrapy_spider_metadata import Args

from job_watcher.custom import WrappedRequest
from job_watcher.spiders.linkedin.model import LinkedinParams


class LinkedinSpider(Args[LinkedinParams], Spider):
    name = "linkedin_spider"
    base_url = "https://www.linkedin.com"
    init_search_enpoint = "/jobs-guest/jobs/search"
    more_search_enpoint = "/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_req_params = self.gen_base_request_params()

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
        params = {**self.base_req_params, "start": self.args.starting_point}
        yield WrappedRequest(
            url=f"{self.base_url}{self.init_search_enpoint}",
            method="GET",
            params=params,
            callback=self.parse,
        )

    def parse(self, response):
        with open("response.html", "+w") as f:
            f.write(response.text)
