import asyncio

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.util import datetime_to_utc_timestamp
from redbot.core import Config


# TODO: use get_lock on config
from redbot.core.bot import Red



class RedConfigJobStore(MemoryJobStore):
    def __init__(self, config: Config, bot: Red):
        super().__init__()
        self.config = config
        # nest_asyncio.apply()
        self.bot = bot
        asyncio.ensure_future(self._load_from_config(), loop=self.bot.loop)

    async def _load_from_config(self):
        self._jobs = await self.config.jobs()
        self._jobs_index = await self.config.jobs_index.all()

    def add_job(self, job):
        if job.id in self._jobs_index:
            raise ConflictingIdError(job.id)

        timestamp = datetime_to_utc_timestamp(job.next_run_time)
        index = self._get_job_index(timestamp, job.id)  # This is fine
        self._jobs.insert(index, (job, timestamp))
        self._jobs_index[job.id] = (job, timestamp)
        asyncio.create_task(self._async_add_job(job, index, timestamp))

    async def _async_add_job(self, job, index, timestamp):
        async with self.config.jobs() as jobs:
            jobs.insert(index, (job, timestamp))
        await self.config.jobs_index.set_raw(job.id, value=(job, timestamp))
        return True

    def update_job(self, job):
        old_job, old_timestamp = self._jobs_index.get(job.id, (None, None))
        if old_job is None:
            raise JobLookupError(job.id)

        # If the next run time has not changed, simply replace the job in its present index.
        # Otherwise, reinsert the job to the list to preserve the ordering.
        old_index = self._get_job_index(old_timestamp, old_job.id)
        new_timestamp = datetime_to_utc_timestamp(job.next_run_time)
        asyncio.ensure_future(self._async_update_job(job, new_timestamp, old_index, old_job, old_timestamp), loop=self.bot.loop)

    async def _async_update_job(self, job, new_timestamp, old_index, old_job, old_timestamp):
        if old_timestamp == new_timestamp:
            self._jobs[old_index] = (job, new_timestamp)
            async with self.config.jobs() as jobs:
                jobs[old_index] = (job, new_timestamp)
        else:
            del self._jobs[old_index]
            new_index = self._get_job_index(new_timestamp, job.id)  # This is fine
            self._jobs.insert(new_index, (job, new_timestamp))
            async with self.config.jobs() as jobs:
                del jobs[old_index]
                jobs.insert(new_index, (job, new_timestamp))
        self._jobs_index[old_job.id] = (job, new_timestamp)
        await self.config.jobs_index.set_raw(old_job.id, value=(job, new_timestamp))

    def remove_job(self, job_id):
        job, timestamp = self._jobs_index.get(job_id, (None, None))
        if job is None:
            raise JobLookupError(job_id)

        index = self._get_job_index(timestamp, job_id)
        del self._jobs[index]
        del self._jobs_index[job.id]
        asyncio.create_task(self._async_remove_job(index, job))

    async def _async_remove_job(self, index, job):
        async with self.config.jobs() as jobs:
            del jobs[index]
        await self.config.jobs_index.clear_raw(job.id)

    def remove_all_jobs(self):
        super().remove_all_jobs()
        asyncio.create_task(self._async_remove_all_jobs())

    async def _async_remove_all_jobs(self):
        await self.config.jobs.clear()
        await self.config.jobs_index.clear()


# import asyncio
#
# from apscheduler.jobstores.base import BaseJobStore, ConflictingIdError
# from apscheduler.util import datetime_to_utc_timestamp
# from redbot.core import Config
# from redbot.core.utils import AsyncIter
#
#
# class RedConfigJobStore(BaseJobStore):
#     def __init__(self, config: Config, loop):
#         super().__init__()
#         self.config = config
#         self.loop: asyncio.BaseEventLoop = loop
#
#         self._jobs = []
#         self._jobs_index = {}  # id -> (job, timestamp) lookup table
#
#     def lookup_job(self, job_id):
#         return asyncio.run(self._async_lookup_job(job_id))
#
#     async def _async_lookup_job(self, job_id):
#         return (await self.config.jobs_index.get_raw(job_id, default=(None, None)))[0]
#
#     def get_due_jobs(self, now):
#         return asyncio.run(self._async_get_due_jobs(now))
#
#     async def _async_get_due_jobs(self, now):
#         now_timestamp = datetime_to_utc_timestamp(now)
#         pending = []
#         all_jobs = await self.config.jobs()
#         async for job, timestamp in AsyncIter(all_jobs, steps=100):
#             if timestamp is None or timestamp > now_timestamp:
#                 break
#             pending.append(job)
#
#         return pending
#
#     def get_next_run_time(self):
#         return asyncio.run(self._async_get_next_run_time())
#
#     async def _async_get_next_run_time(self):
#         _jobs = await self.config.jobs()
#         return _jobs[0][0].next_run_time if _jobs else None
#
#     def get_all_jobs(self):
#         return asyncio.run(self._async_get_all_jobs())
#
#     async def _async_get_all_jobs(self):
#         return [j[0] for j in (await self.config.jobs())]
#
#     def add_job(self, job):
#         return asyncio.run(self._async_add_job(job))
#
#     async def _async_add_job(self, job):
#         if await self.config.jobs_index.get_raw(job.id, default=None) is not None:
#             raise ConflictingIdError(job.id)
#
#         timestamp = datetime_to_utc_timestamp(job.next_run_time)
#         index = self._get_job_index(timestamp, job.id)
#         self._jobs.insert(index, (job, timestamp))
#         self._jobs_index[job.id] = (job, timestamp)
#
#     def update_job(self, job):
#         pass
#
#     def remove_job(self, job_id):
#         pass
#
#     def remove_all_jobs(self):
#         pass
#
#     def _get_job_index(self, timestamp, job_id):
#         """
#         Returns the index of the given job, or if it's not found, the index where the job should be
#         inserted based on the given timestamp.
#
#         :type timestamp: int
#         :type job_id: str
#
#         """
#         lo, hi = 0, len(self._jobs)
#         timestamp = float('inf') if timestamp is None else timestamp
#         while lo < hi:
#             mid = (lo + hi) // 2
#             mid_job, mid_timestamp = self._jobs[mid]
#             mid_timestamp = float('inf') if mid_timestamp is None else mid_timestamp
#             if mid_timestamp > timestamp:
#                 hi = mid
#             elif mid_timestamp < timestamp:
#                 lo = mid + 1
#             elif mid_job.id > job_id:
#                 hi = mid
#             elif mid_job.id < job_id:
#                 lo = mid + 1
#             else:
#                 return mid
#
#         return lo
