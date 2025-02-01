import schedule
import time

from dotenv import load_dotenv

from api_google_sheets import update_all_tasks, get_worksheet

load_dotenv()

def update_google_sheet():
    update_all_tasks(get_worksheet())

def job():
    update_google_sheet()
    print('Google Sheet was updated!')

schedule.every(1).minutes.do(job)  # Запускаем раз в минуту

if __name__ == "__main__":
    print("Stepik to Google Sheets Exporter was started!")
    job()
    while True:
        schedule.run_pending()
        time.sleep(1)  # Ждём секунду перед следующей проверкой