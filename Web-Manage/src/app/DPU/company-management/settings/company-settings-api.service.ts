import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

export interface AiSettings {
  faceMatchThreshold: number;
  cctvCameraIntervalSeconds: number;
  faceMatchThresholdOverride: boolean;
  cctvCameraIntervalOverride: boolean;
}

export interface SessionSettings {
  idleTimeoutMinutes: number;
}

export interface ApiKeyRow {
  apiKeyId: string;
  companyId: string;
  name: string;
  keyPrefix: string;
  scopes: string[];
  createdByMemberId?: string | null;
  createdAt?: string | null;
  lastUsedAt?: string | null;
  revokedAt?: string | null;
  notes?: string | null;
  active: boolean;
  /** Only present on create response — show once. */
  apiKey?: string;
}

@Injectable({ providedIn: 'root' })
export class CompanySettingsApiService {
  constructor(private http: HttpClient) {}

  private base(companyId: string): string {
    return `${environment.baseUrl}/companys/${companyId}`;
  }

  getAiSettings(companyId: string): Observable<AiSettings> {
    return this.http.get<AiSettings>(`${this.base(companyId)}/ai-settings`);
  }

  putAiSettings(companyId: string, body: Partial<AiSettings>): Observable<AiSettings> {
    return this.http.put<AiSettings>(`${this.base(companyId)}/ai-settings`, body);
  }

  getSessionSettings(companyId: string): Observable<SessionSettings> {
    return this.http.get<SessionSettings>(`${this.base(companyId)}/session-settings`);
  }

  putSessionSettings(
    companyId: string,
    body: Partial<SessionSettings>,
  ): Observable<SessionSettings> {
    return this.http.put<SessionSettings>(`${this.base(companyId)}/session-settings`, body);
  }

  listApiKeys(companyId: string): Observable<ApiKeyRow[]> {
    return this.http.get<ApiKeyRow[]>(`${this.base(companyId)}/api-keys`);
  }

  createApiKey(
    companyId: string,
    body: { name: string; scopes: string[]; notes?: string },
  ): Observable<ApiKeyRow> {
    return this.http.post<ApiKeyRow>(`${this.base(companyId)}/api-keys`, body);
  }

  revokeApiKey(companyId: string, apiKeyId: string): Observable<ApiKeyRow> {
    return this.http.delete<ApiKeyRow>(`${this.base(companyId)}/api-keys/${apiKeyId}`);
  }
}
