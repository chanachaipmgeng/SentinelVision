import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../../../environments/environment';
import { dataURLtoFile, isAllowedFaceImage } from '../company-emp.helpers';

export interface FaceUploadItem {
  file: File;
  preview: string;
}

export interface FaceAngleStep {
  id: 'front' | 'left' | 'right' | 'up' | 'down';
  label: string;
  hint: string;
  captured: boolean;
  preview: string | null;
}

export function createDefaultFaceAngleSteps(): FaceAngleStep[] {
  return [
    { id: 'front', label: 'ตรง', hint: 'มองตรงกล้อง ใบหน้าอยู่กลางจอ', captured: false, preview: null },
    { id: 'left', label: 'ซ้าย', hint: 'หันหน้าไปทางซ้ายเล็กน้อย', captured: false, preview: null },
    { id: 'right', label: 'ขวา', hint: 'หันหน้าไปทางขวาเล็กน้อย', captured: false, preview: null },
    { id: 'up', label: 'เงย', hint: 'เงยหน้าขึ้นเล็กน้อย', captured: false, preview: null },
    { id: 'down', label: 'ก้ม', hint: 'ก้มหน้าลงเล็กน้อย', captured: false, preview: null },
  ];
}

export function clearUploadFaceItems(items: FaceUploadItem[]): void {
  items.forEach((item) => {
    if (item.preview) URL.revokeObjectURL(item.preview);
  });
}

export function appendFaceUploadFiles(
  existing: FaceUploadItem[],
  files: File[],
): { items: FaceUploadItem[]; rejected: string[] } {
  const rejected: string[] = [];
  const items = [...existing];
  for (const file of files) {
    if (!isAllowedFaceImage(file)) {
      rejected.push(file.name);
      continue;
    }
    items.push({ file, preview: URL.createObjectURL(file) });
  }
  return { items, rejected };
}

export async function uploadFaceFiles(
  http: HttpClient,
  companyId: string,
  memberId: string,
  files: File[],
  onProgress?: (label: string) => void,
): Promise<void> {
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    onProgress?.(`กำลังอัปโหลด ${i + 1}/${files.length}...`);
    const formData = new FormData();
    formData.append('file', file, file.name || `face-${i + 1}.jpg`);
    if (companyId) {
      formData.append('companyId', companyId);
    }
    await firstValueFrom(
      http.post(environment.baseUrl + `/face/members/${memberId}/add-face`, formData),
    );
  }
}

export async function uploadAnglePreviews(
  http: HttpClient,
  companyId: string,
  memberId: string,
  steps: FaceAngleStep[],
  onProgress?: (label: string) => void,
): Promise<void> {
  const pending = steps.filter((s) => s.captured && s.preview);
  for (let i = 0; i < pending.length; i++) {
    const step = pending[i];
    onProgress?.(`กำลังอัปโหลด ${i + 1}/5 (${step.label})...`);
    const file = dataURLtoFile(step.preview!, `face-${step.id}.jpg`);
    const formData = new FormData();
    formData.append('file', file);
    if (companyId) {
      formData.append('companyId', companyId);
    }
    await firstValueFrom(
      http.post(environment.baseUrl + `/face/members/${memberId}/add-face`, formData),
    );
  }
}
