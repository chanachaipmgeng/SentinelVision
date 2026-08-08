import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { TranslateModule } from '@ngx-translate/core';
import { CompanyService } from '../../services/company.service';
import { TokenService } from '../../../shared/services/token.service';
import { CompanyModel } from '../../models/company.model';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';

interface QuickLink {
  label: string;
  icon: string;
  route: string;
  hint: string;
}

@Component({
  selector: 'app-home-installer',
  templateUrl: './home-installer.component.html',
  standalone: true,
  imports: [
    CommonModule,
    SharedModule,
    TranslateModule,
    RouterModule,
    PageToolbarComponent,
    StatChipComponent,
    EmptyStateComponent,
  ],
  styleUrls: ['./home-installer.component.css'],
})
export class HomeInstallerComponent implements OnInit {
  companyId = '';
  company: CompanyModel | null = null;
  loading = true;
  error: string | null = null;

  readonly links: QuickLink[] = [
    { label: 'แดชบอร์ด', icon: 'ri-dashboard-line', route: '/company/dashboard', hint: 'ภาพรวมลงเวลา' },
    { label: 'พนักงาน', icon: 'ri-team-line', route: '/company/company-emp', hint: 'จัดการพนักงานและใบหน้า' },
    { label: 'ข้อมูลการลงเวลา', icon: 'ri-time-line', route: '/company/timestamp-log', hint: 'ประวัติการลงเวลา' },
    { label: 'อนุมัติการลงเวลา', icon: 'ri-checkbox-circle-line', route: '/company/warning-timestamp-log', hint: 'คิว Warning' },
    { label: 'Kiosk ใบหน้า', icon: 'ri-camera-line', route: '/company/timestamp-face', hint: 'ลงเวลาด้วยกล้อง' },
    { label: 'สถานที่ลงเวลา', icon: 'ri-map-pin-line', route: '/company/company-location', hint: 'จุดลงเวลา / พื้นที่' },
    { label: 'ข้อมูลบริษัท', icon: 'ri-building-2-line', route: '/company/company-info', hint: 'โปรไฟล์บริษัท' },
  ];

  constructor(
    private route: ActivatedRoute,
    private comService: CompanyService,
    private tokenService: TokenService
  ) {
    this.companyId = this.route.snapshot.paramMap.get('companyId') || '';
  }

  ngOnInit(): void {
    this.loadCompany();
  }

  loadCompany(): void {
    if (!this.companyId) {
      this.loading = false;
      this.error = 'ไม่พบรหัสบริษัท';
      return;
    }
    this.loading = true;
    this.error = null;
    this.comService.getById(this.companyId).subscribe({
      next: (result) => {
        this.company = new CompanyModel(result);
        this.tokenService.saveSelectCompany(result);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.error = 'โหลดข้อมูลบริษัทไม่สำเร็จ';
      },
    });
  }
}
