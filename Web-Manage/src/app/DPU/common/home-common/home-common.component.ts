import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { SharedModule } from '../../../shared/shared.module';
import { PageToolbarComponent } from '../../../shared/components/page-toolbar/page-toolbar.component';
import { StatChipComponent } from '../../../shared/components/stat-chip/stat-chip.component';

interface AdminLink {
  label: string;
  icon: string;
  route: string;
  hint: string;
}

@Component({
  selector: 'app-home-common',
  imports: [CommonModule, RouterModule, SharedModule, PageToolbarComponent, StatChipComponent],
  standalone: true,
  templateUrl: './home-common.component.html',
  styleUrls: ['./home-common.component.css'],
})
export class HomeCommonComponent {
  readonly links: AdminLink[] = [
    { label: 'จัดการสมาชิก', icon: 'ri-team-line', route: '/admin/member-manage', hint: 'ผู้ใช้ในระบบ' },
    { label: 'จัดการบริษัท', icon: 'ri-building-line', route: '/admin/manage-companys', hint: 'บริษัทและสถานะ' },
    { label: 'ผู้ดูแลระบบ', icon: 'ri-shield-user-line', route: '/admin/admin-manage', hint: 'สิทธิ์แอดมิน' },
    { label: 'แผนก', icon: 'ri-organization-chart', route: '/admin/emp/department', hint: 'โครงสร้างแผนก' },
    { label: 'ตำแหน่ง', icon: 'ri-briefcase-line', route: '/admin/emp/position', hint: 'ตำแหน่งงาน' },
  ];
}
