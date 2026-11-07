import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import {
  defaultAttendeeForm,
  defaultEventForm,
  filterEventAttendeeItems,
  firstFileFromInput,
} from '../sentinel.helpers';

@Component({
  selector: 'app-sentinel-events-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sentinel-events-panel.component.html',
})
export class SentinelEventsPanelComponent implements OnInit {
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  events: any[] = [];
  identities: any[] = [];
  selectedIdentityPhoto: File | null = null;
  eventForm = defaultEventForm();
  attendeeForm = defaultAttendeeForm();

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadEvents();
    this.loadIdentities();
  }

  get eventAttendeeItems(): any[] {
    return filterEventAttendeeItems(this.identities);
  }

  loadEvents(): void {
    this.api.getEvents(this.companyId).subscribe((rows) => {
      this.events = rows || [];
      if (this.events.length > 0 && !this.attendeeForm.eventId) {
        this.attendeeForm.eventId = this.events[0].eventId;
      }
    });
  }

  loadIdentities(): void {
    this.api.getIdentities(this.companyId).subscribe((rows) => (this.identities = rows || []));
  }

  onIdentityPhotoSelected(event: Event): void {
    this.selectedIdentityPhoto = firstFileFromInput(event);
  }

  createEventCampaign(): void {
    if (!this.eventForm.name.trim()) {
      this.toast.emit('กรุณาระบุชื่องานอีเวนต์');
      return;
    }
    this.api.createEvent(this.companyId, this.eventForm).subscribe({
      next: () => {
        this.eventForm.name = '';
        this.toast.emit('สร้างแคมเปญงานอีเวนต์สำเร็จ');
        this.loadEvents();
        this.overviewChanged.emit();
      },
    });
  }

  deleteEvent(eventId: string): void {
    this.api.deleteEvent(this.companyId, eventId).subscribe({
      next: () => {
        this.toast.emit('ปิดแคมเปญงานอีเวนต์แล้ว');
        this.loadEvents();
        this.overviewChanged.emit();
      },
    });
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
          this.loadEvents();
          this.overviewChanged.emit();
        }
      },
    });
  }

  private uploadIdentityFace(identityId: string, file: File): void {
    this.api.enrollIdentityFace(this.companyId, identityId, file).subscribe({
      next: () => {
        this.toast.emit('ลงทะเบียนใบหน้า 512-d สำเร็จ');
        this.loadIdentities();
        this.loadEvents();
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
        this.loadEvents();
        this.overviewChanged.emit();
      },
    });
  }
}
