import pandas as pd

from job_watcher.model import JobPost


class JobPostPipeline:
    def open_spider(self, spider):
        self.items = []

    def process_item(self, item: JobPost, spider):
        # self.logger.info(item)
        self.items.append(item)
        return item

    def close_spider(self, spider):
        spider.logger.info(f"Total items: {len(self.items)}")
        df = pd.DataFrame([item.dict() for item in self.items])
        df.to_csv("job_posts.csv", index=True)
