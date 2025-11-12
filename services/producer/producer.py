import argparse
import base64
import json
import os
import signal
import sys
import time
from typing import List

import cv2
from kafka import KafkaProducer
from kafka.errors import KafkaError

BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "25"))
LINGER_MS = int(os.environ.get("LINGER_MS", "500"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "5"))
MAX_WIDTH = int(os.environ.get("MAX_WIDTH", "640"))
JPEG_QUALITY = int(os.environ.get("JPEG_QUALITY", "55"))


def encode_frame(frame_id: int, frame) -> dict:
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(1, min(JPEG_QUALITY, 95))]
    success, buffer = cv2.imencode(".jpg", frame, encode_params)
    if not success:
        raise RuntimeError("Failed to encode frame to JPEG")
    payload = {
        "frame_id": frame_id,
        "timestamp": time.time(),
        "width": frame.shape[1],
        "height": frame.shape[0],
        "frame_data": base64.b64encode(buffer).decode("utf-8"),
    }
    return payload


def producer_client(bootstrap_servers: List[str]) -> KafkaProducer:
    security_protocol = os.environ.get("KAFKA_SECURITY_PROTOCOL", "SSL")
    ssl_cafile = os.environ.get("KAFKA_CA_FILE")

    kwargs = {
        "bootstrap_servers": bootstrap_servers,
        "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
        "linger_ms": LINGER_MS,
        "retries": MAX_RETRIES,
        "max_request_size": 1024 * 1024 * 10,
    }

    if security_protocol:
        kwargs["security_protocol"] = security_protocol
    if ssl_cafile:
        kwargs["ssl_cafile"] = ssl_cafile

    return KafkaProducer(**kwargs)


def publish_batches(rtsp_url: str, kafka_bootstrap: List[str], topic: str):
    producer = producer_client(kafka_bootstrap)
    bootstrap_str = ",".join(kafka_bootstrap)

    capture = cv2.VideoCapture(rtsp_url)
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open RTSP stream: {rtsp_url}")

    print(
        "Started streaming from %s -> Kafka topic %s (bootstrap=%s)"
        % (rtsp_url, topic, bootstrap_str),
        flush=True,
    )
    batch = []
    frame_idx = 0

    def handle_sigterm(signo, frame):  # pylint: disable=unused-argument
        print("Received termination signal, flushing pending frames...")
        capture.release()
        producer.flush()
        producer.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    while True:
        ret, frame = capture.read()
        if not ret:
            print("Stream ended or failed, attempting to reconnect in 2s")
            time.sleep(2)
            capture.release()
            capture = cv2.VideoCapture(rtsp_url)
            continue

        if MAX_WIDTH and frame.shape[1] > MAX_WIDTH:
            scale = MAX_WIDTH / frame.shape[1]
            new_dims = (MAX_WIDTH, int(frame.shape[0] * scale))
            frame = cv2.resize(frame, new_dims, interpolation=cv2.INTER_AREA)

        batch.append(encode_frame(frame_idx, frame))
        frame_idx += 1

        if len(batch) >= BATCH_SIZE:
            payload = {"batch_id": int(time.time() * 1000), "frames": batch}
            try:
                future = producer.send(topic, payload)
                metadata = future.get(timeout=10)
                producer.flush()
                print(
                    "Published batch %s with %d frames (partition=%s offset=%s)"
                    % (payload["batch_id"], len(batch), metadata.partition, metadata.offset),
                    flush=True,
                )
                batch = []
            except KafkaError as exc:
                producer.flush()
                print(
                    "[error] Failed to publish batch %s to Kafka (bootstrap=%s topic=%s): %s"
                    % (payload["batch_id"], bootstrap_str, topic, exc),
                    flush=True,
                )
                time.sleep(5)
            except Exception as exc:  # pylint: disable=broad-except
                producer.flush()
                print(
                    "[error] Unexpected failure publishing batch %s: %s"
                    % (payload["batch_id"], exc),
                    flush=True,
                )
                time.sleep(5)

        time.sleep(0.033)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RTSP to Kafka frame producer")
    parser.add_argument("--rtsp-url", required=False, default=os.environ.get("RTSP_URL"))
    parser.add_argument("--kafka-bootstrap", required=False, default=os.environ.get("KAFKA_BOOTSTRAP"))
    parser.add_argument("--topic", required=False, default=os.environ.get("KAFKA_TOPIC", "video-ingest"))

    args = parser.parse_args()

    if not args.rtsp_url or not args.kafka_bootstrap:
        parser.error("RTSP URL and Kafka bootstrap servers are required")

    kafka_servers = [server.strip() for server in args.kafka_bootstrap.split(",") if server.strip()]
    publish_batches(args.rtsp_url, kafka_servers, args.topic)
