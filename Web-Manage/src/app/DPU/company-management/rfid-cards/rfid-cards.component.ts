import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';
import {
  RfidCardItem,
  RfidVerificationResult,
  SentinelApiService,
} from '../sentinel-center/sentinel-api.service';

@Component({
  selector: 'app-rfid-cards',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-page-header [title]="'RFID Physical Access Cards'" [activeTitle]="'Multi-Credential Security'" [title1]="'SentinelVision'"></app-page-header>

    <div class="dpu-list-page min-w-0 max-w-full space-y-4">
      <!-- Operational Topbar -->
      <div class="sv-command-topbar flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl border border-white/10 bg-[#070d14] shadow-xl">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 text-xl shrink-0">
            <i class="ri-bank-card-2-line"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono tracking-wider font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                MULTI-CREDENTIAL PHYSICAL ACCESS GATEWAY
              </span>
              <span *ngIf="lastUpdated" class="text-[11px] text-slate-400">อัปเดตล่าสุด: {{ lastUpdated | date: 'HH:mm:ss' }}</span>
            </div>
            <h2 class="text-base font-bold text-slate-100 mt-0.5 mb-0">ศูนย์บริหารบัตรผ่าน RFID และการยืนยันตัวตนหลายรูปแบบ (Multi-Credential)</h2>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            (click)="openSimulatorModal()"
            class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-purple-500/40 text-purple-300 bg-purple-500/10 hover:bg-purple-500/20 flex items-center gap-1.5"
          >
            <i class="ri-sensor-line"></i>
            <span>จำลองแตะบัตร (Swipe Simulator)</span>
          </button>
          <button
            type="button"
            (click)="openIssueModal()"
            class="ti-btn ti-btn-primary-full modern-btn text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5"
          >
            <i class="ri-add-line"></i>
            <span>ออกบัตร RFID ใหม่</span>
          </button>
          <button
            type="button"
            (click)="refreshData()"
            [disabled]="loading"
            class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-1.5"
          >
            <i class="ri-refresh-line" [class.animate-spin]="loading"></i>
            <span>รีเฟรช</span>
          </button>
        </div>
      </div>

      <!-- Universal 6-Segment Metric Ribbon Standard -->
      <div class="sv-metric-ribbon grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 rounded-2xl border border-white/10 bg-[#070d14] overflow-hidden shadow-lg">
        <!-- Metric 1: Total Badges -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">บัตร RFID ทั้งหมด</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-slate-100">{{ cardsTotal }}</span>
          </div>
          <span class="text-[11px] text-cyan-400 flex items-center gap-1 font-medium">
            <i class="ri-database-2-line"></i> ทะเบียนบัตรในระบบ
          </span>
        </div>

        <!-- Metric 2: Active Badges -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">ใช้งานปกติ (Active)</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-emerald-400">{{ activeCount }}</span>
          </div>
          <span class="text-[11px] text-emerald-300 flex items-center gap-1 font-medium">
            <i class="ri-shield-check-line"></i> ได้รับสิทธิ์ผ่านประตู
          </span>
        </div>

        <!-- Metric 3: Suspended/Lost Badges -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">ระงับ / สูญหาย</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold" [ngClass]="suspendedCount > 0 ? 'text-rose-400' : 'text-slate-400'">{{ suspendedCount }}</span>
          </div>
          <span class="text-[11px] text-rose-300 flex items-center gap-1 font-medium">
            <i class="ri-lock-2-line"></i> ปฏิเสธการเข้าถึง
          </span>
        </div>

        <!-- Metric 4: MIFARE Technology -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">เทคโนโลยี MIFARE</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-purple-400">{{ mifareCount }}</span>
          </div>
          <span class="text-[11px] text-purple-300 flex items-center gap-1 font-medium">
            <i class="ri-cpu-line"></i> 13.56 MHz HF
          </span>
        </div>

        <!-- Metric 5: Employee Badges -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">บัตรพนักงาน</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-cyan-400">{{ employeeCount }}</span>
          </div>
          <span class="text-[11px] text-cyan-300 flex items-center gap-1 font-medium">
            <i class="ri-user-star-line"></i> ผูกตัวตนบุคลากร
          </span>
        </div>

        <!-- Metric 6: Visitor Badges -->
        <div class="p-4 flex flex-col justify-between">
          <span class="text-xs text-slate-400">บัตรผู้มาติดต่อ</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-amber-400">{{ visitorCount }}</span>
          </div>
          <span class="text-[11px] text-amber-300 flex items-center gap-1 font-medium">
            <i class="ri-pass-valid-line"></i> บัตรชั่วคราว / แขก
          </span>
        </div>
      </div>

      <!-- Search & Filters -->
      <div class="flex flex-wrap items-center justify-between gap-3 p-3 lg:pr-28 rounded-xl border border-white/10 bg-[#070d14]">
        <div class="flex items-center gap-2 flex-1 max-w-md">
          <div class="relative w-full">
            <i class="ri-search-line absolute left-3 top-2.5 text-slate-500"></i>
            <input
              type="text"
              [(ngModel)]="searchQuery"
              (keyup.enter)="loadCards()"
              placeholder="ค้นหาเลขบัตร, ชื่อผู้ถือครอง, บันทึก..."
              class="w-full bg-slate-900 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-purple-500"
            />
          </div>
          <button type="button" (click)="loadCards()" class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10">
            ค้นหา
          </button>
        </div>

        <div class="flex items-center gap-2">
          <select
            [(ngModel)]="statusFilter"
            (change)="loadCards()"
            class="bg-slate-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-purple-500"
          >
            <option value="">ทุกสถานะบัตร</option>
            <option value="ACTIVE">ปกติ (ACTIVE)</option>
            <option value="SUSPENDED">ระงับใช้งาน (SUSPENDED)</option>
            <option value="LOST">สูญหาย (LOST)</option>
            <option value="EXPIRED">หมดอายุ (EXPIRED)</option>
          </select>

          <select
            [(ngModel)]="assignedTypeFilter"
            (change)="loadCards()"
            class="bg-slate-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-purple-500"
          >
            <option value="">ทุกประเภทผู้ถือครอง</option>
            <option value="EMPLOYEE">พนักงาน (EMPLOYEE)</option>
            <option value="VISITOR">ผู้มาติดต่อ (VISITOR)</option>
            <option value="CONTRACTOR">ผู้รับเหมา (CONTRACTOR)</option>
          </select>
        </div>
      </div>

      <!-- RFID Cards Table -->
      <div class="rounded-xl border border-white/10 bg-[#070d14] overflow-hidden shadow-xl">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs text-slate-300">
            <thead class="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-white/10">
              <tr>
                <th class="py-3 px-4">เลขบัตร (Card Number)</th>
                <th class="py-3 px-4">Facility Code</th>
                <th class="py-3 px-4">เทคโนโลยี</th>
                <th class="py-3 px-4">ผู้ถือครองบัตร</th>
                <th class="py-3 px-4">ประเภทสิทธิ์</th>
                <th class="py-3 px-4">สถานะบัตร</th>
                <th class="py-3 px-4">การแตะบัตรล่าสุด</th>
                <th class="py-3 px-4 text-right">การจัดการ</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              <tr *ngFor="let card of cards" class="hover:bg-slate-800/30 transition-colors">
                <td class="py-3 px-4 font-mono font-bold text-sm text-purple-300">
                  <div class="flex items-center gap-2">
                    <i class="ri-rfid-fill text-purple-400"></i>
                    <span>{{ card.cardNumber }}</span>
                  </div>
                </td>
                <td class="py-3 px-4 font-mono text-slate-400">
                  {{ card.facilityCode || '-' }}
                </td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-white/5">
                    {{ card.cardType }}
                  </span>
                </td>
                <td class="py-3 px-4 font-medium text-slate-200">
                  {{ card.holderName || '-' }}
                </td>
                <td class="py-3 px-4">
                  <span
                    class="px-2 py-0.5 rounded-full text-[10px] font-semibold font-mono"
                    [ngClass]="{
                      'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30': card.assignedType === 'EMPLOYEE',
                      'bg-purple-500/15 text-purple-300 border border-purple-500/30': card.assignedType === 'VISITOR',
                      'bg-slate-800 text-slate-400': card.assignedType === 'CONTRACTOR'
                    }"
                  >
                    {{ card.assignedType }}
                  </span>
                </td>
                <td class="py-3 px-4">
                  <span
                    class="px-2 py-0.5 rounded-full text-[10px] font-semibold font-mono"
                    [ngClass]="{
                      'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30': card.cardStatus === 'ACTIVE',
                      'bg-amber-500/15 text-amber-300 border border-amber-500/30': card.cardStatus === 'SUSPENDED',
                      'bg-rose-500/15 text-rose-300 border border-rose-500/30': card.cardStatus === 'LOST' || card.cardStatus === 'EXPIRED'
                    }"
                  >
                    {{ card.cardStatus }}
                  </span>
                </td>
                <td class="py-3 px-4 font-mono text-[11px] text-slate-400">
                  <div *ngIf="card.lastSwipedAt">
                    <div class="text-slate-200">{{ card.lastSwipedAt | date: 'dd/MM/yyyy HH:mm:ss' }}</div>
                    <div class="text-[10px] text-slate-500">{{ card.lastDoor || 'Door Sensor' }}</div>
                  </div>
                  <span *ngIf="!card.lastSwipedAt" class="text-slate-600">- ยังไม่มีประวัติ -</span>
                </td>
                <td class="py-3 px-4 text-right">
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      type="button"
                      (click)="toggleStatus(card)"
                      class="px-2 py-1 rounded text-[10px] font-mono transition-colors"
                      [ngClass]="card.cardStatus === 'ACTIVE' ? 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'"
                    >
                      {{ card.cardStatus === 'ACTIVE' ? 'ระงับ' : 'เปิดใช้งาน' }}
                    </button>
                    <button
                      type="button"
                      (click)="editCard(card)"
                      class="p-1 rounded text-slate-400 hover:text-purple-300 hover:bg-slate-800"
                      title="แก้ไข"
                    >
                      <i class="ri-edit-line"></i>
                    </button>
                    <button
                      type="button"
                      (click)="deleteCard(card.cardId)"
                      class="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800"
                      title="ลบ"
                    >
                      <i class="ri-delete-bin-line"></i>
                    </button>
                  </div>
                </td>
              </tr>

              <tr *ngIf="cards.length === 0">
                <td colspan="8" class="py-8 text-center text-slate-500">
                  ไม่พบข้อมูลบัตร RFID ในระบบ
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- MODAL 1: Swipe Simulator -->
    <div *ngIf="showSimulatorModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-2xl border border-purple-500/30 bg-[#070d14] p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div class="flex items-center gap-2 text-purple-400 font-bold">
            <i class="ri-sensor-line text-lg"></i>
            <span>จำลองการแตะบัตรผ่านประตู (Swipe Access Simulator)</span>
          </div>
          <button type="button" (click)="showSimulatorModal = false" class="text-slate-400 hover:text-white">
            <i class="ri-close-line text-xl"></i>
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <label class="block text-slate-400 mb-1">เลขบัตร RFID (Card Number) *</label>
            <input
              type="text"
              [(ngModel)]="simCardNumber"
              placeholder="เช่น E0040150CA8419"
              class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 font-mono text-sm focus:outline-none focus:border-purple-500"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">Facility Code (ตัวเลือก)</label>
              <input
                type="text"
                [(ngModel)]="simFacilityCode"
                placeholder="FAC-01"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
            <div>
              <label class="block text-slate-400 mb-1">ประตูตรวจการเข้าถึง (Door)</label>
              <input
                type="text"
                [(ngModel)]="simDoorName"
                placeholder="Executive Floor Gate"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          <!-- Result HUD Display -->
          <div *ngIf="simResult" class="p-4 rounded-xl border transition-all" [ngClass]="simResult.granted ? 'bg-emerald-950/30 border-emerald-500/40' : 'bg-rose-950/30 border-rose-500/40'">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[11px] font-mono font-semibold" [ngClass]="simResult.granted ? 'text-emerald-300' : 'text-rose-300'">
                {{ simResult.accessStatus }}
              </span>
              <span class="text-xs font-mono font-bold" [ngClass]="simResult.granted ? 'text-emerald-400' : 'text-rose-400'">
                {{ simResult.granted ? 'ACCESS GRANTED ✓' : 'ACCESS DENIED ✕' }}
              </span>
            </div>
            <div class="text-sm font-semibold text-slate-100 mb-1">เหตุผล: {{ simResult.reason }}</div>
            <div *ngIf="simResult.holderName" class="text-xs text-purple-300">
              ผู้ถือครอง: <strong>{{ simResult.holderName }}</strong> ({{ simResult.assignedType }})
            </div>
            <div class="text-[10px] text-slate-400 font-mono mt-1">
              {{ simResult.timestamp | date: 'dd/MM/yyyy HH:mm:ss' }} • {{ simResult.doorName }}
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
          <button type="button" (click)="showSimulatorModal = false" class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10">
            ปิด
          </button>
          <button
            type="button"
            (click)="triggerSwipe()"
            [disabled]="!simCardNumber || simLoading"
            class="ti-btn ti-btn-primary-full modern-btn text-xs px-4 py-1.5 rounded-lg flex items-center gap-1.5"
          >
            <i class="ri-sensor-line" [class.animate-spin]="simLoading"></i>
            <span>ทดสอบแตะบัตร</span>
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL 2: Issue / Edit Card -->
    <div *ngIf="showIssueModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-2xl border border-white/10 bg-[#070d14] p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div class="flex items-center gap-2 text-purple-400 font-bold">
            <i class="ri-rfid-line text-lg"></i>
            <span>{{ editingCardId ? 'แก้ไขข้อมูลบัตร RFID' : 'ออกบัตร RFID ใหม่' }}</span>
          </div>
          <button type="button" (click)="showIssueModal = false" class="text-slate-400 hover:text-white">
            <i class="ri-close-line text-xl"></i>
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">เลขบัตร (Card Number) *</label>
              <input
                type="text"
                [(ngModel)]="cardForm.cardNumber"
                placeholder="เช่น E0040150CA8419"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
            <div>
              <label class="block text-slate-400 mb-1">Facility Code</label>
              <input
                type="text"
                [(ngModel)]="cardForm.facilityCode"
                placeholder="FAC-01"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 font-mono focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">เทคโนโลยีบัตร (Card Type)</label>
              <select
                [(ngModel)]="cardForm.cardType"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
              >
                <option value="MIFARE">MIFARE Classic (13.56MHz)</option>
                <option value="DESFIRE">MIFARE DESFire (High Security)</option>
                <option value="HID_PROX">HID Prox (125kHz)</option>
                <option value="EM4100">EM4100 Standard (125kHz)</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-400 mb-1">ประเภทผู้ถือครอง</label>
              <select
                [(ngModel)]="cardForm.assignedType"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
              >
                <option value="EMPLOYEE">พนักงาน (EMPLOYEE)</option>
                <option value="VISITOR">ผู้มาติดต่อ (VISITOR)</option>
                <option value="CONTRACTOR">ผู้รับเหมา (CONTRACTOR)</option>
              </select>
            </div>
          </div>

          <div>
            <label class="block text-slate-400 mb-1">ชื่อผู้ถือครองบัตร</label>
            <input
              type="text"
              [(ngModel)]="cardForm.holderName"
              placeholder="นางสาววิภาดา สิทธิศักดิ์"
              class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">สถานะบัตร</label>
              <select
                [(ngModel)]="cardForm.cardStatus"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-purple-500"
              >
                <option value="ACTIVE">ปกติ (ACTIVE)</option>
                <option value="SUSPENDED">ระงับใช้งาน (SUSPENDED)</option>
                <option value="LOST">สูญหาย (LOST)</option>
                <option value="EXPIRED">หมดอายุ (EXPIRED)</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-400 mb-1">บันทึกเพิ่มเติม</label>
              <input
                type="text"
                [(ngModel)]="cardForm.notes"
                placeholder="หมายเหตุบัตร"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
          <button type="button" (click)="showIssueModal = false" class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10">
            ยกเลิก
          </button>
          <button
            type="button"
            (click)="saveCard()"
            [disabled]="!cardForm.cardNumber"
            class="ti-btn ti-btn-primary-full modern-btn text-xs px-4 py-1.5 rounded-lg"
          >
            บันทึก
          </button>
        </div>
      </div>
    </div>
  `,
})
export class RfidCardsComponent implements OnInit {
  loading = false;
  lastUpdated: Date | null = null;

  cards: RfidCardItem[] = [];
  cardsTotal = 0;
  searchQuery = '';
  statusFilter = '';
  assignedTypeFilter = '';

  activeCount = 0;
  suspendedCount = 0;
  mifareCount = 0;
  employeeCount = 0;
  visitorCount = 0;

  // Simulator State
  showSimulatorModal = false;
  simCardNumber = 'E0040150CA8419';
  simFacilityCode = 'FAC-01';
  simDoorName = 'Executive Floor Gate';
  simLoading = false;
  simResult: RfidVerificationResult | null = null;

  // Issue Modal State
  showIssueModal = false;
  editingCardId: string | null = null;
  cardForm: Partial<RfidCardItem> = {
    cardNumber: '',
    facilityCode: '',
    cardType: 'MIFARE',
    assignedType: 'EMPLOYEE',
    holderName: '',
    cardStatus: 'ACTIVE',
    notes: '',
  };

  constructor(
    private sentinelApi: SentinelApiService,
    private tokenService: TokenService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.refreshData();
  }

  private get companyId(): string {
    return this.tokenService.getSelectCompany()?.companyId || '';
  }

  refreshData(): void {
    this.loadCards();
  }

  loadCards(): void {
    const cid = this.companyId;
    if (!cid) return;
    this.loading = true;
    this.cdr.markForCheck();

    this.sentinelApi
      .getRfidCards(cid, this.searchQuery, this.statusFilter, this.assignedTypeFilter, 100, 0)
      .subscribe({
        next: (res) => {
          this.cards = res.items;
          this.cardsTotal = res.total;
          this.calculateMetrics(res.items);
          this.lastUpdated = new Date();
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.cdr.markForCheck();
        },
      });
  }

  private calculateMetrics(items: RfidCardItem[]): void {
    this.activeCount = items.filter((c) => c.cardStatus === 'ACTIVE').length;
    this.suspendedCount = items.filter((c) => c.cardStatus === 'SUSPENDED' || c.cardStatus === 'LOST').length;
    this.mifareCount = items.filter((c) => c.cardType === 'MIFARE' || c.cardType === 'DESFIRE').length;
    this.employeeCount = items.filter((c) => c.assignedType === 'EMPLOYEE').length;
    this.visitorCount = items.filter((c) => c.assignedType === 'VISITOR').length;
  }

  openSimulatorModal(): void {
    this.showSimulatorModal = true;
    this.simResult = null;
  }

  triggerSwipe(): void {
    const cid = this.companyId;
    if (!cid || !this.simCardNumber) return;
    this.simLoading = true;
    this.cdr.markForCheck();

    this.sentinelApi
      .verifyRfidAccess(cid, {
        cardNumber: this.simCardNumber,
        facilityCode: this.simFacilityCode,
        doorName: this.simDoorName,
      })
      .subscribe({
        next: (res) => {
          this.simResult = res;
          this.simLoading = false;
          this.loadCards();
          this.cdr.markForCheck();
        },
        error: () => {
          this.simLoading = false;
          this.cdr.markForCheck();
        },
      });
  }

  openIssueModal(): void {
    this.editingCardId = null;
    this.cardForm = {
      cardNumber: '',
      facilityCode: '',
      cardType: 'MIFARE',
      assignedType: 'EMPLOYEE',
      holderName: '',
      cardStatus: 'ACTIVE',
      notes: '',
    };
    this.showIssueModal = true;
  }

  editCard(c: RfidCardItem): void {
    this.editingCardId = c.cardId;
    this.cardForm = { ...c };
    this.showIssueModal = true;
  }

  saveCard(): void {
    const cid = this.companyId;
    if (!cid || !this.cardForm.cardNumber) return;

    if (this.editingCardId) {
      this.sentinelApi.updateRfidCard(cid, this.editingCardId, this.cardForm).subscribe({
        next: () => {
          this.showIssueModal = false;
          this.loadCards();
        },
      });
    } else {
      this.sentinelApi.issueRfidCard(cid, this.cardForm).subscribe({
        next: () => {
          this.showIssueModal = false;
          this.loadCards();
        },
      });
    }
  }

  toggleStatus(card: RfidCardItem): void {
    const cid = this.companyId;
    if (!cid) return;
    const nextStatus = card.cardStatus === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    this.sentinelApi.updateRfidCardStatus(cid, card.cardId, nextStatus).subscribe({
      next: () => this.loadCards(),
    });
  }

  deleteCard(cardId: string): void {
    const cid = this.companyId;
    if (!cid) return;
    if (confirm('ต้องการลบข้อมูลบัตร RFID นี้หรือไม่?')) {
      this.sentinelApi.deleteRfidCard(cid, cardId).subscribe({
        next: () => this.loadCards(),
      });
    }
  }
}
