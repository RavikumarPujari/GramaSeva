import os
import hashlib
from typing import Dict, Any, Optional, Union
from PIL import Image
from io import BytesIO

from workers.adapters.duplicate.similarity import compute_dhash, compute_visual_similarity

class EvidenceAssistanceAdapter:
    """
    Advisory Before/After Evidence Assistance Engine (README Section 7.8).
    Analyzes citizen pre-repair evidence vs worker post-repair proof.
    Strict Rule: AI cannot approve repair or determine safety.
    """

    def analyze_evidence_pair(
        self,
        before_image: Union[str, bytes, Image.Image],
        after_image: Union[str, bytes, Image.Image],
        before_hash: Optional[str] = None,
        after_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compares before/after photographic proof and returns structured guidance.
        """
        # 1. Exact identical photo check (Fraud prevention: worker re-uploading citizen photo)
        if before_hash and after_hash and before_hash == after_hash:
            return {
                "visible_change": False,
                "possible_mismatch": False,
                "insufficient_evidence": True,
                "confidence": 1.0,
                "difference_summary": "Identical photo detected: The uploaded after-photo is identical to the original citizen before-photo. Fresh on-site proof is required.",
                "requires_independent_human_review": True,
                "advisory_decision_suggestion": "REQUEST_EVIDENCE",
            }

        # 2. Perceptual hashing (dHash)
        h_before = compute_dhash(before_image)
        h_after = compute_dhash(after_image)
        similarity = compute_visual_similarity(h_before, h_after)

        # 3. Structural difference analysis
        # - High similarity (> 0.95): minimal visual change between before and after
        # - Moderate similarity (0.60 - 0.90): consistent scene context with physical repair modifications (e.g. patched pothole, repaired pipe)
        # - Low similarity (< 0.50): possible camera angle change or mismatch
        if similarity >= 0.95:
            visible_change = False
            possible_mismatch = False
            insufficient_evidence = True
            summary = "Negligible visual difference detected between before and after photos. Physical repair change is unclear."
            advisory = "REQUEST_EVIDENCE"
        elif 0.55 <= similarity < 0.95:
            visible_change = True
            possible_mismatch = False
            insufficient_evidence = False
            summary = f"Noticeable physical surface change detected in matching scene context (visual consistency: {int(similarity * 100)}%)."
            advisory = "REVIEW_FOR_APPROVAL"
        else:
            visible_change = True
            possible_mismatch = True
            insufficient_evidence = False
            summary = f"Significant viewpoint or scene variation detected (visual consistency: {int(similarity * 100)}%). Verify that both photos represent the same physical asset location."
            advisory = "CHECK_LOCATION_MATCH"

        return {
            "visible_change": visible_change,
            "possible_mismatch": possible_mismatch,
            "insufficient_evidence": insufficient_evidence,
            "visual_consistency_score": similarity,
            "difference_summary": summary,
            "requires_independent_human_review": True,
            "advisory_decision_suggestion": advisory,
            "governance_notice": "AI is advisory only. Authorized Panchayat reviewer must independently verify repairs before closure.",
        }

evidence_assistance_adapter = EvidenceAssistanceAdapter()
