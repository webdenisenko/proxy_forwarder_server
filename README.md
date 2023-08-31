Proxy forwarder server container as a bridge between an entry and exit points.

Install Docker:
$: curl -fsSL https://get.docker.com -o get-docker.sh
$: sudo sh get-docker.sh

Deployment:
$: cp .env.example .env
$: docker-compose up -d --build

Stop container:
$: docker-compose down`

The container will be available on 2 public ports:
- .env :: ${PUBLIC_API_PORT} -> API requests
- .env :: ${PUBLIC_PROXY_PORT} - SOCKS5 proxy

API methods:
- [POST] /api/v1/entrypoint
- [DELETE] /api/v1/entrypoint