import logging
import os
import sys
import time
import requests
import telegram.error
from dotenv import load_dotenv
import telegram

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s, %(funcName)s',
    handlers=[
        logging.FileHandler('log.txt'),
        logging.StreamHandler(stream=sys.stdout)
    ]
)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Бот отправляет сообщение."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError:
        logging.error(f'Сообщение НЕ отправлено: {message}')
    else:
        logging.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    logging.info(f'Отправляем запрос к API: {ENDPOINT}')
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except requests.exceptions('Ошибка запроса'):
        raise
    if homework_statuses.status_code != 200:
        raise ConnectionError(
            f'Ошибка подключения: {homework_statuses.status_code}'
        )
    response = homework_statuses.json()
    return response


def check_response(response):
    """Проверяет ответ API на корректность."""
    logging.info('Проверяем ответ API на корректность')
    if not isinstance(response, dict):
        raise TypeError(
            f'Получен НЕ верный тип данных: {type(response)}, ожидался словарь'
        )
    if not response.get('homeworks'):
        raise IndexError('Список домашних работ пуст или нет изменений')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            f'Получен НЕ верный тип данных: {type(response)}, ожидался список'
        )
    homework = response.get('homeworks')[0]
    return homework


def parse_status(homework):
    """Извлекает из информации статус работы."""
    logging.info('Определяем статус домашней работы')
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            raise KeyError('Статус домашней работы не определен!')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Статус домашней работы не определен!')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def main():
    """Основная логика работы бота."""
    timestamp = 0
    old_message = ''
    if not check_tokens():
        logger.critical('Отсутствие обязательных переменных окружения')
        sys.exit('Бот остановлен')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, 'Старт')
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homework = check_response(response)
            message = parse_status(homework)
            if message != old_message:
                send_message(bot, message)
                message = old_message
            else:
                logging.debug('Ответ не изменился')
                send_message(bot, 'Ответ не изменился')

        except Exception as error:
            send_message(bot, f'{error}')
            logging.error(error, exc_info=True)

        finally:
            send_message(bot, 'Пауза')
            time.sleep(RETRY_PERIOD)
            send_message(bot, 'Новый запрос')


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    main()
