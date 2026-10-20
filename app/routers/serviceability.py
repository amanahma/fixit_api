from fastapi import APIRouter, Path

from app.deps import DbSession, PincodeSvc
from app.schemas import ServiceabilityRead

router = APIRouter(tags=["serviceability"])


@router.get("/serviceability/{pincode}", response_model=ServiceabilityRead)
async def check_serviceability(
    session: DbSession,
    pincodes: PincodeSvc,
    pincode: str = Path(pattern=r"^\d{6}$"),
) -> ServiceabilityRead:
    districts, serviceable, matched = await pincodes.serviceability(session, pincode)
    return ServiceabilityRead(
        pincode=pincode,
        districts=districts,
        serviceable=serviceable,
        matched_district=matched,
    )
