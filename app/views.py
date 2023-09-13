""" Views and Urls of application """
import json
import random

from flask import Blueprint, request
from marshmallow import ValidationError

from app.objetcs.ForwarderProxy import ForwarderProxy, AVAILABLE_COUNTRIES
from app.format_response import success, error
from app.server.ProxyForwarderServer import ProxyForwarderServer
from app.serializers import EntryPointSchema

# registrate Blueprint as route
routes = Blueprint('routes', __name__)


@routes.post('/api/v1/entrypoint')
def entrypoint_create():
    serializer = EntryPointSchema()

    # put client address as inspector address
    request_data = request.form.to_dict()
    if 'inspector' in request_data and request_data['inspector']:
        request_data['inspector'] = json.loads(request_data['inspector']) | {
            'address': request.remote_addr
        }

    # validate data
    try:
        validated_data = serializer.load(request_data)
    except ValidationError as exc:
        return error('Invalid data', exc.messages)

    # check connection is exists
    exists = ProxyForwarderServer.exists_entry_point(validated_data.get('username'))

    # create connection
    if not exists:

        # find proxy and test connection
        for i in range(3):

            # create proxy object
            proxy = ForwarderProxy(
                country=validated_data.get(
                    'ip_country', random.choice(AVAILABLE_COUNTRIES) # set random country if empty
                ),
                session=validated_data.get('ip_session', None),
                duration=validated_data.get('ip_duration', None),
            )

            # test connection
            if proxy.get_ip():
                break

        else:
            raise ConnectionError('failed to get a valid proxy')

        created_at = ProxyForwarderServer.create_entry_point(
            username=validated_data.get('username'),
            password=validated_data.get('password'),
            proxy_kwargs={
                'country': proxy.country,
                'session': proxy.session,
                'duration': proxy.duration,
            },
            client_host=validated_data.get('client_host', None),
            inspector=validated_data.get('inspector'),
        )

        if created_at:
            return success(f'Entry point `{validated_data.get("username")}` successfully created', data={
                'proxy_info': {
                    'ip': proxy.ip,
                    'country': proxy.country,
                    'session': proxy.session,
                    'duration': proxy.duration,
                },
                'credentials': {
                    'username': validated_data.get('username'),
                    'password': validated_data.get('password'),
                },
                'created_at': created_at
            })

    return error(f'Entry point `{validated_data.get("username")}` already exists')


@routes.delete('/api/v1/entrypoint')
def entrypoint_delete():
    username = request.form.get('username', None)

    if not username:
        raise ValidationError('Username not provided')

    response = ProxyForwarderServer.delete_entry_point(username)
    if response is None:
        message = f'Entry point `{username}` not exists'
    else:
        message = f'Entry point `{username}` deleted'

    return success(message, data=response)
