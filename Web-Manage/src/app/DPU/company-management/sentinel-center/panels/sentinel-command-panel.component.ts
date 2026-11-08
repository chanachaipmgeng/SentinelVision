import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import { defaultScanForm, firstFileFromInput } from '../sentinel.helpers';

@Component({
  selector: 'app-sentinel-command-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './sentinel-command-panel.component.html',
})
export class SentinelCommandPanelComponent implements OnInit {
  @Output() toast = new EventEmitter<string>();
  @Output() overviewChanged = new EventEmitter<void>();

  companyId = '';
  zones: any[] = [];
  events: any[] = [];
  incidents: any[] = [];
  incidentFilterSeverity = '';
  scanSelectedFile: File | null = null;
  lastScanResult: any = null;
  isScanning = false;
  scanForm = defaultScanForm();

  siemForm = {
    siemWebhookUrl: '',
    siemWebhookSecret: '',
    hasSiemWebhookSecret: false,
  };
  siemSaving = false;

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadZones();
    this.loadEvents();
    this.loadIncidents();
    this.loadSiemSettings();
  }

  loadSiemSettings(): void {
    this.api.getSiemSettings(this.companyId).subscribe({
      next: (s) => {
        this.siemForm = {
          siemWebhookUrl: s?.siemWebhookUrl || '',
          siemWebhookSecret: '',
          hasSiemWebhookSecret: !!s?.hasSiemWebhookSecret,
        };
      },
    });
  }

  saveSiemSettings(): void {
    this.siemSaving = true;
    const body: Record<string, string> = {
      siemWebhookUrl: this.siemForm.siemWebhookUrl || '',
    };
    if ((this.siemForm.siemWebhookSecret || '').trim()) {
      body['siemWebhookSecret'] = this.siemForm.siemWebhookSecret.trim();
    }
    this.api.putSiemSettings(this.companyId, body).subscribe({
      next: (s) => {
        this.siemSaving = false;
        this.siemForm.siemWebhookSecret = '';
        this.siemForm.hasSiemWebhookSecret = !!s?.hasSiemWebhookSecret;
        this.siemForm.siemWebhookUrl = s?.siemWebhookUrl || this.siemForm.siemWebhookUrl;
        this.toast.emit('บันทึก SIEM export แล้ว');
      },
      error: () => {
        this.siemSaving = false;
        this.toast.emit('บันทึก SIEM ไม่สำเร็จ');
      },
    });
  }

  testSiemSettings(): void {
    this.api.testSiemSettings(this.companyId).subscribe({
      next: (res) => {
        this.toast.emit(
          res?.queued ? 'ส่ง SIEM test ping เข้า outbox แล้ว' : res?.reason || 'ยังไม่ได้ตั้งค่า webhook'
        );
      },
      error: () => this.toast.emit('ทดสอบ SIEM ไม่สำเร็จ'),
    });
  }

  loadZones(): void {
    this.api.getZones(this.companyId).subscribe((rows) => (this.zones = rows || []));
  }

  loadEvents(): void {
    this.api.getEvents(this.companyId).subscribe((rows) => (this.events = rows || []));
  }

  loadIncidents(): void {
    this.api
      .getIncidents(this.companyId, this.incidentFilterSeverity || undefined)
      .subscribe((rows) => (this.incidents = rows || []));
  }

  onScanFileSelected(event: Event): void {
    this.scanSelectedFile = firstFileFromInput(event);
  }

  runUnifiedScan(): void {
    if (!this.scanSelectedFile) return;
    this.isScanning = true;
    const fd = new FormData();
    fd.append('file', this.scanSelectedFile);
    fd.append('stationMode', this.scanForm.stationMode);
    if (this.scanForm.zoneId) fd.append('zoneId', this.scanForm.zoneId);
    if (this.scanForm.eventId) fd.append('eventId', this.scanForm.eventId);
    if (this.scanForm.totpOrPin) fd.append('totpOrPin', this.scanForm.totpOrPin);

    this.api.unifiedScan(this.companyId, fd).subscribe({
      next: (res) => {
        this.isScanning = false;
        this.lastScanResult = res;
        this.loadIncidents();
        this.loadEvents();
        this.overviewChanged.emit();
      },
      error: (err) => {
        this.isScanning = false;
        this.lastScanResult = {
          accessGranted: false,
          decision: 'SCAN_ERROR',
          message: err?.error?.detail || 'เกิดข้อผิดพลาดในการประมวลผลใบหน้า',
        };
      },
    });
  }

  acknowledgeIncident(incidentId: string): void {
    this.api.acknowledgeIncident(this.companyId, incidentId).subscribe({
      next: () => {
        this.toast.emit('รับทราบเหตุการณ์แล้ว');
        this.loadIncidents();
        this.overviewChanged.emit();
      },
    });
  }
}
