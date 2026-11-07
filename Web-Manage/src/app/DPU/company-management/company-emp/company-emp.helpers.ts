import { EmployeeModel } from '../../models/employee.model';

export type EmpListViewMode = 'table' | 'cards';

export const EMP_LIST_VIEW_STORAGE_KEY = 'dpu.companyEmp.listView';
export const EMP_TABLE_PAGE_SIZE = 10;
export const EMP_CARDS_PAGE_SIZE = 9;

/** Client-side employee search across common fields. */
export function filterEmployees(items: EmployeeModel[], term: string): EmployeeModel[] {
  const q = (term || '').toLowerCase().trim();
  if (!q) {
    return [...(items || [])];
  }
  return (items || []).filter(
    (x) =>
      x.company_employeeId?.toLowerCase().indexOf(q) !== -1 ||
      x.employeeId?.toLowerCase().indexOf(q) !== -1 ||
      x.getFullname()?.toLowerCase().indexOf(q) !== -1 ||
      x.getType()?.toLowerCase().indexOf(q) !== -1 ||
      x.getRole()?.toLowerCase().indexOf(q) !== -1 ||
      x.position?.getName()?.toLowerCase().indexOf(q) !== -1 ||
      x.department?.getName()?.toLowerCase().indexOf(q) !== -1 ||
      x.member?.email?.toLowerCase().indexOf(q) !== -1,
  );
}

export function pageSizeForView(mode: EmpListViewMode): number {
  return mode === 'cards' ? EMP_CARDS_PAGE_SIZE : EMP_TABLE_PAGE_SIZE;
}

export function totalPages(totalFiltered: number, pageSize: number): number {
  return Math.max(1, Math.ceil(totalFiltered / pageSize) || 1);
}

export function clampPageIndex(pageIndex: number, totalFiltered: number, pageSize: number): number {
  const pages = totalPages(totalFiltered, pageSize);
  if (pageIndex >= pages) {
    return Math.max(0, pages - 1);
  }
  return Math.max(0, pageIndex);
}

export function slicePage<T>(source: T[], pageIndex: number, pageSize: number): T[] {
  const startIndex = pageIndex * pageSize;
  return (source || []).slice(startIndex, startIndex + pageSize);
}

export function pageStart(totalFiltered: number, pageIndex: number, pageSize: number): number {
  return totalFiltered === 0 ? 0 : pageIndex * pageSize + 1;
}

export function pageEnd(totalFiltered: number, pageIndex: number, pageSize: number): number {
  return Math.min((pageIndex + 1) * pageSize, totalFiltered);
}

export function readStoredListView(storageKey = EMP_LIST_VIEW_STORAGE_KEY): EmpListViewMode {
  try {
    const v = localStorage.getItem(storageKey);
    if (v === 'table' || v === 'cards') return v;
  } catch {
    /* ignore */
  }
  return 'cards';
}

export function writeStoredListView(
  mode: EmpListViewMode,
  storageKey = EMP_LIST_VIEW_STORAGE_KEY,
): void {
  try {
    localStorage.setItem(storageKey, mode);
  } catch {
    /* ignore */
  }
}

/** Client-side employee form validation (Thai messages). */
export function validateEmployeeForm(selectModel: EmployeeModel | null | undefined): string | null {
  const email = (selectModel?.member?.email || '').trim();
  if (!email) {
    return 'กรุณากรอกอีเมล';
  }
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  if (!emailOk) {
    return `รูปแบบอีเมลไม่ถูกต้อง: "${email}"\nตัวอย่างที่ถูกต้อง: name@company.com\n(ต้องมีเครื่องหมาย @ และจุดในโดเมน)`;
  }
  if (!selectModel?.member?.firstName?.trim()) {
    return 'กรุณากรอกชื่อ';
  }
  if (!selectModel?.member?.lastName?.trim()) {
    return 'กรุณากรอกนามสกุล';
  }
  if (!selectModel?.department?.departmentId) {
    return 'กรุณาเลือกแผนก';
  }
  if (!selectModel?.position?.positionId) {
    return 'กรุณาเลือกตำแหน่ง';
  }
  if (selectModel.empType === undefined || selectModel.empType === null) {
    return 'กรุณาเลือกประเภทพนักงาน (รายวัน/รายเดือน)';
  }
  return null;
}

