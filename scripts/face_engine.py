"""
Face Engine — optional face detection and recognition using facenet-pytorch.

This module is intentionally NOT imported at application startup.
All imports of torch/facenet_pytorch are deferred to function call time so
that the rest of IDT starts normally even when the CV engine is not installed.

Requires (install via ``install_persons_engine.py`` or manually):
    pip install facenet-pytorch
    # torch + torchvision are pulled in as dependencies

Public API
----------
    is_engine_available() -> bool
    scan_image(image_path) -> List[FaceResult]
    get_embeddings(image_path) -> List[List[float]]
    cluster_faces(face_db, eps=0.6, min_samples=2) -> Dict[int, int]
    build_person_groups_from_clusters(face_db, workspace) -> List[PersonGroup]

FaceResult
----------
    filename     str    — source image path
    face_index   int    — 0-based index in image
    embedding    List[float] (512-dim)
    bbox         Tuple[float, float, float, float]  (x1, y1, x2, y2)
    confidence   float  — MTCNN detection probability
"""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from face_db import FaceDatabase
    from data_models import ImageWorkspace, PersonGroup

# ---------------------------------------------------------------------------
# Import path resolution
# ---------------------------------------------------------------------------
_project_root = Path(__file__).parent.parent
for _path in (str(_project_root), str(_project_root / "imagedescriber")):
    if _path not in sys.path:
        sys.path.insert(0, _path)


def _ensure_face_packages_on_path() -> None:
    """In frozen mode, inject the face_engine_packages dir into sys.path.

    install_persons_engine.ensure_packages_on_path() does the same thing —
    this local version avoids a circular import by duplicating the one-liner.
    """
    if not getattr(sys, 'frozen', False):
        return
    pkg_dir = str(Path(sys.executable).parent / "face_engine_packages")
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)


@dataclass
class FaceResult:
    """A single detected face with its embedding."""
    filename: str
    face_index: int
    embedding: List[float] = field(default_factory=list)
    bbox: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def is_engine_available() -> bool:
    """Return True if facenet-pytorch (and torch) are installed and importable."""
    _ensure_face_packages_on_path()
    try:
        import torch  # noqa: F401
        from facenet_pytorch import MTCNN, InceptionResnetV1  # noqa: F401
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Lazy model holders (singleton per process)
# ---------------------------------------------------------------------------
_mtcnn = None
_resnet = None


def _get_models():
    """Load MTCNN + InceptionResnetV1 once and cache them."""
    global _mtcnn, _resnet
    if _mtcnn is not None and _resnet is not None:
        return _mtcnn, _resnet

    _ensure_face_packages_on_path()
    try:
        import torch
        from facenet_pytorch import MTCNN, InceptionResnetV1
    except ImportError as exc:
        raise RuntimeError(
            "facenet-pytorch not installed. "
            "Run Tools → Install Face Recognition Engine to install it."
        ) from exc

    device = "cuda" if _torch_cuda_available() else "cpu"
    logger.info("Loading face recognition models on device: %s", device)

    _mtcnn = MTCNN(
        image_size=160,
        margin=20,
        min_face_size=20,
        keep_all=True,           # detect all faces in image
        device=device,
        post_process=False,      # return raw pixel tensors
    )
    _resnet = InceptionResnetV1(pretrained="vggface2").eval().to(device)
    return _mtcnn, _resnet


def _torch_cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Core scanning
# ---------------------------------------------------------------------------

def scan_image(image_path: str) -> List[FaceResult]:
    """Detect faces in *image_path* and return their embeddings.

    Args:
        image_path: Absolute or relative path to a JPEG/PNG/HEIC image.

    Returns:
        List of FaceResult objects, one per detected face.
        Returns empty list if no faces detected or on error.
    """
    try:
        from PIL import Image as PILImage
    except ImportError as exc:
        raise RuntimeError("Pillow is required for face scanning") from exc

    mtcnn, resnet = _get_models()

    try:
        import torch
        img = PILImage.open(image_path).convert("RGB")
    except Exception as exc:
        logger.warning("Could not open image %s: %s", image_path, exc)
        return []

    try:
        # MTCNN returns (faces_tensor, probs, landmarks) when keep_all=True
        faces_tensor, probs, _ = mtcnn(img, return_prob=True)
    except Exception as exc:
        logger.warning("MTCNN detection error for %s: %s", image_path, exc)
        return []

    if faces_tensor is None:
        return []

    # faces_tensor shape: (N, 3, 160, 160) — already aligned face crops
    device = next(resnet.parameters()).device
    results: List[FaceResult] = []
    fname = Path(image_path).name

    import torch
    with torch.no_grad():
        for i, face_crop in enumerate(faces_tensor):
            face_crop = face_crop.unsqueeze(0).float().to(device)
            # Normalise to [-1, 1] as expected by InceptionResnetV1
            face_crop = (face_crop / 127.5) - 1.0
            embedding = resnet(face_crop).squeeze(0).cpu().tolist()

            prob = float(probs[i]) if probs is not None else 1.0
            # bbox from MTCNN requires a second detect pass with return_prob that
            # includes boxes; re-use boxes from a batched call if available.
            # For simplicity we leave bbox as zeros here — it gets filled below.
            results.append(FaceResult(
                filename=fname,
                face_index=i,
                embedding=embedding,
                confidence=prob,
            ))

    logger.debug("Scanned %s → %d face(s)", image_path, len(results))
    return results


