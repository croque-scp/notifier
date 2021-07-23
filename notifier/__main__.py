from apscheduler.schedulers.blocking import BlockingScheduler
from notifier.tasks import Hourly, Daily, Weekly, Monthly


def add_job(scheduler, Task):
    task = Task()
    return scheduler.add_job(task.execute, task.trigger)


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    hourly_job = add_job(scheduler, Hourly)
    daily_job = add_job(scheduler, Daily)
    weekly_job = add_job(scheduler, Weekly)
    monthly_job = add_job(scheduler, Monthly)
