
import json
import sys

from confluent_kafka import Consumer

group_id = (
    sys.argv[1] if len(sys.argv) > 1
    else "analytics-auth"
)

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": group_id,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False
})

consumer.subscribe(["auth-events"])

print(f"Analytics Consumer started: {group_id}")
print("Waiting for authentication events...\n")

try:
    while True:
        message = consumer.poll(1.0)

        if message is None:
            continue

        if message.error():
            print(message.error())
            continue

        event = json.loads(
            message.value().decode("utf-8")
        )

        print("=" * 45)
        print("Event:", event["event_type"])
        print("User ID:", event["data"]["user_id"])
        print("Timestamp:", event["timestamp"])
        print("Partition:", message.partition())
        print("Offset:", message.offset())
        print("=" * 45)

        consumer.commit(
            message=message,
            asynchronous=False
        )

except KeyboardInterrupt:
    print("\nConsumer stopped.")

finally:
    consumer.close()
