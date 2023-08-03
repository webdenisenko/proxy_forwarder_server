The container deploys the Proxy Forwarder Server that acts as a bridge between the entry and exit points.

Deployment:
1. Rename `.env.example` -> `.env` and setup
2. Launch command `docker-compose up -d --build`

Stop container:
2. Launch command `docker-compose down`

The container will start as a damon on specified ports (PUBLIC_API_PORT, PUBLIC_PROXY_PORT).

API methods:
- [GET] /api/v1/proxy/new - generate *proxy ident
- [POST] /api/v1/entrypoint - create an **entrypoint and set a proxy for it (using a compressed proxy ident)
- [DELETE] /api/v1/entrypoint - delete entry point and close all connections

*proxy ident is a string that contains dynamic proxy parameters (such as country and ip lifetime).
**entry point is the usual [username, password] format.
    The entry point is usually a client that uses the ***address of the current container as a socks5 proxy.
    Username is used to identify the created entry point to which the specific proxy ident is bound.
***address: socks5://[username:password]@[x.x.x.x]:[port]
    [x.x.x.x] - address of the current server where the container is deployed.
    [port] - the port on which the Proxy Forwarder Server listens (PUBLIC_PROXY_PORT in .env).
    [username:password] - as described above.