import asyncio
import base64
import logging
import pickle

from apscheduler.job import Job
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.asyncio import run_in_event_loop
from apscheduler.util import datetime_to_utc_timestamp
from redbot.core import Config

# TODO: use get_lock on config maybe
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
        self._eventloop = self.bot.loop  # Used for @run_in_event_loop

    @run_in_event_loop
    def start(self, scheduler, alias):
        super().start(scheduler, alias)
        for job, timestamp in self._jobs:
            job._scheduler = self._scheduler
            job._jobstore_alias = self._alias

    async def load_from_config(self):
        _jobs = await self.config.jobs()
        # self._jobs = [
        #     (await self._decode_job(job), timestamp) async for (job, timestamp) in AsyncIter(_jobs)
        # ]
        async for job, timestamp in AsyncIter(_jobs, steps=5):
            job = await self._decode_job(job)
            index = self._get_job_index(timestamp, job.id)
            self._jobs.insert(index, (job, timestamp))
            self._jobs_index[job.id] = (job, timestamp)

    async def save_to_config(self):
        """Yea that's basically it"""
        await self.config.jobs.set(
            [(self._encode_job(job), timestamp) for job, timestamp in self._jobs]
        )

        # self._jobs_index = await self.config.jobs_index.all()  # Overwritten by next
        # self._jobs_index = {job.id: (job, timestamp) for job, timestamp in self._jobs}

    def _encode_job(self, job: Job):
        job_state = job.__getstate__()
        job_state["kwargs"]["config"] = None
        job_state["kwargs"]["bot"] = None
        # new_kwargs = job_state["kwargs"]
        # new_kwargs["config"] = None
        # new_kwargs["bot"] = None
        # job_state["kwargs"] = new_kwargs
        encoded = base64.b64encode(pickle.dumps(job_state, self.pickle_protocol))
        out = {
            "_id": job.id,
            "next_run_time": datetime_to_utc_timestamp(job.next_run_time),
            "job_state": encoded.decode("ascii"),
        }
        job_state["kwargs"]["config"] = self.config
        job_state["kwargs"]["bot"] = self.bot
        # new_kwargs = job_state["kwargs"]
        # new_kwargs["config"] = self.config
        # new_kwargs["bot"] = self.bot
        # job_state["kwargs"] = new_kwargs
        # log.debug(f"Encoding job id: {job.id}\n"
        #           f"Encoded as: {out}")

        return out

    async def _decode_job(self, in_job):
        if in_job is None:
            return None
        job_state = in_job["job_state"]
        job_state = pickle.loads(base64.b64decode(job_state))
        if job_state["args"]:  # Backwards compatibility on args to kwargs
            job_state["kwargs"] = {**job_state["args"][0]}
            job_state["args"] = []
        job_state["kwargs"]["config"] = self.config
        job_state["kwargs"]["bot"] = self.bot
        # new_kwargs = job_state["kwargs"]
        # new_kwargs["config"] = self.config
        # new_kwargs["bot"] = self.bot
        # job_state["kwargs"] = new_kwargs
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
    def remove_all_jobs(self):
        super().remove_all_jobs()
        asyncio.create_task(self._async_remove_all_jobs())

    async def _async_remove_all_jobs(self):
        await self.config.jobs.clear()
        # await self.config.jobs_index.clear()

    def shutdown(self):
        """Removes all jobs without clearing config"""
        asyncio.create_task(self.async_shutdown())

    async def async_shutdown(self):
        await self.save_to_config()
        self._jobs = []
        self._jobs_index = {}