def scan_image_with_boxes(image_path: str) -> List[FaceResult]:
    """Like scan_image() but also populates the bbox field."""
    try:
        from PIL import Image as PILImage
    except ImportError as exc:
        raise RuntimeError("Pillow is required for face scanning") from exc

    mtcnn, resnet = _get_models()

    try:
        import torch
        img = PILImage.open(image_path).convert("RGB")
    except Exception as exc:
        logger.warning("Could not open image %s: %s", image_path, exc)
        return []

    try:
        boxes, probs = mtcnn.detect(img)
    except Exception as exc:
        logger.warning("MTCNN detect() error for %s: %s", image_path, exc)
        return []

    if boxes is None:
        return []

    basename = Path(image_path).name
    results: List[FaceResult] = []
    device = next(resnet.parameters()).device

    import torch
    from facenet_pytorch.models.utils.detect_face import extract_face

    with torch.no_grad():
        for i, box in enumerate(boxes):
            prob = float(probs[i]) if probs is not None else 1.0
            bbox = tuple(float(v) for v in box)

            embedding: List[float] = []
            try:
                # extract_face returns a (3, 160, 160) float tensor in [0, 255]
                face_tensor = extract_face(img, box, image_size=160, margin=20)
                crop = face_tensor.unsqueeze(0).float().to(device)
                crop = (crop / 127.5) - 1.0
                embedding = resnet(crop).squeeze(0).cpu().tolist()
            except Exception as exc:
                logger.warning("Embedding extraction failed for face %d in %s: %s",
                               i, image_path, exc)

            results.append(FaceResult(
                filename=basename,
                face_index=i,
                embedding=embedding,
                bbox=bbox,
                confidence=prob,
            ))

    return results


def get_embeddings(image_path: str) -> List[List[float]]:
    """Convenience: return just embeddings (one per face) for *image_path*."""
    return [r.embedding for r in scan_image(image_path) if r.embedding]


# ---------------------------------------------------------------------------
# DBSCAN clustering
# ---------------------------------------------------------------------------

def cluster_faces(
    face_db: "FaceDatabase",
    eps: float = 0.6,
    min_samples: int = 2,
) -> Dict[int, int]:
    """Run DBSCAN clustering on all embeddings stored in *face_db*.

    Args:
        face_db: Opened FaceDatabase instance.
        eps: DBSCAN neighbourhood radius (cosine distance).
        min_samples: Minimum faces to form a cluster.

    Returns:
        ``{face_row_id: cluster_label}`` — label -1 = noise.
        Also persists assignments to the DB via ``face_db.save_cluster_assignments()``.

    Raises:
        RuntimeError: If scikit-learn is not installed.
    """
    try:
        from sklearn.cluster import DBSCAN
        from sklearn.preprocessing import normalize
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "scikit-learn and numpy are required for face clustering. "
            "Run: pip install scikit-learn numpy"
        ) from exc

    all_faces = face_db.get_all_faces()
    if len(all_faces) < 2:
        logger.info("cluster_faces: not enough faces to cluster (%d)", len(all_faces))
        return {}

    import json as _json
    import numpy as _np

    face_ids = [row["id"] for row in all_faces]
    embeddings = _np.array([_json.loads(row["embedding"]) for row in all_faces], dtype=_np.float32)

    # Normalise to unit sphere so L2 distance ≈ cosine distance
    embeddings = normalize(embeddings)

    db = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean", n_jobs=-1)
    labels = db.fit_predict(embeddings)

    assignments = {fid: int(lbl) for fid, lbl in zip(face_ids, labels)}

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())
    logger.info(
        "cluster_faces: %d clusters, %d noise points from %d faces",
        n_clusters, n_noise, len(all_faces),
    )

    face_db.save_cluster_assignments(assignments, method="cv")
    return assignments


# ---------------------------------------------------------------------------
# Convert clusters → PersonGroup objects
# ---------------------------------------------------------------------------

def build_person_groups_from_clusters(
    face_db: "FaceDatabase",
    workspace: "ImageWorkspace",
) -> List["PersonGroup"]:
    """Convert DBSCAN cluster assignments stored in *face_db* into PersonGroup objects.

    Existing 'cv' PersonGroups in *workspace* are replaced.

    Args:
        face_db: FaceDatabase with clusters already computed.
        workspace: ImageWorkspace to update.

    Returns:
        List of new PersonGroup objects (not yet added to workspace.person_groups —
        caller decides whether to add/merge/display first).
    """
    from data_models import PersonGroup  # local import avoids circular at module load

    labels = face_db.get_distinct_cluster_labels(method="cv")
    groups: List[PersonGroup] = []

    for label in labels:
        images = face_db.get_cluster_images(label, method="cv")
        if len(images) < 2:
            continue
        group = PersonGroup(
            display_label=f"Face cluster {label}",
            description_summary="",
            method="cv",
        )
        group.images = images
        groups.append(group)

    groups.sort(key=lambda g: len(g.images), reverse=True)
    return groups
