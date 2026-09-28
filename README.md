# PromptGate

PromptGate is a production-style backend built with Django REST Framework. It
provides the foundation for an AI gateway that will integrate with Gemini in a
later stage.

The current foundation includes PostgreSQL-backed Django, a health endpoint,
and Docker services for the application, PostgreSQL, and Redis. Redis is
available as infrastructure only and is not used by the application yet.

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

## Tests

Run the test suite with:

```sh
pytest
```
