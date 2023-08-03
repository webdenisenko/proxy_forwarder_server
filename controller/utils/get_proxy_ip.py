import requests

from controller.utils.get_logger import get_logger

logger = get_logger(__name__)


def get_proxy_ip(proxy: str):

    CHECK_CONN_URLS = {
        'http://ip-api.com/json/?fields=61439': 'query',
        'https://api.seeip.org/jsonip': 'ip',
        'https://api.myip.com/': 'ip',
        'https://api.my-ip.io/ip.json': 'ip',
        'https://api.bigdatacloud.net/data/client-ip': 'ipString',
    }

    for url, ip_json_key in CHECK_CONN_URLS.items():

        try:

            logger.debug(f'checking proxy({proxy}) on url: {url}')

            # send request
            response = requests.get(url, proxies={
                'http': proxy,
                'https': proxy
            }, timeout=15)

            # success
            logger.debug(f'success proxy({proxy})')
            return response.json()[ip_json_key]

        # proxy not available
        except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError):
            logger.debug(f'failed proxy({proxy})')
            break

        # url not available
        except (requests.exceptions.JSONDecodeError, ):
            logger.debug(f'failed url({url})')
            continue

    return None
