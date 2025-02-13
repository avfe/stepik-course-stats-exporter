import asyncio

import aiohttp
import os

from dotenv import load_dotenv

load_dotenv()

####### ENVIRONMENTS
COURSE_ID = os.getenv("COURSE_ID")
STEPIK_CLIENT_ID = os.getenv("STEPIK_CLIENT_ID")
STEPIK_CLIENT_SECRET = os.getenv("STEPIK_CLIENT_SECRET")

ACCESS_TOKEN = None


async def authenticate_stepik(client_id: str, client_secret: str, session: aiohttp.ClientSession) -> str:
    """Асинхронная аутентификация в Stepik и получение access_token."""
    global ACCESS_TOKEN
    auth_url = "https://stepik.org/oauth2/token/"
    auth_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    }
    async with session.post(auth_url, data=auth_data) as response:
        response.raise_for_status()
        data = await response.json()
        ACCESS_TOKEN = data.get('access_token')
    return ACCESS_TOKEN


async def get_headers(session: aiohttp.ClientSession) -> dict:
    """Возвращает заголовки с токеном для аутентифицированных запросов к Stepik API."""
    global ACCESS_TOKEN
    if not ACCESS_TOKEN:
        await authenticate_stepik(STEPIK_CLIENT_ID, STEPIK_CLIENT_SECRET, session)
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


async def get_steps(session, lesson_id):
    headers = await get_headers(session)
    url = f'https://stepik.org/api/steps?lesson={lesson_id}'
    async with session.get(url, headers=headers) as resp:
        data = await resp.json()
        return [step['id'] for step in data['steps']]


async def fetch_units(session, course_id, page):
    headers = await get_headers(session)
    url = f'https://stepik.org/api/units?course={course_id}&page={page}'
    async with session.get(url, headers=headers) as resp:
        return await resp.json()


async def scan_course():
    unis = []  # Итоговый трехмерный массив
    section_map = {}  # Сопоставление section_id с индексом в массиве
    page = 1

    async with aiohttp.ClientSession() as session:
        while True:
            print(f"Fetching page {page}")
            data = await fetch_units(session, COURSE_ID, page)

            if 'units' not in data:
                break

            tasks = []
            for unit in data['units']:
                section_id = unit['section']
                lesson_id = unit['lesson']

                if section_id not in section_map:
                    section_map[section_id] = len(unis)
                    unis.append([])
                section_index = section_map[section_id]

                tasks.append(get_steps(session, lesson_id))

            lessons_steps = await asyncio.gather(*tasks)

            for i, unit in enumerate(data['units']):
                section_id = unit['section']
                section_index = section_map[section_id]
                unis[section_index].append(lessons_steps[i])

            if not data.get("meta", {}).get("has_next"):
                break
            page += 1

    return unis

async def get_attempt(attempt_id: int, session: aiohttp.ClientSession, headers: dict):
    """Получает информацию о попытке."""
    url = f"https://stepik.org/api/attempts/{attempt_id}"
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        data = await response.json()
        attempts = data.get("attempts", [])
        return attempts[0] if attempts else None

async def get_user_from_submission(submission: dict, session: aiohttp.ClientSession, headers: dict) -> int:
    """Извлекает user_id из submission, дополнительно запрашивая информацию об attempt."""
    attempt_id = submission.get("attempt")
    if not attempt_id:
        raise ValueError("Submission не содержит attempt ID.")

    attempt = await get_attempt(attempt_id, session, headers)
    if not attempt or "user" not in attempt:
        raise ValueError(f"Attempt {attempt_id} не содержит информации о пользователе.")

    return attempt["user"]

async def _process_submission(submission: dict, session: aiohttp.ClientSession, headers: dict) -> dict:
    """
    Вспомогательная функция для get_successful_submissions_with_users,
    чтобы аккуратно вытащить user_id и вернуть итоговый словарь.
    """
    try:
        user_id = await get_user_from_submission(submission, session, headers)
        return {
            "user": user_id,
            "submission_id": submission["id"],
            "time": submission["time"]
        }
    except ValueError:
        # Если не удалось получить user_id из-за отсутствующих данных
        return {}

async def get_successful_submissions_with_users(step_id: int, session: aiohttp.ClientSession, headers: dict) -> list:
    """
    Получает успешные (correct) решения с информацией о пользователях.
    Возвращает список словарей {"user": ..., "submission_id": ..., "time": ...}.
    """
    url = f"https://stepik.org/api/submissions?step={step_id}"
    page = 1
    usrs = set()
    while True:
        page_url = f"{url}&page={page}"
        async with session.get(page_url, headers=headers) as response:
            response.raise_for_status()
            data = await response.json()
        atms = set()
        for i in data['submissions']:
            atms.add(i['attempt'])
        base_url = "https://stepik.org/api/attempts"

        query_string = "&".join([f"ids[]={id_}" for id_ in atms])
        full_url = f"{base_url}?{query_string}"
        async with session.get(full_url, headers=headers) as response:
           response.raise_for_status()
           d = await response.json()


        for i in d['attempts']:
            usrs.add(i['user'])

        if not data["meta"]["has_next"]:
            break
        page += 1

    return usrs

async def get_solutions_by_code(code, all_structured_units):
    try:
        section_number, lesson_position, step_position = map(int, code.split('.'))
    except ValueError:
        raise ValueError(f"Неверный формат кода: {code}. Ожидаемый формат: секция.урок.шаг")

    step_id = all_structured_units[section_number - 1][lesson_position - 1][step_position - 1]
    async with aiohttp.ClientSession() as session:
        headers = await get_headers(session)
        s = await get_successful_submissions_with_users(step_id, session, headers)
    return s

async def get_successful_users_by_task(code_id: str, all_structured_units) -> list:
    """
    Получает список user_id пользователей, успешно решивших задание
    по коду формата "секция.урок.шаг".
    """
    async with aiohttp.ClientSession() as session:
        headers = await get_headers(session)
        successful_submissions = await get_solutions_by_code(code_id, all_structured_units)
    # Возвращаем только user_id
    return successful_submissions