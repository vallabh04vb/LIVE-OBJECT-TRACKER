import base64
import io
import os
from functools import lru_cache
from typing import List

import cv2
import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

MODEL_URL = os.environ.get(
    "MODEL_URL",
    "https://github.com/ultralytics/yolov5/releases/download/v6.0/yolov5s.onnx",
)
MODEL_PATH = os.environ.get("MODEL_PATH", "/models/yolov5s.onnx")
CONF_THRESHOLD = float(os.environ.get("CONF_THRESHOLD", "0.4"))
IOU_THRESHOLD = float(os.environ.get("IOU_THRESHOLD", "0.45"))

app = FastAPI(title="Video Batch Inference API", version="1.0.0")


class FramePayload(BaseModel):
    frame_id: int
    timestamp: float
    width: int
    height: int
    frame_data: str  # base64 encoded JPEG


class BatchPayload(BaseModel):
    batch_id: int
    frames: List[FramePayload]


def download_model() -> None:
    if os.path.exists(MODEL_PATH):
        return

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    import requests

    response = requests.get(MODEL_URL, timeout=60)
    response.raise_for_status()
    with open(MODEL_PATH, "wb") as model_file:
        model_file.write(response.content)


@lru_cache(maxsize=1)
def get_session() -> ort.InferenceSession:
    download_model()
    providers = ["CPUExecutionProvider"]
    return ort.InferenceSession(MODEL_PATH, providers=providers)


def preprocess(image: np.ndarray) -> np.ndarray:
    resized = cv2.resize(image, (640, 640))
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    blob = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
    return blob[np.newaxis, ...]


def non_max_suppression(
    outputs: np.ndarray,
    conf_threshold: float,
    iou_threshold: float,
    orig_width: int,
    orig_height: int,
):
    predictions = outputs[0]
    boxes_xywh = []
    boxes_xyxy = []
    scores = []
    classes = []

    for pred in predictions:
        obj_conf = pred[4]
        class_scores = pred[5:]
        class_id = np.argmax(class_scores)
        confidence = obj_conf * class_scores[class_id]
        if confidence < conf_threshold:
            continue
        cx, cy, w, h = pred[:4]
        x1 = cx - w / 2
        y1 = cy - h / 2
        x2 = cx + w / 2
        y2 = cy + h / 2

        x = max(min(x1, 1e9), -1e9)
        y = max(min(y1, 1e9), -1e9)
        width = max(w, 0)
        height = max(h, 0)

        boxes_xywh.append([float(x), float(y), float(width), float(height)])
        boxes_xyxy.append([float(x1), float(y1), float(x2), float(y2)])
        scores.append(float(confidence))
        classes.append(int(class_id))

    if not boxes_xywh:
        return []

    width_scale = orig_width / 640.0
    height_scale = orig_height / 640.0

    indices = cv2.dnn.NMSBoxes(
        boxes_xywh,
        scores,
        conf_threshold,
        iou_threshold,
    )

    if len(indices) == 0:
        return []

    filtered = []
    for idx in indices.flatten():
        x1, y1, x2, y2 = boxes_xyxy[idx]
        scaled = [
            max(0, min(orig_width - 1, int(x1 * width_scale))),
            max(0, min(orig_height - 1, int(y1 * height_scale))),
            max(0, min(orig_width - 1, int(x2 * width_scale))),
            max(0, min(orig_height - 1, int(y2 * height_scale))),
        ]
        filtered.append({
            "bbox": scaled,
            "confidence": scores[idx],
            "class_id": classes[idx],
        })
    return filtered


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/infer")
async def infer(batch: BatchPayload):
    session = get_session()
    input_name = session.get_inputs()[0].name

    batch_results = []

    for frame in batch.frames:
        raw_frame = frame.frame_data or ""
        try:
            decoded = base64.b64decode(raw_frame)
        except Exception as exc:  # pylint: disable=broad-except
            decoded = b""
            print(f"[warn] base64 decode failed for frame {frame.frame_id}: {exc}")

        np_buffer = np.frombuffer(decoded, np.uint8)
        if np_buffer.size == 0:
            print(f"[warn] empty frame buffer for frame {frame.frame_id}, skipping")
            batch_results.append({
                "frame_id": frame.frame_id,
                "timestamp": frame.timestamp,
                "width": frame.width,
                "height": frame.height,
                "detections": [],
                "frame_data": frame.frame_data,
            })
            continue

        image = cv2.imdecode(np_buffer, cv2.IMREAD_COLOR)
        if image is None:
            print(f"[warn] imdecode returned None for frame {frame.frame_id}, skipping")
            batch_results.append({
                "frame_id": frame.frame_id,
                "timestamp": frame.timestamp,
                "width": frame.width,
                "height": frame.height,
                "detections": [],
                "frame_data": frame.frame_data,
            })
            continue

        input_tensor = preprocess(image)
        outputs = session.run(None, {input_name: input_tensor})
        detections = non_max_suppression(
            outputs[0],
            CONF_THRESHOLD,
            IOU_THRESHOLD,
            frame.width,
            frame.height,
        )

        batch_results.append({
            "frame_id": frame.frame_id,
            "timestamp": frame.timestamp,
            "width": frame.width,
            "height": frame.height,
            "detections": detections,
            "frame_data": frame.frame_data,
        })

    return {"batch_id": batch.batch_id, "results": batch_results}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
