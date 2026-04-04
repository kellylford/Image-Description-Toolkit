"""
Face Database — SQLite-based storage for face embeddings.

Stores face embeddings alongside workspace-level person data so that
facenet-pytorch embeddings persist between sessions without re-processing
every image each run.

The DB lives at ``<workspace_dir>/.idt_faces.db`` alongside the
``.idtworkspace`` JSON file.

Schema
------
- ``faces``  : one row per face detected in an image
- ``clusters``: pre-computed DBSCAN cluster assignments

Usage
-----
    from face_db import FaceDatabase
    db = FaceDatabase(workspace_dir)
    db.upsert_face(filename, face_index, embedding, bbox)
    faces = db.get_faces_for_image(filename)
    db.save_cluster_assignments(assignments)
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DB_FILENAME = ".idt_faces.db"

# Embedding dimension for InceptionResnetV1 (facenet-pytorch default)
_EMBEDDING_DIM = 512

_DDL = """
CREATE TABLE IF NOT EXISTS faces (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filename        TEXT    NOT NULL,
    face_index      INTEGER NOT NULL DEFAULT 0,  -- 0-based index when multiple faces in image
    embedding       TEXT    NOT NULL,            -- JSON list of 512 floats
    bbox_x1         REAL,
    bbox_y1         REAL,
    bbox_x2         REAL,
    bbox_y2         REAL,
    confidence      REAL    DEFAULT 1.0,
    person_id       TEXT,                        -- PersonRecord.id if resolved
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (filename, face_index)
);

CREATE TABLE IF NOT EXISTS clusters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    face_id         INTEGER NOT NULL REFERENCES faces(id) ON DELETE CASCADE,
    cluster_label   INTEGER NOT NULL,            -- DBSCAN label; -1 = noise
    method          TEXT    NOT NULL DEFAULT 'cv',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_faces_filename ON faces(filename);
CREATE INDEX IF NOT EXISTS idx_faces_person   ON faces(person_id);
CREATE INDEX IF NOT EXISTS idx_clusters_label ON clusters(cluster_label);
"""


class FaceDatabase:
    """Thread-safe(ish) wrapper around the face embeddings SQLite DB."""

    def __init__(self, workspace_dir: Path):
        self.db_path = Path(workspace_dir) / _DB_FILENAME
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=10,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
        return self._conn

    def _ensure_schema(self) -> None:
        try:
            conn = self._connect()
            conn.executescript(_DDL)
            conn.commit()
        except sqlite3.Error as exc:
            logger.error("FaceDatabase schema init failed: %s", exc)
            raise

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # Face CRUD
    # ------------------------------------------------------------------

    def upsert_face(
        self,
        filename: str,
        face_index: int,
        embedding: List[float],
        bbox: Optional[Tuple[float, float, float, float]] = None,
        confidence: float = 1.0,
    ) -> int:
        """Insert or replace a face embedding. Returns the row id."""
        if len(embedding) != _EMBEDDING_DIM:
            raise ValueError(
                f"Expected {_EMBEDDING_DIM}-dim embedding, got {len(embedding)}"
            )
        bbox = bbox or (None, None, None, None)
        conn = self._connect()
        cursor = conn.execute(
            """
            INSERT INTO faces (filename, face_index, embedding,
                               bbox_x1, bbox_y1, bbox_x2, bbox_y2, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filename, face_index) DO UPDATE SET
                embedding  = excluded.embedding,
                bbox_x1    = excluded.bbox_x1,
                bbox_y1    = excluded.bbox_y1,
                bbox_x2    = excluded.bbox_x2,
                bbox_y2    = excluded.bbox_y2,
                confidence = excluded.confidence
            """,
            (
                filename, face_index,
                json.dumps(embedding),
                bbox[0], bbox[1], bbox[2], bbox[3],
                confidence,
            ),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_faces_for_image(self, filename: str) -> List[dict]:
        """Return all face rows for a given image filename."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM faces WHERE filename = ? ORDER BY face_index",
            (filename,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_faces(self) -> List[dict]:
        """Return all face rows, sorted by filename then face_index."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM faces ORDER BY filename, face_index"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_embedding(self, face_id: int) -> Optional[List[float]]:
        """Return the embedding list for a face row id, or None."""
        conn = self._connect()
        row = conn.execute(
            "SELECT embedding FROM faces WHERE id = ?", (face_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["embedding"])

    def set_person_id(self, face_id: int, person_id: Optional[str]) -> None:
        """Assign (or clear) a PersonRecord.id for a detected face."""
        conn = self._connect()
        conn.execute(
            "UPDATE faces SET person_id = ? WHERE id = ?",
            (person_id, face_id),
        )
        conn.commit()

    def get_faces_for_person(self, person_id: str) -> List[dict]:
        """Return all faces that have been resolved to a given PersonRecord.id."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM faces WHERE person_id = ? ORDER BY filename",
            (person_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_faces_for_image(self, filename: str) -> int:
        """Remove all face rows for *filename*. Returns deleted count."""
        conn = self._connect()
        cursor = conn.execute(
            "DELETE FROM faces WHERE filename = ?", (filename,)
        )
        conn.commit()
        return cursor.rowcount

    def face_count(self) -> int:
        """Total number of stored faces."""
        conn = self._connect()
        row = conn.execute("SELECT COUNT(*) FROM faces").fetchone()
        return row[0] if row else 0

    def image_count(self) -> int:
        """Number of distinct images with stored faces."""
        conn = self._connect()
        row = conn.execute(
            "SELECT COUNT(DISTINCT filename) FROM faces"
        ).fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------
    # Cluster storage
    # ------------------------------------------------------------------

    def save_cluster_assignments(
        self,
        assignments: Dict[int, int],
        method: str = "cv",
    ) -> None:
        """Persist DBSCAN cluster labels for face row ids.

        Args:
            assignments: ``{face_id: cluster_label}``; label -1 = noise.
            method: Clustering method tag stored in DB.
        """
        conn = self._connect()
        conn.execute(
            "DELETE FROM clusters WHERE method = ?", (method,)
        )
        conn.executemany(
            "INSERT INTO clusters (face_id, cluster_label, method) VALUES (?, ?, ?)",
            [(fid, label, method) for fid, label in assignments.items()],
        )
        conn.commit()

    def get_cluster_assignments(
        self, method: str = "cv"
    ) -> Dict[int, int]:
        """Load previously saved cluster assignments.

        Returns ``{face_id: cluster_label}``.
        """
        conn = self._connect()
        rows = conn.execute(
            "SELECT face_id, cluster_label FROM clusters WHERE method = ?",
            (method,),
        ).fetchall()
        return {r["face_id"]: r["cluster_label"] for r in rows}

    def get_cluster_images(
        self, cluster_label: int, method: str = "cv"
    ) -> List[str]:
        """Return distinct filenames belonging to a given cluster."""
        conn = self._connect()
        rows = conn.execute(
            """
            SELECT DISTINCT f.filename
            FROM faces f
            JOIN clusters c ON c.face_id = f.id
            WHERE c.cluster_label = ? AND c.method = ?
            ORDER BY f.filename
            """,
            (cluster_label, method),
        ).fetchall()
        return [r["filename"] for r in rows]

    def get_distinct_cluster_labels(self, method: str = "cv") -> List[int]:
        """Return all distinct cluster labels (excluding noise = -1)."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT DISTINCT cluster_label FROM clusters WHERE method = ? AND cluster_label != -1",
            (method,),
        ).fetchall()
        return sorted(r["cluster_label"] for r in rows)
