import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import swal from 'sweetalert';
import { TokenService } from '../../../../shared/services/token.service';
import { SentinelApiService } from '../sentinel-api.service';
import { downloadMusterCsv } from '../sentinel.helpers';
import { SentinelEdgeManifest, SentinelMusterRollItem, SentinelOverview } from '../sentinel.models';

@Component({
    selector: 'app-sentinel-muster-panel',
    imports: [CommonModule],
    templateUrl: './sentinel-muster-panel.component.html'
})
export class SentinelMusterPanelComponent implements OnInit, OnChanges {
  @Input() overview: SentinelOverview | null = null;

  companyId = '';
  edgeManifest: SentinelEdgeManifest | null = null;
  reindexResult: Record<string, unknown> | null = null;
  reindexing = false;
  musterItems: SentinelMusterRollItem[] = [];
  musterTotal = 0;
  musterWorkDate: string | null = null;
  musterLoading = false;
  musterLimit = 100;
  musterOffset = 0;
  safeKeys = new Set<string>();

  constructor(private api: SentinelApiService, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) return;
    this.loadSafeKeys();
    this.loadEdgeManifest();
    this.applyOverviewMuster(this.overview);
    this.refreshMuster();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['overview'] && changes['overview'].currentValue) {
      this.applyOverviewMuster(changes['overview'].currentValue);
    }
  }

  private applyOverviewMuster(ov: SentinelOverview | null): void {
    if (!ov) return;
    if (Array.isArray(ov.musterRoll)) {
      this.musterItems = ov.musterRoll;
    }
    const meta = ov.musterMeta || {};
    if (meta.total != null) this.musterTotal = Number(meta.total) || this.musterItems.length;
    else this.musterTotal = this.musterItems.length;
    if (meta.workDate) this.musterWorkDate = meta.workDate;
  }

  loadEdgeManifest(): void {
    if (!this.companyId) return;
    this.api.getEdgeSync(this.companyId).subscribe((res) => (this.edgeManifest = res));
  }

  runVectorReindex(): void {
    if (!this.companyId || this.reindexing) return;
    this.reindexing = true;
    this.api.reindexVectors(this.companyId).subscribe({
      next: (res) => {
        this.reindexResult = res;
        this.reindexing = false;
        this.loadEdgeManifest();
      },
      error: () => {
        this.reindexing = false;
      },
    });
  }

  triggerFireAlarm(): void {
    swal({
      title: 'เปิดโหมดฉุกเฉิน Fire Alarm?',
      text: 'ระบบจะปลดล็อกประตูทุกโซนอัตโนมัติเพื่อให้ทุกคนอพยพไปยังจุดรวมพล',
      icon: 'warning',
      buttons: ['ยกเลิก', 'ปลดล็อกทุกประตู'],
      dangerMode: true,
    }).then((confirmed) => {
      if (!confirmed) return;
      this.api.triggerFireAlarm(this.companyId, 'Muster Roll Emergency Evacuation').subscribe({
        next: (res) => {
          const count = Number(res?.['unlockedCount'] ?? 0);
          swal('ปลดล็อกแล้ว', `สั่งปลดล็อกประตูทุกโซน (${count} โซน) เรียบร้อย`, 'success');
          this.refreshMuster();
        },
        error: () => swal('Error', 'ไม่สามารถส่งคำสั่ง Fire Alarm ได้', 'error'),
      });
    });
  }

  refreshMuster(): void {
    if (!this.companyId) return;
    this.musterLoading = true;
    this.api
      .getMuster(this.companyId, { limit: this.musterLimit, offset: this.musterOffset })
      .subscribe({
        next: (res) => {
          this.musterLoading = false;
          this.musterItems = res?.items || [];
          this.musterTotal = Number(res?.total || 0);
          this.musterWorkDate = res?.workDate || this.musterWorkDate;
          this.musterLimit = Number(res?.limit || this.musterLimit);
          this.musterOffset = Number(res?.offset || 0);
        },
        error: () => {
          this.musterLoading = false;
        },
      });
  }

  nextPage(): void {
    if (this.musterOffset + this.musterLimit >= this.musterTotal) return;
    this.musterOffset += this.musterLimit;
    this.refreshMuster();
  }

  prevPage(): void {
    if (this.musterOffset <= 0) return;
    this.musterOffset = Math.max(0, this.musterOffset - this.musterLimit);
    this.refreshMuster();
  }

  personKey(person: SentinelMusterRollItem): string {
    return `${person.category}:${person.badgeCode || person.fullName}`;
  }

  isSafe(person: SentinelMusterRollItem): boolean {
    return this.safeKeys.has(this.personKey(person));
  }

  toggleSafe(person: SentinelMusterRollItem): void {
    const key = this.personKey(person);
    if (this.safeKeys.has(key)) {
      this.safeKeys.delete(key);
    } else {
      this.safeKeys.add(key);
    }
    this.saveSafeKeys();
  }

  private safeStorageKey(): string {
    const day = this.musterWorkDate || new Date().toISOString().slice(0, 10);
    return `sv_muster_safe_${this.companyId}_${day}`;
  }

  private loadSafeKeys(): void {
    try {
      const raw = localStorage.getItem(this.safeStorageKey());
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) {
          this.safeKeys = new Set(arr.map(String));
        }
      }
    } catch {
      // ignore storage errors
    }
  }

  private saveSafeKeys(): void {
    try {
      localStorage.setItem(this.safeStorageKey(), JSON.stringify(Array.from(this.safeKeys)));
    } catch {
      // ignore storage errors
    }
  }

  get safeCount(): number {
    return this.musterItems.filter((p) => this.isSafe(p)).length;
  }

  exportMusterCsv(): void {
    downloadMusterCsv(this.musterItems, this.safeKeys, (p) => this.personKey(p));
  }
}
