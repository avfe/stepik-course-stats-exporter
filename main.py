import asyncio
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from api_google_sheets import update_all_tasks, get_worksheet

load_dotenv()


async def update_google_sheet():
    await update_all_tasks(get_worksheet())

async def job():
    x1 = time.time()
    await update_google_sheet()
    x2 = time.time()
    print(f"{x2 - x1:.2f} sec - Google Sheet was updated!")

async def main():
    print("Stepik to Google Sheets Exporter was started!")
    await job()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job, "interval", minutes=5)  # Запускаем раз в 5 минут
    scheduler.start()

    while True:
        await asyncio.sleep(1)  # Поддерживаем асинхронный цикл активным

if __name__ == "__main__":
    asyncio.run(main())  # Запускаем асинхронный главный цикл