import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import {
  defaultWatchlistForm,
  filterWatchlistItems,
  firstFileFromInput,
} from '../sentinel.helpers';

@Component({
  selector: 'app-sentinel-watchlist-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sentinel-watchlist-panel.component.html',
})
export class SentinelWatchlistPanelComponent implements OnInit {
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  identities: any[] = [];
  selectedIdentityPhoto: File | null = null;
  watchlistForm = defaultWatchlistForm();

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadIdentities();
  }

  get watchlistItems(): any[] {
    return filterWatchlistItems(this.identities);
  }

  loadIdentities(): void {
    this.api.getIdentities(this.companyId).subscribe((rows) => (this.identities = rows || []));
  }

  onIdentityPhotoSelected(event: Event): void {
    this.selectedIdentityPhoto = firstFileFromInput(event);
  }

  createIdentityRecord(formObj: any): void {
    if (!formObj.fullName || !String(formObj.fullName).trim()) {
      this.toast.emit('กรุณาระบุชื่อ-นามสกุล');
      return;
    }
    this.api.createIdentity(this.companyId, formObj).subscribe({
      next: (created) => {
        const photo = this.selectedIdentityPhoto;
        this.selectedIdentityPhoto = null;
        formObj.fullName = '';
        if (photo && created?.identityId) {
          this.uploadIdentityFace(created.identityId, photo);
        } else {
          this.toast.emit('บันทึกรายชื่อสำเร็จ');
          this.loadIdentities();
          this.overviewChanged.emit();
        }
      },
    });
  }

  enrollExistingIdentityFace(identityId: string, event: Event): void {
    const file = firstFileFromInput(event);
    if (!file) return;
    this.uploadIdentityFace(identityId, file);
  }

  private uploadIdentityFace(identityId: string, file: File): void {
    this.api.enrollIdentityFace(this.companyId, identityId, file).subscribe({
      next: () => {
        this.toast.emit('ลงทะเบียนใบหน้า 512-d สำเร็จ');
        this.loadIdentities();
        this.overviewChanged.emit();
      },
      error: (err) => {
        this.toast.emit(err?.error?.detail || 'ไม่พบใบหน้าในภาพที่อัปโหลด');
        this.loadIdentities();
      },
    });
  }

  deleteIdentity(identityId: string): void {
    this.api.deleteIdentity(this.companyId, identityId).subscribe({
      next: () => {
        this.toast.emit('ลบรายการเรียบร้อยแล้ว');
        this.loadIdentities();
        this.overviewChanged.emit();
      },
    });
  }
}
