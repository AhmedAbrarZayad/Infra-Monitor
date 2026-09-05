FROM python:3.14-slim AS builder

WORKDIR /app


RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    pip install -r requirements.txt


FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "/venv/bin/python manage.py migrate && /venv/bin/daphne -b 0.0.0.0 -p 8000 infra_monitor.asgi:application"]
