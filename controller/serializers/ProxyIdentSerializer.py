from rest_framework import serializers

from controller.objetcs.Proxy import Proxy
from controller.utils.get_proxy_ip import get_proxy_ip


class ProxyIdentSerializer(serializers.Serializer):
    country = serializers.CharField(max_length=2, required=False)
    lifetime = serializers.CharField(max_length=3, required=False)

    def validate(self, attrs):
        if not len(attrs):
            raise serializers.ValidationError(f'At least 1 parameter must be specified (country or lifetime)')
        return attrs

    def validate_country(self, value):
        try:
            Proxy.validate_country(value)
        except ValueError as exc:
            raise serializers.ValidationError(exc)
        return value

    def validate_lifetime(self, value):
        try:
            Proxy.validate_lifetime_duration(value)
        except ValueError as exc:
            raise serializers.ValidationError(exc)

        return value

    def create(self, validated_data):

        for i in range(5):
            # create new proxy with parameters
            new_proxy = Proxy.new(
                country=validated_data.get('country', None),
                lifetime=validated_data.get('lifetime', None)
            )

            # check proxy ip and availability
            proxy_ip = get_proxy_ip(str(new_proxy))
            if not proxy_ip:
                continue

            # success response
            return {
                'ident': new_proxy.ident,
                'ip': proxy_ip
            }

        raise ConnectionError('Cannot find available proxy')