export function fieldLabelTh(field: string, locParts: string[] = []): string {
  const map: Record<string, string> = {
    email: 'อีเมล',
    firstName: 'ชื่อ',
    lastName: 'นามสกุล',
    phoneNumber: 'เบอร์โทร',
    birthDate: 'วันเกิด',
    address: 'ที่อยู่',
    emergencyContactName: 'ผู้ติดต่อฉุกเฉิน',
    emergencyContactPhone: 'เบอร์ติดต่อฉุกเฉิน',
    employeeId: 'รหัสพนักงาน',
    salary: 'เงินเดือน',
    bossId: 'หัวหน้างาน',
    startDate: 'วันเริ่มงาน',
    empType: 'ประเภทพนักงาน',
    companyRoleType: 'สิทธิ์การใช้งาน',
    position: 'ตำแหน่ง',
    department: 'แผนก',
    positionId: 'ตำแหน่ง',
    departmentId: 'แผนก',
    member: 'ข้อมูลสมาชิก',
  };
  if (map[field]) {
    return map[field];
  }
  if (locParts.includes('email')) {
    return 'อีเมล';
  }
  return field || 'ข้อมูล';
}

export function translateApiMessage(msg: string): string {
  const m = (msg || '').toLowerCase();
  if (m.includes('not a valid email') || m.includes('value is not a valid email')) {
    if (m.includes('period') || m.includes('dot')) {
      return 'รูปแบบอีเมลไม่ถูกต้อง — หลัง @ ต้องมีจุด เช่น name@company.com (ตอนนี้ใช้แบบ name@sss ไม่ได้)';
    }
    return 'รูปแบบอีเมลไม่ถูกต้อง กรุณาใช้รูปแบบ name@company.com';
  }
  if (m.includes('already registered') || m.includes('already exists')) {
    return 'อีเมลนี้มีพนักงานในบริษัทนี้อยู่แล้ว';
  }
  if (m.includes('field required') || m.includes('missing')) {
    return 'ยังไม่ได้กรอก / เลือกค่านี้';
  }
  if (m.includes('valid date') || m.includes('datetime')) {
    return 'รูปแบบวันที่ไม่ถูกต้อง';
  }
  if (m.includes('กรุณาเลือก')) {
    return msg;
  }
  return msg || 'ข้อมูลไม่ถูกต้อง';
}

export function translateValidationItem(d: any): string {
  const locParts = Array.isArray(d?.loc)
    ? d.loc.filter((x: any) => x !== 'body' && typeof x === 'string')
    : [];
  const fieldKey = locParts[locParts.length - 1] || '';
  const label = fieldLabelTh(fieldKey, locParts);
  const msg = translateApiMessage(String(d?.msg || ''));
  if (label && msg) {
    return `• ${label}: ${msg}`;
  }
  return msg ? `• ${msg}` : '';
}

export function formatApiError(err: any): string {
  const detail = err?.error?.detail;
  if (typeof detail === 'string') {
    return translateApiMessage(detail);
  }
  if (Array.isArray(detail)) {
    const lines = detail.map((d: any) => translateValidationItem(d));
    return lines.filter(Boolean).join('\n') || 'กรุณาตรวจสอบข้อมูลแล้วลองใหม่';
  }
  if (err?.status === 0) {
    return 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองใหม่';
  }
  return err?.message || 'กรุณาตรวจสอบข้อมูลแล้วลองใหม่';
}

export function saveErrorTitle(status: number | undefined): string {
  if (status === 422) return 'ข้อมูลไม่ถูกต้อง (422)';
  if (status === 400) return 'ไม่สามารถเพิ่มพนักงานได้';
  if (status === 409) return 'ข้อมูลซ้ำ';
  return 'บันทึกไม่สำเร็จ';
}

export function isExcelImportFile(fileName: string): boolean {
  const name = (fileName || '').toLowerCase();
  return name.endsWith('.xlsx') || name.endsWith('.xlsm');
}

export function isZipFile(fileName: string): boolean {
  return (fileName || '').toLowerCase().endsWith('.zip');
}

export function isAllowedFaceImage(file: File): boolean {
  const allowed = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
  return (
    allowed.includes((file.type || '').toLowerCase()) ||
    /\.(jpe?g|png|webp)$/i.test(file.name || '')
  );
}

export interface SmoothBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function lerpBox(from: SmoothBox | null, to: SmoothBox, t: number): SmoothBox {
  if (!from) return { ...to };
  return {
    x: from.x + (to.x - from.x) * t,
    y: from.y + (to.y - from.y) * t,
    width: from.width + (to.width - from.width) * t,
    height: from.height + (to.height - from.height) * t,
  };
}

export function dataURLtoFile(dataurl: string, filename: string): File {
  const arr = dataurl.split(',');
  const mimeMatch = arr[0].match(/:(.*?);/);
  const mime = mimeMatch ? mimeMatch[1] : 'image/jpeg';
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new File([u8arr], filename, { type: mime });
}
