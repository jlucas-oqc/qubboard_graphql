from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.responses import Response

from qupboard_graphql.db.mapper import hardware_model_from_orm, hardware_model_to_orm
from qupboard_graphql.db.models import HardwareModelORM
from qupboard_graphql.db.session import get_db
from qupboard_graphql.schemas.hardware_model import HardwareModel


rest_router = APIRouter()


@rest_router.get("/healthcheck")
async def healthcheck() -> Response:
    return Response("OK")


@rest_router.get("/logical-hardware/{uuid}")
async def get_logical_hardware(
    uuid: UUID,
    db: Session = Depends(get_db),
) -> HardwareModel:
    orm_obj = HardwareModelORM.get_by_uuid(db, uuid)
    if orm_obj is None:
        raise HTTPException(status_code=404, detail=f"HardwareModel {uuid} not found")
    return hardware_model_from_orm(orm_obj)


@rest_router.post("/logical-hardware", status_code=201)
async def create_logical_hardware(
    model: HardwareModel,
    db: Session = Depends(get_db),
) -> UUID:
    orm_obj = hardware_model_to_orm(model)
    db.add(orm_obj)
    db.commit()
    return orm_obj.id


@rest_router.post("/logical-hardware/upload", status_code=201)
async def upload_logical_hardware(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> UUID:
    """Upload a JSON file containing a HardwareModel and persist it, returning its UUID."""
    if file.content_type not in ("application/json", "text/plain"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Expected application/json.",
        )
    raw = await file.read()
    try:
        model = HardwareModel.model_validate_json(raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid hardware model file: {exc}") from exc
    orm_obj = hardware_model_to_orm(model)
    db.add(orm_obj)
    db.commit()
    return orm_obj.id
