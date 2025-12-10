# Minimal Postgres image for local development
# Usage example:
#   docker build -t logistic-postgres .
#   docker run -d --name logistic-db \
#     -e POSTGRES_USER=logistic \
#     -e POSTGRES_PASSWORD=logistic \
#     -e POSTGRES_DB=logistic \
#     -p 5432:5432 \
#     -v logistic_pgdata:/var/lib/postgresql/data \
#     logistic-postgres
# You can pass any valid Postgres env vars at run time.

FROM postgres:15-alpine

# Set default runtime environment (override at `docker run`)
ENV POSTGRES_USER=logistic \
    POSTGRES_PASSWORD=logistic \
    POSTGRES_DB=logistic

# Expose default Postgres port
EXPOSE 8090

# Healthcheck to ensure Postgres is accepting connections
HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD pg_isready -U "$POSTGRES_USER" || exit 1
