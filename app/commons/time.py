import time

from datetime import datetime, timedelta, timezone


def now() -> int:
    return time.time_ns()


def get_posix_time_until_day() -> int:
    # Define the Colombian time zone offset (UTC-5)
    colombia_tz = timezone(timedelta(hours=-5))

    # Get the current time in the Colombian time zone
    current_time = datetime(hour=21,year=2025,month=7,day=2)

    # Create a new datetime with hours, minutes, and seconds set to zero
    day_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert the datetime back to a POSIX timestamp
    return int(day_time.timestamp())

if __name__ == "__main__":
    print(get_posix_time_until_day())