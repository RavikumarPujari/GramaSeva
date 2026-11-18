import math
import hashlib
from io import BytesIO
from typing import Dict, Any, Optional, Union, List, Tuple
from PIL import Image

def compute_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic coordinates in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

def compute_spatial_score(distance_meters: float, max_radius: float = 300.0) -> float:
    """Scales distance between 0m (1.0) and max_radius (0.0)."""
    if distance_meters <= 0:
        return 1.0
    if distance_meters >= max_radius:
        return 0.0
    return round(1.0 - (distance_meters / max_radius), 3)

def compute_text_similarity(text1: Optional[str], text2: Optional[str]) -> float:
    """Calculates Jaccard token overlap similarity between two complaint descriptions."""
    if not text1 or not text2:
        return 0.0
    
    tokens1 = set(text1.lower().split())
    tokens2 = set(text2.lower().split())
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return round(len(intersection) / len(union), 3)

def compute_dhash(image_input: Union[str, bytes, Image.Image], hash_size: int = 8) -> str:
    """
    Computes 64-bit Difference Hash (dHash) for visual similarity.
    Robust against image recompression, resizing, and slight lighting variations.
    """
    try:
        if isinstance(image_input, bytes):
            img = Image.open(BytesIO(image_input))
        elif isinstance(image_input, str):
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            return ""

        # Convert to grayscale and resize to (hash_size + 1, hash_size)
        resized = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.tobytes())
        
        # Compare adjacent pixels
        diff = []
        for row in range(hash_size):
            for col in range(hash_size):
                idx = row * (hash_size + 1) + col
                diff.append(pixels[idx] > pixels[idx + 1])
        
        # Convert boolean array to hex string
        decimal_val = 0
        hex_string = []
        for index, value in enumerate(diff):
            if value:
                decimal_val += 2 ** (index % 4)
            if index % 4 == 3:
                hex_string.append(hex(decimal_val)[2:])
                decimal_val = 0
        return "".join(hex_string)
    except Exception:
        return ""

def compute_visual_similarity(hash1: Optional[str], hash2: Optional[str], is_exact_sha_match: bool = False) -> float:
    """
    Computes visual similarity between two image hashes.
    Exact SHA-256 copy match returns 1.0 (Copied photo detection).
    dHash hamming distance returns scaled similarity score (0.0 to 1.0).
    """
    if is_exact_sha_match:
        return 1.0
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 0.0
    
    # Hamming distance
    hamming_dist = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
    max_dist = len(hash1)
    similarity = max(0.0, 1.0 - (hamming_dist / max_dist))
    return round(similarity, 3)

def rank_duplicate_candidate(
    sub_lat: Optional[float],
    sub_lon: Optional[float],
    sub_desc: Optional[str],
    sub_hash: Optional[str],
    issue_lat: Optional[float],
    issue_lon: Optional[float],
    issue_desc: Optional[str],
    issue_hash: Optional[str],
    category_match: bool,
    max_radius: float = 300.0,
) -> Dict[str, Any]:
    """
    Combines Spatial, Textual, and Visual signals into a transparent ranking score.
    Never auto-merges: Explains why candidate is suggested for human confirmation.
    """
    distance_meters = 0.0
    spatial_score = 0.5  # Neutral default if GPS absent
    if sub_lat and sub_lon and issue_lat and issue_lon:
        distance_meters = compute_haversine_distance(sub_lat, sub_lon, issue_lat, issue_lon)
        spatial_score = compute_spatial_score(distance_meters, max_radius=max_radius)

    text_score = compute_text_similarity(sub_desc, issue_desc)
    
    visual_score = 0.0
    if sub_hash and issue_hash:
        visual_score = compute_visual_similarity(sub_hash, issue_hash)

    # Weighted composite score
    weights = [0.4, 0.3, 0.3]
    composite_score = round(
        (spatial_score * weights[0]) + (text_score * weights[1]) + (visual_score * weights[2]), 2
    )

    # Human-readable explanation
    reasons = []
    if category_match:
        reasons.append("Matching category")
    if distance_meters > 0:
        reasons.append(f"{int(distance_meters)}m away")
    if visual_score >= 0.7:
        reasons.append(f"{int(visual_score * 100)}% visual image similarity")
    if text_score >= 0.3:
        reasons.append(f"{int(text_score * 100)}% description overlap")

    explanation = " · ".join(reasons) if reasons else "Nearby locality suggestion"

    return {
        "distance_meters": distance_meters,
        "spatial_score": spatial_score,
        "text_score": text_score,
        "visual_score": visual_score,
        "composite_score": composite_score,
        "explanation": explanation,
        "is_strong_candidate": composite_score >= 0.55,
    }
