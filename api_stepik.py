import os

import requests
from collections import defaultdict
from dotenv import load_dotenv

####### ENVIRONMENTS
load_dotenv()

# Course ID
COURSE_ID = os.getenv("COURSE_ID")

# Stepik API credentials
STEPIK_CLIENT_ID = os.getenv("STEPIK_CLIENT_ID")
STEPIK_CLIENT_SECRET = os.getenv("STEPIK_CLIENT_SECRET")

# Authenticate with Stepik API
def authenticate_stepik(client_id, client_secret):
    auth_url = "https://stepik.org/oauth2/token/"
    auth_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    }
    response = requests.post(auth_url, data=auth_data)
    response.raise_for_status()
    return response.json().get('access_token')

def get_headers():
    # Access token для Stepik API
    access_token = authenticate_stepik(STEPIK_CLIENT_ID, STEPIK_CLIENT_SECRET)

    headers = {"Authorization": f"Bearer {access_token}"}
    
    return headers

def get_units(course_id):
    """Получает все юниты курса."""
    url = f"https://stepik.org/api/units?course={course_id}"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json().get("units", [])


def group_units_by_section(units):
    """Группирует юниты по секциям."""
    sections = defaultdict(list)
    for unit in units:
        sections[unit["section"]].append(unit)
    return sections


def get_steps_for_lesson(lesson_id):
    """Получает список шагов для урока."""
    url = f"https://stepik.org/api/lessons/{lesson_id}"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()["lessons"][0]["steps"]


def get_attempt(attempt_id):
    """Получает информацию о попытке."""
    url = f"https://stepik.org/api/attempts/{attempt_id}"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    attempts = response.json().get("attempts", [])
    return attempts[0] if attempts else None


def get_user_from_submission(submission):
    """Извлекает user_id из submission."""
    attempt_id = submission.get("attempt")
    if not attempt_id:
        raise ValueError("Submission не содержит attempt ID.")

    attempt = get_attempt(attempt_id)
    if not attempt or "user" not in attempt:
        raise ValueError(f"Attempt {attempt_id} не содержит информации о пользователе.")

    return attempt["user"]


def get_successful_submissions_with_users(step_id):
    """Получает успешные решения с информацией о пользователях."""
    url = f"https://stepik.org/api/submissions?step={step_id}"
    successful_submissions = []
    page = 1

    while True:
        response = requests.get(f"{url}&page={page}", headers=get_headers())
        response.raise_for_status()
        data = response.json()

        for submission in data["submissions"]:
            if submission["status"] == "correct":
                try:
                    user_id = get_user_from_submission(submission)
                    successful_submissions.append({
                        "user": user_id,
                        "submission_id": submission["id"],
                        "time": submission["time"]
                    })
                except ValueError:
                    pass  # Игнорируем ошибки с попытками без пользователей

        if not data["meta"]["has_next"]:
            break
        page += 1

    return successful_submissions


def get_solutions_by_code(course_id, code):
    """Обрабатывает код и получает успешные решения."""
    try:
        section_number, lesson_position, step_position = map(int, code.split('.'))
    except ValueError:
        raise ValueError(f"Неверный формат кода: {code}. Ожидаемый формат: секция.урок.шаг")

    # Получаем и группируем юниты
    units = get_units(course_id)
    grouped_units = group_units_by_section(units)

    sections = list(grouped_units.keys())
    if section_number > len(sections):
        raise ValueError(f"Секция {section_number} не существует. Запрашиваемый код: {code}")

    target_section_id = sections[section_number - 1]

    # Ищем урок по позиции
    lesson_id = next(
        (unit["lesson"] for unit in grouped_units[target_section_id] if unit["position"] == lesson_position),
        None
    )
    if not lesson_id:
        raise ValueError(f"Урок {lesson_position} не найден в секции {section_number}. Запрашиваемый код: {code}")

    # Получаем шаги урока
    steps = get_steps_for_lesson(lesson_id)
    if step_position > len(steps):
        raise ValueError(f"Шаг {step_position} отсутствует в уроке {lesson_id}. Запрашиваемый код: {code}")

    step_id = steps[step_position - 1]

    # Получаем успешные решения
    return get_successful_submissions_with_users(step_id)


def get_successful_users_by_task(code_id):
    """Получает список пользователей, решивших задание."""

    successful_submissions = get_solutions_by_code(COURSE_ID, code_id)
    return [item["user"] for item in successful_submissions]
