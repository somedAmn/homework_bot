import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)


def send_message(bot, message):
    """Отправлка уведомления пользователю в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Удачная отправка сообщения в Telegram')
    except telegram.TelegramError:
        logger.error('Ошибка отправки сообщения в Telegram')


def get_api_answer(current_timestamp):
    """Отправка запроса к API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        logger.error('Урл недоступен')
        raise SystemExit(e)

    if response.status_code == HTTPStatus.OK:
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            logger.error('Не удалось преобразовать результат запроса в json')
    else:
        logger.error('Запрос к эндпоинту не дал статус код 200')
        raise Exception


def check_response(response):
    """Проверка корректности ответа API."""
    try:
        homeworks = response.get('homeworks')
        if homeworks is not None and isinstance(homeworks, list):
            return homeworks
        else:
            logger.error('Отсутствуют ожидаемые ключи в ответе API')
            raise Exception
    except AttributeError:
        return 'status'


def parse_status(homework):
    """Формирование сообщения о статусе."""
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            raise KeyError
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError
    homework_name = homework['homework_name']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных окружения."""
    if None in (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN):
        logger.critical('Отсутствуют обязательные переменные окружения')
        return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise Exception
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks)
                send_message(bot, message)

            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
