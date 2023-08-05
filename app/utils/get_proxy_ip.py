import requests

GET_IP_URLS = {
    'http://ip-api.com/json/?fields=61439': 'query',
    'https://api.seeip.org/jsonip': 'ip',
    'https://api.myip.com/': 'ip',
    'https://api.my-ip.io/ip.json': 'ip',
    'https://api.bigdatacloud.net/data/client-ip': 'ipString',
}

BROKEN_URL_EXCEPTIONS = (
    requests.exceptions.JSONDecodeError,
)

BROKEN_PROXY_EXCEPTIONS = (
    requests.exceptions.ProxyError,
    requests.exceptions.ConnectionError,
    requests.exceptions.ReadTimeout
)


def get_proxy_ip(proxy: str):
    for url, ip_json_key in GET_IP_URLS.items():
        try:

            # send request
            response = requests.get(url, proxies={
                'http': proxy,
                'https': proxy
            }, timeout=15)

            proxy_ip = response.json()[ip_json_key]

            # success
            return proxy_ip

        except BROKEN_PROXY_EXCEPTIONS:
            # proxy not available
            break

        except BROKEN_URL_EXCEPTIONS:
            # url not available
            continue

    return None
