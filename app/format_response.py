from flask import jsonify


def base_format(status_code: int, status_name: str, message: str, data: dict = None):
    response = {
        'status': status_name,
        'message': message,
    }

    if data:
        response['data'] = data

    return jsonify(response), status_code


def success(message: str = None, data: dict = None):
    return base_format(200, 'success', message or 'Done', data)


def error(message: str = None, data: dict = None):
    return base_format(400, 'error', message or 'Server error', data)