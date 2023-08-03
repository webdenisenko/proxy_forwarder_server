from rest_framework import serializers

from controller.objetcs.Proxy import Proxy


class EntryPointSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=64)
    password = serializers.CharField(max_length=64)
    proxy_ident = serializers.CharField(max_length=15)
    entry_host = serializers.CharField(max_length=20, default=None, required=False)

    def validate_proxy_ident(self, value):
        try:
            Proxy(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc))

        return value