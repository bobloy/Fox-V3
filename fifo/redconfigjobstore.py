import asyncio
import base64
import logging
import pickle

from apscheduler.job import Job
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.util import datetime_to_utc_timestamp
from redbot.core import Config

# TODO: use get_lock on config
from redbot.core.bot import Red

log = logging.getLogger("red.fox_v3.fifo.jobstore")
log.setLevel(logging.DEBUG)

save_task_objects = []


class RedConfigJobStore(MemoryJobStore):
    def __init__(self, config: Config, bot: Red):
        super().__init__()
        self.config = config
        self.bot = bot
        self.pickle_protocol = pickle.HIGHEST_PROTOCOL
        asyncio.ensure_future(self._load_from_config(), loop=self.bot.loop)

    async def _load_from_config(self):
        self._jobs = await self.config.jobs()
        self._jobs = [
            (await self._decode_job(job["job_state"]), timestamp)
            for (job, timestamp) in self._jobs
        ]
        self._jobs_index = await self.config.jobs_index.all()
        self._jobs_index = {job.id: (job, timestamp) for job, timestamp in self._jobs}

    def _encode_job(self, job: Job):
        log.info(f"Encoding job id: {job.id}")
        job_state = job.__getstate__()
        new_args = list(job_state["args"])
        new_args[0]["config"] = None
        new_args[0]["bot"] = None
        job_state["args"] = tuple(new_args)
        encoded = base64.b64encode(pickle.dumps(job_state, self.pickle_protocol))
        out = {
            "_id": job.id,
            "next_run_time": datetime_to_utc_timestamp(job.next_run_time),
            "job_state": encoded.decode("ascii"),
        }
        new_args = list(job_state["args"])
        new_args[0]["config"] = self.config
        new_args[0]["bot"] = self.bot
        job_state["args"] = tuple(new_args)
        log.info(f"After encode: Check job args: {job.args=}")
        return out

    async def _decode_job(self, job_state):
        job_state = pickle.loads(base64.b64decode(job_state))
        new_args = list(job_state["args"])
        new_args[0]["config"] = self.config
        new_args[0]["bot"] = self.bot
        job_state["args"] = tuple(new_args)
        job = Job.__new__(Job)
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        # task_name, guild_id = _disassemble_job_id(job.id)
        # task = Task(task_name, guild_id, self.config)
        # await task.load_from_config()
        # save_task_objects.append(task)
        #
        # job.func = task.execute

        log.info(f"Decoded job id: {job.id}")

        return job

    def add_job(self, job: Job):
        if job.id in self._jobs_index:
            raise ConflictingIdError(job.id)
        log.info(f"Check job args: {job.args=}")
        timestamp = datetime_to_utc_timestamp(job.next_run_time)
        index = self._get_job_index(timestamp, job.id)  # This is fine
        self._jobs.insert(index, (job, timestamp))
        self._jobs_index[job.id] = (job, timestamp)
        asyncio.create_task(self._async_add_job(job, index, timestamp))
        log.info(f"Added job: {self._jobs[index][0].args}")

    async def _async_add_job(self, job, index, timestamp):
        async with self.config.jobs() as jobs:
            jobs.insert(index, (self._encode_job(job), timestamp))
        await self.config.jobs_index.set_raw(job.id, value=(self._encode_job(job), timestamp))
        return True

    def update_job(self, job):
        old_job, old_timestamp = self._jobs_index.get(job.id, (None, None))
        if old_job is None:
            raise JobLookupError(job.id)

        # If the next run time has not changed, simply replace the job in its present index.
        # Otherwise, reinsert the job to the list to preserve the ordering.
        old_index = self._get_job_index(old_timestamp, old_job.id)
        new_timestamp = datetime_to_utc_timestamp(job.next_run_time)
        asyncio.ensure_future(
            self._async_update_job(job, new_timestamp, old_index, old_job, old_timestamp),
            loop=self.bot.loop,
        )

    async def _async_update_job(self, job, new_timestamp, old_index, old_job, old_timestamp):
        encoded_job = self._encode_job(job)
        if old_timestamp == new_timestamp:
            self._jobs[old_index] = (job, new_timestamp)
            async with self.config.jobs() as jobs:
                jobs[old_index] = (encoded_job, new_timestamp)
        else:
            del self._jobs[old_index]
            new_index = self._get_job_index(new_timestamp, job.id)  # This is fine
            self._jobs.insert(new_index, (job, new_timestamp))
            async with self.config.jobs() as jobs:
                del jobs[old_index]
                jobs.insert(new_index, (encoded_job, new_timestamp))
        self._jobs_index[old_job.id] = (job, new_timestamp)
        await self.config.jobs_index.set_raw(old_job.id, value=(encoded_job, new_timestamp))

        log.info(f"Async Updated {job.id=}")
        log.info(f"Check job args: {job.args=}")

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
