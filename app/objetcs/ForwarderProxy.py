import random
import string
from typing import Optional

import requests
from decouple import config

from app.utils.get_proxy_ip import get_proxy_ip

PROXY_USERNAME = config('PROXY_USERNAME')
PROXY_HOST = config('PROXY_HOST')
PROXY_PORT = config('PROXY_PORT', cast=int)
PROXY_BASE_PASSWORD = config('PROXY_BASE_PASSWORD')


AVAILABLE_COUNTRIES = ['ae', 'al', 'am', 'ao', 'ar', 'at', 'au', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg', 'bh', 'bj', 'bn', 'bo', 'br', 'bw', 'by', 'bz', 'ca', 'ch', 'ci', 'cl', 'cm', 'cn', 'co', 'cr', 'cu', 'cw', 'cy', 'cz', 'de', 'dk', 'dm', 'do', 'dz', 'ec', 'ee', 'eg', 'es', 'et', 'fi', 'fr', 'ga', 'gb', 'ge', 'gh', 'gr', 'gt', 'gy', 'hk', 'hn', 'hr', 'ht', 'hu', 'id', 'ie', 'il', 'in', 'iq', 'ir', 'is', 'it', 'jm', 'jo', 'jp', 'ke', 'kg', 'kh', 'kr', 'kw', 'kz', 'la', 'lb', 'lc', 'lk', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'md', 'me', 'mg', 'mk', 'ml', 'mm', 'mn', 'mo', 'mt', 'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'ng', 'ni', 'nl', 'no', 'np', 'nz', 'om', 'pa', 'pe', 'ph', 'pk', 'pl', 'pr', 'ps', 'pt', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'se', 'sg', 'si', 'sk', 'sn', 'so', 'sr', 'sv', 'sy', 'tg', 'th', 'tj', 'tn', 'tr', 'tt', 'tw', 'tz', 'ua', 'ug', 'us', 'uy', 'uz', 've', 'vn', 'za', 'zm', 'zw']
DURATION_TYPES = {'s': 59, 'm': 59, 'h': 24, 'd': 7}


class ForwarderProxy:
    """
    HTTP proxy wrapper for Forwarder.
    """

    SESSION_LEN = 8

    host: str
    port: int
    username: str
    password: str

    country: Optional[str]
    session: Optional[str]
    duration: Optional[str]
    ip: Optional[str]

    def __init__(self, country: str = None, session: str = None, duration: str = None):

        # generate password with parameters
        password = PROXY_BASE_PASSWORD

        # set country
        if country:
            password += f'_country-{country}'

        # set duration of ip session
        if duration:

            # generate new session if empty
            if not session:
                session = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=self.SESSION_LEN))

            password += f'_session-{session}_lifetime-{duration}_skipispstatic-1'

        # set parameters
        self.ip = None
        self.country = country
        self.session = session
        self.duration = duration

        # set credentials
        self.host = PROXY_HOST
        self.port = PROXY_PORT
        self.username = PROXY_USERNAME
        self.password = password

    def get_ip(self):
        self.ip = get_proxy_ip(str(self))
        return self.ip

    def __str__(self):
        return f'http://{self.username}:{self.password}@{self.host}:{self.port}'
