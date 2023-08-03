from rest_framework.status import HTTP_400_BAD_REQUEST
from controller.responses.BaseJSONResponse import BaseJSONResponse


class ErrorResponse(BaseJSONResponse):
    status_code = HTTP_400_BAD_REQUEST
    status_name = 'error'
