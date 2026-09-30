# PromptGate

PromptGate is a production-style backend built with Django REST Framework. It
provides an authenticated AI gateway backed by Google Gemini.

The current foundation includes PostgreSQL-backed Django, JWT account
authentication, PromptGate client API keys, a Gemini generation endpoint, and
Docker services for the application, PostgreSQL, and Redis. Generation usage is
recorded in PostgreSQL, and Redis enforces per-API-key request limits.

## Requirements

- Docker and Docker Compose (recommended), or
- Python 3.13+ and PostgreSQL 17+

## Setup with Docker

1. Create your local environment file:

   ```sh
   cp .env.example .env
   ```

2. Replace the placeholder secrets in `.env`.

3. Build the images and apply database migrations:

   ```sh
   docker compose build
   docker compose run --rm web python manage.py migrate
   ```

4. Start the services:

   ```sh
   docker compose up
   ```

The API is available at `http://localhost:8000`, and its health endpoint is
`GET http://localhost:8000/api/health/`.

## Local setup

1. Create and activate a virtual environment:

   ```sh
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, activate it with `.venv\Scripts\Activate.ps1`.

2. Install dependencies and create the environment file:

   ```sh
   pip install -r requirements.txt
   cp .env.example .env
   ```

3. Create a PostgreSQL database and update the `DB_*` values in `.env`.

4. Apply migrations and run the development server:

   ```sh
   python manage.py migrate
   python manage.py runserver
   ```

## Gemini configuration

Set the provider credentials and model in `.env`:

```env
GEMINI_API_KEY=your-google-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash
REDIS_URL=redis://redis:6379/0
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW_SECONDS=60
CACHE_ENABLED=True
CACHE_TTL_SECONDS=300
```

The default model is `gemini-3.8-flash`. Never commit the local `.env` file.
The default rate limit is 60 generation requests per 60-second fixed window for
each PromptGate client API key. If Redis is unavailable, generation requests
fail explicitly with HTTP 503 instead of bypassing the limit.

Successful generation responses are cached in Redis for 300 seconds by
default. Cache entries are isolated by PromptGate API-key UUID, provider, and
model, and use a SHA-256 prompt digest instead of the raw prompt. Cache read or
write failures fall back to the normal provider flow because caching is an
optimization; rate limiting remains fail-closed.

## Generate text

Authenticate generation requests with a PromptGate client API key. The raw key
is returned only when it is created through `POST /api/api-keys/`.

```http
POST /api/v1/generate/
Authorization: Api-Key <promptgate-client-api-key>
Content-Type: application/json

{
  "prompt": "Explain database indexing simply."
}
```

Example response:

```json
{
  "output": "An index is like a book's table of contents...",
  "provider": "gemini",
  "model": "gemini-3.8-flash",
  "request_id": "gateway-request-id",
  "usage": {
    "input_tokens": 8,
    "output_tokens": 12,
    "total_tokens": 20
  },
  "latency_ms": 340,
  "cached": false
}
```

PromptGate stores the request ID, client API-key reference, provider/model,
token counts, latency, status, and creation time for completed provider calls.
Raw prompts, raw API keys, and provider exception messages are not persisted.
Successful generated output may be stored temporarily in Redis for the cache
TTL. Cache hits receive a fresh request ID, report `cached: true`, record zero
provider tokens and latency, and do not call Gemini. Requests over the limit
return HTTP 429 with a `Retry-After` header and use neither cache nor Gemini.

## API documentation

- OpenAPI schema: `GET /api/schema/`
- Swagger UI: `GET /api/docs/`

The schema documents registration, JWT tokens, PromptGate API-key management,
and text generation, including cache and usage metadata.

## Continuous integration

GitHub Actions runs on pushes and pull requests. It installs dependencies with
PostgreSQL and Redis service containers, then runs the automated tests, Django
system checks, and migration drift check. CI does not require a Gemini API key,
and tests mock all provider calls.

## Tests

Run the test suite with:

```sh
pytest
```
