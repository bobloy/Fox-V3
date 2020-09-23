import asyncio
import base64
import logging
import pickle
from datetime import datetime
from typing import Tuple, Union

from apscheduler.job import Job
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import run_in_event_loop
from apscheduler.util import datetime_to_utc_timestamp
from redbot.core import Config

# TODO: use get_lock on config
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter

log = logging.getLogger("red.fox_v3.fifo.jobstore")
log.setLevel(logging.DEBUG)

save_task_objects = []


class RedConfigJobStore(MemoryJobStore):
    def __init__(self, config: Config, bot: Red):
        super().__init__()
        self.config = config
        self.bot = bot
        self.pickle_protocol = pickle.HIGHEST_PROTOCOL
        self._eventloop = self.bot.loop
        # TODO: self.config.jobs_index is never used,
        #  fine but maybe a sign of inefficient use of config

        # task = asyncio.create_task(self.load_from_config())
        # while not task.done():
        #     sleep(0.1)
        # future = asyncio.ensure_future(self.load_from_config(), loop=self.bot.loop)

    @run_in_event_loop
    def start(self, scheduler, alias):
        super().start(scheduler, alias)

    async def load_from_config(self, scheduler, alias):
        super().start(scheduler, alias)
        _jobs = await self.config.jobs()
        self._jobs = [
            (await self._decode_job(job), timestamp) async for (job, timestamp) in AsyncIter(_jobs)
        ]
        # self._jobs_index = await self.config.jobs_index.all()  # Overwritten by next
        self._jobs_index = {job.id: (job, timestamp) for job, timestamp in self._jobs}

    def _encode_job(self, job: Job):
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
        # log.debug(f"Encoding job id: {job.id}\n"
        #           f"Encoded as: {out}")

        return out

    async def _decode_job(self, in_job):
        if in_job is None:
            return None
        job_state = in_job["job_state"]
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

        # log.debug(f"Decoded job id: {job.id}\n"
        #           f"Decoded as {job_state}")

        return job

    @run_in_event_loop
    def add_job(self, job: Job):
        if job.id in self._jobs_index:
            raise ConflictingIdError(job.id)
        # log.debug(f"Check job args: {job.args=}")
        timestamp = datetime_to_utc_timestamp(job.next_run_time)
        index = self._get_job_index(timestamp, job.id)  # This is fine
        self._jobs.insert(index, (job, timestamp))
        self._jobs_index[job.id] = (job, timestamp)
        asyncio.create_task(self._async_add_job(job, index, timestamp))
        # log.debug(f"Added job: {self._jobs[index][0].args}")

    async def _async_add_job(self, job, index, timestamp):
        encoded_job = self._encode_job(job)
        job_tuple = tuple([encoded_job, timestamp])
        async with self.config.jobs() as jobs:
            jobs.insert(index, job_tuple)
        # await self.config.jobs_index.set_raw(job.id, value=job_tuple)
        return True

    @run_in_event_loop
    def update_job(self, job):
        old_tuple: Tuple[Union[Job, None], Union[datetime, None]] = self._jobs_index.get(
            job.id, (None, None)
        )
        old_job = old_tuple[0]
        old_timestamp = old_tuple[1]
        if old_job is None:
            raise JobLookupError(job.id)

        # If the next run time has not changed, simply replace the job in its present index.
        # Otherwise, reinsert the job to the list to preserve the ordering.
        old_index = self._get_job_index(old_timestamp, old_job.id)
        new_timestamp = datetime_to_utc_timestamp(job.next_run_time)
        asyncio.create_task(
            self._async_update_job(job, new_timestamp, old_index, old_job, old_timestamp)
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
        # await self.config.jobs_index.set_raw(old_job.id, value=(encoded_job, new_timestamp))

        log.debug(f"Async Updated {job.id=}")
        log.debug(f"Check job args: {job.args=}")

    @run_in_event_loop
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
        # await self.config.jobs_index.clear_raw(job.id)

    @run_in_event_loop
    def remove_all_jobs(self):
        super().remove_all_jobs()
        asyncio.create_task(self._async_remove_all_jobs())

    async def _async_remove_all_jobs(self):
        await self.config.jobs.clear()
        # await self.config.jobs_index.clear()

    def shutdown(self):
        """Removes all jobs without clearing config"""
        super().remove_all_jobs()
