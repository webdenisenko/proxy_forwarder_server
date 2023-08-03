import traceback

from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView

from controller.serializers import ProxyIdentSerializer
from controller.responses.ErrorResponse import ErrorResponse
from controller.responses.SuccessResponse import SuccessResponse


class ProxyIdentAPIView(APIView):
    def get(self, request):
        try:

            # serialize
            serializer = ProxyIdentSerializer(data=request.GET)

            # validate
            serializer.is_valid(raise_exception=True)

            # generate proxy ident
            generated_proxy_ident = serializer.create(serializer.data)

        except ValidationError as exc:
            return ErrorResponse('Incorrect data', exc.get_full_details())

        except:
            traceback.print_exc()
            return ErrorResponse('Server error')

        return SuccessResponse('Ident generated', generated_proxy_ident)
