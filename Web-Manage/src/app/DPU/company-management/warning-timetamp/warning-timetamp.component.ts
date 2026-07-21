import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { TimestampService } from '../../services/timestamp.service';
import { TokenService } from '../../../shared/services/token.service';
import { TimestampModel } from '../../models/timestamp.model';
import swal from 'sweetalert';

@Component({
  selector: 'app-warning-timetamp',
  templateUrl: './warning-timetamp.component.html',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  styleUrls: ['./warning-timetamp.component.css'],
})
export class WarningTimetampComponent implements OnInit {
  companyId = '';
  items: TimestampModel[] = [];
  loading = false;

  constructor(
    private timestampService: TimestampService,
    private tokenService: TokenService
  ) {
    this.companyId = this.tokenService.getSelectCompany()?.companyId || '';
  }

  ngOnInit() {
    this.loadPending();
  }

  loadPending() {
    if (!this.companyId) return;
    this.loading = true;
    this.timestampService
      .getListsSearch(this.companyId, '', '', '', undefined, 'PENDING')
      .subscribe({
        next: (result) => {
          this.items = result.sort((a, b) =>
            (b.timestamp || '').localeCompare(a.timestamp || '')
          );
          this.loading = false;
        },
        error: () => {
          this.loading = false;
          swal('Error', 'โหลดคิวอนุมัติไม่สำเร็จ', 'error');
        },
      });
  }

  approve(item: TimestampModel) {
    swal({
      title: 'อนุมัติการลงเวลานี้?',
      text: item.employee?.getFullname?.() || '',
      icon: 'warning',
      buttons: ['ยกเลิก', 'อนุมัติ'],
    }).then((ok: any) => {
      if (!ok) return;
      this.timestampService
        .approve(this.companyId, item.timestampId, {
          approve: true,
          approvedBy: this.tokenService.getUserData()?.memberId,
        })
        .subscribe(() => {
          swal('สำเร็จ', 'อนุมัติแล้ว', 'success');
          this.loadPending();
        });
    });
  }

  reject(item: TimestampModel) {
    swal({
      title: 'ปฏิเสธการลงเวลา',
      text: 'กรอกเหตุผลที่ปฏิเสธ',
      content: {
        element: 'input',
        attributes: { placeholder: 'เหตุผล' },
      } as any,
      buttons: ['ยกเลิก', 'ปฏิเสธ'],
    }).then((reason: any) => {
      if (reason === null || reason === false) return;
      const rejectReason = String(reason || '').trim();
      if (!rejectReason) {
        swal('ต้องระบุเหตุผล', '', 'info');
        return;
      }
      this.timestampService
        .approve(this.companyId, item.timestampId, {
          approve: false,
          rejectReason,
          approvedBy: this.tokenService.getUserData()?.memberId,
        })
        .subscribe(() => {
          swal('สำเร็จ', 'ปฏิเสธแล้ว', 'success');
          this.loadPending();
        });
    });
  }
}
