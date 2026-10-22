const cityAir = db.getSiblingDB("city_air");

if (!cityAir.getCollectionNames().includes("measurements")) {
  cityAir.createCollection("measurements", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: [
          "_id", "station", "timestamp", "source_timezone", "measurements",
          "source", "ingested_at", "quality"
        ],
        properties: {
          _id: { bsonType: "string" },
          station: { bsonType: "string", minLength: 1 },
          timestamp: { bsonType: "date" },
          source_timezone: { bsonType: "string" },
          measurements: { bsonType: "object" },
          source: { bsonType: "string" },
          source_record_number: { bsonType: ["string", "null"] },
          ingested_at: { bsonType: "date" },
          quality: {
            bsonType: "object",
            required: ["status", "flags", "pollutant_completeness", "rules_version"],
            properties: {
              status: { enum: ["accepted", "warning"] },
              flags: { bsonType: "array" },
              pollutant_completeness: { bsonType: ["double", "int"] },
              rules_version: { bsonType: "string" }
            }
          }
        }
      }
    }
  });
}

for (const name of ["rejected_measurements", "ingestion_runs", "source_metadata", "query_benchmarks"]) {
  if (!cityAir.getCollectionNames().includes(name)) {
    cityAir.createCollection(name);
  }
}

cityAir.measurements.createIndex({ station: 1, timestamp: -1 });
cityAir.measurements.createIndex({ timestamp: -1 });
cityAir.measurements.createIndex({ "quality.status": 1, timestamp: -1 });
cityAir.ingestion_runs.createIndex({ started_at: -1 });
cityAir.ingestion_runs.createIndex({ status: 1, finished_at: -1 });
cityAir.rejected_measurements.createIndex({ quarantined_at: -1 });
cityAir.query_benchmarks.createIndex({ run_at: -1 });

cityAir.source_metadata.updateOne(
  { _id: "uci-beijing-multisite-2013-2017" },
  { $set: {
    name: "UCI Beijing Multi-Site Air Quality",
    role: "Historical test fixture simulating a future municipal hourly batch feed",
    source_rows_expected: 420768,
    limitations: [
      "Historical Beijing observations are not evidence about another municipality.",
      "Station coordinates and siting context are absent from the supplied CSV files.",
      "Calibration, precision and government publication processes are not verified here.",
      "Hourly observations are not suitable for every health or policy question."
    ],
    spatial_coverage_assessed: false,
    health_thresholds_authoritative: false,
    updated_at: new Date()
  }},
  { upsert: true }
);
