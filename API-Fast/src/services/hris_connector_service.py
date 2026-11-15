"""Native HRIS & Payroll Connector formatters (SAP, Workday, PEAK, FlowAccount)."""

from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import HTTPException, status

SUPPORTED_CONNECTORS = {"SAP_CSV", "WORKDAY_JSON", "PEAK_CSV", "FLOWACCOUNT_CSV"}


def _build_csv(headers: list[str], rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return buf.getvalue()


def format_payroll_for_connector(summary: dict[str, Any], connector: str) -> dict[str, Any]:
    """Format a `build_payroll_summary` payload for an Enterprise HRIS / Payroll connector."""
    conn_key = (connector or "").strip().upper()
    if conn_key not in SUPPORTED_CONNECTORS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported HRIS connector '{connector}'. Supported: {', '.join(sorted(SUPPORTED_CONNECTORS))}",
        )

    start_date = str(summary.get("startDate") or "")
    end_date = str(summary.get("endDate") or "")
    items: list[dict[str, Any]] = list(summary.get("items") or [])

    if conn_key == "WORKDAY_JSON":
        workers = [
            {
                "Worker_ID": item.get("employeeId") or item.get("company_employeeId"),
                "Employee_Name": item.get("employeeName") or "",
                "Cost_Center": item.get("department") or "",
                "Period_Start": start_date,
                "Period_End": end_date,
                "Regular_Hours": round(float(item.get("workMinutes") or 0) / 60.0, 2),
                "Present_Days": int(item.get("presentDays") or 0),
                "Absent_Days": int(item.get("absentDays") or 0),
                "Late_Minutes": int(item.get("lateMinutes") or 0),
                "Leave_Hours": float(item.get("leaveHours") or 0.0),
                "OT_10_Hours": round(float(item.get("ot10Minutes") or 0) / 60.0, 2),
                "OT_15_Hours": round(float(item.get("ot15Minutes") or 0) / 60.0, 2),
                "OT_20_Hours": round(float(item.get("ot20Minutes") or 0) / 60.0, 2),
                "OT_30_Hours": round(float(item.get("ot30Minutes") or 0) / 60.0, 2),
                "Weighted_OT_Hours": float(item.get("weightedOtHours") or 0.0),
            }
            for item in items
        ]
        return {
            "connector": "WORKDAY_JSON",
            "contentType": "application/json",
            "filename": f"workday_payroll_{start_date}_{end_date}.json",
            "companyId": summary.get("companyId"),
            "startDate": start_date,
            "endDate": end_date,
            "total": len(workers),
            "workers": workers,
        }

    if conn_key == "SAP_CSV":
        headers = [
            "PERNR",
            "ENAME",
            "KOSTL",
            "BEGDA",
            "ENDDA",
            "REGULAR_HRS",
            "OT_1_0",
            "OT_1_5",
            "OT_2_0",
            "OT_3_0",
            "LEAVE_HRS",
            "LATE_MINS",
            "ABSENT_DAYS",
        ]
        rows = [
            [
                item.get("employeeId") or item.get("company_employeeId"),
                item.get("employeeName") or "",
                item.get("department") or "",
                start_date,
                end_date,
                round(float(item.get("workMinutes") or 0) / 60.0, 2),
                round(float(item.get("ot10Minutes") or 0) / 60.0, 2),
                round(float(item.get("ot15Minutes") or 0) / 60.0, 2),
                round(float(item.get("ot20Minutes") or 0) / 60.0, 2),
                round(float(item.get("ot30Minutes") or 0) / 60.0, 2),
                float(item.get("leaveHours") or 0.0),
                int(item.get("lateMinutes") or 0),
                int(item.get("absentDays") or 0),
            ]
            for item in items
        ]
        return {
            "connector": "SAP_CSV",
            "contentType": "text/csv",
            "filename": f"sap_payroll_{start_date}_{end_date}.csv",
            "total": len(rows),
            "csv": _build_csv(headers, rows),
        }

    if conn_key == "PEAK_CSV":
        headers = [
            "EmployeeCode",
            "EmployeeName",
            "Department",
            "PayPeriodStart",
            "PayPeriodEnd",
            "WorkDays",
            "WorkHours",
            "WeightedOTHours",
            "LeaveHours",
            "LateMinutes",
        ]
        rows = [
            [
                item.get("employeeId") or item.get("company_employeeId"),
                item.get("employeeName") or "",
                item.get("department") or "",
                start_date,
                end_date,
                int(item.get("presentDays") or 0),
                round(float(item.get("workMinutes") or 0) / 60.0, 2),
                float(item.get("weightedOtHours") or 0.0),
                float(item.get("leaveHours") or 0.0),
                int(item.get("lateMinutes") or 0),
            ]
            for item in items
        ]
        return {
            "connector": "PEAK_CSV",
            "contentType": "text/csv",
            "filename": f"peak_payroll_{start_date}_{end_date}.csv",
            "total": len(rows),
            "csv": _build_csv(headers, rows),
        }

    # FLOWACCOUNT_CSV
    headers = [
        "EmpID",
        "FullName",
        "Department",
        "StartDate",
        "EndDate",
        "PresentDays",
        "AbsentDays",
        "OTHours",
        "LateMinutes",
    ]
    rows = [
        [
            item.get("employeeId") or item.get("company_employeeId"),
            item.get("employeeName") or "",
            item.get("department") or "",
            start_date,
            end_date,
            int(item.get("presentDays") or 0),
            int(item.get("absentDays") or 0),
            float(item.get("weightedOtHours") or 0.0),
            int(item.get("lateMinutes") or 0),
        ]
        for item in items
    ]
    return {
        "connector": "FLOWACCOUNT_CSV",
        "contentType": "text/csv",
        "filename": f"flowaccount_payroll_{start_date}_{end_date}.csv",
        "total": len(rows),
        "csv": _build_csv(headers, rows),
    }
