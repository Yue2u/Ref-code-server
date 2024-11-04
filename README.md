# Ref code server
## What can it do?
    - Full user logic (register/login/logout/user info)
    - Referral system - create referral codes, register with referral codes
    - OAuth2 - register with Google/Github, or link your profile

## Stack
    - FastAPI
    - Postgresql
    - Async sqlalchemy and alembic for migrations
    - Redis

## How to run
    1. For local run just execute command 'docker compose up' - server will be available on http://localhost:5000 or http://127.0.0.1:5000, you will use default secrets, so don't forget to change them later in .env file
    2. To run tests just run 'docker compose -f docker-compose.tests.yml up'
    3. For production run you need to do some more actions:
        - Set your email in traefik.prod.yml to automatically generate certificate for your domain with letsencrypte (its free)
        - Set your domain in docker-compose.prod.yml (line 45)
        - Set your secrets and other variables in .env
        - Finally, run 'docker compose -f docker-compose.prod.yml up'
    4. For local development we use uv (https://docs.astral.sh/uv/getting-started/installation/), so after installation run 'uv sync' to download all packages
