import asyncio

from apscheduler.jobstores.base import BaseJobStore
from redbot.core import Config


class RedConfigJobStore(BaseJobStore):
    def __init__(self, config: Config, loop):
        super().__init__()
        self.config = config
        self.loop: asyncio.BaseEventLoop = loop

    def lookup_job(self, job_id):
        task = self.loop.create_task(self.config.jobs_index.get_raw(job_id))

    def get_due_jobs(self, now):
        pass

    def get_next_run_time(self):
        pass

    def get_all_jobs(self):
        pass

    def add_job(self, job):
        pass

    def update_job(self, job):
        pass

    def remove_job(self, job_id):
        pass

    def remove_all_jobs(self):
        pass
