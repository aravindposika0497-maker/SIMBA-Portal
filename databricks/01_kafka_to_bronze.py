# Databricks notebook source
# MAGIC %md
# MAGIC # Plumery Kafka → `bronze.kafka_events` (Structured Streaming)
# MAGIC
# MAGIC Lands **raw** Kafka records into one Delta table. No payload parsing happens here: topic schemas
# MAGIC have not been confirmed, so `value` is stored as a string exactly as received. Silver jobs parse
# MAGIC it per topic once the event schemas are agreed with Plumery.
# MAGIC
# MAGIC The portal's Kafka Events page reads this table, so the portal updates as soon as this
# MAGIC stream commits a micro-batch.
# MAGIC
# MAGIC **Before running, verify (none of this is confirmed yet):**
# MAGIC 1. Network: this cluster can reach the MSK brokers (VPC peering / PrivateLink / Transit Gateway).
# MAGIC 2. The auth mode. On Amazon MSK, port **9096 = SASL/SCRAM** and port **9098 = IAM** (private). The
# MAGIC    earlier notes said "9098 + SCRAM-SHA-512", which do not normally go together; confirm with Plumery.
# MAGIC 3. Credentials: SCRAM username/password in a Databricks secret scope, or an IAM role the cluster may assume.
# MAGIC 4. Topic retention, because `startingOffsets=earliest` only replays what Kafka still retains.

# COMMAND ----------

dbutils.widgets.text("bootstrap_servers", "", "Bootstrap servers (comma-separated host:port)")
dbutils.widgets.text("topic_pattern", "", "Topic regex, e.g. .*\\.event\\..*")
dbutils.widgets.dropdown("auth_mode", "SCRAM", ["SCRAM", "IAM"], "MSK auth mode")
dbutils.widgets.text("secret_scope", "simba-kafka", "Secret scope (SCRAM)")
dbutils.widgets.text("iam_role_arn", "", "IAM role ARN to assume (IAM mode, optional)")
dbutils.widgets.text("target_table", "simba_data_poc.bronze.kafka_events", "Target Delta table")
dbutils.widgets.text("checkpoint", "/Volumes/simba_data_poc/bronze/checkpoints/kafka_events", "Checkpoint location (UC volume)")
dbutils.widgets.dropdown("starting_offsets", "earliest", ["earliest", "latest"], "Starting offsets (first run only)")
dbutils.widgets.dropdown("trigger", "availableNow", ["availableNow", "1 minute", "30 seconds"], "Trigger")
dbutils.widgets.text("max_offsets_per_trigger", "200000", "Max offsets per micro-batch")

# COMMAND ----------

import re

bootstrap = dbutils.widgets.get("bootstrap_servers").strip()
topic_pattern = dbutils.widgets.get("topic_pattern").strip()
auth_mode = dbutils.widgets.get("auth_mode")
target_table = dbutils.widgets.get("target_table").strip()
checkpoint = dbutils.widgets.get("checkpoint").strip()

assert bootstrap, "bootstrap_servers is required"
assert topic_pattern, "topic_pattern is required"
assert re.fullmatch(r"[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+", target_table), "target_table must be catalog.schema.table"
re.compile(topic_pattern)  # fail fast on an invalid regex

# COMMAND ----------

# MAGIC %md ## Target table (created once)

