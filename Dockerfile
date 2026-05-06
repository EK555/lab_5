FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    sqlalchemy==2.0.23 \
    psycopg2-binary==2.9.9 \
    alembic==1.12.1 \
    bcrypt==4.1.2 \
    PyJWT==2.8.0 \
    python-dotenv==1.0.0 \
    email-validator==2.1.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    httpx==0.27.0 \
    redis==7.4.0

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]