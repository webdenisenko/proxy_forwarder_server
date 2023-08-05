import multiprocessing
import random

from decouple import config
from flask import url_for

from app import app
from app.objetcs.ForwarderProxy import ForwarderProxy, AVAILABLE_COUNTRIES
from app.server.ProxyForwarderServer import ProxyForwarderServer
from app.utils.get_proxy_ip import get_proxy_ip

PUBLIC_PROXY_PORT = config('PUBLIC_PROXY_PORT')

credentials = {
    'username': 'test_username',
    'password': 'test_password',
}
proxy = None

# run PFS
PFS_process = multiprocessing.Process(target=ProxyForwarderServer, daemon=True)
PFS_process.start()


def test_no_connect_without_entry_point():
    PFS_proxy_url = f'socks5://{credentials["username"]}:{credentials["password"]}@127.0.0.1:{PUBLIC_PROXY_PORT}'

    assert get_proxy_ip(PFS_proxy_url) is None


def test_get_and_check_proxy():
    global proxy

    for i in range(3):
        country = random.choice(AVAILABLE_COUNTRIES)
        proxy = ForwarderProxy(country=country, duration='10m')
        if proxy.get_ip():
            break
    else:
        raise AssertionError


def test_create_entry_point():
    global proxy

    with app.test_request_context():
        url = url_for('routes.entrypoint_create')

    with app.test_client() as client:
        response = client.post(url, data=credentials | {
            'ip_country': proxy.country,
            'ip_session': proxy.session,
            'ip_duration': proxy.duration,
        })

    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'


def test_connect_with_entry_point():
    global proxy

    PFS_proxy_url = f'socks5://{credentials["username"]}:{credentials["password"]}@127.0.0.1:{PUBLIC_PROXY_PORT}'
    print('___', PFS_proxy_url, '___')

    direct_proxy_ip = proxy.ip
    via_forwarder_proxy_ip = get_proxy_ip(PFS_proxy_url)

    assert direct_proxy_ip == via_forwarder_proxy_ip


def test_delete_entry_point():
    with app.test_request_context():
        url = url_for('routes.entrypoint_delete')

    with app.test_client() as client:
        response = client.delete(url, data=credentials)

    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'
    assert response.get_json()['message'] == f'Entry point `{credentials["username"]}` deleted'


def test_no_connect_without_entry_point_again():
    PFS_proxy_url = f'socks5://{credentials["username"]}:{credentials["password"]}@127.0.0.1:{PUBLIC_PROXY_PORT}'

    assert get_proxy_ip(PFS_proxy_url) is None


def test_terminate():
    global PFS_process
    ProxyForwarderServer.terminate()
    PFS_process.terminate()