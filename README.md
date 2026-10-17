# Municipal Air Quality Batch Ingestion

A portable Task 1 prototype for loading a public multi-site air-quality dataset into MongoDB in retryable batches. It is designed as the data-ingestion layer behind a city dashboard. The dashboard can query measurements by monitoring station and time; the loader itself does not issue health alerts.

## Dataset

The default input is the UCI Machine Learning Repository's **Beijing Multi-Site Air Quality** dataset (UCI dataset 501). It contains 420,768 hourly records from 12 monitoring stations, recorded from 2013 to 2017. The loader downloads UCI's `PRSA2017_Data_20130301-20170228.zip` archive, which contains one CSV for each monitoring station, and processes the CSV files one at a time. The rows contain timestamp parts, station, PM2.5, PM10, SO2, NO2, CO, O3, temperature, pressure, dew point, rain, wind direction, and wind speed.

Source: <https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data>

## Run locally

Requirements: Docker Desktop or Docker Engine with Docker Compose.

```bash
docker compose up --build
```

The MongoDB service exposes port `27017`; its data is kept in a named Docker volume. The ingestion service waits for MongoDB's health check, downloads and extracts the dataset, and loads it in batches of 1,000 documents. It exits after a successful load. To stop the services while keeping stored data, run `docker compose down`. To reset the database and load again from scratch, run `docker compose down -v` and then `docker compose up --build`.

The sample credentials in `docker-compose.yml` are for a local educational prototype only. Use secrets, TLS, network controls, and a managed or properly configured MongoDB deployment before any real use.

## Data model

Each document represents one station-hour. `_id` is deterministic (`station|ISO-8601 timestamp`) and is used as the uniqueness key. A document has `station`, a timezone-aware `timestamp`, `source_timezone`, a nested `measurements` object, and `source`. The source date fields are interpreted as Beijing local time (`Asia/Shanghai`); MongoDB stores BSON dates as UTC instants while the explicit source timezone preserves how the source record should be interpreted. The measurement object omits fields whose source values are missing and stores numeric values as numbers; unknown future sensor fields can be added there without redesigning every stored record.

Example:

```json
{
  "_id": "Aotizhongxin|2013-03-01T00:00:00+08:00",
  "station": "Aotizhongxin",
  "timestamp": "2013-02-28T16:00:00Z",
  "source_timezone": "Asia/Shanghai",
  "measurements": {"pm25": 4.0, "pm10": 4.0, "temperature_c": -0.7},
  "source": "UCI Beijing Multi-Site Air Quality"
}
```

The collection indexes `(station, timestamp)` for common dashboard filters. Stable IDs plus `$setOnInsert` upserts make a whole batch safe to retry after an uncertain write result. Bounded exponential backoff is used for transient MongoDB errors. The current proof of concept uses a single local MongoDB container; it demonstrates portability and restartable ingestion, not production high availability.

## Scale-out and operational notes

For a larger deployment, move the same application to a MongoDB replica-set or sharded-cluster connection string, store credentials in a secret manager, and define a shard key only after measuring query patterns and distribution. A likely candidate to evaluate is a hashed station identifier combined with a time bucket, but it must be benchmarked against the municipality's actual queries. Sharding and replication add operational work; the local Compose setup does not provide either.

Before a citizen-facing warning service is built, the municipality must define authoritative thresholds, sensor-quality rules, alert ownership, and delivery safeguards. This prototype only makes validated readings available for downstream applications.

## Files

- `src/ingest.py` - download, transform, batch, retry, and upsert.
- `mongo/init.js` - create collection and indexes.
- `Dockerfile` and `docker-compose.yml` - portable local runtime.
- `tests/` - transformation and batch-boundary checks.
- `docs/` - portfolio phase PDFs generated with this submission.

## References

- UCI Machine Learning Repository, Beijing Multi-Site Air Quality: <https://archive.ics.uci.edu/dataset/501/beijing+multi+site+air+quality+data>
- MongoDB, Data Modeling: <https://www.mongodb.com/docs/manual/data-modeling/>
- MongoDB, Sharding: <https://www.mongodb.com/docs/manual/sharding/>
- MongoDB, PyMongo Bulk Write Operations: <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/bulk-write/>

## Repository link

https://github.com/yerkebttt/municipal-air-quality-batch-ingestion
