# syntax=docker/dockerfile:labs

FROM node:alpine AS build-web

ARG PUBLIC_BASE=/

SHELL ["/bin/sh", "-e", "-c"]

COPY /web /app/web

RUN <<'EOF'
cd /app/web
npm i
npm run build -- --base $PUBLIC_BASE
EOF

FROM python:alpine

SHELL ["/bin/sh", "-e", "-c"]

RUN <<'EOF'
apk add --no-cache expect caddy supervisor
apk add --no-cache nodejs-current npm

pip install --no-cache-dir uvicorn

apk add --no-cache build-base libffi-dev zlib-dev jpeg-dev
EOF

RUN --mount=type=bind,source=/api,target=/app/api <<'EOF'
pip install --no-cache-dir -r /app/api/requirements.txt
EOF

COPY --from=build-web /app/web/dist /app/web/dist

COPY /api/src /app/api/src

COPY <<'EOF' /etc/caddy/Caddyfile
:80 {
    handle_path /api/* {
        reverse_proxy localhost:5000
    }

    handle /* {
        root * /app/web/dist
        file_server
        try_files {path} /index.html
    }
}
EOF

COPY <<'EOF' /etc/supervisord.conf
[supervisord]
user = root

[program:proxy]
command=unbuffer caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:api]
directory=/app/api
command=unbuffer uvicorn src.api:app --root-path /api --port 5000
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

COPY --chmod=755 <<'EOF' /entrypoint
#!/bin/sh -e
exec supervisord -n -c /etc/supervisord.conf
EOF

ENTRYPOINT ["/entrypoint"]

EXPOSE 80
