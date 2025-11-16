import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TokenService } from '../../shared/services/token.service';

// Define an interface for the expected API response for better type safety
export interface DashboardStats {
  summary: {
    checkInsToday: number;
  };
  chartData: {
    checkInsLast7Days: { date: string; count: number }[];
  };
  recentActivity: {
    employeeName: string;
    timestamp: string;
    locationName: string;
    timestampType: number;
  }[];
}

@Injectable({
  providedIn: 'root'
})
export class DashboardService {

  private companyId: string;

  constructor(private http: HttpClient, private tokenService: TokenService) { 
    this.companyId = this.tokenService.getSelectCompany().companyId;
  }

  getStats(): Observable<DashboardStats> {
    if (!this.companyId) {
      throw new Error('Company ID is not available.');
    }
    return this.http.get<DashboardStats>(`${environment.baseUrl}/dashboard/stats/${this.companyId}`);
  }
}
