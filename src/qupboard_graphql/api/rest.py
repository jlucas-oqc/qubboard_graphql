from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from starlette.responses import Response

from qupboard_graphql.db.mapper import hardware_model_from_orm, hardware_model_to_orm
from qupboard_graphql.db.models import HardwareModelORM
from qupboard_graphql.db.session import get_db
from qupboard_graphql.schemas.hardware_model import HardwareModel


rest_router = APIRouter(tags=["Hardware Models"])


@rest_router.get("/healthcheck", tags=["Health"], summary="Health check")
async def healthcheck() -> Response:
    """Return a simple OK response to confirm the service is running."""
    return Response("OK")


@rest_router.get(
    "/logical-hardware",
    summary="List all hardware model IDs",
    response_description="A list of UUIDs for every stored hardware model",
)
async def get_all_logical_hardware_ids(
    db: Session = Depends(get_db),
) -> list[UUID]:
    """Return the UUIDs of all hardware models currently stored in the database."""
    return HardwareModelORM.get_all_pks(db)


@rest_router.get(
    "/logical-hardware/{uuid}",
    summary="Get a hardware model by ID",
    response_description="The hardware model matching the given UUID",
    responses={404: {"description": "Hardware model not found"}},
)
async def get_logical_hardware(
    uuid: UUID,
    db: Session = Depends(get_db),
) -> HardwareModel:
    """Retrieve a single hardware model by its UUID.

    Returns a 404 if no hardware model with the given UUID exists.
    """
    orm_obj = HardwareModelORM.get_by_uuid(db, uuid)
    if orm_obj is None:
        raise HTTPException(status_code=404, detail=f"HardwareModel {uuid} not found")
    return hardware_model_from_orm(orm_obj)


@rest_router.post(
    "/logical-hardware",
    status_code=201,
    summary="Create a hardware model",
    response_description="The UUID assigned to the newly created hardware model",
    responses={
        415: {"description": "Unsupported file type — only application/json is accepted"},
        422: {"description": "File content could not be parsed as a valid hardware model"},
    },
)
async def create_logical_hardware(
    model: HardwareModel,
    db: Session = Depends(get_db),
) -> UUID:
    """Persist a new hardware model supplied as a JSON body.

    Returns the UUID assigned to the created record.
    Raises a 415 if the file's content type is not `application/json` or `text/plain`.
    Raises a 422 if the file content cannot be parsed as a valid `HardwareModel`.
    """
    orm_obj = hardware_model_to_orm(model)
    db.add(orm_obj)
    db.commit()
    return orm_obj.id


@rest_router.post(
    "/logical-hardware/upload",
    status_code=201,
    summary="Upload a hardware model from a file",
    response_description="The UUID assigned to the newly created hardware model",
    responses={
        415: {"description": "Unsupported file type — only application/json is accepted"},
        422: {"description": "File content could not be parsed as a valid hardware model"},
    },
)
async def upload_logical_hardware(
    file: UploadFile,
    db: Session = Depends(get_db),
) -> UUID:
    """Upload a JSON file containing a hardware model and persist it.

    - **file**: A JSON file whose content conforms to the `HardwareModel` schema.

    Returns the UUID assigned to the created record.
    Raises a 415 if the file's content type is not `application/json` or `text/plain`.
    Raises a 422 if the file content cannot be parsed as a valid `HardwareModel`.
    """
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
