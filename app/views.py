""" Views and Urls of application """
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

    # validate data
    try:
        validated_data = serializer.load(request.form)
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
                duration=validated_data.get('ip_duration', None)
            )

            # test connection
            if proxy.get_ip():
                break

        else:
            raise ConnectionError('failed to get a valid proxy')

        created = ProxyForwarderServer.create_entry_point(
            username=validated_data.get('username'),
            password=validated_data.get('password'),
            proxy_kwargs={
                'country': proxy.country,
                'session': proxy.session,
                'duration': proxy.duration,
            },
            client_host=validated_data.get('client_host', None),
        )

        if created:
            return success(f'Entry point `{validated_data.get("username")}` successfully created', data={
                'ip': {
                    'address': proxy.ip,
                    'country': proxy.country,
                    'session': proxy.session,
                    'duration': proxy.duration,
                },
                'credentials': {
                    'username': validated_data.get('username'),
                    'password': validated_data.get('password'),
                }
            })

    return error(f'Entry point `{validated_data.get("username")}` already exists')


@routes.delete('/api/v1/entrypoint')
def entrypoint_delete():
    username = request.form.get('username', None)

    if not username:
        raise ValidationError('Username not provided')

    if ProxyForwarderServer.delete_entry_point(username):
        message = f'Entry point `{username}` deleted'
    else:
        message = f'Entry point `{username}` not exists'

    return success(message)