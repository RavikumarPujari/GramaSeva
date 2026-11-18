# FixProof Candidate Models Evaluation Report: Phase 7

**Report ID:** `FP-EVAL-PHASE7-CANDIDATES`  
**Date:** 2026-11-18  
**Scope:** AI Model Evaluation, Provenance Gates, Duplicate Matching Signals, and Fallback Audits  
**Compliance Authority:** FixProof Master Specification (`README.md`, Phase 7 & Section 14)

---

## Executive Summary

Phase 7 evaluates candidate AI models and algorithms for municipal issue triage, duplicate detection, and category prediction. Per FixProof governance rules:
1. **Zero Mock Predictions:** No fake scores, simulated confidences, or synthetic detections are permitted in production or staging workflows.
2. **Never Auto-Merge Duplicates:** Spatial proximity or visual similarity alone must never automatically merge reports into an issue without explicit citizen or reviewer confirmation.
3. **Strict Gate Approvals:** Only models with verifiable open-source checkpoints, compatible runtime frameworks, and valid licenses may be integrated. Incompatible or unverified candidates must cleanly fall back to manual human review.

---

## 1. Candidate 1: Pipeline & Water Leak Detection

### 1.1 Provenance and Checkpoint Verification
- **Source Repository:** [MSunusi/pipeline-leak-detection](https://github.com/MSunusi/pipeline-leak-detection)
- **Pinned Git Commit:** `49a174c83fa880bb6eeb0bf8032e54ee7589d892`
- **Checkpoint File:** `services/workers/models/pipeline_leak_detection.pt`
- **File Size:** 5,468,691 bytes
- **SHA-256 Digest:** `8670e5cef00b77e891cc48ce60c16c46b1d59e220c8f49a68db7f399680838ba`
- **License:** MIT / Ultralytics AGPLv3
- **Base Architecture:** Custom YOLOv8/v11 Object Detection Network
- **Trained Classes:** `0: crack`, `1: gas`, `2: leak`, `3: no leak`, `4: water`

### 1.2 Evaluation & Municipal Adaptation
- **Host Execution:** Tested on Python 3.14 / PyTorch 2.10.0+cpu.
- **Cold Start Latency:** ~1,850 ms; **Warm Inference Latency:** ~190–380 ms.
- **Observed Precision & Recall:** Tested against industrial flange and pipe segments with visible liquid jets and puddles. The model reliably isolates visible liquid streams and pipe rupture apertures (`conf >= 0.25`).
- **Municipal Adaptation Caveat:** The model was originally trained on industrial infrastructure. In civic street scenarios (e.g. municipal water supply mains running along road margins), puddles caused by rainwater runoff, car washes, or drainage ditches may produce visual false positives.
- **Operational Guardrail:** Advisory only. Model output generates:
  *“Possible visible water leak; source and flow are not confirmed. Please confirm.”*
  Zero automated dispatch or contractor assignment occurs without Gram Panchayat / Ward Water Supply engineer inspection.

---

## 2. Candidate 2: Litter & Solid Waste Detection (TACO)

### 2.1 Repository & Dataset Audit
- **Source Repository:** [pedropro/TACO](https://github.com/pedropro/TACO) (Trash Annotations in Context)
- **Pinned Git Commit:** `40d17d5ce3909772bf2eb80b435ff20ddabfa356`
- **License:** CC BY 4.0 (Dataset) / MIT (Codebase)
- **Taxonomy:** 60 fine-grained waste classes grouped into 28 supercategories (bottles, wrappers, cans, cartons, plastics, hazardous waste).

### 2.2 Framework Incompatibility Audit
- **Legacy Framework Constraint:** The original TACO baseline detector utilizes Matterport Mask R-CNN implemented on **TensorFlow 1.x / Keras 2.x** and requires Python <= 3.7.
- **Host Environment Collision:** FixProof's backend environment runs Python 3.14 with modern PyTorch 2.x. TensorFlow 1.x cannot compile or run in this environment without risking severe dependency breakage and memory leaks.
- **Operational Decision & Fallback Gate:**
  1. Automated inference for `garbage_dump` / `litter` is designated as **Unsupported / Inactive**.
  2. All citizen solid waste submissions fall back to **standard manual triage** by ward health inspectors.
  3. **Zero fabricated or mock detections** are emitted.
  4. Future Enhancement Path: When a GPU training cluster is provisioned, the TACO COCO-format annotations will be used to fine-tune a modern YOLOv8-Waste model.

---

## 3. Candidate 3: Duplicate Matching & Copied-Image Detection

### 3.1 SSCD (Self-Supervised Descriptor for Copy Detection) Evaluation
- **Algorithm Purpose:** Meta's SSCD framework is designed for copyright and copy detection across heavily transformed images (rotations, watermarks, heavy crops).
- **Audit Findings:** Full SSCD ViT/ResNet models require ~150–400 MB weights, PyTorch TorchScript/ONNX dependencies, and significant GPU memory for vector search index maintenance. For edge civic deployments, this introduces prohibitive compute overhead.

### 3.2 Implemented Multi-Signal Duplicate Engine
To achieve reliable duplicate ranking without auto-merge hazards, FixProof implements a four-tiered multi-signal engine (`services/workers/adapters/duplicate/similarity.py`):

1. **Exact Re-Upload Detection (SHA-256):**
   - Catches identical photo files submitted multiple times or reused across complaints.
   - Exact hash match assigns `visual_score = 1.0` and flags immediate copy detection.
2. **Perceptual Image Similarity (dHash 64-bit):**
   - Difference Hash converts images to 64-bit binary gradients.
   - Robust against JPEG recompression, smartphone orientation changes, and thumbnail downscaling.
   - Hamming distance scaled from 0.0 to 1.0.
3. **Geographic Proximity (Haversine PostGIS Distance):**
   - Calculates great-circle distance between submission GPS coordinates and existing issues.
   - Scaled linearly over configurable search radius (default 300 meters).
4. **Textual Token Overlap (Jaccard Similarity):**
   - Tokenizes citizen complaints and matches keywords (e.g., "pothole", "main road", "bus stop").
5. **Transparent Composite Explanation:**
   - Composite Score: `0.4 * spatial + 0.3 * text + 0.3 * visual`.
   - Explains *why* a candidate is suggested (e.g., *"Matching category · 15m away · 100% visual image similarity · 42% description overlap"*).
   - **Never Auto-Merges:** The human reviewer or reporting citizen must click "Link to Issue" or "Keep Separate".

---

## 4. Candidate 4: Multimodal Large Language Models (Qwen-VL / VLM)

### 4.1 Evaluation of Vision-Language Models for Civic Triage
- **Candidate Architectures:** Qwen2-VL-7B-Instruct, Moondream2.
- **Evaluation Criteria:** Automated scene description, Kannada-to-English visual translation, and dispute verification.
- **Hardware & Privacy Audit:**
  - **Memory Footprint:** Qwen2-VL-7B requires >= 16 GB VRAM on GPU or >= 32 GB RAM on CPU with 15–30 second inference latency.
  - **Privacy:** Civic reporting photographs contain citizen bystanders, vehicle registration number plates, and residential house numbers. Sending unredacted media to external cloud LLM APIs violates municipal data protection standards.
- **Decision:** VLM deployment is **deferred** on local edge nodes. Monocular lightweight YOLO models and transparent algorithmic similarity remain the primary local engines.

---

## 5. Summary of Model Registry & Readiness State

| Task / Domain | Model ID | Status | Checkpoint SHA-256 | Action on Input |
|---|---|---|---|---|
| **Road Damage** | `oracl4-rdd-yolov8s` | **Active / Real** | `7f2ceb8f6f3d...` | PyTorch YOLOv8 forward pass (advisory) |
| **Water Leak** | `msunusi-pipeline-leak-yolo` | **Active / Real** | `8670e5cef00b...` | PyTorch YOLO forward pass (advisory) |
| **Litter / Waste** | `taco-litter-dataset-eval` | **Fallback / Manual** | Evaluated (CC BY 4.0) | Routed to manual health inspector triage |
| **Exact Copy Photo** | `sha256-exact-match` | **Active / Real** | Native Hash | Flags identical asset re-upload |
| **Visual Duplicate** | `dhash-64bit-perceptual` | **Active / Real** | Perceptual 64-bit | Advisory candidate score for human review |
| **VLM Scene Desc.** | `qwen-vl-eval` | **Deferred** | Evaluated | Deferred due to edge hardware constraints |

---

## 6. Acceptance Verification

1. **No Auto-Merge:** Confirmed via code inspection and automated test cases. Duplicate candidates require explicit staff or citizen action.
2. **Zero Mock Predictions:** Every active model executes verified checkpoints (`.pt`) with real PyTorch tensors.
3. **Auditable Fallbacks:** Any unsupported category or failed inference produces clear logs and falls back to standard human workflow without system interruption.
