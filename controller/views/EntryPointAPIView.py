import traceback

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from controller.serializers import EntryPointSerializer
from main import ProxyForwarderServer
from controller.responses.ErrorResponse import ErrorResponse
from controller.responses.SuccessResponse import SuccessResponse


class EntryPointAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:

            # serialize
            serializer = EntryPointSerializer(data=request.data)

            # validate
            serializer.is_valid(raise_exception=True)

            # create connection
            created = ProxyForwarderServer.create_entry_point(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password'],
                proxy_ident=serializer.validated_data['proxy_ident'],
                entry_host=serializer.validated_data['entry_host'],
            )

            if not created:
                return ErrorResponse(f'Entry point `{serializer.validated_data["username"]}` already exists. You can delete and create again.')

        except ValidationError as exc:
            return ErrorResponse('Incorrect data', exc.get_full_details())

        except:
            traceback.print_exc()
            return ErrorResponse('Server error')

        return SuccessResponse('Connection is ready')

    def delete(self, request, *args, **kwargs):
        username = request.data.get('username', None)

        if not username:
            return ErrorResponse('Username not provided')

        if ProxyForwarderServer.delete_entry_point(username):
            message = f'Entry point `{username}` deleted'
        else:
            message = f'Entry point `{username}` not exists'

        return SuccessResponse(message)