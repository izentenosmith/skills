# Service catalog

Correct starting definitions for the backing services [SKILL.md](SKILL.md) Step 1 detects. Each entry gives the image, the **healthcheck that proves readiness** (not just an open port), the data path that needs a named volume, and the connection string as seen **from inside the network**.

Pin to the major your production runs. The versions here are current-stable examples, not recommendations to upgrade.

**Treat the version tags in this file as stale until checked.** They were current when written and drift continuously; the *probes, volume paths and traps* age far more slowly and are the reason this catalog exists. So take the shape from here and confirm the tag against the image's registry page — and against what production runs, which outranks both. If a probe here fails against a newer image, the image's own entrypoint documentation is the authority, not this file.

---

## PostgreSQL

```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: ${POSTGRES_USER:-app}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?required}
    POSTGRES_DB: ${POSTGRES_DB:-app_development}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-app} -d ${POSTGRES_DB:-app_development}"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s
  restart: unless-stopped
```

**Connection:** `postgresql://app:${POSTGRES_PASSWORD}@postgres:5432/app_development`

- **Pass `-U` and `-d` to `pg_isready`.** Bare `pg_isready` reports ready while the server is still in its init phase — the entrypoint starts a temporary server to run the init scripts, and a bare probe happily succeeds against it. Naming the user and database is what makes this gate real.
- **`:?required`** makes compose fail loudly on a missing password instead of starting with an empty one.
- **`/var/lib/postgresql/data`** is the path that must be a named volume. Bind-mounting it hits permission errors on macOS and Windows.
- **Init scripts** at `/docker-entrypoint-initdb.d/*.{sql,sh}` run **only when the data directory is empty**. Editing one after first boot does nothing — a routine and confusing waste of an afternoon. Mount read-only.
- **pgvector / PostGIS:** swap the image (`pgvector/pgvector:pg16`, `postgis/postgis:16-3.4`); everything else holds.

---

## MySQL / MariaDB

```yaml
mysql:
  image: mysql:8.4
  environment:
    MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?required}
    MYSQL_DATABASE: ${MYSQL_DATABASE:-app_development}
    MYSQL_USER: ${MYSQL_USER:-app}
    MYSQL_PASSWORD: ${MYSQL_PASSWORD:?required}
  volumes:
    - mysql_data:/var/lib/mysql
  healthcheck:
    test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 30s
  restart: unless-stopped
```

**Connection:** `mysql://app:${MYSQL_PASSWORD}@mysql:3306/app_development`

- **`start_period: 30s`** — MySQL's first boot initializes the data directory and is genuinely slow. This is the service where omitting `start_period` most often kills the container before it finishes starting.
- MariaDB is a drop-in swap (`mariadb:11`), with `healthcheck.sh --connect --innodb_initialized` as the better probe.
- `/var/lib/mysql` is the volume path.

---

## MongoDB

```yaml
mongo:
  image: mongo:7
  environment:
    MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-app}
    MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:?required}
    MONGO_INITDB_DATABASE: ${MONGO_DB:-app_development}
  volumes:
    - mongo_data:/data/db
  healthcheck:
    test: ["CMD", "mongosh", "--quiet", "--eval", "db.adminCommand('ping').ok"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 15s
  restart: unless-stopped
```

**Connection:** `mongodb://app:${MONGO_PASSWORD}@mongo:27017/app_development?authSource=admin`

- **`authSource=admin`** — the root user is created in `admin`, not in your app database. Omitting it is the standard "auth failed" on a stack that otherwise looks correct.
- `mongosh` on 6+; `mongo` on 4.x.
- **Transactions need a replica set**, which the single-node image doesn't provide by default. If the app uses them, run `--replSet rs0` and initiate it once — otherwise transactions fail only in local dev, which is a confusing way to learn this.

---

## Redis / Valkey

```yaml
redis:
  image: redis:7-alpine
  command: ["redis-server", "--appendonly", "yes", "--maxmemory", "256mb", "--maxmemory-policy", "noeviction"]
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 5s
    timeout: 3s
    retries: 5
  restart: unless-stopped
```

**Connection:** `redis://redis:6379/0`

- **`--maxmemory-policy` is a correctness decision, not a tuning one.** `allkeys-lru` is right for a pure cache and **catastrophic for a job queue** — it silently evicts queued jobs under memory pressure, and the failure is work that quietly never happens. If Redis backs BullMQ, Sidekiq, Celery or RQ, use `noeviction`.
- **`--appendonly yes`** to persist. A cache-only Redis can skip it and the volume with it; a queue cannot.
- Valkey (`valkey/valkey:8-alpine`) is a drop-in with the same probe.
- Add `--requirepass ${REDIS_PASSWORD}` if the app expects auth, and `-a` on the probe to match.

---

## RabbitMQ

```yaml
rabbitmq:
  image: rabbitmq:3.13-management-alpine
  environment:
    RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-app}
    RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:?required}
  ports:
    - "15672:15672"   # management UI — dev convenience
  volumes:
    - rabbitmq_data:/var/lib/rabbitmq
  healthcheck:
    test: ["CMD", "rabbitmq-diagnostics", "-q", "check_running", "&&", "rabbitmq-diagnostics", "-q", "check_local_alarms"]
    interval: 10s
    timeout: 10s
    retries: 10
    start_period: 30s
  restart: unless-stopped
```

**Connection:** `amqp://app:${RABBITMQ_PASSWORD}@rabbitmq:5672/`

- `check_running` alone reports a broker that's up but in an alarm state; pairing it with `check_local_alarms` is what makes the gate meaningful.
- The `-management` tag adds the UI on 15672. Publish it in the **override** file, not the base.
- Erlang boot is slow — `start_period: 30s`.

