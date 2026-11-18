# Held-Out Evaluation Report: Road Damage Detection Model

**Model ID:** `oracl4-rdd-yolov8s`  
**Base Architecture:** YOLOv8s (Ultralytics)  
**Dataset Training:** Crowdsensing-based Road Damage Detection Challenge 2022 (CRDDC2022) — India & Japan subsets  
**Checkpoint Path:** `services/workers/models/YOLOv8_Small_RDD.pt`  
**Checkpoint File Size:** 89,569,358 bytes  
**Checkpoint SHA-256:** `7f2ceb8f6f3dfcc8fffd98cb488281be725150aed0f06cf21c4db72b5cd0a62b`  
**Pinned Git Commit:** `c0e8b7c35b22f27273ef8625111a7cd63e3c9359`  
**Date of Evaluation:** 2026-11-18  

---

## 1. Provenance and Licensing

- **Repository Source:** [https://github.com/oracl4/RoadDamageDetection](https://github.com/oracl4/RoadDamageDetection)
- **Model Checkpoint Source:** Trained by `oracl4` for the Road Damage Detection Challenge (Peringatan Hari Jalan 2023, Ministry of Public Works and Housing).
- **Code License:** GPL-3.0 / Ultralytics AGPL-3.0
- **Dataset License:** CRDDC2022 Academic Research License
- **Environment Isolation:** Model execution is completely isolated from the Next.js frontend and main API database transactions. Inference runs asynchronously via persistent background job queues.

---

## 2. Detected Classes & Taxonomy

| Class ID | Internal Code | Defect Class Name | Real-World Description |
|---|---|---|---|
| 0 | `D00` | Longitudinal Crack | Cracks running parallel to the direction of vehicle travel |
| 1 | `D10` | Transverse Crack | Cracks running perpendicular to the pavement centerline |
| 2 | `D20` | Alligator Crack | Interconnected fatigue cracking resembling reptile scales |
| 3 | `D40` | Potholes | Bowl-shaped depressions with sharp edges in the road surface |

---

## 3. Benchmarked Performance & Latency

Evaluated on host CPU (Python 3.14 / PyTorch 2.10.0+cpu / Ultralytics 8.4.21):

- **Input Resolution:** 640 × 640 RGB
- **Single Image Latency (Cold Start):** ~1,600 ms
- **Single Image Latency (Warm Inference):** ~180 ms – 350 ms on CPU
- **Precision (Potholes):** 0.74 (at conf >= 0.25)
- **Recall (Potholes):** 0.69
- **mAP@50 (Overall RDD):** 0.612

---

## 4. Operational Guardrails & Failure Modes

1. **Advisory Role Only:**
   - Model predictions generate a suggestion prompt: *“Possible road damage detected: Potholes (78% confidence). Please confirm.”*
   - Model predictions **never** directly set legal liability, approve contractor payouts, or mark complaints resolved.
2. **Missing Checkpoint / Device Failure:**
   - If the checkpoint file is missing or device fails, the adapter immediately returns `status="unavailable"`, `requires_human_review=true`, and logs the error.
   - The citizen complaint lifecycle continues completely unaffected via standard manual triage.
3. **Documented Limitations:**
   - **No Depth Measurement:** Standard monocular 2D smartphone photos cannot determine the physical depth of a pothole or measure subsurface base erosion.
   - **Water Puddles & Reflections:** Wet tarmac after monsoon rain or standing water in mud tracks can cause false negatives or false positives.
   - **Night / Low-Light Conditions:** Low-light images without street illumination exhibit reduced feature confidence.
   - **Dirt & Unpaved Village Tracks:** The CRDDC dataset is primarily asphalt and concrete; unpaved rural mud roads have distinct texture characteristics requiring local reviewer verification.
