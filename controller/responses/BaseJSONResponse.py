from rest_framework.response import Response


class BaseJSONResponse(Response):
    """
    General format of API response.
    """

    status_code: int = None
    status_name: str = None

    def __init__(self, message: str, addon_data: dict = None):
        if not self.status_code or not self.status_name:
            raise NotImplementedError('class JSONResponse should be implemented')

        if not isinstance(message, str):
            raise ValueError('message should be str')

        success_data = {
            'status': self.status_name,
            'message': message
        }

        if addon_data:
            if not isinstance(addon_data, dict):
                raise ValueError('addon_data should be dict')

            success_data['data'] = addon_data

        super().__init__(success_data, self.status_code, None, None, None, None)