Proxy Forwarder Server (PFS) container as a middleware between client and remote server.

PFS allows you to create a single entry point and manage it using an API.

Possibilities:
- set proxy for each remote host in real time
- duplicate outgoing/incoming traffic to socket inspector

*was used to decrypt the mtproto protocol(https://core.telegram.org/mtproto), already deprecated.

Deployment:
$: curl -fsSL https://get.docker.com -o get-docker.sh
$: sudo sh get-docker.sh
$: cp .env.example .env
$: docker-compose up -d --build

Stop container:
$: docker-compose down

The container will be available on 2 public ports:
- .env :: ${PUBLIC_API_PORT} -> API requests
- .env :: ${PUBLIC_PROXY_PORT} - SOCKS5 proxy

API methods:
- [POST] /api/v1/entrypoint
- [DELETE] /api/v1/entrypoint