---

## Kafka (KRaft, no ZooKeeper)

```yaml
kafka:
  image: confluentinc/cp-kafka:7.6.0
  environment:
    KAFKA_NODE_ID: 1
    KAFKA_PROCESS_ROLES: broker,controller
    KAFKA_CONTROLLER_QUORUM_VOTERS: "1@kafka:29093"
    KAFKA_LISTENERS: "PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093"
    KAFKA_ADVERTISED_LISTENERS: "PLAINTEXT://kafka:9092"
    KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: "PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT"
    KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
    KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
    CLUSTER_ID: "MkU3OEVBNTcwNTJENDM2Qk"
  volumes:
    - kafka_data:/var/lib/kafka/data
  healthcheck:
    test: ["CMD-SHELL", "kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1"]
    interval: 10s
    timeout: 10s
    retries: 15
    start_period: 45s
  restart: unless-stopped
```

**Connection:** `kafka:9092` from inside the network.

- **`KAFKA_ADVERTISED_LISTENERS` is the whole game.** Kafka tells clients where to reconnect, so a client inside the network needs `kafka:9092` and a client on the host needs `localhost:…`. Serving both requires two listeners with different names. Nearly every "Kafka works then times out" report is this.
- **The replication-factor-1 settings are mandatory single-node**, and are exactly the settings that must not follow you to production.
- Slowest service in this catalog — `start_period: 45s` is not padding.
- Redpanda (`redpandadata/redpanda`) is a far lighter Kafka-API-compatible local substitute if the app only speaks the protocol.

---

## Elasticsearch / OpenSearch

```yaml
elasticsearch:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.13.0
  environment:
    discovery.type: single-node
    xpack.security.enabled: "false"      # dev only
    ES_JAVA_OPTS: "-Xms512m -Xmx512m"
  volumes:
    - elasticsearch_data:/usr/share/elasticsearch/data
  healthcheck:
    test: ["CMD-SHELL", "curl -fsS http://localhost:9200/_cluster/health | grep -qE '\"status\":\"(green|yellow)\"'"]
    interval: 10s
    timeout: 10s
    retries: 15
    start_period: 60s
  restart: unless-stopped
```

**Connection:** `http://elasticsearch:9200`

- **Accept `yellow`.** A single node cannot allocate replicas, so a healthy single-node cluster is permanently yellow. A probe demanding `green` never passes and the stack never starts.
- **`xpack.security.enabled: false` is dev-only**, and must be commented as such — it's the setting most likely to be copied somewhere it matters.
- Memory-hungry. Cap the heap or it will take whatever the Docker VM has.
- OpenSearch (`opensearchproject/opensearch:2`) is similar with `DISABLE_SECURITY_PLUGIN=true`.

---

## Meilisearch

```yaml
meilisearch:
  image: getmeili/meilisearch:v1.7
  environment:
    MEILI_MASTER_KEY: ${MEILI_MASTER_KEY:?required}
    MEILI_ENV: development
  volumes:
    - meilisearch_data:/meili_data
  healthcheck:
    test: ["CMD", "curl", "-fsS", "http://localhost:7700/health"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s
  restart: unless-stopped
```

**Connection:** `http://meilisearch:7700`

Starts in about a second and uses a fraction of Elasticsearch's memory — the right default when the requirement is "search works locally" rather than "reproduce the production cluster."

---

## MinIO (S3-compatible)

```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?required}
  ports:
    - "9001:9001"   # console — dev convenience
  volumes:
    - minio_data:/data
  healthcheck:
    test: ["CMD", "mc", "ready", "local"]
    interval: 5s
    timeout: 5s
    retries: 10
    start_period: 10s
  restart: unless-stopped
```

**Connection:** endpoint `http://minio:9000`, path-style addressing, region `us-east-1`.

- **Set `forcePathStyle: true` / `AWS_S3_FORCE_PATH_STYLE`** in the client. Virtual-host addressing (`bucket.minio:9000`) doesn't resolve inside the compose network.
- Bucket creation needs a one-shot `mc` container with `depends_on: {minio: {condition: service_healthy}}`.

---

## Mailpit (SMTP capture)

```yaml
mailpit:
  image: axllent/mailpit:latest
  ports:
    - "8025:8025"   # web UI
  healthcheck:
    test: ["CMD", "/mailpit", "readyz"]
    interval: 5s
    timeout: 3s
    retries: 5
  restart: unless-stopped
```

**Connection:** SMTP `mailpit:1025`, no auth, no TLS.

Stateless — no volume needed. Worth adding whenever the app sends mail, because the alternative is either real mail from a dev environment or an untested code path.

---

## One-shot migrations

```yaml
migrate:
  build: .
  command: ["npm", "run", "migrate:deploy"]
  environment:
    DATABASE_URL: ${DATABASE_URL}
  depends_on:
    postgres:
      condition: service_healthy
  restart: "no"

api:
  depends_on:
    migrate:
      condition: service_completed_successfully
```

`service_completed_successfully` is the condition that makes this work: the app starts only after migrations **exit 0**, and a failed migration stops the stack instead of producing an app running against a stale schema. `restart: "no"` prevents a re-run loop.

---

## Conventions across all of these

- **Reach services by name** — `postgres:5432`, never `localhost:5432`. Inside a container, `localhost` is that container.
- **Use the internal port**, not the published one. Publishing `5433:5432` does not change the address inside the network.
- **Publish only what a human needs**, and prefer to publish it from the override file.
- **`${VAR:?required}` for anything with no safe default**, `${VAR:-default}` for anything with one.
- **Named volume on every data path.** Without it, `docker compose down` deletes the database.
