import logging
import os
import time

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
    if bot.send_message(TELEGRAM_CHAT_ID, message):
        logging.info('Удачная отправка сообщения в Telegram')
    else:
        logging.error('Ошибка отправки сообщения в Telegram')


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error('Запрос к эндпоинту не дал статус код 200')
        raise Exception


def check_response(response):
    if isinstance(response, list):
        homeworks = response[0].get('homeworks')
    else:
        homeworks = response.get('homeworks')

    if homeworks is not None and isinstance(homeworks, list):
        return homeworks
    else:
        logging.error('Отсутствуют ожидаемые ключи в ответе API')
        raise Exception


def parse_status(homework):
    if isinstance(homework, list):
        homework_name = homework[0].get('homework_name')
        homework_status = homework[0].get('status')
    else:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
    if homework_name is None:
        logging.error('Недокументированный статус домашней работы')
    if homework_status is None:
        logging.debug('В ответе отсутствует новый статус')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    if None in (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN):
        logging.critical('Отсутствуют обязательные переменные окружения')
        return False
    return True


def main():
    """Основная логика работы бота."""
    check_tokens()
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
