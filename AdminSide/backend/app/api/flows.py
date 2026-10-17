import mimetypes
import re
import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import CurrentTenant, CurrentUser, DbSession
from app.api.errors import service_errors
from app.schemas.flow import (
    FlowCreate, FlowListResponse, FlowResponse, FlowUpdate, FlowUploadResponse,
)
from app.services import flow_service
from app.services.flow_service import FlowNotFoundError
from app.storage import StorageError, get_storage

router = APIRouter(prefix="/flows", tags=["Flows"])
ERRORS = {FlowNotFoundError: status.HTTP_404_NOT_FOUND}

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_EXT = re.compile(r"[^a-z0-9]")


@router.get("", response_model=FlowListResponse)
def list_flows(tenant: CurrentTenant, db: DbSession, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), search: str | None = None):
    items, total = flow_service.list_flows(db, tenant.id, skip, limit, (search or "").strip() or None)
    return {"items": items, "total": total}


@router.post("", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
def create_flow(data: FlowCreate, user: CurrentUser, tenant: CurrentTenant, db: DbSession):
    return flow_service.create_flow(db, tenant.id, user, data)


@router.post("/upload", response_model=FlowUploadResponse)
async def upload_asset(tenant: CurrentTenant, file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than 25 MB.")
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")
    raw_name = file.filename or "file"
    dot = raw_name.rsplit(".", 1)
    ext = _EXT.sub("", dot[1].lower())[:8] if len(dot) == 2 else ""
    content_type = file.content_type or mimetypes.guess_type(raw_name)[0] or "application/octet-stream"
    key = f"flow-assets/{tenant.id.hex}/{uuid.uuid4().hex}{('.' + ext) if ext else ''}"
    try:
        get_storage().save(key, content, content_type)
    except StorageError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"key": key, "url": f"/api/flows/assets/{key}", "filename": raw_name[:255], "content_type": content_type, "size": len(content)}


@router.get("/assets/{asset_key:path}", response_class=StreamingResponse)
def serve_asset(asset_key: str, tenant: CurrentTenant):
    # Keys embed the tenant id; refuse anything outside this tenant's prefix.
    if not asset_key.startswith(f"flow-assets/{tenant.id.hex}/"):
        raise HTTPException(status_code=404, detail="Asset not found.")
    storage = get_storage()
    if not storage.exists(asset_key):
        raise HTTPException(status_code=404, detail="Asset not found.")
    content_type = mimetypes.guess_type(asset_key)[0] or "application/octet-stream"
    return StreamingResponse(
        storage.iter_chunks(asset_key),
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{flow_id}", response_model=FlowResponse)
def get_flow(flow_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return flow_service.get_flow(db, tenant.id, flow_id)


@router.patch("/{flow_id}", response_model=FlowResponse)
def update_flow(flow_id: uuid.UUID, data: FlowUpdate, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return flow_service.update_flow(db, tenant.id, flow_id, data)


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flow(flow_id: uuid.UUID, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        flow_service.delete_flow(db, tenant.id, flow_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{flow_id}/copy", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
def copy_flow(flow_id: uuid.UUID, user: CurrentUser, tenant: CurrentTenant, db: DbSession):
    with service_errors(ERRORS):
        return flow_service.copy_flow(db, tenant.id, flow_id, user)
