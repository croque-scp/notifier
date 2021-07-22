from apscheduler.schedulers.blocking import BlockingScheduler

HOURLY = "0 * * * *"
DAILY = "0 0 * * *"
WEEKLY = "0 0 * * 0"
MONTHLY = "0 0 1 * *"

if __name__ == "__main__":
    scheduler = BlockingScheduler()
