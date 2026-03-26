from datetime import datetime


class TimeChecker:
    @staticmethod
    def is_active(schedule) -> bool:
        now = datetime.now()
        if now.isoweekday() not in schedule.enabled_days:
            return False
        return TimeChecker._check(now.strftime("%H:%M:%S"), schedule.start_time, schedule.end_time)

    @staticmethod
    def _check(current: str, start: str, end: str) -> bool:
        return start <= current <= end
