import { EmployeeModel } from '../../models/employee.model';

export interface HrShift {
  shiftId: string;
  name: string;
  startTime: string;
  endTime: string;
  graceMinutes?: number;
  roundingMinutes?: number;
  breakMinutes?: number;
  otThresholdMinutes?: number;
  isCrossMidnight?: boolean;
  isDefault?: boolean;
}

export interface HrShiftsResponse {
  shifts?: HrShift[];
}

export interface HrDepartmentShiftRow {
  departmentId: string;
  thName?: string;
  engName?: string;
  shiftId?: string | null;
}

export type HrEmployeeShiftRow = EmployeeModel & { shiftId?: string | null };

export interface HrLeave {
  leaveId: string;
  company_employeeId?: string;
  leaveType?: string;
  startDate?: string;
  endDate?: string;
  reason?: string;
  status?: number | string;
  memberName?: string;
  employeeName?: string;
  employeeCode?: string;
}

export interface HrHoliday {
  holidayId: string;
  holidayDate?: string;
  name?: string;
  source?: string | null;
}

export interface HrPdpaSummary {
  totalEmployees?: number;
  consentedEmployees?: number;
  enrolledEmployees?: number;
  consentPolicy?: { version?: string; textTh?: string; textEn?: string };
  retentionPolicy?: RetentionPolicyFields & {
    imageRetentionDays?: number;
    tempRetentionHours?: number;
  };
}

export interface RetentionPolicyFields {
  biometricDays?: number;
  punchPhotoDays?: number;
  imageRetentionDays?: number;
  incidentSnapshotDays?: number;
  videoClipDays?: number;
  tempRetentionHours?: number;
}

export interface HrKioskDevice {
  deviceId: string;
  name?: string;
  pairingCode?: string | null;
  pairingCodeTtlMinutes?: number;
  lastSeenAt?: string | Date | null;
  isActive?: boolean;
  isPaired?: boolean;
  pairingPending?: boolean;
  pairingExpiresAt?: string | Date | null;
}

export interface HrMetricHistogram {
  p95Ms?: number;
  avgMs?: number;
  count?: number;
}

export interface HrObservabilitySummary {
  histograms?: {
    dpu_face_gpu_latency_ms?: HrMetricHistogram;
    dpu_pgvector_search_ms?: HrMetricHistogram;
  };
  httpAvgLatencyMs?: number;
  activeKioskWebSockets?: number;
  httpRequestsTotal?: number;
  storage?: {
    backend?: string;
    s3Enabled?: boolean;
    localFileCounts?: { enrolled_images?: number; uploaded_images?: number };
  };
}

export interface NotifyOutboxRow {
  id?: string;
  event?: string;
  status?: string;
  channel?: string;
  attempts?: number;
  lastError?: string;
  createdAt?: string;
}
