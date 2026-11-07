"""C2: Pydantic schemas for HR shift / leave / holiday payloads (HH:MM validated)."""
from __future__ import annotations

import re
from typing import Annotated, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _require_hhmm(value: str) -> str:
    text = str(value or "").strip()
    if not _HHMM.match(text):
        raise ValueError("must be HH:MM (00:00–23:59)")
    return text


HhMm = Annotated[str, Field(description="HH:MM 24-hour clock")]


class BreakWindow(BaseModel):
    start: HhMm
    end: HhMm

    @field_validator("start", "end", mode="before")
    @classmethod
    def validate_hhmm(cls, v: object) -> str:
        return _require_hhmm(str(v))


class WorkShiftBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    startTime: HhMm = "09:00"
    endTime: HhMm = "18:00"
    graceMinutes: int = Field(default=15, ge=0, le=480)
    roundingMinutes: int = Field(default=0, ge=0, le=60)
    breakMinutes: int = Field(default=0, ge=0, le=480)
    breakWindows: list[BreakWindow] = Field(default_factory=list)
    otThresholdMinutes: int = Field(default=0, ge=0, le=480)
    isCrossMidnight: bool = False
    isDefault: bool = False

    @field_validator("startTime", "endTime", mode="before")
    @classmethod
    def validate_shift_hhmm(cls, v: object) -> str:
        return _require_hhmm(str(v) if v is not None else "")

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: object) -> str:
        text = str(v or "").strip()
        if not text:
            raise ValueError("Shift name is required")
        return text


class WorkShiftCreate(WorkShiftBase):
    pass


class WorkShiftUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    startTime: Optional[HhMm] = None
    endTime: Optional[HhMm] = None
    graceMinutes: Optional[int] = Field(default=None, ge=0, le=480)
    roundingMinutes: Optional[int] = Field(default=None, ge=0, le=60)
    breakMinutes: Optional[int] = Field(default=None, ge=0, le=480)
    breakWindows: Optional[list[BreakWindow]] = None
    otThresholdMinutes: Optional[int] = Field(default=None, ge=0, le=480)
    isCrossMidnight: Optional[bool] = None
    isDefault: Optional[bool] = None

    @field_validator("startTime", "endTime", mode="before")
    @classmethod
    def validate_optional_hhmm(cls, v: object) -> object:
        if v is None:
            return v
        return _require_hhmm(str(v))

    @field_validator("name", mode="before")
    @classmethod
    def strip_optional_name(cls, v: object) -> object:
        if v is None:
            return v
        text = str(v).strip()
        if not text:
            raise ValueError("Shift name is required")
        return text


class WorkShiftResponse(WorkShiftBase):
    shiftId: UUID
    companyId: UUID
    createdAt: Optional[object] = None

    class Config:
        from_attributes = True


class AssignShiftBody(BaseModel):
    shiftId: Optional[UUID] = None
    departmentId: Optional[UUID] = None
    company_employeeId: Optional[UUID] = None


class CompanyHolidayCreate(BaseModel):
    holidayDate: str = Field(description="YYYY-MM-DD")
    name: str = Field(min_length=1, max_length=150)

    @field_validator("name", mode="before")
    @classmethod
    def strip_holiday_name(cls, v: object) -> str:
        text = str(v or "").strip()
        if not text:
            raise ValueError("name is required")
        return text


class LeaveRequestCreate(BaseModel):
    company_employeeId: UUID
    startDate: str
    endDate: str
    leaveType: str = "ANNUAL"
    reason: str = ""
    autoApprove: bool = False


class LeaveApprovalBody(BaseModel):
    approve: Optional[bool] = True
    status: Optional[object] = None
    rejectReason: Optional[str] = None
