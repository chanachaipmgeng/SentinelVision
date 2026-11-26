import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { ConfirmDialogService } from '../../../shared/services/confirm-dialog.service';
import { TokenService } from '../../../shared/services/token.service';
import {
  LprScanResult,
  ParkingSpotItem,
  ParkingTransactionItem,
  SentinelApiService,
  VehicleItem,
} from '../sentinel-center/sentinel-api.service';

interface ParkingOverview {
  totalSpots: number;
  occupiedSpots: number;
  availableSpots: number;
  occupancyRate: number;
  totalVehicles: number;
  activeVehicles: number;
  blacklistedVehicles: number;
  entriesToday: number;
  exitsToday: number;
  zoneBreakdown: Array<{
    zone: string;
    total: number;
    occupied: number;
    available: number;
    rate: number;
  }>;
  recentTransactions: ParkingTransactionItem[];
}

@Component({
  selector: 'app-parking',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <app-page-header [title]="'parking.pageTitle' | translate" [activeTitle]="'Vehicle & Parking'" [title1]="'SentinelVision'"></app-page-header>

    <div class="dpu-list-page min-w-0 max-w-full space-y-4">
      <!-- Operational Topbar (Reusable Wrapper) -->
      <app-command-topbar
        icon="ri-parking-box-line"
        accent="cyan"
        [badgeText]="'parking.badge' | translate"
        [title]="'parking.title' | translate"
        [lastUpdated]="lastUpdated"
      >
        <ng-container actions>
          <button
            type="button"
            (click)="openLprModal()"
            class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-cyan-500/40 text-cyan-300 bg-cyan-500/10 hover:bg-cyan-500/20 flex items-center gap-1.5"
          >
            <i class="ri-barcode-box-line"></i>
            <span>{{ 'parking.simLpr' | translate }}</span>
          </button>
          <button
            type="button"
            (click)="openVehicleModal()"
            class="ti-btn ti-btn-primary-full modern-btn text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5"
          >
            <i class="ri-add-line"></i>
            <span>{{ 'parking.addVehicle' | translate }}</span>
          </button>
          <button
            type="button"
            (click)="openSpotModal()"
            class="ti-btn ti-btn-secondary-full modern-btn text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5"
          >
            <i class="ri-layout-grid-line"></i>
            <span>{{ 'parking.addSpot' | translate }}</span>
          </button>
          <button
            type="button"
            (click)="refreshData()"
            [disabled]="loading"
            class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-1.5"
          >
            <i class="ri-refresh-line" [class.animate-spin]="loading"></i>
            <span>{{ 'parking.refresh' | translate }}</span>
          </button>
        </ng-container>
      </app-command-topbar>

      <!-- Universal 6-Segment Metric Ribbon Standard (Reusable Wrapper) -->
      <app-metric-ribbon [columns]="6">
        <!-- Metric 1: Total Spots -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">{{ 'parking.metric.totalSpots' | translate }}</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-slate-100">{{ overview.totalSpots }}</span>
          </div>
          <span class="text-[11px] text-cyan-400 flex items-center gap-1 font-medium">
            <i class="ri-building-line"></i> {{ 'parking.metric.totalCap' | translate }}
          </span>
        </div>

        <!-- Metric 2: Occupied Spots -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">{{ 'parking.metric.occupied' | translate }}</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-amber-400">{{ overview.occupiedSpots }}</span>
          </div>
          <span class="text-[11px] text-amber-300 flex items-center gap-1 font-medium">
            <i class="ri-car-line"></i> {{ 'parking.metric.occupied' | translate }}
          </span>
        </div>

        <!-- Metric 3: Available Spots -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">{{ 'parking.metric.available' | translate }}</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-emerald-400">{{ overview.availableSpots }}</span>
          </div>
          <span class="text-[11px] text-emerald-300 flex items-center gap-1 font-medium">
            <i class="ri-checkbox-circle-line"></i> {{ 'parking.metric.available' | translate }}
          </span>
        </div>

        <!-- Metric 4: Occupancy Rate -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">อัตราการใช้งาน</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold" [ngClass]="overview.occupancyRate >= 90 ? 'text-rose-400' : (overview.occupancyRate >= 70 ? 'text-amber-400' : 'text-cyan-400')">
              {{ overview.occupancyRate }}%
            </span>
          </div>
          <div class="w-full bg-slate-800 rounded-full h-1.5 mt-1 overflow-hidden">
            <div class="h-1.5 rounded-full transition-all duration-500" [ngClass]="overview.occupancyRate >= 90 ? 'bg-rose-500' : (overview.occupancyRate >= 70 ? 'bg-amber-500' : 'bg-cyan-500')" [style.width.%]="overview.occupancyRate"></div>
          </div>
        </div>

        <!-- Metric 5: Registered Vehicles -->
        <div class="p-4 border-b sm:border-b-0 border-r border-dashed border-white/10 flex flex-col justify-between">
          <span class="text-xs text-slate-400">{{ 'parking.metric.vehicles' | translate }}</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-slate-100">{{ overview.totalVehicles }}</span>
          </div>
          <span class="text-[11px] text-slate-400 flex items-center gap-1 font-medium">
            <span class="text-emerald-400 font-mono">{{ overview.activeVehicles }} active</span>
            <span *ngIf="overview.blacklistedVehicles > 0" class="text-rose-400 font-mono">• {{ overview.blacklistedVehicles }} {{ 'parking.metric.blacklist' | translate }}</span>
          </span>
        </div>

        <!-- Metric 6: Today's Flow -->
        <div class="p-4 flex flex-col justify-between">
          <span class="text-xs text-slate-400">{{ 'parking.metric.todayTraffic' | translate }}</span>
          <div class="my-1.5">
            <span class="text-2xl font-mono font-bold text-teal-400">{{ overview.entriesToday }} / {{ overview.exitsToday }}</span>
          </div>
          <span class="text-[11px] text-teal-300 flex items-center gap-1 font-medium">
            <i class="ri-arrow-up-down-line"></i> LPR Gate
          </span>
        </div>
      </app-metric-ribbon>

      <!-- Main Navigation Tabs -->
      <div class="flex items-center gap-2 border-b border-white/10 pb-2">
        <button
          type="button"
          (click)="activeTab = 'grid'"
          class="px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2"
          [ngClass]="activeTab === 'grid' ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200 border border-transparent'"
        >
          <i class="ri-layout-grid-line"></i>
          <span>{{ 'parking.tab.grid' | translate }} ({{ parkingSpots.length }})</span>
        </button>

        <button
          type="button"
          (click)="activeTab = 'vehicles'"
          class="px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2"
          [ngClass]="activeTab === 'vehicles' ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200 border border-transparent'"
        >
          <i class="ri-car-line"></i>
          <span>{{ 'parking.tab.vehicles' | translate }} ({{ vehiclesTotal }})</span>
        </button>

        <button
          type="button"
          (click)="activeTab = 'transactions'"
          class="px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2"
          [ngClass]="activeTab === 'transactions' ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-slate-200 border border-transparent'"
        >
          <i class="ri-history-line"></i>
          <span>{{ 'parking.tab.transactions' | translate }} ({{ transactionsTotal }})</span>
        </button>
      </div>

      <!-- TAB 1: Live Parking Grid -->
      <div *ngIf="activeTab === 'grid'" class="space-y-4">
        <!-- Zone Filter Pills -->
        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            (click)="selectedZone = 'ALL'"
            class="px-3 py-1 rounded-lg text-xs font-medium transition-all"
            [ngClass]="selectedZone === 'ALL' ? 'bg-slate-700 text-white font-semibold' : 'bg-slate-800/60 text-slate-400 hover:text-slate-200'"
          >
            ทุกโซน ({{ parkingSpots.length }})
          </button>
          <button
            *ngFor="let zb of overview.zoneBreakdown"
            type="button"
            (click)="selectedZone = zb.zone"
            class="px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5"
            [ngClass]="selectedZone === zb.zone ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold' : 'bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent'"
          >
            <span>{{ zb.zone }}</span>
            <span class="text-[10px] px-1.5 py-0.2 rounded-full font-mono" [ngClass]="zb.occupied > 0 ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-700 text-slate-300'">
              {{ zb.occupied }}/{{ zb.total }}
            </span>
          </button>
        </div>

        <!-- Spots Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div
            *ngFor="let spot of filteredSpots"
            class="p-3.5 rounded-xl border transition-all relative flex flex-col justify-between"
            [ngClass]="spot.isOccupied ? 'bg-amber-950/20 border-amber-500/30 hover:border-amber-500/50' : 'sv-subpanel border-white/10 hover:border-cyan-500/40'"
          >
            <div class="flex items-start justify-between">
              <div>
                <span class="text-[11px] font-mono text-slate-400 block">{{ spot.zone }} {{ spot.floor ? '• ' + spot.floor : '' }}</span>
                <span class="text-base font-bold font-mono tracking-tight text-slate-100">{{ spot.spotCode }}</span>
              </div>
              <span
                class="px-1.5 py-0.5 rounded text-[10px] font-semibold font-mono"
                [ngClass]="{
                  'bg-amber-500/15 text-amber-300 border border-amber-500/30': spot.spotType === 'VIP',
                  'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30': spot.spotType === 'EV_CHARGING',
                  'bg-sky-500/15 text-sky-300 border border-sky-500/30': spot.spotType === 'HANDICAP',
                  'bg-slate-800 text-slate-400': spot.spotType === 'STANDARD'
                }"
              >
                {{ spot.spotType }}
              </span>
            </div>

            <div class="my-3 min-h-[3rem] flex flex-col justify-center">
              <div *ngIf="spot.isOccupied" class="space-y-1">
                <div class="flex items-center gap-1.5 text-amber-300 font-mono font-bold text-sm">
                  <i class="ri-car-fill"></i>
                  <span>{{ spot.occupiedPlate }}</span>
                </div>
                <div class="text-[10px] text-slate-400 flex items-center gap-1">
                  <i class="ri-time-line"></i>
                  <span>{{ spot.occupiedSince | date: 'HH:mm' }} น.</span>
                </div>
              </div>

              <div *ngIf="!spot.isOccupied" class="flex items-center gap-1.5 text-emerald-400 text-xs">
                <i class="ri-checkbox-circle-line"></i>
                <span class="font-medium">ว่าง พร้อมจอด</span>
              </div>
            </div>

            <div class="pt-2 border-t border-white/5 flex items-center justify-between text-[11px]">
              <span class="text-slate-500 font-mono">{{ spot.status }}</span>
              <button
                type="button"
                (click)="deleteSpot(spot.spotId)"
                class="text-slate-500 hover:text-rose-400 p-0.5 transition-colors"
                title="ลบช่องจอด"
              >
                <i class="ri-delete-bin-line"></i>
              </button>
            </div>
          </div>
        </div>

        <div *ngIf="filteredSpots.length === 0" class="p-8 text-center rounded-2xl border border-white/10 bg-[#070d14] text-slate-400">
          <i class="ri-inbox-line text-3xl mb-2 text-slate-500 block"></i>
          <span>ไม่พบข้อมูลช่องจอดในโซนที่เลือก</span>
        </div>
      </div>

      <!-- TAB 2: Registered Vehicles -->
      <div *ngIf="activeTab === 'vehicles'" class="space-y-4">
        <!-- Search & Filter bar -->
        <div class="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl border border-white/10 bg-[#070d14]">
          <div class="flex items-center gap-2 flex-1 max-w-md">
            <div class="relative w-full">
              <i class="ri-search-line absolute left-3 top-2.5 text-slate-500"></i>
              <input
                type="text"
                [(ngModel)]="vehicleSearch"
                (keyup.enter)="loadVehicles()"
                placeholder="ค้นหาทะเบียน, ชื่อเจ้าของ, ยี่ห้อ..."
                class="w-full bg-slate-900 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <button type="button" (click)="loadVehicles()" class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10">
              ค้นหา
            </button>
          </div>

          <div class="flex items-center gap-2">
            <select
              [(ngModel)]="vehicleOwnerTypeFilter"
              (change)="loadVehicles()"
              class="bg-slate-900 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">ทุกประเภทเจ้าของ</option>
              <option value="EMPLOYEE">พนักงาน (Employee)</option>
              <option value="VIP">ผู้บริหาร / VIP</option>
              <option value="VISITOR">ผู้มาติดต่อ (Visitor)</option>
              <option value="CONTRACTOR">ผู้รับเหมา (Contractor)</option>
            </select>
          </div>
        </div>

        <!-- Vehicles Table -->
        <div class="rounded-xl border border-white/10 bg-[#070d14] overflow-hidden shadow-xl">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead class="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-white/10">
                <tr>
                  <th class="py-3 px-4">ทะเบียนรถ</th>
                  <th class="py-3 px-4">จังหวัด</th>
                  <th class="py-3 px-4">ยานพาหนะ</th>
                  <th class="py-3 px-4">เจ้าของรถ</th>
                  <th class="py-3 px-4">ประเภท</th>
                  <th class="py-3 px-4">สถานะ</th>
                  <th class="py-3 px-4 text-right">การจัดการ</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr *ngFor="let veh of vehicles" class="hover:bg-slate-800/30 transition-colors">
                  <td class="py-3 px-4 font-mono font-bold text-sm text-cyan-300">
                    {{ veh.licensePlate }}
                  </td>
                  <td class="py-3 px-4 text-slate-400">
                    {{ veh.province || '-' }}
                  </td>
                  <td class="py-3 px-4">
                    <div class="flex items-center gap-2">
                      <i class="text-base text-slate-400" [ngClass]="veh.vehicleType === 'MOTORCYCLE' ? 'ri-motorbike-line' : (veh.vehicleType === 'VAN' ? 'ri-bus-line' : 'ri-car-line')"></i>
                      <span>{{ veh.brand }} {{ veh.model }}</span>
                      <span *ngIf="veh.color" class="text-slate-500 font-mono">({{ veh.color }})</span>
                    </div>
                  </td>
                  <td class="py-3 px-4">
                    <div class="font-medium text-slate-200">{{ veh.ownerName || '-' }}</div>
                    <div *ngIf="veh.ownerContact" class="text-[11px] text-slate-500">{{ veh.ownerContact }}</div>
                  </td>
                  <td class="py-3 px-4">
                    <span
                      class="px-2 py-0.5 rounded-full text-[10px] font-semibold font-mono"
                      [ngClass]="{
                        'bg-amber-500/15 text-amber-300 border border-amber-500/30': veh.ownerType === 'VIP',
                        'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30': veh.ownerType === 'EMPLOYEE',
                        'bg-purple-500/15 text-purple-300 border border-purple-500/30': veh.ownerType === 'VISITOR',
                        'bg-slate-800 text-slate-400': veh.ownerType === 'CONTRACTOR'
                      }"
                    >
                      {{ veh.ownerType }}
                    </span>
                  </td>
                  <td class="py-3 px-4">
                    <span
                      class="px-2 py-0.5 rounded-full text-[10px] font-semibold font-mono"
                      [ngClass]="{
                        'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30': veh.status === 'ACTIVE',
                        'bg-rose-500/15 text-rose-300 border border-rose-500/30': veh.status === 'BLACKLISTED',
                        'bg-amber-500/15 text-amber-300 border border-amber-500/30': veh.status === 'SUSPENDED'
                      }"
                    >
                      {{ veh.status }}
                    </span>
                  </td>
                  <td class="py-3 px-4 text-right">
                    <div class="flex items-center justify-end gap-1.5">
                      <button
                        type="button"
                        (click)="editVehicle(veh)"
                        class="p-1 rounded text-slate-400 hover:text-cyan-300 hover:bg-slate-800"
                        title="แก้ไข"
                      >
                        <i class="ri-edit-line"></i>
                      </button>
                      <button
                        type="button"
                        (click)="deleteVehicle(veh.vehicleId)"
                        class="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800"
                        title="ลบ"
                      >
                        <i class="ri-delete-bin-line"></i>
                      </button>
                    </div>
                  </td>
                </tr>

                <tr *ngIf="vehicles.length === 0">
                  <td colspan="7" class="py-8 text-center text-slate-500">
                    ไม่พบข้อมูลยานพาหนะที่ลงทะเบียน
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- TAB 3: LPR Transactions -->
      <div *ngIf="activeTab === 'transactions'" class="space-y-4">
        <div class="rounded-xl border border-white/10 bg-[#070d14] overflow-hidden shadow-xl">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-slate-300">
              <thead class="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-white/10">
                <tr>
                  <th class="py-3 px-4">เวลาเข้า</th>
                  <th class="py-3 px-4">เวลาออก</th>
                  <th class="py-3 px-4">ทะเบียนรถ</th>
                  <th class="py-3 px-4">จุดสแกน (Gate)</th>
                  <th class="py-3 px-4">ระยะเวลาจอด</th>
                  <th class="py-3 px-4">สถานะสิทธิ์</th>
                  <th class="py-3 px-4">คำสั่งไม้กั้น</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-white/5">
                <tr *ngFor="let tx of transactions" class="hover:bg-slate-800/30 transition-colors">
                  <td class="py-3 px-4 font-mono text-slate-300">
                    {{ tx.entryTime | date: 'dd/MM/yyyy HH:mm:ss' }}
                  </td>
                  <td class="py-3 px-4 font-mono text-slate-400">
                    {{ tx.exitTime ? (tx.exitTime | date: 'dd/MM/yyyy HH:mm:ss') : '-' }}
                  </td>
                  <td class="py-3 px-4 font-mono font-bold text-sm text-cyan-300">
                    {{ tx.licensePlate }} <span *ngIf="tx.province" class="text-[10px] text-slate-500 font-normal">({{ tx.province }})</span>
                  </td>
                  <td class="py-3 px-4 text-slate-300">
                    {{ tx.gateIn || tx.gateOut || 'Main Gate' }}
                  </td>
                  <td class="py-3 px-4 font-mono">
                    <span *ngIf="tx.dwellMinutes !== null && tx.dwellMinutes !== undefined" class="text-amber-300">
                      {{ tx.dwellMinutes }} นาที
                    </span>
                    <span *ngIf="tx.dwellMinutes === null || tx.dwellMinutes === undefined" class="text-emerald-400">
                      กำลังจอด
                    </span>
                  </td>
                  <td class="py-3 px-4">
                    <span
                      class="px-2 py-0.5 rounded-full text-[10px] font-semibold font-mono"
                      [ngClass]="{
                        'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30': tx.authStatus === 'AUTHORIZED',
                        'bg-purple-500/15 text-purple-300 border border-purple-500/30': tx.authStatus === 'VISITOR_TEMP',
                        'bg-rose-500/15 text-rose-300 border border-rose-500/30': tx.authStatus === 'DENIED'
                      }"
                    >
                      {{ tx.authStatus }}
                    </span>
                  </td>
                  <td class="py-3 px-4">
                    <span
                      class="inline-flex items-center gap-1 font-mono text-[11px]"
                      [ngClass]="tx.actionTaken === 'BARRIER_OPEN' ? 'text-emerald-400' : 'text-rose-400'"
                    >
                      <i [ngClass]="tx.actionTaken === 'BARRIER_OPEN' ? 'ri-door-open-line' : 'ri-door-lock-line'"></i>
                      {{ tx.actionTaken }}
                    </span>
                  </td>
                </tr>

                <tr *ngIf="transactions.length === 0">
                  <td colspan="7" class="py-8 text-center text-slate-500">
                    ไม่พบประวัติการสแกน LPR
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL 1: LPR Simulator -->
    <div *ngIf="showLprModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-2xl border border-cyan-500/30 bg-[#070d14] p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div class="flex items-center gap-2 text-cyan-400 font-bold">
            <i class="ri-barcode-box-line text-lg"></i>
            <span>จำลองการตรวจจับป้ายทะเบียน LPR Barrier</span>
          </div>
          <button type="button" (click)="showLprModal = false" class="text-slate-400 hover:text-white">
            <i class="ri-close-line text-xl"></i>
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <label class="block text-slate-400 mb-1">ทิศทางการผ่านไม้กั้น</label>
            <div class="grid grid-cols-2 gap-2">
              <button
                type="button"
                (click)="simDirection = 'ENTRY'"
                class="py-2 rounded-lg font-bold transition-all flex items-center justify-center gap-2"
                [ngClass]="simDirection === 'ENTRY' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'bg-slate-800 text-slate-400 border border-transparent'"
              >
                <i class="ri-login-box-line"></i> ขาเข้า (ENTRY)
              </button>
              <button
                type="button"
                (click)="simDirection = 'EXIT'"
                class="py-2 rounded-lg font-bold transition-all flex items-center justify-center gap-2"
                [ngClass]="simDirection === 'EXIT' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-slate-800 text-slate-400 border border-transparent'"
              >
                <i class="ri-logout-box-line"></i> ขาออก (EXIT)
              </button>
            </div>
          </div>

          <div>
            <label class="block text-slate-400 mb-1">เลขทะเบียนรถ (เช่น 9กก9999, 1กข1234, 8ฮฮ8888)</label>
            <input
              type="text"
              [(ngModel)]="simPlate"
              placeholder="กรอกเลขทะเบียนรถทดสอบ"
              class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 font-mono text-sm focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label class="block text-slate-400 mb-1">จุดติดตั้งกล้อง (Gate)</label>
            <input
              type="text"
              [(ngModel)]="simGate"
              placeholder="North Gate Barrier 1"
              class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 text-xs focus:outline-none focus:border-cyan-500"
            />
          </div>

          <!-- LPR Result HUD Display -->
          <div *ngIf="simResult" class="p-4 rounded-xl border transition-all" [ngClass]="simResult.barrierOpen ? 'bg-emerald-950/30 border-emerald-500/40' : 'bg-rose-950/30 border-rose-500/40'">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[11px] font-mono font-semibold" [ngClass]="simResult.barrierOpen ? 'text-emerald-300' : 'text-rose-300'">
                {{ simResult.actionTaken }}
              </span>
              <span class="text-xs font-mono font-bold" [ngClass]="simResult.barrierOpen ? 'text-emerald-400' : 'text-rose-400'">
                {{ simResult.barrierOpen ? 'BARRIER OPEN ✓' : 'BARRIER HOLD ✕' }}
              </span>
            </div>
            <div class="text-sm font-semibold text-slate-100 mb-1">{{ simResult.reason }}</div>
            <div *ngIf="simResult.spotAllocated" class="text-xs text-cyan-300 font-mono">
              จัดสรรช่องจอด: <strong>{{ simResult.spotAllocated.spotCode }}</strong> ({{ simResult.spotAllocated.zone }})
            </div>
            <div *ngIf="simResult.dwellMinutes !== null && simResult.dwellMinutes !== undefined" class="text-xs text-amber-300 font-mono">
              เวลาจอดรวม: {{ simResult.dwellMinutes }} นาที
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
          <button type="button" (click)="showLprModal = false" class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10">
            ปิด
          </button>
          <button
            type="button"
            (click)="triggerLprScan()"
            [disabled]="!simPlate || simLoading"
            class="ti-btn ti-btn-primary-full modern-btn text-xs px-4 py-1.5 rounded-lg flex items-center gap-1.5"
          >
            <i class="ri-flashlight-line" [class.animate-spin]="simLoading"></i>
            <span>ส่งข้อมูลสแกน</span>
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL 2: Register/Edit Vehicle -->
    <div *ngIf="showVehicleModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div class="w-full max-w-lg rounded-2xl border border-white/10 bg-[#070d14] p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div class="flex items-center gap-2 text-cyan-400 font-bold">
            <i class="ri-car-line text-lg"></i>
            <span>{{ editingVehicleId ? 'แก้ไขข้อมูลยานพาหนะ' : 'ลงทะเบียนยานพาหนะใหม่' }}</span>
          </div>
          <button type="button" (click)="showVehicleModal = false" class="text-slate-400 hover:text-white">
            <i class="ri-close-line text-xl"></i>
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">เลขทะเบียนรถ *</label>
              <input
                type="text"
                [(ngModel)]="vehicleForm.licensePlate"
                placeholder="เช่น 9กก9999"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label class="block text-slate-400 mb-1">จังหวัด</label>
              <input
                type="text"
                [(ngModel)]="vehicleForm.province"
                placeholder="เช่น กรุงเทพมหานคร"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">ประเภทรถ</label>
              <select
                [(ngModel)]="vehicleForm.vehicleType"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="CAR">รถยนต์ส่วนบุคคล (Car)</option>
                <option value="MOTORCYCLE">รถจักรยานยนต์ (Motorcycle)</option>
                <option value="VAN">รถตู้ (Van)</option>
                <option value="TRUCK">รถบรรทุก / ขนส่ง (Truck)</option>
              </select>
            </div>
            <div>
              <label class="block text-slate-400 mb-1">กลุ่มผู้ถือครอง (Owner Type)</label>
              <select
                [(ngModel)]="vehicleForm.ownerType"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
              >
                <option value="EMPLOYEE">พนักงาน (Employee)</option>
                <option value="VIP">ผู้บริหาร / VIP</option>
                <option value="VISITOR">ผู้มาติดต่อ (Visitor)</option>
                <option value="CONTRACTOR">ผู้รับเหมา (Contractor)</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-3 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">ยี่ห้อ (Brand)</label>
              <input
                type="text"
                [(ngModel)]="vehicleForm.brand"
                placeholder="Toyota, Tesla"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label class="block text-slate-400 mb-1">รุ่น (Model)</label>
              <input
                type="text"
                [(ngModel)]="vehicleForm.model"
                placeholder="Camry, Model 3"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label class="block text-slate-400 mb-1">สี (Color)</label>
              <input
                type="text"
                [(ngModel)]="vehicleForm.color"
                placeholder="ขาว, ดำ"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">ชื่อเจ้าของรถ</label>
              <input
                type="text"
                [(ngModel)]="vehicleForm.ownerName"
                placeholder="นายสมชาย วงศ์สว่าง"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label class="block text-slate-400 mb-1">เบอร์ติดต่อ</label>
              <input
                type="text"
                [(ngModel)]="vehicleForm.ownerContact"
                placeholder="081-xxx-xxxx"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label class="block text-slate-400 mb-1">สถานะสิทธิ์</label>
            <select
              [(ngModel)]="vehicleForm.status"
              class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="ACTIVE">อนุญาตปกติ (ACTIVE)</option>
              <option value="SUSPENDED">ระงับชั่วคราว (SUSPENDED)</option>
              <option value="BLACKLISTED">ขึ้นบัญชีดำ ห้ามเข้า (BLACKLISTED)</option>
            </select>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
          <button type="button" (click)="showVehicleModal = false" class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10">
            ยกเลิก
          </button>
          <button
            type="button"
            (click)="saveVehicle()"
            [disabled]="!vehicleForm.licensePlate"
            class="ti-btn ti-btn-primary-full modern-btn text-xs px-4 py-1.5 rounded-lg"
          >
            บันทึก
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL 3: Add Parking Spot -->
    <div *ngIf="showSpotModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div class="w-full max-w-md rounded-2xl border border-white/10 bg-[#070d14] p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between border-b border-white/10 pb-3">
          <div class="flex items-center gap-2 text-cyan-400 font-bold">
            <i class="ri-layout-grid-line text-lg"></i>
            <span>เพิ่มช่องจอดรถใหม่</span>
          </div>
          <button type="button" (click)="showSpotModal = false" class="text-slate-400 hover:text-white">
            <i class="ri-close-line text-xl"></i>
          </button>
        </div>

        <div class="space-y-3 text-xs">
          <div>
            <label class="block text-slate-400 mb-1">รหัสช่องจอด * (เช่น A-101, VIP-02)</label>
            <input
              type="text"
              [(ngModel)]="spotForm.spotCode"
              placeholder="A-101"
              class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-slate-400 mb-1">โซน *</label>
              <input
                type="text"
                [(ngModel)]="spotForm.zone"
                placeholder="Zone A"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
            <div>
              <label class="block text-slate-400 mb-1">ชั้น (Floor)</label>
              <input
                type="text"
                [(ngModel)]="spotForm.floor"
                placeholder="1F, B1"
                class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div>
            <label class="block text-slate-400 mb-1">ประเภทช่องจอด</label>
            <select
              [(ngModel)]="spotForm.spotType"
              class="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="STANDARD">ช่องจอดทั่วไป (STANDARD)</option>
              <option value="VIP">ช่องจอดผู้บริหาร / VIP (VIP)</option>
              <option value="EV_CHARGING">จุดชาร์จรถไฟฟ้า (EV_CHARGING)</option>
              <option value="HANDICAP">ช่องจอดผู้พิการ (HANDICAP)</option>
            </select>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
          <button type="button" (click)="showSpotModal = false" class="ti-btn ti-btn-light modern-btn text-xs px-3 py-1.5 rounded-lg border border-white/10">
            ยกเลิก
          </button>
          <button
            type="button"
            (click)="saveSpot()"
            [disabled]="!spotForm.spotCode"
            class="ti-btn ti-btn-primary-full modern-btn text-xs px-4 py-1.5 rounded-lg"
          >
            บันทึกช่องจอด
          </button>
        </div>
      </div>
    </div>
  `,
})
export class ParkingComponent implements OnInit {
  private readonly destroyRef = inject(DestroyRef);
  private readonly confirmDialog = inject(ConfirmDialogService);
  loading = false;
  lastUpdated: Date | null = null;
  activeTab: 'grid' | 'vehicles' | 'transactions' = 'grid';
  selectedZone = 'ALL';

  overview: ParkingOverview = {
    totalSpots: 0,
    occupiedSpots: 0,
    availableSpots: 0,
    occupancyRate: 0,
    totalVehicles: 0,
    activeVehicles: 0,
    blacklistedVehicles: 0,
    entriesToday: 0,
    exitsToday: 0,
    zoneBreakdown: [],
    recentTransactions: [],
  };

  parkingSpots: ParkingSpotItem[] = [];
  vehicles: VehicleItem[] = [];
  vehiclesTotal = 0;
  vehicleSearch = '';
  vehicleOwnerTypeFilter = '';

  transactions: ParkingTransactionItem[] = [];
  transactionsTotal = 0;

  // LPR Simulator State
  showLprModal = false;
  simDirection = 'ENTRY';
  simPlate = '1กข1234';
  simGate = 'North Gate Barrier 1';
  simLoading = false;
  simResult: LprScanResult | null = null;

  // Vehicle Modal State
  showVehicleModal = false;
  editingVehicleId: string | null = null;
  vehicleForm: Partial<VehicleItem> = {
    licensePlate: '',
    province: 'กรุงเทพมหานคร',
    vehicleType: 'CAR',
    ownerType: 'EMPLOYEE',
    brand: '',
    model: '',
    color: '',
    ownerName: '',
    ownerContact: '',
    status: 'ACTIVE',
  };

  // Spot Modal State
  showSpotModal = false;
  spotForm: Partial<ParkingSpotItem> = {
    spotCode: '',
    zone: 'Zone A',
    floor: '1F',
    spotType: 'STANDARD',
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

  get filteredSpots(): ParkingSpotItem[] {
    if (this.selectedZone === 'ALL') {
      return this.parkingSpots;
    }
    return this.parkingSpots.filter((s) => s.zone === this.selectedZone);
  }

  refreshData(): void {
    const cid = this.companyId;
    if (!cid) return;
    this.loading = true;
    this.cdr.markForCheck();

    this.sentinelApi.getParkingOverview(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        this.overview = res;
        this.lastUpdated = new Date();
        this.cdr.markForCheck();
      },
    });

    this.sentinelApi.getParkingSpots(cid).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (spots) => {
        this.parkingSpots = spots;
        this.cdr.markForCheck();
      },
    });

    this.loadVehicles();
    this.loadTransactions();
  }

  loadVehicles(): void {
    const cid = this.companyId;
    if (!cid) return;
    this.sentinelApi
      .getVehicles(cid, this.vehicleSearch, this.vehicleOwnerTypeFilter, 50, 0)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (res) => {
          this.vehicles = res.items;
          this.vehiclesTotal = res.total;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.cdr.markForCheck();
        },
      });
  }

  loadTransactions(): void {
    const cid = this.companyId;
    if (!cid) return;
    this.sentinelApi.getParkingTransactions(cid, undefined, 50, 0).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => {
        this.transactions = res.items;
        this.transactionsTotal = res.total;
        this.cdr.markForCheck();
      },
    });
  }

  openLprModal(): void {
    this.showLprModal = true;
    this.simResult = null;
  }

  triggerLprScan(): void {
    const cid = this.companyId;
    if (!cid || !this.simPlate) return;
    this.simLoading = true;
    this.cdr.markForCheck();

    this.sentinelApi
      .scanLprBarrier(cid, {
        licensePlate: this.simPlate,
        direction: this.simDirection,
        gateName: this.simGate,
        confidence: 0.98,
      })
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (res) => {
          this.simResult = res;
          this.simLoading = false;
          this.refreshData();
          this.cdr.markForCheck();
        },
        error: () => {
          this.simLoading = false;
          this.cdr.markForCheck();
        },
      });
  }

  openVehicleModal(): void {
    this.editingVehicleId = null;
    this.vehicleForm = {
      licensePlate: '',
      province: 'กรุงเทพมหานคร',
      vehicleType: 'CAR',
      ownerType: 'EMPLOYEE',
      brand: '',
      model: '',
      color: '',
      ownerName: '',
      ownerContact: '',
      status: 'ACTIVE',
    };
    this.showVehicleModal = true;
  }

  editVehicle(v: VehicleItem): void {
    this.editingVehicleId = v.vehicleId;
    this.vehicleForm = { ...v };
    this.showVehicleModal = true;
  }

  saveVehicle(): void {
    const cid = this.companyId;
    if (!cid || !this.vehicleForm.licensePlate) return;

    if (this.editingVehicleId) {
      this.sentinelApi.updateVehicle(cid, this.editingVehicleId, this.vehicleForm).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.showVehicleModal = false;
          this.refreshData();
        },
      });
    } else {
      this.sentinelApi.createVehicle(cid, this.vehicleForm).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => {
          this.showVehicleModal = false;
          this.refreshData();
        },
      });
    }
  }

  async deleteVehicle(vehicleId: string): Promise<void> {
    const cid = this.companyId;
    if (!cid) return;
    const confirmed = await this.confirmDialog.confirm({
      title: 'ลบข้อมูลยานพาหนะ',
      message: 'ต้องการลบข้อมูลยานพาหนะนี้หรือไม่?',
      variant: 'danger',
      confirmText: 'ลบข้อมูล',
    });
    if (confirmed) {
      this.sentinelApi.deleteVehicle(cid, vehicleId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => this.refreshData(),
      });
    }
  }

  openSpotModal(): void {
    this.spotForm = {
      spotCode: '',
      zone: 'Zone A',
      floor: '1F',
      spotType: 'STANDARD',
    };
    this.showSpotModal = true;
  }

  saveSpot(): void {
    const cid = this.companyId;
    if (!cid || !this.spotForm.spotCode) return;
    this.sentinelApi.createParkingSpot(cid, this.spotForm).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.showSpotModal = false;
        this.refreshData();
      },
    });
  }

  async deleteSpot(spotId: string): Promise<void> {
    const cid = this.companyId;
    if (!cid) return;
    const confirmed = await this.confirmDialog.confirm({
      title: 'ลบช่องจอดรถ',
      message: 'ต้องการลบช่องจอดนี้หรือไม่?',
      variant: 'danger',
      confirmText: 'ลบช่องจอด',
    });
    if (confirmed) {
      this.sentinelApi.deleteParkingSpot(cid, spotId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: () => this.refreshData(),
      });
    }
  }
}
