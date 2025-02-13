import os

from dotenv import load_dotenv
from gspread import Cell, Worksheet, Client, service_account

from api_stepik_async import scan_course, get_successful_users_by_task

####### ENVIRONMENTS
load_dotenv()
GOOGLE_TABLE_LINK = os.getenv("GOOGLE_TABLE_LINK")
GOOGLE_TABLE_ID = os.getenv("GOOGLE_TABLE_ID")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

def client_init_json() -> Client:
    """Создание клиента для работы с Google Sheets."""
    return service_account(filename='credentials.json')

def get_table_by_id(client: Client, table_url):
    """Получение таблицы из Google Sheets по ID таблицы."""
    return client.open_by_key(table_url)

def get_worksheet():
    client = client_init_json()
    table = get_table_by_id(client, GOOGLE_TABLE_ID)
    worksheet = table.worksheet(GOOGLE_SHEET_NAME)
    return worksheet

async def update_all_tasks(worksheet: Worksheet):
    """Обрабатывает все задания и отмечает успешные решения в таблице."""

    structured_units = await scan_course()

    # Получаем список кодов заданий (из 5-й строки)
    codes_row = worksheet.row_values(5)

    # Получаем список Stepik ID студентов (из 2-го столбца, начиная с 6-й строки)
    user_ids = worksheet.col_values(2)[5:]

    # Массив для массового обновления ячеек
    result_list = []

    # Проходим по каждому коду задания
    for task_col in range(2, len(codes_row)):
        code = codes_row[task_col]
        print(code)

        # Получаем список успешных пользователей по этому коду
        successful_user_ids = await get_successful_users_by_task(code, structured_units)

        # Проходим по каждому студенту
        for user_row, user_id in enumerate(user_ids, start=5):
            # Проверяем, решал ли студент задание
            value = 1 if int(user_id) in successful_user_ids else 0

            # Добавляем изменение в список
            result_list.append(Cell(user_row + 1, task_col + 1, value))

    # Массовое обновление ячеек
    worksheet.update_cells(result_list)
