export type HrScheduleTab =
  | 'shifts'
  | 'leaves'
  | 'holidays'
  | 'pdpa'
  | 'security'
  | 'observability';

export const HR_SCHEDULE_TABS: Array<{
  id: HrScheduleTab;
  label: string;
  icon: string;
}> = [
  { id: 'shifts', label: 'กะเวลาทำงาน (Multi-Shift)', icon: 'ri-time-line' },
  { id: 'leaves', label: 'ใบลาและการอนุมัติ', icon: 'ri-calendar-check-line' },
  { id: 'holidays', label: 'ปฏิทินวันหยุดบริษัท', icon: 'ri-calendar-event-line' },
  { id: 'pdpa', label: 'PDPA & ข้อมูลชีวมิติ', icon: 'ri-shield-user-line' },
  { id: 'security', label: 'อุปกรณ์ Kiosk & 2FA', icon: 'ri-key-2-line' },
  { id: 'observability', label: 'Payroll Webhook & Cloud Metrics', icon: 'ri-pulse-line' },
];

export function defaultNewShift(): {
  name: string;
  startTime: string;
  endTime: string;
  graceMinutes: number;
  roundingMinutes: number;
  breakMinutes: number;
  otThresholdMinutes: number;
  breakWindows: { start: string; end: string }[];
  isCrossMidnight: boolean;
  isDefault: boolean;
} {
  return {
    name: '',
    startTime: '09:00',
    endTime: '18:00',
    graceMinutes: 15,
    roundingMinutes: 0,
    breakMinutes: 0,
    otThresholdMinutes: 0,
    breakWindows: [],
    isCrossMidnight: false,
    isDefault: false,
  };
}

export function defaultNewLeave(): {
  company_employeeId: string;
  leaveType: string;
  startDate: string;
  endDate: string;
  reason: string;
} {
  return {
    company_employeeId: '',
    leaveType: 'ANNUAL',
    startDate: '',
    endDate: '',
    reason: '',
  };
}

export function defaultNewHoliday(): { holidayDate: string; name: string } {
  return { holidayDate: '', name: '' };
}

export function defaultConsentPolicy(): {
  version: string;
  textTh: string;
  textEn: string;
} {
  return { version: '1.0', textTh: '', textEn: '' };
}

export function defaultRetentionSettings(): {
  biometricDays: number;
  punchPhotoDays: number;
  incidentSnapshotDays: number;
  tempHours: number;
} {
  return {
    biometricDays: 90,
    punchPhotoDays: 90,
    incidentSnapshotDays: 90,
    tempHours: 24,
  };
}

export function defaultNotifySettings(): {
  email: string;
  lineToken: string;
  webhookUrl: string;
  webhookSecret: string;
  hasWebhookSecret: boolean;
  cutoff: string;
  events: string[];
} {
  return {
    email: '',
    lineToken: '',
    webhookUrl: '',
    webhookSecret: '',
    hasWebhookSecret: false,
    cutoff: '09:30',
    events: [
      'attendance.checked_in',
      'attendance.checked_out',
      'attendance.approved',
      'attendance.missing',
    ],
  };
}

/** Human-readable holiday source label (Thai UI). */
export function holidaySourceLabel(source: string | null | undefined): string {
  switch ((source || 'MANUAL').toUpperCase()) {
    case 'CSV':
      return 'CSV';
    case 'ICAL':
      return 'iCal';
    case 'THAI_PRESET':
      return 'ราชการไทย';
    default:
      return 'กำหนดเอง';
  }
}

/** Detect holiday import format from filename. */
export function holidayImportFormat(fileName: string): 'ical' | 'csv' {
  const lower = fileName.toLowerCase();
  if (lower.endsWith('.ics') || lower.endsWith('.ical')) {
    return 'ical';
  }
  return 'csv';
}

export function parseLeaveList(res: any): any[] {
  return Array.isArray(res) ? res : res?.items || [];
}

export function retentionFromPdpaSummary(
  retentionPolicy: any,
  fallback: ReturnType<typeof defaultRetentionSettings>,
): ReturnType<typeof defaultRetentionSettings> {
  if (!retentionPolicy) return { ...fallback };
  return {
    biometricDays: retentionPolicy.biometricDays ?? fallback.biometricDays,
    punchPhotoDays:
      retentionPolicy.punchPhotoDays ?? retentionPolicy.imageRetentionDays ?? fallback.punchPhotoDays,
    incidentSnapshotDays:
      retentionPolicy.incidentSnapshotDays ?? fallback.incidentSnapshotDays,
    tempHours: retentionPolicy.tempRetentionHours ?? fallback.tempHours,
  };
}

export function isHrScheduleTab(value: string | null | undefined): value is HrScheduleTab {
  return (
    value === 'shifts' ||
    value === 'leaves' ||
    value === 'holidays' ||
    value === 'pdpa' ||
    value === 'security' ||
    value === 'observability'
  );
}
