import multiprocessing
import random
import time

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from controller.objetcs.Proxy import AVAILABLE_COUNTRIES
from controller.serializers import ProxyIdentSerializer
from controller.utils.get_proxy_ip import get_proxy_ip
from controller.utils.random_str import random_str
from main import ProxyForwarderServer
from pfs.settings import PUBLIC_PROXY_PORT


class ProxyForwarderAPITestCase(APITestCase):
    def test_get_proxy_ident(self):

        # generate proxy ident via API
        response = self.client.get(reverse('proxy_ident'), {
            'country': 'la',
            'lifetime': '1h'
        })

        # status success
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        # response is valid
        self.assertIn('data', response.data)
        self.assertIn('ident', response.data['data'])
        self.assertIn('ip', response.data['data'])

        print('SUCCESS RESPONSE:', response.data)

    def test_proxy_forwarder_connection(self):

        # run proxy forwarder server
        PFS = multiprocessing.Process(target=ProxyForwarderServer, daemon=True)
        PFS.start()

        # set parameters to serialization
        serializer = ProxyIdentSerializer(data={
            'country': random.choice(AVAILABLE_COUNTRIES),
            'lifetime': '1h'
        })

        # validate
        serializer.is_valid(raise_exception=True)

        # set test credentials
        ident_data = serializer.create(serializer.validated_data)
        ident, original_ip = ident_data['ident'], ident_data['ip']
        username = random_str()
        password = 'passwordstr'
        print('LEVEL 1/5 -- TEST CREDENTIALS:\n -', '\n - '.join([
            f'username `{username}`',
            f'password `{password}`',
            f'proxy_ident `{ident}`',
            f'original_ip `{original_ip}`',
        ]))

        # set entry point via API
        response = self.client.post(reverse('entrypoint'), {
            'username': username, # entry credentials
            'password': password, # entry credentials
            'proxy_ident': ident, # proxy ident
        })
        print('LEVEL 2/5 -- ENTRYPOINT CREATED:', response.data)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        # test proxy via proxy forwarder server
        forwarder_ip = get_proxy_ip(f'socks5://{username}:{password}@127.0.0.1:{PUBLIC_PROXY_PORT}')
        self.assertEqual(original_ip, forwarder_ip)
        print(f'LEVEL 3/5 -- IPS MATCH: {original_ip}=={forwarder_ip}')

        # delete entry point via API
        response = self.client.delete(reverse('entrypoint'), {
            'username': username,
        })
        print('LEVEL 4/5 -- ENTRYPOINT DELETED:', response.data)
        self.assertEqual(status.HTTP_200_OK, response.status_code)

        none_ip = get_proxy_ip(f'socks5://{username}:{password}@127.0.0.1:{PUBLIC_PROXY_PORT}')
        self.assertIsNone(none_ip)
        print('LEVEL 5/5 -- CONNECTION CLOSED:', none_ip)