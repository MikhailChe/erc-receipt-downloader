import logging
import os
import telebot

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NOTIFICATION_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID'))

log = logging.getLogger(__name__)


def send_message(msg):
    if not (TELEGRAM_TOKEN and NOTIFICATION_CHAT_ID):
        log.warning('Tried to send message, but telegram is not configured')
        return
    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    bot.send_message(NOTIFICATION_CHAT_ID, msg)


def send_document(filename, caption):
    if not (TELEGRAM_TOKEN and NOTIFICATION_CHAT_ID):
        log.warning('Tried to send document, but telegram is not configured')
        return
    with open(filename, 'rb') as f:
        bot = telebot.TeleBot(TELEGRAM_TOKEN)
        bot.send_document(NOTIFICATION_CHAT_ID, f, caption=caption)
