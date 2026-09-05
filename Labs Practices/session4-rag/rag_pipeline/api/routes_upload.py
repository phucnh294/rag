"""POST /upload — accept a .md file, save it, and index it.

Task (see rag-structure.md > api/): accept multipart file, write it into
input/ (see shared/file_utils.py), call indexing.index_runner, return
{"chunks_indexed": N}.
"""

from __future__ import annotations

from pathlib import Path

import psycopg2
import requests
from fastapi import APIRouter, Form, HTTPException, UploadFile

from config.env_config import load_config_martin
from indexing.index_runner import run_indexing_martin
from shared.file_utils import save_upload_martin

router = APIRouter()

_INPUT_DIR = Path(__file__).parent.parent / "input"


@router.post("/upload")
async def upload_martin(
    file: UploadFile, status: str | None = Form(None), area: str | None = Form(None)
) -> dict[str, int]:
    """Save the uploaded .md into input/ and index it. Return chunks_indexed.

    `status`/`area` optionally tag the document, overriding anything its
    own frontmatter declares — see indexing/index_runner.py.
    """
    content = await file.read()
    saved_path = save_upload_martin(_INPUT_DIR, file.filename or "upload.md", content)

    config = load_config_martin()
    try:
        chunks_indexed = run_indexing_martin(config, saved_path, status=status, area=area)
    except requests.exceptions.Timeout as err:
        raise HTTPException(status_code=504, detail=f"Embedding request timed out: {err}") from err
    except requests.exceptions.RequestException as err:
        raise HTTPException(status_code=502, detail=f"Embedding request failed: {err}") from err
    except psycopg2.Error as err:
        raise HTTPException(status_code=502, detail=f"Database error: {err}") from err
    return {"chunks_indexed": chunks_indexed}
