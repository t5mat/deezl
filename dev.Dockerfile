# syntax=docker/dockerfile:labs

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

COPY <<'EOF' /etc/caddy/Caddyfile
:80 {
    handle_path /api/* {
        reverse_proxy localhost:5000
    }

    route /* {
        reverse_proxy localhost:{$PUBLIC_PORT}
        try_files {path} /
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
command=unbuffer uvicorn src.api:app --reload --root-path /api --port 5000
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:web]
directory=/app/web
command=npm run dev -- --base %(ENV_PUBLIC_BASE)s --port %(ENV_PUBLIC_PORT)s
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

COPY --chmod=755 <<'EOF' /entrypoint
#!/bin/sh -e
PUBLIC_BASE="${PUBLIC_BASE:-/}" exec supervisord -n -c /etc/supervisord.conf
EOF

ENTRYPOINT ["/entrypoint"]

EXPOSE 80
