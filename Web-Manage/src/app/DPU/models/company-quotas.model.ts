export interface CompanyQuotaUsage {
  devices?: number;
  employees?: number;
  [key: string]: unknown;
}

export interface CompanyQuotasPayload {
  maxDevices?: number | null;
  maxEmployees?: number | null;
  gpuPriority?: number;
}

export interface CompanyQuotasResponse {
  packageCode?: string;
  usage?: CompanyQuotaUsage | null;
  quotas?: CompanyQuotasPayload;
}
