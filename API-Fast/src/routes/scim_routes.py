"""SCIM 2.0 Provisioning endpoints (/scim/v2/company/{companyId}/Users)."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..security.deps import assert_request_company_access
from ..services import scim_service

router = APIRouter()


@router.get("/v2/company/{companyId}/ServiceProviderConfig")
async def scim_service_provider_config(
    companyId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return scim_service.service_provider_config()


@router.get("/v2/company/{companyId}/Users")
async def scim_list_users(
    companyId: UUID,
    request: Request,
    startIndex: int = Query(1, ge=1),
    count: int = Query(50, ge=1, le=200),
    filter: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await scim_service.list_scim_users(
        db, companyId, start_index=startIndex, count=count, filter_str=filter
    )


@router.post("/v2/company/{companyId}/Users", status_code=status.HTTP_201_CREATED)
async def scim_create_user(
    companyId: UUID,
    body: dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await scim_service.create_scim_user(db, companyId, body)


@router.get("/v2/company/{companyId}/Users/{memberId}")
async def scim_get_user(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await scim_service.get_scim_user(db, companyId, memberId)


@router.patch("/v2/company/{companyId}/Users/{memberId}")
async def scim_patch_user(
    companyId: UUID,
    memberId: UUID,
    body: dict[str, Any],
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    return await scim_service.patch_scim_user(db, companyId, memberId, body)


@router.delete("/v2/company/{companyId}/Users/{memberId}", status_code=status.HTTP_204_NO_CONTENT)
async def scim_delete_user(
    companyId: UUID,
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await assert_request_company_access(request, db, companyId)
    await scim_service.delete_scim_user(db, companyId, memberId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
