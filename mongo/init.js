const cityAir = db.getSiblingDB("city_air");

cityAir.createCollection("measurements", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "station", "timestamp", "source_timezone", "measurements", "source"],
      properties: {
        _id: { bsonType: "string" },
        station: { bsonType: "string" },
        timestamp: { bsonType: "date" },
        source_timezone: { bsonType: "string" },
        measurements: { bsonType: "object" },
        source: { bsonType: "string" }
      }
    }
  }
});

cityAir.measurements.createIndex({ station: 1, timestamp: 1 });
