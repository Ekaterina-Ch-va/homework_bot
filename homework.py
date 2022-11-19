import logging
import os
import sys
import time
import requests
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s'
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Бот отправляет сообщение."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != 200:
        raise ConnectionError('Ошибка подключения!')
    response = homework_statuses.json()
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response['homeworks'], list):
        raise TypeError('Получен НЕ верный тип данных')
    if not response.get('homeworks'):
        raise IndexError('Список домашних работ пуст или нет изменений')
    homework = response.get('homeworks')[0]
    return homework


def parse_status(homework):
    """Извлекает из информации статус работы."""
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            raise KeyError('Статус домашней работы не определен!')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError('Статус домашней работы не определен!')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID is not None:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    old_message = ''
    if check_tokens() is False:
        logger.critical(
            'Отсутствие обязательных переменных окружения'
        )
        sys.exit()
    send_message(bot, 'Старт')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            homework = check_response(response)
            message = parse_status(homework)
            if message != old_message:
                send_message(bot, message)
                message = old_message
            else:
                logger.debug('Ответ не изменился')
                send_message(bot, 'Ответ не изменился')

            send_message(bot, 'Пауза')
            time.sleep(RETRY_TIME)
            send_message(bot, 'Новый запрос')

        except Exception as error:
            send_message(bot, f'{error}')
            logger.error(error, exc_info=True)

            send_message(bot, 'Пауза')
            time.sleep(RETRY_TIME)
            send_message(bot, 'Новый запрос')


if __name__ == '__main__':
    main()