# COMMAND ----------

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {target_table} (
  topic                STRING    COMMENT 'Kafka topic',
  `partition`          INT       COMMENT 'Kafka partition',
  `offset`             BIGINT    COMMENT 'Kafka offset within the partition',
  kafka_timestamp      TIMESTAMP COMMENT 'Kafka record timestamp',
  kafka_timestamp_type INT       COMMENT '0 = CreateTime, 1 = LogAppendTime',
  key                  STRING    COMMENT 'Record key as UTF-8 string',
  value                STRING    COMMENT 'Raw record value as UTF-8 string (unparsed)',
  headers              ARRAY<STRUCT<key: STRING, value: BINARY>> COMMENT 'Kafka headers',
  _ingested_at         TIMESTAMP COMMENT 'When this row was written to Bronze',
  event_date           DATE      COMMENT 'Date of kafka_timestamp (for pruning)'
)
CLUSTER BY (event_date, topic)
COMMENT 'Raw Plumery Kafka events. One row per Kafka record. (topic, partition, offset) is unique.'
""")

# COMMAND ----------

# MAGIC %md ## Kafka source options

# COMMAND ----------

options = {
    "kafka.bootstrap.servers": bootstrap,
    "subscribePattern": topic_pattern,
    "startingOffsets": dbutils.widgets.get("starting_offsets"),  # ignored after the first run (checkpoint wins)
    "maxOffsetsPerTrigger": dbutils.widgets.get("max_offsets_per_trigger"),
    "includeHeaders": "true",
    # true = stop loudly if offsets were deleted by retention before we read them (data loss is visible).
    "failOnDataLoss": "true",
    "kafka.security.protocol": "SASL_SSL",
}

if auth_mode == "SCRAM":
    scope = dbutils.widgets.get("secret_scope")
    username = dbutils.secrets.get(scope, "kafka-username")
    password = dbutils.secrets.get(scope, "kafka-password")
    options.update({
        "kafka.sasl.mechanism": "SCRAM-SHA-512",
        "kafka.sasl.jaas.config": (
            "kafkashaded.org.apache.kafka.common.security.scram.ScramLoginModule required "
            f'username="{username}" password="{password}";'
        ),
    })
else:  # IAM (MSK port 9098). Requires DBR 13.3 LTS+ and an instance profile / role that can kafka-cluster:Connect etc.
    role_arn = dbutils.widgets.get("iam_role_arn").strip()
    jaas = "shadedmskiam.software.amazon.msk.auth.iam.IAMLoginModule required"
    if role_arn:
        jaas += f' awsRoleArn="{role_arn}" awsStsRegion="eu-west-1"'
    options.update({
        "kafka.sasl.mechanism": "AWS_MSK_IAM",
        "kafka.sasl.jaas.config": jaas + ";",
        "kafka.sasl.client.callback.handler.class": "shadedmskiam.software.amazon.msk.auth.iam.IAMClientCallbackHandler",
    })

# COMMAND ----------

from pyspark.sql import functions as F

raw = spark.readStream.format("kafka").options(**options).load()

bronze = raw.select(
    F.col("topic"),
    F.col("partition"),
    F.col("offset"),
    F.col("timestamp").alias("kafka_timestamp"),
    F.col("timestampType").alias("kafka_timestamp_type"),
    F.col("key").cast("string").alias("key"),
    F.col("value").cast("string").alias("value"),
    F.col("headers"),
    F.current_timestamp().alias("_ingested_at"),
    F.to_date("timestamp").alias("event_date"),
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Start the stream
# MAGIC * `availableNow` — read everything currently available, then stop (good for a scheduled job and for the initial replay).
# MAGIC * `1 minute` / `30 seconds` — run continuously; the portal shows new events within one trigger + one portal refresh.
# MAGIC
# MAGIC The checkpoint makes this exactly-once into Delta: re-running continues from the last committed offsets.

# COMMAND ----------

trigger = dbutils.widgets.get("trigger")
writer = (
    bronze.writeStream
    .format("delta")
    .option("checkpointLocation", checkpoint)
    .queryName("plumery_kafka_to_bronze")
)
writer = writer.trigger(availableNow=True) if trigger == "availableNow" else writer.trigger(processingTime=trigger)
query = writer.toTable(target_table)

if trigger == "availableNow":
    query.awaitTermination()
    print(f"Caught up. Rows now in {target_table}: {spark.table(target_table).count():,}")

# COMMAND ----------

# MAGIC %md ## Verification queries (run after the first batch)

# COMMAND ----------

display(spark.sql(f"""
SELECT topic, COUNT(*) AS events, MIN(kafka_timestamp) AS first_event, MAX(kafka_timestamp) AS last_event,
       COUNT(DISTINCT `partition`) AS partitions
FROM {target_table}
GROUP BY topic
ORDER BY events DESC
"""))

# COMMAND ----------

# Duplicate check: (topic, partition, offset) must be unique. Expect zero rows.
display(spark.sql(f"""
SELECT topic, `partition`, `offset`, COUNT(*) AS n
FROM {target_table}
GROUP BY topic, `partition`, `offset`
HAVING COUNT(*) > 1
LIMIT 20
"""))
