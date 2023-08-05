import ipaddress

from marshmallow import Schema, fields, ValidationError, validates, validate

from app.objetcs.ForwarderProxy import AVAILABLE_COUNTRIES, DURATION_TYPES


class EntryPointSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=1, max=64))
    password = fields.String(required=True, validate=validate.Length(min=1, max=64))
    ip_country = fields.String()
    ip_session = fields.String(validate=validate.Length(min=8, max=14))
    ip_duration = fields.String()
    client_host = fields.String()

    @validates('ip_country')
    def validate_ip_country(self, value):

        # check in supported list
        if value not in AVAILABLE_COUNTRIES:
            raise ValidationError(f'country `{value}` not supported')

    @validates('ip_duration')
    def validate_ip_duration(self, value):
        if not (2 <= len(value) <= 3) or not value[:-1].isdigit():
            raise ValidationError(f'Wrong format `{value}`. Example: 59s')

        # validate duration type
        duration_type = value[-1]
        if duration_type not in DURATION_TYPES:
            raise ValidationError(f'Invalid duration type `{duration_type}`. Supported types: {", ".join(DURATION_TYPES)}')

        # validate duration value
        duration_value = int(value[:-1])
        if duration_value > DURATION_TYPES[duration_type]:
            raise ValidationError(f'Too big duration `{value}`. Maximum: {DURATION_TYPES[duration_type]}{duration_type}')

    @validates('client_host')
    def validate_client_host(self, value):
        try:
            ipaddress.ip_address(value)
        except ValueError as exc:
            raise ValidationError(str(exc))