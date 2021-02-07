import json
import logging
import logging.config
import os
import sys
from datetime import date

import requests

log = logging.getLogger(__name__)

ERC_LOGIN = os.environ['ERC_LOGIN']
ERC_PASSWORD = os.environ['ERC_PASSWORD']
_contract_numbers_ = os.environ['ERC_CONTRACT_NUMBERS']
if not _contract_numbers_:
    raise ValueError('No contract numbers')
ERC_CONTRACT_NUMBERS = _contract_numbers_.split(',')

LOG_PATH = os.getenv('LOG_PATH', default='logs')


class ERC:
    _RECEIPT_URL_TEMPLATE_ = 'https://lk.erc-ekb.ru/erc/client/private_office/private_office.htp?receipt={}&quitance'
    _LOGIN_URL_ = 'https://lk.erc-ekb.ru/client/private_office/private_office.htp'

    def __init__(self, login, password):
        self._login = login
        self._password = password

        session = requests.session()
        self._session = session

    def login(self):
        # Pretend we are Chrome. Dont think it's really needed, but yet
        login_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.60 YaBrowser/20.12.0.1065 Yowser/2.5 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        }
        login_form = {
            'smth': '',
            'username': self._login,
            'password': self._password,
        }
        self._session.post(ERC._LOGIN_URL_, headers=login_headers, data=login_form)
        log.debug('Logged in to ERC')

    def get_receipt(self, contract):
        log.debug('Getting receipt for contract %s', contract)
        return self._session.get(ERC._RECEIPT_URL_TEMPLATE_.format(contract)).content


class LastReceipt:
    _LAST_FILE_CONFIG_ = 'last.json'

    def __init__(self, directory):
        self.directory = directory

    def get_last(self):
        last_struct = None
        try:
            last_struct = self._get_last()
            return last_struct.get('last_name')
        except:
            return None

    def _last_config_path(self):
        return os.path.join(self.directory, LastReceipt._LAST_FILE_CONFIG_)

    def _get_last(self) -> dict:
        path = self._last_config_path()
        with open(path) as fp:
            return json.load(fp)

    def get_last_content(self):
        last_path = self.get_last()
        if not last_path:
            return None
        last_file_name = os.path.join(self.directory, last_path)
        with open(last_file_name, 'rb') as f:
            return f.read()

    def same_as_last(self, content):
        last = self.get_last_content()
        if not last:
            return False
        log.debug('Compare current receipt to last one')
        log.debug('Last: size: %s, type: %s; New size: %s, type %s',
                  len(last),
                  type(last),
                  len(content),
                  type(content),
                  )
        min_size = min(len(content), len(last))
        similar_bytes = sum(1 if last[i] == content[i] else 0 for i in range(min(len(content), len(last)))) / min_size
        similar_sizes = min_size / max(len(content), len(last))
        similarity = similar_sizes * similar_bytes
        return similarity > .99

    def update_last(self, filename):
        last_struct = None
        try:
            last_struct = self._get_last()
        except:
            last_struct = {'last_name': filename}
        finally:
            with open(self._last_config_path(), 'w') as f:
                json.dump(last_struct, f)


def configure_logging():
    global log
    os.makedirs(LOG_PATH, exist_ok=True)
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
        'loggers': {
            '': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
            '__main__': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'root': {
                'handlers': ['console', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
        'formatters': {
            'simple': {
                'format': '%(levelname)s: %(name)s: %(asctime)s %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'stream': sys.stdout,
                'formatter': 'simple',
            },
            'file': {
                'level': 'INFO',
                'filename': os.path.join(LOG_PATH, 'erc.log'),
                'mode': 'a',
                'formatter': 'simple',
                'class': 'logging.FileHandler',
            }
        }
    })
    log = logging.getLogger(__name__)


def main():
    configure_logging()

    erc_client = ERC(ERC_LOGIN, ERC_PASSWORD)
    erc_client.login()

    today = date.today()

    for contract in ERC_CONTRACT_NUMBERS:
        try:
            content = erc_client.get_receipt(contract)
            last_receipt_provider = LastReceipt(contract)
            if last_receipt_provider.same_as_last(content):
                log.info('Downloaded receipt is same as last one, no need to update')
                break

            filename = '{}.pdf'.format(today.strftime('%Y-%m-%d'))
            receipt_path = os.path.join(contract, filename)
            os.makedirs(contract, exist_ok=True)
            with open(receipt_path, 'wb') as f:
                f.write(content)
            last_receipt_provider.update_last(filename)
            log.info('Successfully downloaded receipt to a file %s', receipt_path)
            # TODO: insert some callbacks here to send TG notification
        except:
            log.exception('Error managing receipt %s', contract)


if __name__ == '__main__':
    try:
        main()
    except:
        log.exception('Uncaught error')
