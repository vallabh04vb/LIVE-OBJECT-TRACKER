import base64
import json
import os
import time
from io import BytesIO
from typing import Dict, List

import boto3
import cv2
import numpy as np
import requests
from kafka import KafkaConsumer

BATCH_LIMIT = int(os.environ.get("BATCH_LIMIT", "100"))
S3_PREFIX = os.environ.get("S3_PREFIX", "annotated")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")


def draw_boxes(frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]
        conf = detection.get("confidence", 0.0)
        class_id = detection.get("class_id", -1)
        pt1 = (int(x1), int(y1))
        pt2 = (int(x2), int(y2))
        label = f"id:{class_id} {conf:.2f}"
        cv2.rectangle(frame, pt1, pt2, (0, 255, 0), 2)
        cv2.putText(frame, label, (pt1[0], max(pt1[1] - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    return frame


def upload_to_s3(bucket: str, key: str, image: np.ndarray):
    success, buffer = cv2.imencode(".jpg", image)
    if not success:
        raise RuntimeError("Failed to encode annotated frame")
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=BytesIO(buffer.tobytes()),
        ContentType="image/jpeg",
    )


def consume(
    kafka_bootstrap: List[str],
    topic: str,
    inference_url: str,
    s3_bucket: str,
):
    security_protocol = os.environ.get("KAFKA_SECURITY_PROTOCOL", "SSL")
    ssl_cafile = os.environ.get("KAFKA_CA_FILE")

    print(
        "Starting consumer with topic=%s bootstrap=%s" % (topic, ",".join(kafka_bootstrap)),
        flush=True,
    )

    consumer_kwargs = {
        "bootstrap_servers": kafka_bootstrap,
        "group_id": os.environ.get("KAFKA_GROUP", "inference-consumer"),
        "value_deserializer": lambda v: json.loads(v.decode("utf-8")),
        "auto_offset_reset": "earliest",
        "enable_auto_commit": True,
        "consumer_timeout_ms": 1000,
    }

    if security_protocol:
        consumer_kwargs["security_protocol"] = security_protocol
    if ssl_cafile:
        consumer_kwargs["ssl_cafile"] = ssl_cafile

    consumer = KafkaConsumer(topic, **consumer_kwargs)

    processed_frames = 0

    while True:
        for message in consumer:
            batch = message.value
            batch_id = batch.get("batch_id")
            frames = batch.get("frames", [])
            print(
                "Processing batch %s containing %d frames" % (batch_id, len(frames)),
                flush=True,
            )

            response = requests.post(
                f"{inference_url.rstrip('/')}/infer",
                json=batch,
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])

            if not results:
                print("Inference returned no results for batch %s" % batch_id, flush=True)
                continue

            for result in results:
                encoded = result.get("frame_data")
                if not encoded:
                    continue

                image = cv2.imdecode(
                    np.frombuffer(base64.b64decode(encoded), np.uint8),
                    cv2.IMREAD_COLOR,
                )
                if image is None:
                    continue

                annotated = draw_boxes(image, result.get("detections", []))

                frame_id = result.get("frame_id")
                key = f"{S3_PREFIX}/{batch_id}_{frame_id}.jpg"
                upload_to_s3(s3_bucket, key, annotated)
                print("Annotated frame uploaded to s3://%s/%s" % (s3_bucket, key), flush=True)
                processed_frames += 1

                if BATCH_LIMIT and processed_frames >= BATCH_LIMIT:
                    print("Processed frame limit reached, exiting")
                    return

        time.sleep(1)


if __name__ == "__main__":
    kafka_bootstrap = os.environ.get("KAFKA_BOOTSTRAP")
    topic = os.environ.get("KAFKA_TOPIC", "video-ingest")
    inference_url = os.environ.get("INFERENCE_URL")
    s3_bucket = os.environ.get("S3_BUCKET")

    if not all([kafka_bootstrap, topic, inference_url, s3_bucket]):
        raise SystemExit("Missing required environment variables")

    servers = [server.strip() for server in kafka_bootstrap.split(",") if server.strip()]
    consume(servers, topic, inference_url, s3_bucket)
