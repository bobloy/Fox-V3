from apscheduler.triggers.date import DateTrigger


class CustomDateTrigger(DateTrigger):
    def get_next_fire_time(self, previous_fire_time, now):
        next_run = super().get_next_fire_time(previous_fire_time, now)
        return next_run if next_run is not None and next_run >= now else None

    def __getstate__(self):
        return {"version": 1, "run_date": self.run_date}
