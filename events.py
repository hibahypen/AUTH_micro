
import json
import os
import logging
from uuid import uuid4
from datetime import datetime, timezone

from confluent_kafka import Producer

logger = logging.getLogger(__name__)

TOPIC = "auth-events"

producer = Producer({
    "bootstrap.servers": os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
    ),
    "client.id": "auth-service",
    "acks": "all",
    "enable.idempotence": True,
    "delivery.timeout.ms": 5000
})


def publish_event(event_type, user_id):
    event = {
        "event_id": str(uuid4()),
        "event_type": event_type,
        "event_version": 1,
        "source": "auth-service",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "user_id": user_id
        }
    }

    def delivery_report(err, msg):
        if err is not None:
            logger.error("Kafka delivery failed: %s", err)
        else:
            print(
                f"Event published: {event_type} | "
                f"Partition: {msg.partition()} | "
                f"Offset: {msg.offset()}"
            )

    try:
        producer.produce(
            topic=TOPIC,
            key=user_id,
            value=json.dumps(event),
            callback=delivery_report
        )

        remaining = producer.flush(6)

        if remaining:
            logger.error("Kafka delivery not confirmed")

    except Exception as e:
        logger.error("Kafka error: %s", e)