import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import {
  defaultAttendeeForm,
  defaultEventForm,
  downloadCsv,
  filterEventAttendeeItems,
  firstFileFromInput,
} from '../sentinel.helpers';
import { SentinelEventDwellReport, SentinelEventRule, SentinelIdentity } from '../sentinel.models';
import { EventsSection } from '../sentinel-routing';
import { ImageDropzoneComponent } from '../../../../shared/components/image-dropzone/image-dropzone.component';

@Component({
    selector: 'app-sentinel-events-panel',
    imports: [CommonModule, FormsModule, RouterModule, TranslateModule, ImageDropzoneComponent],
    templateUrl: './sentinel-events-panel.component.html'
})
export class SentinelEventsPanelComponent implements OnInit, OnChanges {
  @Input() section: EventsSection = 'campaigns';
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  events: SentinelEventRule[] = [];
  identities: SentinelIdentity[] = [];
  selectedIdentityPhoto: File | null = null;
  eventForm = defaultEventForm();
  attendeeForm = defaultAttendeeForm();
  selectedDwellEventId = '';
  dwellReport: SentinelEventDwellReport | null = null;
  dwellLoading = false;
  breakoutForm = { eventId: '', roomCode: 'ROOM-A', capacity: 50, subjectName: '' };
  breakoutStatus = '';

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadEvents();
    this.loadIdentities();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['section'] && this.section === 'checkins' && this.selectedDwellEventId) {
      this.loadEventDwell(this.selectedDwellEventId);
    }
  }

  get eventAttendeeItems(): SentinelIdentity[] {
    return filterEventAttendeeItems(this.identities);
  }

  get totalCapacity(): number {
    return this.events.reduce((acc, ev) => acc + Number(ev.capacity || 0), 0);
  }

  get totalCheckedIn(): number {
    return this.events.reduce((acc, ev) => acc + Number(ev.checkedInCount || 0), 0);
  }

  get totalRegistered(): number {
    return this.events.reduce((acc, ev) => acc + Number(ev.attendeeCount || 0), 0);
  }

  checkinPercent(ev: SentinelEventRule): number {
    const denom = Number(ev.attendeeCount || ev.capacity || 0);
    if (!denom) return 0;
    return Math.min(100, Math.round((Number(ev.checkedInCount || 0) / denom) * 100));
  }

  loadEvents(): void {
    this.api.getEvents(this.companyId).subscribe((rows) => {
      this.events = rows || [];
      if (this.events.length > 0 && !this.attendeeForm.eventId) {
        this.attendeeForm.eventId = this.events[0].eventId;
      }
      if (this.events.length > 0 && !this.selectedDwellEventId) {
        this.selectedDwellEventId = this.events[0].eventId;
        if (this.section === 'checkins') {
          this.loadEventDwell(this.selectedDwellEventId);
        }
      }
    });
  }

  loadEventDwell(eventId: string): void {
    if (!this.companyId || !eventId) {
      this.dwellReport = null;
      return;
    }
    this.dwellLoading = true;
    this.api.getEventDwell(this.companyId, eventId).subscribe({
      next: (res) => {
        this.dwellReport = res;
        this.dwellLoading = false;
      },
      error: () => {
        this.dwellReport = null;
        this.dwellLoading = false;
      },
    });
  }

  exportDwellCsv(): void {
    const people = this.dwellReport?.people || [];
    downloadCsv(
      ['FullName', 'FirstSeenAt', 'TotalDwellMinutes', 'Booths'],
      people.map((p) => [
        p.fullName || p.memberId || '',
        p.firstSeenAt || '',
        p.totalDwellMinutes ?? 0,
        (p.booths || []).map((b) => `${b.cameraName || b.cameraId}:${b.dwellMinutes}m`).join(' | '),
      ]),
      'event-booth-dwell',
    );
  }

  toggleRegistration(ev: SentinelEventRule): void {
    if (!this.companyId || !ev.eventId) return;
    const targetState = !ev.registrationOpen;
    this.api
      .updateEventRegistration(this.companyId, ev.eventId, {
        registrationOpen: targetState,
      })
      .subscribe({
        next: (res) => {
          ev.registrationOpen = targetState;
          if (res['publicSlug']) {
            ev.publicSlug = String(res['publicSlug']);
          }
          const msg = targetState
            ? `เปิดรับสมัคร Public สำหรับ "${ev.name}" แล้ว`
            : `ปิดรับสมัคร Public แล้ว`;
          this.toast.emit(msg);
        },
        error: (err) => {
          this.toast.emit(err?.error?.detail || 'เกิดข้อผิดพลาดในการเปลี่ยนสถานะการลงทะเบียน');
        },
      });
  }

  copyPublicUrl(ev: SentinelEventRule): void {
    const slug = ev.publicSlug || ev.eventId;
    const url = `${window.location.origin}/events/register/${encodeURIComponent(slug)}`;
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(url).then(
        () => this.toast.emit(`คัดลอกลิงก์ลงทะเบียนเรียบร้อยแล้ว: ${url}`),
        () => this.toast.emit(`ลิงก์ลงทะเบียน: ${url}`),
      );
    } else {
      this.toast.emit(`ลิงก์ลงทะเบียน: ${url}`);
    }
  }

  exportRegistrations(ev: SentinelEventRule): void {
    if (!this.companyId || !ev.eventId) return;
    const url = this.api.exportEventRegistrationsUrl(this.companyId, ev.eventId);
    window.open(url, '_blank');
  }

  loadIdentities(): void {
    this.api.getIdentities(this.companyId).subscribe((rows) => (this.identities = rows || []));
  }

  onIdentityPhotoSelected(event: Event): void {
    this.selectedIdentityPhoto = firstFileFromInput(event);
  }

  enrollExistingAttendeeFace(identityId: string, event: Event): void {
    const file = firstFileFromInput(event);
    if (!file) return;
    this.uploadIdentityFace(identityId, file);
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

  createIdentityRecord(formObj: { fullName?: string; [key: string]: unknown }): void {
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

  submitBreakoutCheckin(): void {
    const eventId = this.breakoutForm.eventId || this.events[0]?.eventId || '';
    if (!eventId || !this.breakoutForm.roomCode.trim()) {
      this.toast.emit('กรุณาเลือกงานอีเวนต์และระบุรหัสห้องย่อย');
      return;
    }
    this.api
      .checkInBreakoutRoom(this.companyId, eventId, {
        roomCode: this.breakoutForm.roomCode.trim(),
        capacity: Number(this.breakoutForm.capacity || 50),
        subjectName: this.breakoutForm.subjectName.trim() || 'Attendee',
      })
      .subscribe({
        next: (res) => {
          this.breakoutStatus = `Checked in ${res['roomCode']} (${res['occupancy']}/${res['capacity']})`;
          this.toast.emit(this.breakoutStatus);
        },
        error: (err) => {
          this.breakoutStatus = err?.error?.detail?.message || 'ห้องย่อยเต็มความจุแล้ว (409 EVENT_ROOM_FULL)';
          this.toast.emit(this.breakoutStatus);
        },
      });
  }
}
