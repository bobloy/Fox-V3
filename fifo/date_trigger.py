from apscheduler.triggers.date import DateTrigger


class CustomDateTrigger(DateTrigger):
    def get_next_fire_time(self, previous_fire_time, now):
        next_run = super().get_next_fire_time(previous_fire_time, now)
        return next_run if next_run >= now else None
