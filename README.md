# Campus Cart

A reproducible container deployment of a stateless order API. This project demonstrates the full container lifecycle: **build, test, scan, run, fail over, and roll back**.

## Objective

Eliminate runtime drift between developer and test environments by packaging the Campus Cart API and its pinned dependencies in a container. Secrets and persistent order data remain outside the application image.

## Architecture

```text
Client -> Nginx :8080 -> api1 :8080 --\
                       -> api2 :8080 ----> PostgreSQL 16 -> named volume
                                secret -> /run/secrets/db_password
```

- Flask + Gunicorn stateless API
- Two equivalent API containers
- Nginx load balancing and retry
- PostgreSQL persistent named volume
- Runtime-injected Docker secret
- Non-root application user
- GitHub Actions test, build, and Trivy scan

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health, version, and serving instance |
| GET | `/orders` | List persisted orders |
| POST | `/orders` | Create an order using `{ "item": "notebook", "qty": 2 }` |

## Quick start

```bash
cp .env.example .env
mkdir -p secrets
printf '%s' 'ChangeMe-CampusCart-2026' > secrets/db_password.txt
docker build -t campuscart-api:1.0.0 --build-arg APP_VERSION=1.0.0 .
docker compose up -d
docker compose ps
curl http://localhost:8080/health
```

Or run `./scripts/demo.sh 1.0.0`.

## Test

```bash
docker run --rm -v "$PWD":/app -w /app python:3.12-slim \
  sh -c "pip install -q -r requirements-dev.txt && pytest -v"
```

## Functional verification

```bash
curl -X POST http://localhost:8080/orders \
  -H 'Content-Type: application/json' \
  -d '{"item":"notebook","qty":2}'
curl http://localhost:8080/orders
```

## Failover

```bash
docker compose stop api1
curl http://localhost:8080/health
docker compose start api1
```

The request should continue through `api2`.

## Vulnerability scan

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image --severity HIGH,CRITICAL --ignore-unfixed \
  campuscart-api:1.0.0
```

## Faulty release and rollback

```bash
docker build -t campuscart-api:1.1.0 \
  --build-arg APP_VERSION=1.1.0 --build-arg BROKEN=true .
API_TAG=1.1.0 docker compose up -d api1 api2
curl -i http://localhost:8080/health

API_TAG=1.0.0 docker compose up -d api1 api2
curl -i http://localhost:8080/health
curl http://localhost:8080/orders
```

The faulty image returns HTTP 500. Rollback restores HTTP 200 while order data remains in the database volume.

## Repository creation

GitHub repository names cannot contain spaces. Use **Campus-Cart** as the repository slug and **Campus Cart** as the project title.

```bash
git init
git add .
git commit -m "Initial Campus Cart containerized API"
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/Campus-Cart.git
git push -u origin main
```

## Security notes

- Replace the demonstration password before running.
- `secrets/` is excluded from Git and Docker build context.
- Only Nginx publishes a host port.
- PostgreSQL is available only on the internal Compose network.
- The API runs as UID 10001, not root.

## Limitations

This proof runs on one Docker host, so it demonstrates container-level failover rather than host or availability-zone resilience. Production options include Azure Container Apps, AKS, Amazon ECS, Azure Database for PostgreSQL, and Azure Key Vault.
