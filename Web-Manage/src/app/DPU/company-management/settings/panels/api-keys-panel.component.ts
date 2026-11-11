import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule } from '@ngx-translate/core';
import { TokenService } from '../../../../shared/services/token.service';
import {
  ApiKeyRow,
  CompanySettingsApiService,
} from '../company-settings-api.service';

type PanelStatus = 'idle' | 'created' | 'revoked' | 'error';

const ALL_SCOPES = ['cameras.read', 'incidents.read'] as const;

/** Tenant API keys CRUD — settings hub panel. Plaintext shown once on create. */
@Component({
    selector: 'app-api-keys-panel',
    imports: [CommonModule, FormsModule, TranslateModule],
    template: `
    <div class="box modern-card glass mb-4">
      <div class="box-body space-y-4">
        <div>
          <h6 class="font-bold text-base mb-1">{{ 'settingsHub.apiKeys.title' | translate }}</h6>
          <p class="text-xs text-dpu-muted mb-0">{{ 'settingsHub.apiKeys.hint' | translate }}</p>
        </div>

        <div *ngIf="loading" class="text-xs text-dpu-muted">{{ 'settingsHub.loading' | translate }}</div>

        <div *ngIf="!loading" class="space-y-3">
          <label class="block">
            <span class="text-xs font-semibold text-slate-700">
              {{ 'settingsHub.apiKeys.name' | translate }}
            </span>
            <input
              type="text"
              class="form-control mt-1"
              maxlength="120"
              [(ngModel)]="newName"
              [disabled]="busy"
            />
          </label>

          <div>
            <span class="text-xs font-semibold text-slate-700">
              {{ 'settingsHub.apiKeys.scopes' | translate }}
            </span>
            <div class="mt-1 flex flex-wrap gap-3">
              <label *ngFor="let s of allScopes" class="inline-flex items-center gap-1 text-xs">
                <input type="checkbox" [checked]="scopeOn(s)" (change)="toggleScope(s)" [disabled]="busy" />
                <code>{{ s }}</code>
              </label>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="ti-btn ti-btn-primary-full font-semibold text-xs"
              [disabled]="busy || !newName.trim() || !selectedScopes.length"
              (click)="create()"
            >
              {{ 'settingsHub.apiKeys.create' | translate }}
            </button>
            <span class="text-xs font-semibold text-rose-700" *ngIf="status === 'error'">
              {{ 'settingsHub.apiKeys.error' | translate }}
            </span>
          </div>

          <div
            *ngIf="freshKey"
            class="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs"
          >
            <p class="font-semibold text-amber-900 mb-1">
              {{ 'settingsHub.apiKeys.freshTitle' | translate }}
            </p>
            <code class="break-all select-all">{{ freshKey }}</code>
            <p class="text-amber-800 mt-1 mb-0">
              {{ 'settingsHub.apiKeys.freshHelp' | translate }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="box modern-card glass" *ngIf="!loading">
      <div class="box-body">
        <h6 class="font-bold text-sm mb-3">{{ 'settingsHub.apiKeys.listTitle' | translate }}</h6>
        <p *ngIf="!rows.length" class="text-xs text-dpu-muted mb-0">
          {{ 'settingsHub.apiKeys.empty' | translate }}
        </p>
        <ul class="space-y-2 mb-0" *ngIf="rows.length">
          <li
            *ngFor="let row of rows"
            class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2 last:border-0"
          >
            <div class="min-w-0">
              <p class="mb-0 text-sm font-semibold">{{ row.name }}</p>
              <p class="mb-0 text-[0.7rem] text-dpu-muted">
                <code>{{ row.keyPrefix }}…</code>
                · {{ (row.scopes || []).join(', ') }}
                <span *ngIf="!row.active" class="text-rose-700 font-semibold">
                  · {{ 'settingsHub.apiKeys.revoked' | translate }}
                </span>
              </p>
            </div>
            <button
              type="button"
              class="ti-btn ti-btn-outline-danger font-semibold text-xs"
              *ngIf="row.active"
              [disabled]="busy"
              (click)="revoke(row)"
            >
              {{ 'settingsHub.apiKeys.revoke' | translate }}
            </button>
          </li>
        </ul>
      </div>
    </div>
  `
})
export class ApiKeysPanelComponent implements OnInit {
  @Input() companyId = '';
  @Output() statusFlash = new EventEmitter<string>();

  readonly allScopes = ALL_SCOPES;
  rows: ApiKeyRow[] = [];
  newName = '';
  selectedScopes: string[] = ['cameras.read'];
  freshKey = '';
  loading = false;
  busy = false;
  status: PanelStatus = 'idle';

  constructor(private api: CompanySettingsApiService, private token: TokenService) {}

  ngOnInit(): void {
    if (!this.companyId) {
      this.companyId = this.token.getSelectCompany()?.companyId || '';
    }
    if (!this.companyId) return;
    this.reload();
  }

  scopeOn(code: string): boolean {
    return this.selectedScopes.includes(code);
  }

  toggleScope(code: string): void {
    if (this.scopeOn(code)) {
      this.selectedScopes = this.selectedScopes.filter((s) => s !== code);
    } else {
      this.selectedScopes = [...this.selectedScopes, code];
    }
  }

  private reload(): void {
    this.loading = true;
    this.api.listApiKeys(this.companyId).subscribe({
      next: (rows) => {
        this.rows = rows || [];
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  create(): void {
    if (!this.companyId || this.busy) return;
    this.busy = true;
    this.freshKey = '';
    this.api
      .createApiKey(this.companyId, {
        name: this.newName.trim(),
        scopes: [...this.selectedScopes],
      })
      .subscribe({
        next: (row) => {
          this.busy = false;
          this.status = 'created';
          this.freshKey = row.apiKey || '';
          this.newName = '';
          this.reload();
          this.statusFlash.emit('สร้าง API key แล้ว');
        },
        error: () => {
          this.busy = false;
          this.status = 'error';
        },
      });
  }

  revoke(row: ApiKeyRow): void {
    if (!this.companyId || this.busy || !row?.apiKeyId) return;
    this.busy = true;
    this.api.revokeApiKey(this.companyId, row.apiKeyId).subscribe({
      next: () => {
        this.busy = false;
        this.status = 'revoked';
        this.reload();
        this.statusFlash.emit('ยกเลิก API key แล้ว');
      },
      error: () => {
        this.busy = false;
        this.status = 'error';
      },
    });
  }
}
