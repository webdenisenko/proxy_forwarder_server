import random
import string

from pfs.settings import PROXY_USERNAME, PROXY_HOST, PROXY_PORT, PROXY_BASE_PASSWORD


AVAILABLE_COUNTRIES = ['ae', 'al', 'am', 'ao', 'ar', 'at', 'au', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg', 'bh', 'bj', 'bn', 'bo', 'br', 'bw', 'by', 'bz', 'ca', 'ch', 'ci', 'cl', 'cm', 'cn', 'co', 'cr', 'cu', 'cw', 'cy', 'cz', 'de', 'dk', 'dm', 'do', 'dz', 'ec', 'ee', 'eg', 'es', 'et', 'fi', 'fr', 'ga', 'gb', 'ge', 'gh', 'gr', 'gt', 'gy', 'hk', 'hn', 'hr', 'ht', 'hu', 'id', 'ie', 'il', 'in', 'iq', 'ir', 'is', 'it', 'jm', 'jo', 'jp', 'ke', 'kg', 'kh', 'kr', 'kw', 'kz', 'la', 'lb', 'lc', 'lk', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'md', 'me', 'mg', 'mk', 'ml', 'mm', 'mn', 'mo', 'mt', 'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'ng', 'ni', 'nl', 'no', 'np', 'nz', 'om', 'pa', 'pe', 'ph', 'pk', 'pl', 'pr', 'ps', 'pt', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'se', 'sg', 'si', 'sk', 'sn', 'so', 'sr', 'sv', 'sy', 'tg', 'th', 'tj', 'tn', 'tr', 'tt', 'tw', 'tz', 'ua', 'ug', 'us', 'uy', 'uz', 've', 'vn', 'za', 'zm', 'zw']
DURATION_TYPES = {
    's': 59,
    'm': 59,
    'h': 24,
    'd': 7
}
LIFETIME_SESSION_IDENT_LENGTH = 8


class Proxy:
    """
    HTTP proxy wrapper.
    """

    ident: str
    host: str
    port: int
    username: str
    password: str

    def __init__(self, ident: str):
        """
        Ident examples:
         * au - only country (rotated ip)
         * abcdFG12_59s - only lifetime session (random country)
         * au:abcdFG12_59s - country and lifetime session
        """

        if not ident:
            raise ValueError('Ident not provided')

        if not isinstance(ident, str):
            raise ValueError('Ident should be string')

        password = PROXY_BASE_PASSWORD

        # parse ident parts
        for part in ident.split(':'):

            # country
            if len(part) == 2:

                # validate country
                self.validate_country(part)

                # put parsed parameter
                password += f'_country-{part}'

            # lifetime
            elif LIFETIME_SESSION_IDENT_LENGTH + 3 <= len(part) <= LIFETIME_SESSION_IDENT_LENGTH + 4:
                lifetime_session, lifetime_duration = part.split('_')

                # validate session
                if len(lifetime_session) != LIFETIME_SESSION_IDENT_LENGTH:
                    raise ValueError(f'Invalid lifetime session format `{lifetime_session}`. Should be length {LIFETIME_SESSION_IDENT_LENGTH}')

                # validate duration
                self.validate_lifetime_duration(lifetime_duration)

                # put parsed parameter
                password += f'_session-{lifetime_session}_lifetime-{lifetime_duration}'

            else:
                raise ValueError(f'Cannot parse ident part `{part}`')

        self.host = PROXY_HOST
        self.port = PROXY_PORT
        self.username = PROXY_USERNAME
        self.password = password
        self.ident = ident

    @classmethod
    def new(cls, country: str = '', lifetime: str = ''):
        """
        Generate proxy with new ident.
        Depends on attributes: country and lifetime.
        """

        new_ident = []

        if country:
            new_ident.append(country) # put country

        if lifetime:
            lifetime_session = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=LIFETIME_SESSION_IDENT_LENGTH))
            new_ident.append(f'{lifetime_session}_{lifetime}') # put lifetime session

        # convert to string ident
        new_ident = ':'.join(new_ident)

        return Proxy(new_ident)

    @staticmethod
    def validate_country(value: str):
        if value not in AVAILABLE_COUNTRIES:
            raise ValueError(f'Country `{value}` not supported')

        return True

    @staticmethod
    def validate_lifetime_duration(value: str):

        # validate duration type
        duration_type = value[-1]
        if duration_type not in DURATION_TYPES:
            raise ValueError(f'Invalid duration type `{duration_type}`. Supported types: {", ".join(DURATION_TYPES)}')

        # validate duration value
        duration_value = int(value[:-1])
        if duration_value > DURATION_TYPES[duration_type]:
            raise ValueError(f'Too big duration `{value}`. Maximum: {DURATION_TYPES[duration_type]}{duration_type}')

        return True

    def __str__(self):
        return f'http://{self.username}:{self.password}@{self.host}:{self.port}'
