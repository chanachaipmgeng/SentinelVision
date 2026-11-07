import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SharedModule } from '../../../shared/shared.module';
import { TokenService } from '../../../shared/services/token.service';

@Component({
  selector: 'app-hr-schedule',
  standalone: true,
  imports: [CommonModule, FormsModule, SharedModule],
  template: `
    <app-page-header
      [title]="'กะทำงาน / วันลา / วันหยุด / PDPA / Kiosk 2FA / Webhook & Observability'"
      [activeTitle]="'จัดการข้อมูลการลงเวลา'"
      [title1]="'กะงาน / วันลา / PDPA / Cloud'"
    ></app-page-header>

    <div class="grid grid-cols-12 gap-6">
      <div class="col-span-12">
        <div class="box">
          <div class="box-header flex flex-wrap items-center justify-between gap-2">
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="ti-btn"
                [ngClass]="activeTab === 'shifts' ? 'ti-btn-primary-full' : 'ti-btn-light'"
                (click)="activeTab = 'shifts'"
              >
                <i class="ri-time-line me-1"></i> กะเวลาทำงาน (Multi-Shift)
              </button>
              <button
                type="button"
                class="ti-btn"
                [ngClass]="activeTab === 'leaves' ? 'ti-btn-primary-full' : 'ti-btn-light'"
                (click)="activeTab = 'leaves'"
              >
                <i class="ri-calendar-check-line me-1"></i> ใบลาและการอนุมัติ
              </button>
              <button
                type="button"
                class="ti-btn"
                [ngClass]="activeTab === 'holidays' ? 'ti-btn-primary-full' : 'ti-btn-light'"
                (click)="activeTab = 'holidays'"
              >
                <i class="ri-calendar-event-line me-1"></i> ปฏิทินวันหยุดบริษัท
              </button>
              <button
                type="button"
                class="ti-btn"
                [ngClass]="activeTab === 'pdpa' ? 'ti-btn-primary-full' : 'ti-btn-light'"
                (click)="activeTab = 'pdpa'"
              >
                <i class="ri-shield-user-line me-1"></i> PDPA &amp; ข้อมูลชีวมิติ
              </button>
              <button
                type="button"
                class="ti-btn"
                [ngClass]="activeTab === 'security' ? 'ti-btn-primary-full' : 'ti-btn-light'"
                (click)="activeTab = 'security'"
              >
                <i class="ri-key-2-line me-1"></i> อุปกรณ์ Kiosk &amp; 2FA
              </button>
              <button
                type="button"
                class="ti-btn"
                [ngClass]="activeTab === 'observability' ? 'ti-btn-primary-full' : 'ti-btn-light'"
                (click)="switchToObservability()"
              >
                <i class="ri-pulse-line me-1"></i> Payroll Webhook &amp; Cloud Metrics
              </button>
            </div>
            <span *ngIf="statusMsg" class="badge bg-success/10 text-success px-3 py-1">
              {{ statusMsg }}
            </span>
          </div>

          <!-- TAB 1: WORK SHIFTS & ASSIGNMENT -->
          <div class="box-body space-y-6" *ngIf="activeTab === 'shifts'">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 lg:col-span-5 p-4 rounded-lg border border-defaultborder">
                <h6 class="font-semibold mb-3">เพิ่มกะเวลาทำงานใหม่ (รองรับกะข้ามคืน)</h6>
                <div class="grid grid-cols-12 gap-3">
                  <div class="col-span-12">
                    <label class="form-label">ชื่อกะทำงาน</label>
                    <input class="form-control" [(ngModel)]="newShift.name" placeholder="เช่น กะเช้า / กะดึกข้ามคืน" />
                  </div>
                  <div class="col-span-6">
                    <label class="form-label">เวลาเข้างาน (HH:MM)</label>
                    <input type="time" class="form-control" [(ngModel)]="newShift.startTime" />
                  </div>
                  <div class="col-span-6">
                    <label class="form-label">เวลาเลิกงาน (HH:MM)</label>
                    <input type="time" class="form-control" [(ngModel)]="newShift.endTime" />
                  </div>
                  <div class="col-span-4">
                    <label class="form-label">อนุโลมสาย (นาที)</label>
                    <input type="number" min="0" max="180" class="form-control" [(ngModel)]="newShift.graceMinutes" />
                  </div>
                  <div class="col-span-4">
                    <label class="form-label">ปัดเวลา (นาที)</label>
                    <input type="number" min="0" max="60" class="form-control" [(ngModel)]="newShift.roundingMinutes" />
                  </div>
                  <div class="col-span-4">
                    <label class="form-label">พัก (นาที)</label>
                    <input type="number" min="0" max="480" class="form-control" [(ngModel)]="newShift.breakMinutes" />
                  </div>
                  <div class="col-span-6">
                    <label class="form-label">เกณฑ์ OT หลังเลิกงาน (นาที)</label>
                    <input type="number" min="0" max="480" class="form-control" [(ngModel)]="newShift.otThresholdMinutes" />
                  </div>
                  <div class="col-span-6 flex flex-col justify-end gap-2">
                    <label class="flex items-center gap-2 text-sm cursor-pointer">
                      <input type="checkbox" [(ngModel)]="newShift.isCrossMidnight" />
                      <span>กะข้ามเที่ยงคืน (Night Shift)</span>
                    </label>
                    <label class="flex items-center gap-2 text-sm cursor-pointer">
                      <input type="checkbox" [(ngModel)]="newShift.isDefault" />
                      <span>ตั้งเป็นกะหลักของบริษัท</span>
                    </label>
                  </div>
                  <div class="col-span-12">
                    <button type="button" class="ti-btn ti-btn-primary-full w-full" (click)="createShift()">
                      + บันทึกกะเวลาทำงาน
                    </button>
                  </div>
                </div>
              </div>

              <div class="col-span-12 lg:col-span-7 p-4 rounded-lg border border-defaultborder">
                <h6 class="font-semibold mb-3">รายการกะเวลาทำงานทั้งหมด ({{ shifts.length }})</h6>
                <div class="table-responsive">
                  <table class="table whitespace-nowrap min-w-full">
                    <thead>
                      <tr class="border-b border-defaultborder">
                        <th class="text-start">ชื่อกะ</th>
                        <th class="text-start">เวลาเข้า - ออก</th>
                        <th class="text-start">อนุโลม / ปัด / พัก / OT</th>
                        <th class="text-start">รูปแบบ</th>
                        <th class="text-end">จัดการ</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let s of shifts" class="border-b border-defaultborder">
                        <td class="font-medium">
                          {{ s.name }}
                          <span *ngIf="s.isDefault" class="badge bg-primary/10 text-primary ms-1">Default</span>
                        </td>
                        <td>{{ s.startTime }} - {{ s.endTime }}</td>
                        <td>
                          สาย {{ s.graceMinutes }} · ปัด {{ s.roundingMinutes || 0 }} · พัก
                          {{ s.breakMinutes || 0 }} · OT≥{{ s.otThresholdMinutes || 0 }}
                        </td>
                        <td>
                          <span *ngIf="s.isCrossMidnight" class="badge bg-warning/10 text-warning">ข้ามคืน</span>
                          <span *ngIf="!s.isCrossMidnight" class="badge bg-success/10 text-success">ปกติ</span>
                        </td>
                        <td class="text-end">
                          <button type="button" class="ti-btn ti-btn-sm ti-btn-danger" (click)="deleteShift(s.shiftId)">
                            ลบ
                          </button>
                        </td>
                      </tr>
                      <tr *ngIf="shifts.length === 0">
                        <td colspan="5" class="text-center text-gray-500 py-4">
                          ยังไม่มีกะเพิ่มเติม (ระบบใช้ค่ากะหลักของบริษัท)
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Assign shift to Department or Employee -->
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 lg:col-span-6 p-4 rounded-lg border border-defaultborder">
                <h6 class="font-semibold mb-3">ผูกกะเวลาทำงานตามแผนก (Department Shift)</h6>
                <div class="table-responsive">
                  <table class="table whitespace-nowrap min-w-full">
                    <thead>
                      <tr class="border-b border-defaultborder">
                        <th class="text-start">แผนก</th>
                        <th class="text-start">กะเวลาทำงาน</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let d of departments" class="border-b border-defaultborder">
                        <td>{{ d.thName }} ({{ d.engName }})</td>
                        <td>
                          <select
                            class="form-control form-control-sm"
                            [ngModel]="d.shiftId || ''"
                            (ngModelChange)="assignDeptShift(d.departmentId, $event)"
                          >
                            <option value="">-- ใช้กะหลักของบริษัท --</option>
                            <option *ngFor="let s of shifts" [value]="s.shiftId">
                              {{ s.name }} ({{ s.startTime }}-{{ s.endTime }})
                            </option>
                          </select>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="col-span-12 lg:col-span-6 p-4 rounded-lg border border-defaultborder">
                <h6 class="font-semibold mb-3">ผูกกะเวลาทำงานรายบุคคล (Employee Override)</h6>
                <div class="table-responsive max-h-80 overflow-y-auto">
                  <table class="table whitespace-nowrap min-w-full">
                    <thead>
                      <tr class="border-b border-defaultborder">
                        <th class="text-start">พนักงาน</th>
                        <th class="text-start">แผนก</th>
                        <th class="text-start">กะเฉพาะบุคคล</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let emp of employees" class="border-b border-defaultborder">
                        <td>{{ emp.member?.firstName }} {{ emp.member?.lastName }} ({{ emp.employeeId || '-' }})</td>
                        <td>{{ emp.department?.thName || '-' }}</td>
                        <td>
                          <select
                            class="form-control form-control-sm"
                            [ngModel]="emp.shiftId || ''"
                            (ngModelChange)="assignEmpShift(emp.company_employeeId, $event)"
                          >
                            <option value="">-- ตามแผนก / กะหลัก --</option>
                            <option *ngFor="let s of shifts" [value]="s.shiftId">
                              {{ s.name }} ({{ s.startTime }}-{{ s.endTime }})
                            </option>
                          </select>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 2: LEAVE MANAGEMENT -->
          <div class="box-body space-y-6" *ngIf="activeTab === 'leaves'">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 lg:col-span-4 p-4 rounded-lg border border-defaultborder">
                <h6 class="font-semibold mb-3">ยื่นใบลา / บันทึกวันลาพนักงาน</h6>
                <div class="space-y-3">
                  <div>
                    <label class="form-label">เลือกพนักงาน</label>
                    <select class="form-control" [(ngModel)]="newLeave.company_employeeId">
                      <option value="">-- เลือกพนักงาน --</option>
                      <option *ngFor="let emp of employees" [value]="emp.company_employeeId">
                        {{ emp.member?.firstName }} {{ emp.member?.lastName }} ({{ emp.employeeId || emp.member?.email }})
                      </option>
                    </select>
                  </div>
                  <div>
                    <label class="form-label">ประเภทการลา</label>
                    <select class="form-control" [(ngModel)]="newLeave.leaveType">
                      <option value="ANNUAL">ลาพักร้อน (ANNUAL)</option>
                      <option value="SICK">ลาป่วย (SICK)</option>
                      <option value="PERSONAL">ลากิจ (PERSONAL)</option>
                      <option value="WFH">ปฏิบัติงานนอกสถานที่ (WFH)</option>
                    </select>
                  </div>
                  <div class="grid grid-cols-2 gap-2">
                    <div>
                      <label class="form-label">ตั้งแต่วันที่</label>
                      <input type="date" class="form-control" [(ngModel)]="newLeave.startDate" />
                    </div>
                    <div>
                      <label class="form-label">ถึงวันที่</label>
                      <input type="date" class="form-control" [(ngModel)]="newLeave.endDate" />
                    </div>
                  </div>
                  <div>
                    <label class="form-label">เหตุผลการลา</label>
                    <input class="form-control" [(ngModel)]="newLeave.reason" placeholder="ระบุรายละเอียด..." />
                  </div>
                  <button type="button" class="ti-btn ti-btn-primary-full w-full" (click)="createLeave()">
                    + บันทึกคำขอลา
                  </button>
                </div>
              </div>

              <div class="col-span-12 lg:col-span-8 p-4 rounded-lg border border-defaultborder">
                <h6 class="font-semibold mb-3">รายการใบลาและสถานะการอนุมัติ ({{ leaves.length }})</h6>
                <p class="text-xs text-gray-500 mb-3">
                  * พนักงานที่ได้รับอนุมัติวันลา (APPROVED) จะถูกยกเว้นจากการแจ้งเตือนขาดงานอัตโนมัติในวันดังกล่าว
                </p>
                <div class="table-responsive">
                  <table class="table whitespace-nowrap min-w-full">
                    <thead>
                      <tr class="border-b border-defaultborder">
                        <th class="text-start">พนักงาน</th>
                        <th class="text-start">ประเภท</th>
                        <th class="text-start">ช่วงวันที่</th>
                        <th class="text-start">เหตุผล</th>
                        <th class="text-start">สถานะ</th>
                        <th class="text-end">การอนุมัติ</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let l of leaves" class="border-b border-defaultborder">
                        <td class="font-medium">{{ l.employeeName }} ({{ l.employeeCode || '-' }})</td>
                        <td><span class="badge bg-primary/10 text-primary">{{ l.leaveType }}</span></td>
                        <td>{{ l.startDate }} ถึง {{ l.endDate }}</td>
                        <td>{{ l.reason || '-' }}</td>
                        <td>
                          <span *ngIf="l.status === 0" class="badge bg-warning/10 text-warning">รออนุมัติ</span>
                          <span *ngIf="l.status === 1" class="badge bg-success/10 text-success">อนุมัติแล้ว</span>
                          <span *ngIf="l.status === 2" class="badge bg-danger/10 text-danger">ไม่อนุมัติ</span>
                        </td>
                        <td class="text-end space-x-1">
                          <button
                            *ngIf="l.status === 0"
                            type="button"
                            class="ti-btn ti-btn-sm ti-btn-success"
                            (click)="decideLeave(l.leaveId, 1)"
                          >
                            อนุมัติ
                          </button>
                          <button
                            *ngIf="l.status === 0"
                            type="button"
                            class="ti-btn ti-btn-sm ti-btn-danger"
                            (click)="decideLeave(l.leaveId, 2)"
                          >
                            ปฏิเสธ
                          </button>
                        </td>
                      </tr>
                      <tr *ngIf="leaves.length === 0">
                        <td colspan="6" class="text-center text-gray-500 py-4">ยังไม่มีรายการใบลา</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 3: COMPANY HOLIDAYS -->
          <div class="box-body space-y-6" *ngIf="activeTab === 'holidays'">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 lg:col-span-4 p-4 rounded-lg border border-defaultborder space-y-4">
                <div>
                  <h6 class="font-semibold mb-3">เพิ่มวันหยุดประจำปีของบริษัท</h6>
                  <div class="space-y-3">
                    <div>
                      <label class="form-label">วันที่หยุด</label>
                      <input type="date" class="form-control" [(ngModel)]="newHoliday.holidayDate" />
                    </div>
                    <div>
                      <label class="form-label">ชื่อวันหยุด</label>
                      <input class="form-control" [(ngModel)]="newHoliday.name" placeholder="เช่น วันสงกรานต์ / วันขึ้นปีใหม่" />
                    </div>
                    <button type="button" class="ti-btn ti-btn-primary-full w-full" (click)="createHoliday()">
                      + เพิ่มวันหยุดบริษัท
                    </button>
                  </div>
                </div>

                <div class="border-t border-defaultborder pt-4 space-y-3">
                  <h6 class="font-semibold">นำเข้า / Preset</h6>
                  <div class="flex flex-wrap gap-2">
                    <button type="button" class="ti-btn ti-btn-outline-primary" (click)="applyThaiHolidayPreset()" [disabled]="holidayBusy">
                      โหลดวันหยุดราชการไทย {{ holidayPresetYear }}
                    </button>
                  </div>
                  <div>
                    <label class="form-label">นำเข้าไฟล์ CSV หรือ iCal (.ics)</label>
                    <input type="file" class="form-control" accept=".csv,.ics,.ical,text/csv,text/calendar" (change)="onHolidayFileSelected($event)" />
                  </div>
                  <p class="text-xs text-gray-500" *ngIf="holidayImportHint">{{ holidayImportHint }}</p>
                </div>
              </div>

              <div class="col-span-12 lg:col-span-8 p-4 rounded-lg border border-defaultborder">
                <h6 class="font-semibold mb-3">ปฏิทินวันหยุดบริษัท ({{ holidays.length }})</h6>
                <p class="text-xs text-gray-500 mb-3">
                  * ระบบแจ้งเตือนขาดงานอัตโนมัติ (Cutoff Notification) และเมตริก Late/OT จะข้ามวันหยุดที่บันทึกไว้ในตารางนี้
                </p>
                <div class="table-responsive">
                  <table class="table whitespace-nowrap min-w-full">
                    <thead>
                      <tr class="border-b border-defaultborder">
                        <th class="text-start">วันที่</th>
                        <th class="text-start">ชื่อวันหยุด</th>
                        <th class="text-start">แหล่งที่มา</th>
                        <th class="text-end">จัดการ</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let h of holidays" class="border-b border-defaultborder">
                        <td class="font-medium">{{ h.holidayDate }}</td>
                        <td>{{ h.name }}</td>
                        <td class="text-xs text-gray-500">{{ holidaySourceLabel(h.source) }}</td>
                        <td class="text-end">
                          <button type="button" class="ti-btn ti-btn-sm ti-btn-danger" (click)="deleteHoliday(h.holidayId)">
                            ลบ
                          </button>
                        </td>
                      </tr>
                      <tr *ngIf="holidays.length === 0">
                        <td colspan="4" class="text-center text-gray-500 py-4">ยังไม่ได้กำหนดวันหยุดประจำปี</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 4: PDPA & BIOMETRIC COMPLIANCE -->
          <div class="box-body space-y-6" *ngIf="activeTab === 'pdpa'">
            <div class="grid grid-cols-12 gap-4" *ngIf="pdpaSummary">
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
                <div class="text-xs text-gray-500">พนักงานทั้งหมด</div>
                <div class="text-2xl font-bold mt-1">{{ pdpaSummary.totalEmployees }} คน</div>
              </div>
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-success/5 border border-success/20">
                <div class="text-xs text-gray-500">ยินยอมใช้ข้อมูลชีวมิติ (PDPA Consent)</div>
                <div class="text-2xl font-bold text-success mt-1">{{ pdpaSummary.consentedEmployees }} คน</div>
              </div>
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-info/5 border border-info/20">
                <div class="text-xs text-gray-500">ลงทะเบียนใบหน้าแล้ว</div>
                <div class="text-2xl font-bold text-info mt-1">{{ pdpaSummary.enrolledEmployees }} คน</div>
              </div>
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-warning/5 border border-warning/20">
                <div class="text-xs text-gray-500">นโยบายจัดเก็บภาพถ่ายลงเวลา</div>
                <div class="text-lg font-bold text-warning mt-1">
                  {{ pdpaSummary.retentionPolicy?.imageRetentionDays }} วัน (Temp {{ pdpaSummary.retentionPolicy?.tempRetentionHours }} ชม.)
                </div>
              </div>
            </div>

            <div class="p-4 rounded-lg border border-defaultborder space-y-3" *ngIf="consentPolicy">
              <h6 class="font-semibold">ข้อความและเวอร์ชันความยินยอม (แสดงบน Kiosk / Enroll)</h6>
              <div class="grid grid-cols-12 gap-3">
                <div class="col-span-12 md:col-span-3">
                  <label class="form-label text-xs">เวอร์ชัน</label>
                  <input class="form-control" [(ngModel)]="consentPolicy.version" />
                </div>
                <div class="col-span-12 md:col-span-9">
                  <label class="form-label text-xs">ข้อความ (ไทย)</label>
                  <textarea class="form-control" rows="3" [(ngModel)]="consentPolicy.textTh"></textarea>
                </div>
                <div class="col-span-12">
                  <label class="form-label text-xs">ข้อความ (อังกฤษ)</label>
                  <textarea class="form-control" rows="3" [(ngModel)]="consentPolicy.textEn"></textarea>
                </div>
              </div>
              <button type="button" class="ti-btn ti-btn-primary-full" (click)="saveConsentPolicy()">บันทึกนโยบายความยินยอม</button>
            </div>

            <div class="p-4 rounded-lg border border-defaultborder space-y-3" *ngIf="retentionSettings">
              <h6 class="font-semibold">Retention ต่อชนิดข้อมูล (วัน / ชม.)</h6>
              <div class="grid grid-cols-12 gap-3">
                <div class="col-span-6 md:col-span-3">
                  <label class="form-label text-xs">Biometric (วัน)</label>
                  <input type="number" class="form-control" [(ngModel)]="retentionSettings.biometricDays" />
                </div>
                <div class="col-span-6 md:col-span-3">
                  <label class="form-label text-xs">Punch photo (วัน)</label>
                  <input type="number" class="form-control" [(ngModel)]="retentionSettings.punchPhotoDays" />
                </div>
                <div class="col-span-6 md:col-span-3">
                  <label class="form-label text-xs">Incident snapshot (วัน)</label>
                  <input type="number" class="form-control" [(ngModel)]="retentionSettings.incidentSnapshotDays" />
                </div>
                <div class="col-span-6 md:col-span-3">
                  <label class="form-label text-xs">Temp (ชม.)</label>
                  <input type="number" class="form-control" [(ngModel)]="retentionSettings.tempHours" />
                </div>
              </div>
              <button type="button" class="ti-btn ti-btn-primary-full" (click)="saveRetentionSettings()">บันทึก Retention</button>
            </div>

            <div class="p-4 rounded-lg border border-defaultborder">
              <h6 class="font-semibold mb-3">การจัดการความยินยอมข้อมูลชีวมิติรายบุคคล (PDPA Right to Erasure)</h6>
              <p class="text-xs text-gray-500 mb-3">
                * การเพิกถอน/Erasure จะลบ encodings, ภาพ punch และ incident snapshots ของพนักงานทันที
              </p>
              <div class="table-responsive">
                <table class="table whitespace-nowrap min-w-full">
                  <thead>
                    <tr class="border-b border-defaultborder">
                      <th class="text-start">พนักงาน</th>
                      <th class="text-start">อีเมล</th>
                      <th class="text-start">วันที่ให้ความยินยอม (PDPA Consent)</th>
                      <th class="text-end">จัดการข้อมูลชีวมิติ</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let emp of employees" class="border-b border-defaultborder">
                      <td class="font-medium">{{ emp.member?.firstName }} {{ emp.member?.lastName }}</td>
                      <td>{{ emp.member?.email }}</td>
                      <td>
                        <span *ngIf="emp.member?.biometricConsentAt" class="badge bg-success/10 text-success">
                          {{ emp.member.biometricConsentAt | date: 'dd/MM/yyyy HH:mm' }}
                        </span>
                        <span *ngIf="!emp.member?.biometricConsentAt" class="badge bg-gray-100 text-gray-600">
                          ยังไม่ระบุ / รอลงทะเบียน
                        </span>
                      </td>
                      <td class="text-end space-x-2">
                        <button
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-light"
                          (click)="exportDsar(emp.member?.memberId)"
                        >
                          DSAR
                        </button>
                        <button
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-success"
                          (click)="grantConsent(emp.member?.memberId)"
                        >
                          บันทึกความยินยอม
                        </button>
                        <button
                          type="button"
                          class="ti-btn ti-btn-sm ti-btn-danger"
                          (click)="revokeConsent(emp.member?.memberId)"
                        >
                          Erasure
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- TAB 5: KIOSK DEVICE TOKENS & 2FA MFA -->
          <div class="box-body space-y-6" *ngIf="activeTab === 'security'">
            <div class="grid grid-cols-12 gap-4">
              <div class="col-span-12 lg:col-span-6 p-4 rounded-lg border border-defaultborder space-y-4">
                <h6 class="font-semibold">ลงทะเบียนตู้ Kiosk ประจำจุดสแกน (จับคู่ด้วยรหัสครั้งเดียว)</h6>
                <p class="text-xs text-gray-500">
                  สร้างอุปกรณ์แล้วนำรหัสจับคู่ 8 หลักไปกรอกบนแท็บเล็ตที่หน้า <span class="font-mono">/kiosk/pair</span>
                  อุปกรณ์จะได้รับ Token เฉพาะเครื่องอายุสั้น (ต่ออายุอัตโนมัติ) ที่จำกัดสิทธิ์เฉพาะการสแกนใบหน้าลงเวลา
                  ไม่สามารถเข้าถึงเมนูจัดการพนักงานหรือตั้งค่าบริษัทได้ และไม่มี Token ปรากฏใน URL
                </p>
                <div class="flex gap-2">
                  <input
                    class="form-control"
                    [(ngModel)]="newKioskName"
                    placeholder="ชื่อจุดติดตั้ง เช่น ตู้ Kiosk อาคาร 1 ชั้น 1"
                  />
                  <button type="button" class="ti-btn ti-btn-primary-full whitespace-nowrap" (click)="createKioskDevice()">
                    + สร้างอุปกรณ์และรหัสจับคู่
                  </button>
                </div>

                <div *ngIf="issuedKiosk" class="p-3 rounded bg-success/10 border border-success/30 text-xs space-y-2">
                  <div class="font-semibold text-success">
                    รหัสจับคู่สำหรับ "{{ issuedKiosk.name }}" (แสดงครั้งเดียว ใช้ได้ {{ issuedKiosk.pairingCodeTtlMinutes || 10 }} นาที):
                  </div>
                  <div class="font-mono text-2xl tracking-[0.35em] text-center bg-white dark:bg-bodybg p-3 rounded border select-all">
                    {{ issuedKiosk.pairingCode }}
                  </div>
                  <div class="text-gray-500">
                    บนแท็บเล็ต: เปิด <span class="font-mono">{{ pairPageUrl }}</span> แล้วกรอกรหัสนี้ หากหมดอายุให้กด "ออกรหัสใหม่" ที่แถวอุปกรณ์
                  </div>
                </div>

                <div class="table-responsive">
                  <table class="table whitespace-nowrap min-w-full">
                    <thead>
                      <tr class="border-b border-defaultborder">
                        <th class="text-start">ชื่ออุปกรณ์ Kiosk</th>
                        <th class="text-start">เชื่อมต่อล่าสุด</th>
                        <th class="text-start">สถานะ</th>
                        <th class="text-end">จัดการ</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let kd of kioskDevices" class="border-b border-defaultborder">
                        <td class="font-medium">{{ kd.name }}</td>
                        <td>{{ kd.lastSeenAt ? (kd.lastSeenAt | date: 'dd/MM/yyyy HH:mm') : 'ยังไม่เชื่อมต่อ' }}</td>
                        <td>
                          <span *ngIf="!kd.isActive" class="badge bg-danger/10 text-danger">เพิกถอนแล้ว</span>
                          <span *ngIf="kd.isActive && kd.isPaired" class="badge bg-success/10 text-success">จับคู่แล้ว</span>
                          <span *ngIf="kd.isActive && !kd.isPaired && kd.pairingPending" class="badge bg-warning/10 text-warning">
                            รอจับคู่ (หมดอายุ {{ kd.pairingExpiresAt | date: 'HH:mm' }})
                          </span>
                          <span *ngIf="kd.isActive && !kd.isPaired && !kd.pairingPending" class="badge bg-gray-200/60 text-gray-600">
                            ยังไม่จับคู่ / รหัสหมดอายุ
                          </span>
                        </td>
                        <td class="text-end space-x-1">
                          <button
                            *ngIf="kd.isActive"
                            type="button"
                            class="ti-btn ti-btn-sm ti-btn-outline-primary"
                            (click)="reissueKioskPairingCode(kd.deviceId)"
                            title="ยกเลิก Token เดิมของอุปกรณ์นี้และออกรหัสจับคู่ใหม่"
                          >
                            ออกรหัสใหม่
                          </button>
                          <button
                            *ngIf="kd.isActive"
                            type="button"
                            class="ti-btn ti-btn-sm ti-btn-danger"
                            (click)="revokeKioskDevice(kd.deviceId)"
                          >
                            เพิกถอนสิทธิ์
                          </button>
                        </td>
                      </tr>
                      <tr *ngIf="kioskDevices.length === 0">
                        <td colspan="4" class="text-center text-gray-500 py-3">ยังไม่มีอุปกรณ์ Kiosk ที่ลงทะเบียน</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div class="col-span-12 lg:col-span-6 p-4 rounded-lg border border-defaultborder space-y-4">
                <h6 class="font-semibold">การยืนยันตัวตน 2 ชั้น (TOTP 2FA Authenticator)</h6>
                <p class="text-xs text-gray-500">
                  เพิ่มความปลอดภัยให้บัญชีผู้ดูแลระบบด้วยรหัส 6 หลักตามมาตรฐาน RFC 6238 (Google Authenticator / Microsoft Authenticator)
                </p>

                <div class="p-3 rounded border border-defaultborder flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium">สถานะ 2FA ของบัญชีคุณ ({{ mfaStatus?.username || '-' }})</div>
                    <div class="text-xs text-gray-500">
                      {{ mfaStatus?.totpEnabled ? 'เปิดใช้งาน 2FA แล้ว' : 'ยังไม่ได้เปิดใช้งาน 2FA' }}
                    </div>
                  </div>
                  <span
                    class="badge px-3 py-1"
                    [ngClass]="mfaStatus?.totpEnabled ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'"
                  >
                    {{ mfaStatus?.totpEnabled ? 'ENABLED' : 'DISABLED' }}
                  </span>
                </div>

                <div *ngIf="!mfaStatus?.totpEnabled" class="space-y-3">
                  <button type="button" class="ti-btn ti-btn-primary-full" (click)="setupMfa()">
                    1. สร้างรหัส Secret สำหรับแอป Authenticator
                  </button>

                  <div *ngIf="mfaSetupData" class="p-3 rounded bg-primary/5 border border-primary/20 space-y-2 text-xs">
                    <div><strong>Secret Key (กรอกในแอป Authenticator):</strong> <code class="font-mono text-sm">{{ mfaSetupData.secret }}</code></div>
                    <div class="break-all text-gray-500">URI: {{ mfaSetupData.otpauthUri }}</div>
                    <div class="flex gap-2 pt-2">
                      <input
                        class="form-control"
                        maxlength="6"
                        [(ngModel)]="mfaVerifyCode"
                        placeholder="กรอกรหัส 6 หลักจากแอปเพื่อเปิดใช้งาน"
                      />
                      <button type="button" class="ti-btn ti-btn-success whitespace-nowrap" (click)="enableMfa()">
                        2. ยืนยันและเปิดใช้ 2FA
                      </button>
                    </div>
                  </div>
                </div>

                <div *ngIf="mfaStatus?.totpEnabled">
                  <button type="button" class="ti-btn ti-btn-danger" (click)="disableMfa()">
                    ปิดการใช้งาน 2FA สำหรับบัญชีนี้
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB 6: SIGNED PAYROLL WEBHOOKS & CLOUD OBSERVABILITY (PHASE 5) -->
          <div class="box-body space-y-6" *ngIf="activeTab === 'observability'">
            <!-- Telemetry & Cloud Storage Cards -->
            <div class="grid grid-cols-12 gap-4" *ngIf="obsSummary">
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-primary/5 border border-primary/20">
                <div class="text-xs text-gray-500">GPU Face Inference Latency (P95)</div>
                <div class="text-2xl font-bold mt-1">
                  {{ obsSummary.histograms?.dpu_face_gpu_latency_ms?.p95Ms || 0 }} ms
                </div>
                <div class="text-xs text-gray-500 mt-1">
                  Avg {{ obsSummary.histograms?.dpu_face_gpu_latency_ms?.avgMs || 0 }} ms ({{ obsSummary.histograms?.dpu_face_gpu_latency_ms?.count || 0 }} jobs)
                </div>
              </div>
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-success/5 border border-success/20">
                <div class="text-xs text-gray-500">pgvector 1:N HNSW Search (P95)</div>
                <div class="text-2xl font-bold text-success mt-1">
                  {{ obsSummary.histograms?.dpu_pgvector_search_ms?.p95Ms || 0 }} ms
                </div>
                <div class="text-xs text-gray-500 mt-1">
                  Avg {{ obsSummary.histograms?.dpu_pgvector_search_ms?.avgMs || 0 }} ms ({{ obsSummary.histograms?.dpu_pgvector_search_ms?.count || 0 }} queries)
                </div>
              </div>
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-info/5 border border-info/20">
                <div class="text-xs text-gray-500">HTTP API Latency &amp; Active Kiosks</div>
                <div class="text-2xl font-bold text-info mt-1">
                  {{ obsSummary.httpAvgLatencyMs || 0 }} ms
                </div>
                <div class="text-xs text-gray-500 mt-1">
                  Active Kiosk WS: {{ obsSummary.activeKioskWebSockets || 0 }} | Total Req: {{ obsSummary.httpRequestsTotal || 0 }}
                </div>
              </div>
              <div class="col-span-12 md:col-span-3 p-4 rounded-lg bg-warning/5 border border-warning/20">
                <div class="text-xs text-gray-500">Storage Backend (S3 / MinIO / Local)</div>
                <div class="text-xl font-bold text-warning mt-1 uppercase">
                  {{ obsSummary.storage?.backend || 'local' }}
                  <span *ngIf="obsSummary.storage?.s3Enabled" class="badge bg-success/10 text-success text-xs ms-1">S3 Presigned</span>
                </div>
                <div class="text-xs text-gray-500 mt-1">
                  Enrolled: {{ obsSummary.storage?.localFileCounts?.enrolled_images || 0 }} | Punches: {{ obsSummary.storage?.localFileCounts?.uploaded_images || 0 }}
                </div>
              </div>
            </div>

            <div class="grid grid-cols-12 gap-4">
              <!-- Signed Outbound Webhook Config -->
              <div class="col-span-12 lg:col-span-5 p-4 rounded-lg border border-defaultborder space-y-3">
                <h6 class="font-semibold">ตั้งค่า Signed Outbound Webhook (เชื่อมระบบเงินเดือน Payroll / ERP)</h6>
                <p class="text-xs text-gray-500">
                  ส่งข้อมูลลงเวลาเข้า-ออกงานแบบเรียลไทม์พร้อมลายเซ็น <code>X-DPU-Signature-256: v1=&lt;hmac_sha256&gt;</code>
                </p>
                <div>
                  <label class="form-label">Webhook Endpoint URL (SAP / Workday / ERP)</label>
                  <input
                    class="form-control"
                    [(ngModel)]="notifySettings.webhookUrl"
                    placeholder="https://erp.example.com/webhooks/dpu-attendance"
                  />
                </div>
                <div>
                  <label class="form-label">
                    HMAC-SHA256 Signing Secret
                    <span *ngIf="notifySettings.hasWebhookSecret" class="badge bg-success/10 text-success ms-1">ตั้งค่าแล้ว</span>
                  </label>
                  <input
                    type="password"
                    class="form-control"
                    [(ngModel)]="notifySettings.webhookSecret"
                    placeholder="กรอก Secret Key เพื่อเซ็นรับรอง Payload"
                  />
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="form-label">เวลาแจ้งเตือนขาดงาน (Cutoff)</label>
                    <input type="time" class="form-control" [(ngModel)]="notifySettings.cutoff" />
                  </div>
                  <div>
                    <label class="form-label">อีเมลผู้รับแจ้งเตือน</label>
                    <input class="form-control" [(ngModel)]="notifySettings.email" placeholder="hr@company.com" />
                  </div>
                </div>
                <div class="flex gap-2 pt-2">
                  <button type="button" class="ti-btn ti-btn-primary-full flex-1" (click)="saveNotifySettings()">
                    บันทึกการตั้งค่า Webhook
                  </button>
                  <button type="button" class="ti-btn ti-btn-light" (click)="sendTestWebhook()">
                    ส่ง Test Webhook
                  </button>
                </div>
              </div>

              <!-- Recent Outbox Delivery Log -->
              <div class="col-span-12 lg:col-span-7 p-4 rounded-lg border border-defaultborder">
                <div class="flex items-center justify-between mb-3">
                  <h6 class="font-semibold">ประวัติการส่ง Outbound Webhook &amp; Notification Outbox ({{ outboxLogs.length }})</h6>
                  <button type="button" class="ti-btn ti-btn-sm ti-btn-light" (click)="loadObservabilityAndWebhooks()">
                    รีเฟรช
                  </button>
                </div>
                <div class="table-responsive max-h-80 overflow-y-auto">
                  <table class="table whitespace-nowrap min-w-full">
                    <thead>
                      <tr class="border-b border-defaultborder">
                        <th class="text-start">เวลา</th>
                        <th class="text-start">Event</th>
                        <th class="text-start">ช่องทาง</th>
                        <th class="text-start">สถานะ (Attempts)</th>
                        <th class="text-start">หมายเหตุ / Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr *ngFor="let item of outboxLogs" class="border-b border-defaultborder">
                        <td class="text-xs">{{ item.createdAt | date: 'dd/MM HH:mm:ss' }}</td>
                        <td class="font-mono text-xs">{{ item.event }}</td>
                        <td><span class="badge bg-primary/10 text-primary uppercase">{{ item.channel }}</span></td>
                        <td>
                          <span *ngIf="item.status === 'sent'" class="badge bg-success/10 text-success">
                            SENT ({{ item.attempts }})
                          </span>
                          <span *ngIf="item.status === 'pending'" class="badge bg-warning/10 text-warning">
                            PENDING ({{ item.attempts }})
                          </span>
                          <span *ngIf="item.status === 'failed'" class="badge bg-danger/10 text-danger">
                            FAILED ({{ item.attempts }})
                          </span>
                        </td>
                        <td class="text-xs text-gray-500 max-w-xs truncate">{{ item.lastError || 'OK' }}</td>
                      </tr>
                      <tr *ngIf="outboxLogs.length === 0">
                        <td colspan="5" class="text-center text-gray-500 py-4">ยังไม่มีประวัติการส่งข้อมูลใน Outbox</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
})
export class HrScheduleComponent implements OnInit {
  activeTab: 'shifts' | 'leaves' | 'holidays' | 'pdpa' | 'security' | 'observability' = 'shifts';
  companyId = '';
  statusMsg = '';

  shifts: any[] = [];
  departments: any[] = [];
  employees: any[] = [];
  leaves: any[] = [];
  holidays: any[] = [];
  holidayBusy = false;
  holidayImportHint = '';
  holidayPresetYear = new Date().getFullYear();
  pdpaSummary: any = null;
  consentPolicy: any = { version: '1.0', textTh: '', textEn: '' };
  retentionSettings: any = {
    biometricDays: 90,
    punchPhotoDays: 90,
    incidentSnapshotDays: 90,
    tempHours: 24,
  };
  kioskDevices: any[] = [];
  newKioskName = '';
  issuedKiosk: any = null;
  readonly pairPageUrl = `${window.location.origin}/kiosk/pair`;
  mfaStatus: any = null;
  mfaSetupData: any = null;
  mfaVerifyCode = '';

  obsSummary: any = null;
  outboxLogs: any[] = [];
  notifySettings: any = {
    email: '',
    lineToken: '',
    webhookUrl: '',
    webhookSecret: '',
    hasWebhookSecret: false,
    cutoff: '09:30',
    events: ['attendance.checked_in', 'attendance.checked_out', 'attendance.approved', 'attendance.missing'],
  };

  newShift = {
    name: '',
    startTime: '09:00',
    endTime: '18:00',
    graceMinutes: 15,
    roundingMinutes: 0,
    breakMinutes: 0,
    otThresholdMinutes: 0,
    breakWindows: [] as { start: string; end: string }[],
    isCrossMidnight: false,
    isDefault: false,
  };

  newLeave = {
    company_employeeId: '',
    leaveType: 'ANNUAL',
    startDate: '',
    endDate: '',
    reason: '',
  };

  newHoliday = {
    holidayDate: '',
    name: '',
  };

  constructor(private http: HttpClient, private token: TokenService) {
    this.companyId = this.token.getSelectCompany()?.companyId || '';
  }

  ngOnInit(): void {
    if (!this.companyId) {
      return;
    }
    this.reloadAll();
  }

  private flash(msg: string): void {
    this.statusMsg = msg;
    setTimeout(() => {
      if (this.statusMsg === msg) {
        this.statusMsg = '';
      }
    }, 3500);
  }

  reloadAll(): void {
    this.loadShifts();
    this.loadDepartmentsAndEmployees();
    this.loadLeaves();
    this.loadHolidays();
    this.loadPdpaSummary();
    this.loadKioskDevices();
    this.loadMfaStatus();
    this.loadObservabilityAndWebhooks();
  }

  switchToObservability(): void {
    this.activeTab = 'observability';
    this.loadObservabilityAndWebhooks();
  }

  loadObservabilityAndWebhooks(): void {
    this.http.get<any>(`/system/observability-summary`).subscribe((res) => {
      this.obsSummary = res;
    });
    this.http.get<any>(`/notifications/company/${this.companyId}/settings`).subscribe((res) => {
      if (res) {
        this.notifySettings = { ...this.notifySettings, ...res };
      }
    });
    this.http.get<any[]>(`/notifications/company/${this.companyId}/outbox`).subscribe((rows) => {
      this.outboxLogs = rows || [];
    });
  }

  saveNotifySettings(): void {
    this.http
      .put<any>(`/notifications/company/${this.companyId}/settings`, this.notifySettings)
      .subscribe((res) => {
        if (res) {
          this.notifySettings = { ...this.notifySettings, ...res };
        }
        this.flash('บันทึกการตั้งค่า Signed Webhook เรียบร้อย');
      });
  }

  sendTestWebhook(): void {
    this.http.post(`/notifications/company/${this.companyId}/test`, {}).subscribe(() => {
      this.loadObservabilityAndWebhooks();
      this.flash('ส่ง Test Webhook เข้าคิว Outbox แล้ว');
    });
  }

  loadShifts(): void {
    this.http.get<any>(`/hr/company/${this.companyId}/shifts`).subscribe((res) => {
      this.shifts = res?.shifts || [];
    });
  }

  loadDepartmentsAndEmployees(): void {
    this.http.get<any[]>(`/departments/company/${this.companyId}`).subscribe((rows) => {
      this.departments = rows || [];
    });
    this.http.get<any[]>(`/employees/company/${this.companyId}`).subscribe((rows) => {
      this.employees = rows || [];
    });
  }

  loadLeaves(): void {
    this.http.get<any>(`/hr/company/${this.companyId}/leaves`).subscribe((res) => {
      this.leaves = Array.isArray(res) ? res : res?.items || [];
    });
  }

  loadHolidays(): void {
    this.http.get<any[]>(`/hr/company/${this.companyId}/holidays`).subscribe((rows) => {
      this.holidays = rows || [];
    });
  }

  loadPdpaSummary(): void {
    this.http.get<any>(`/hr/company/${this.companyId}/pdpa-summary`).subscribe((res) => {
      this.pdpaSummary = res;
      if (res?.consentPolicy) {
        this.consentPolicy = { ...this.consentPolicy, ...res.consentPolicy };
      }
      if (res?.retentionPolicy) {
        this.retentionSettings = {
          biometricDays: res.retentionPolicy.biometricDays ?? this.retentionSettings.biometricDays,
          punchPhotoDays: res.retentionPolicy.punchPhotoDays ?? res.retentionPolicy.imageRetentionDays,
          incidentSnapshotDays:
            res.retentionPolicy.incidentSnapshotDays ?? this.retentionSettings.incidentSnapshotDays,
          tempHours: res.retentionPolicy.tempRetentionHours ?? this.retentionSettings.tempHours,
        };
      }
    });
    this.http.get<any>(`/hr/company/${this.companyId}/pdpa/consent-policy`).subscribe((res) => {
      if (res) this.consentPolicy = { ...this.consentPolicy, ...res };
    });
    this.http.get<any>(`/hr/company/${this.companyId}/pdpa/retention`).subscribe((res) => {
      if (res) this.retentionSettings = { ...this.retentionSettings, ...res };
    });
  }

  saveConsentPolicy(): void {
    this.http
      .put(`/hr/company/${this.companyId}/pdpa/consent-policy`, this.consentPolicy)
      .subscribe((res) => {
        this.consentPolicy = { ...this.consentPolicy, ...res };
      });
  }

  saveRetentionSettings(): void {
    this.http
      .put(`/hr/company/${this.companyId}/pdpa/retention`, this.retentionSettings)
      .subscribe((res) => {
        this.retentionSettings = { ...this.retentionSettings, ...res };
        this.loadPdpaSummary();
      });
  }

  exportDsar(memberId?: string): void {
    if (!memberId) return;
    this.http.get(`/hr/company/${this.companyId}/members/${memberId}/dsar-export`).subscribe((data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `dsar-${memberId}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    });
  }

  loadKioskDevices(): void {
    this.http.get<any[]>(`/hr/company/${this.companyId}/kiosk-devices`).subscribe((rows) => {
      this.kioskDevices = rows || [];
    });
  }

  loadMfaStatus(): void {
    this.http.get<any>(`/auth/mfa/status`).subscribe((res) => {
      this.mfaStatus = res;
    });
  }

  createShift(): void {
    if (!this.newShift.name.trim()) {
      return;
    }
    this.http.post(`/hr/company/${this.companyId}/shifts`, this.newShift).subscribe(() => {
      this.newShift = {
        name: '',
        startTime: '09:00',
        endTime: '18:00',
        graceMinutes: 15,
        roundingMinutes: 0,
        breakMinutes: 0,
        otThresholdMinutes: 0,
        breakWindows: [],
        isCrossMidnight: false,
        isDefault: false,
      };
      this.loadShifts();
      this.flash('บันทึกกะเวลาทำงานเรียบร้อย');
    });
  }

  deleteShift(shiftId: string): void {
    this.http.delete(`/hr/company/${this.companyId}/shifts/${shiftId}`).subscribe(() => {
      this.loadShifts();
      this.loadDepartmentsAndEmployees();
      this.flash('ลบกะเวลาทำงานเรียบร้อย');
    });
  }

  assignDeptShift(departmentId: string, shiftId: string): void {
    this.http
      .put(`/hr/company/${this.companyId}/assign-shift`, {
        departmentId,
        shiftId: shiftId || null,
      })
      .subscribe(() => {
        this.flash('อัปเดตกะเวลาทำงานของแผนกแล้ว');
      });
  }

  assignEmpShift(company_employeeId: string, shiftId: string): void {
    this.http
      .put(`/hr/company/${this.companyId}/assign-shift`, {
        company_employeeId,
        shiftId: shiftId || null,
      })
      .subscribe(() => {
        this.flash('อัปเดตกะเวลาทำงานรายบุคคลแล้ว');
      });
  }

  createLeave(): void {
    if (!this.newLeave.company_employeeId || !this.newLeave.startDate || !this.newLeave.endDate) {
      return;
    }
    this.http.post(`/hr/company/${this.companyId}/leaves`, this.newLeave).subscribe(() => {
      this.newLeave = {
        company_employeeId: '',
        leaveType: 'ANNUAL',
        startDate: '',
        endDate: '',
        reason: '',
      };
      this.loadLeaves();
      this.flash('บันทึกใบลาเรียบร้อย');
    });
  }

  decideLeave(leaveId: string, status: number): void {
    this.http
      .post(`/hr/company/${this.companyId}/leaves/${leaveId}/approval`, { status })
      .subscribe(() => {
        this.loadLeaves();
        this.flash(status === 1 ? 'อนุมัติใบลาแล้ว' : 'ปฏิเสธใบลาแล้ว');
      });
  }

  createHoliday(): void {
    if (!this.newHoliday.holidayDate || !this.newHoliday.name.trim()) {
      return;
    }
    this.http.post(`/hr/company/${this.companyId}/holidays`, this.newHoliday).subscribe(() => {
      this.newHoliday = { holidayDate: '', name: '' };
      this.loadHolidays();
      this.flash('เพิ่มวันหยุดบริษัทเรียบร้อย');
    });
  }

  deleteHoliday(holidayId: string): void {
    this.http.delete(`/hr/company/${this.companyId}/holidays/${holidayId}`).subscribe(() => {
      this.loadHolidays();
      this.flash('ลบวันหยุดบริษัทเรียบร้อย');
    });
  }

  holidaySourceLabel(source: string | null | undefined): string {
    switch ((source || 'MANUAL').toUpperCase()) {
      case 'CSV':
        return 'CSV';
      case 'ICAL':
        return 'iCal';
      case 'THAI_PRESET':
        return 'ราชการไทย';
      default:
        return 'กำหนดเอง';
    }
  }

  applyThaiHolidayPreset(): void {
    if (!this.companyId || this.holidayBusy) return;
    this.holidayBusy = true;
    this.holidayImportHint = '';
    this.http
      .post(`/hr/company/${this.companyId}/holidays/thai-preset`, { year: this.holidayPresetYear })
      .subscribe({
        next: (res: any) => {
          this.holidayBusy = false;
          this.loadHolidays();
          const n = Number(res?.imported || 0);
          this.flash(`โหลดวันหยุดราชการไทย ${res?.year || this.holidayPresetYear} แล้ว (${n} รายการ)`);
        },
        error: (err) => {
          this.holidayBusy = false;
          this.holidayImportHint = err?.error?.detail || 'โหลด preset ไม่สำเร็จ';
        },
      });
  }

  onHolidayFileSelected(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const file = input?.files?.[0];
    if (!file || !this.companyId) return;
    this.holidayBusy = true;
    this.holidayImportHint = '';
    const form = new FormData();
    form.append('file', file, file.name);
    const lower = file.name.toLowerCase();
    if (lower.endsWith('.ics') || lower.endsWith('.ical')) {
      form.append('format', 'ical');
    } else {
      form.append('format', 'csv');
    }
    this.http.post(`/hr/company/${this.companyId}/holidays/import`, form).subscribe({
      next: (res: any) => {
        this.holidayBusy = false;
        this.loadHolidays();
        this.flash(
          `นำเข้าวันหยุดแล้ว (ใหม่ ${res?.created || 0} / อัปเดต ${res?.updated || 0})`,
        );
        if (input) input.value = '';
      },
      error: (err) => {
        this.holidayBusy = false;
        this.holidayImportHint = err?.error?.detail || 'นำเข้าไฟล์ไม่สำเร็จ';
        if (input) input.value = '';
      },
    });
  }

  grantConsent(memberId: string): void {
    if (!memberId) return;
    this.http
      .post(`/hr/company/${this.companyId}/members/${memberId}/biometric-consent`, {})
      .subscribe(() => {
        this.loadDepartmentsAndEmployees();
        this.loadPdpaSummary();
        this.flash('บันทึกความยินยอม PDPA เรียบร้อย');
      });
  }

  revokeConsent(memberId: string): void {
    if (!memberId) return;
    this.http
      .delete(`/hr/company/${this.companyId}/members/${memberId}/biometric-consent`)
      .subscribe(() => {
        this.loadDepartmentsAndEmployees();
        this.loadPdpaSummary();
        this.flash('เพิกถอนความยินยอมและลบข้อมูลใบหน้าเรียบร้อย');
      });
  }

  createKioskDevice(): void {
    if (!this.newKioskName.trim()) return;
    this.http
      .post(`/hr/company/${this.companyId}/kiosk-devices`, { name: this.newKioskName })
      .subscribe((res) => {
        this.issuedKiosk = res;
        this.newKioskName = '';
        this.loadKioskDevices();
        this.flash('สร้างอุปกรณ์และรหัสจับคู่สำเร็จ');
      });
  }

  reissueKioskPairingCode(deviceId: string): void {
    this.http
      .post(`/hr/company/${this.companyId}/kiosk-devices/${deviceId}/pairing-code`, {})
      .subscribe((res) => {
        this.issuedKiosk = res;
        this.loadKioskDevices();
        this.flash('ออกรหัสจับคู่ใหม่แล้ว Token เดิมของอุปกรณ์ถูกยกเลิก');
      });
  }

  revokeKioskDevice(deviceId: string): void {
    this.http.delete(`/hr/company/${this.companyId}/kiosk-devices/${deviceId}`).subscribe(() => {
      if (this.issuedKiosk?.deviceId === deviceId) {
        this.issuedKiosk = null;
      }
      this.loadKioskDevices();
      this.flash('เพิกถอนสิทธิ์อุปกรณ์ Kiosk แล้ว');
    });
  }

  setupMfa(): void {
    this.http.post(`/auth/mfa/setup`, {}).subscribe((res) => {
      this.mfaSetupData = res;
      this.flash('สร้างรหัส Secret สำหรับ 2FA แล้ว');
    });
  }

  enableMfa(): void {
    if (!this.mfaVerifyCode.trim()) return;
    this.http.post(`/auth/mfa/enable`, { code: this.mfaVerifyCode }).subscribe(() => {
      this.mfaSetupData = null;
      this.mfaVerifyCode = '';
      this.loadMfaStatus();
      this.flash('เปิดใช้งาน 2FA สำเร็จ');
    });
  }

  disableMfa(): void {
    this.http.post(`/auth/mfa/disable`, {}).subscribe(() => {
      this.mfaSetupData = null;
      this.loadMfaStatus();
      this.flash('ปิดการใช้งาน 2FA แล้ว');
    });
  }
}
