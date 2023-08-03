from rest_framework.status import HTTP_200_OK
from controller.responses.BaseJSONResponse import BaseJSONResponse


class SuccessResponse(BaseJSONResponse):
    status_code = HTTP_200_OK
    status_name = 'success'
