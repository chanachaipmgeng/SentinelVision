import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TokenService } from '../../shared/services/token.service';

export interface DashboardActivity {
  timestampId?: string;
  employeeName: string;
  employeeId?: string;
  timestamp: string;
  locationName: string;
  timestampType: number;
  latitude?: number | null;
  longitude?: number | null;
  photoTimestamp?: string | null;
  picture?: string | null;
  approvalStatus?: string;
  note?: string;
}

export interface DashboardCompanyLocation {
  locationId?: string;
  locationName?: string;
  latitude: number;
  longitude: number;
  radius?: number;
  locationType?: number;
}

export interface DashboardStats {
  summary: {
    checkInsToday: number;
    inAreaToday?: number;
    outsideToday?: number;
    pendingApproval?: number;
  };
  chartData: {
    checkInsLast7Days: { date: string; count: number }[];
    todayBreakdown?: { inArea: number; outside: number };
  };
  mapPoints?: DashboardActivity[];
  companyLocations?: DashboardCompanyLocation[];
  recentActivity: DashboardActivity[];
  serverTime?: string;
}

@Injectable({
  providedIn: 'root',
})
export class DashboardService {
  private companyId: string;

  constructor(private http: HttpClient, private tokenService: TokenService) {
    this.companyId = this.tokenService.getSelectCompany()?.companyId;
  }

  getStats(): Observable<DashboardStats> {
    if (!this.companyId) {
      this.companyId = this.tokenService.getSelectCompany()?.companyId;
    }
    if (!this.companyId) {
      throw new Error('Company ID is not available.');
    }
    return this.http.get<DashboardStats>(
      `${environment.baseUrl}/dashboard/stats/${this.companyId}`
    );
  }
}
