import { Injectable, OnDestroy } from '@angular/core';
import { Subject, BehaviorSubject, fromEvent } from 'rxjs';
import { takeUntil, debounceTime } from 'rxjs/operators';
import { Router } from '@angular/router';
import { TokenService } from './token.service';
import {
  ALWAYS_ON_MODULES,
  PlatformModule,
  TOGGLEABLE_COMPANY_MODULES,
} from '../../DPU/services/company-module-config.service';

/** Menu item; `moduleId` drives per-company sidebar filtering. */
export interface Menu {
  headTitle?: string;
  headTitle2?: string;
  path?: string;
  title?: string;
  icon?: string;
  type?: string;
  badgeValue?: string;
  badgeClass?: string;
  badgeText?: string;
  active?: boolean;
  selected?: boolean;
  bookmark?: boolean;
  children?: Menu[];
  children2?: Menu[];
  Menusub?: boolean;
  target?: boolean;
  menutype?: string;
  /** Platform module this entry belongs to. Omit for always-visible command chrome. */
  moduleId?: PlatformModule | 'COMMAND';
  /** D1 RBAC: hide unless the server-granted permission is present. */
  permission?: string;
}

@Injectable({
  providedIn: 'root',
})
export class NavService implements OnDestroy {
  private unsubscriber: Subject<any> = new Subject();
  public screenWidth: BehaviorSubject<number> = new BehaviorSubject(
    window.innerWidth
  );

  // Search Box
  public search = false;

  // Language
  public language = false;

  // Mega Menu
  public megaMenu = false;
  public levelMenu = false;
  public megaMenuColapse: boolean = window.innerWidth < 1199 ? true : false;

  // Collapse Sidebar
  public collapseSidebar: boolean = window.innerWidth < 991 ? true : false;

  // For Horizontal Layout Mobile
  public horizontal: boolean = window.innerWidth < 991 ? false : true;

  // Full screen
  public fullScreen = false;
  active: any;

  constructor(private router: Router, private tokenService: TokenService) {
    this.setScreenWidth(window.innerWidth);
    fromEvent(window, 'resize')
      .pipe(debounceTime(1000), takeUntil(this.unsubscriber))
      .subscribe((evt: any) => {
        this.setScreenWidth(evt.target.innerWidth);
        if (evt.target.innerWidth < 991) {
          this.collapseSidebar = true;
          this.megaMenu = false;
          this.levelMenu = false;
        }
        if (evt.target.innerWidth < 1199) {
          this.megaMenuColapse = true;
        }
      });
    if (window.innerWidth < 991) {
      // Detect Route change sidebar close
      this.router.events.subscribe(() => {
        this.collapseSidebar = true;
        this.megaMenu = false;
        this.levelMenu = false;
      });
    }
  }

  ngOnDestroy() {
    this.unsubscriber.next;
    this.unsubscriber.complete();
  }

  private setScreenWidth(width: number): void {
    this.screenWidth.next(width);
  }

  MENUITEMS: Menu[] = [];

  getCommonMenu() {
    return [
      { headTitle: 'ผู้ดูแลระบบ', permission: 'system.admin' },
      {
        icon: 'user',
        path: '/admin/member-manage',
        title: 'จัดการสมาชิก',
        type: 'link',
        permission: 'system.admin',
      },
      {
        icon: 'buildings',
        path: '/admin/manage-companys',
        title: 'จัดการบริษัท',
        type: 'link',
        permission: 'system.admin',
      },
      {
        icon: 'user-check',
        path: '/admin/admin-manage',
        title: 'จัดการสิทธิ์ผู้ดูแลระบบ',
        type: 'link',
        permission: 'system.admin',
      },
      {
        icon: 'settings',
        path: '/admin/system-setting',
        title: 'ตั้งค่าระบบ / TTS',
        type: 'link',
        permission: 'system.admin',
      },
    ];
  }

  /**
   * Full company sidebar tree (7 modules). Filter with
   * {@link filterCompanyMenuByModules} using `enabledModules`.
   */
  getCompanyMenu(): Menu[] {
    return [
      { headTitle: 'SENTINELVISION COMMAND', moduleId: 'COMMAND' },
      {
        icon: 'home',
        path: '/company/dashboard',
        title: 'แดชบอร์ดภาพรวม',
        type: 'link',
        moduleId: 'COMMAND',
        permission: 'company.read',
      },
      {
        icon: 'radar',
        path: '/company/scan-hub',
        title: 'Scan & Action Hub',
        type: 'link',
        moduleId: 'COMMAND',
        badgeValue: 'AI',
        badgeClass: 'primary',
        badgeText: 'primary',
        permission: 'company.read',
      },

      { headTitle: 'CORE — องค์กรและบุคลากร', moduleId: 'CORE' },
      {
        title: 'องค์กรและบุคลากร',
        icon: 'buildings',
        type: 'sub',
        active: false,
        moduleId: 'CORE',
        permission: 'employees.read',
        children: [
          { path: '/company/company-info', title: 'ข้อมูลบริษัท', type: 'link', permission: 'company.read' },
          { path: '/company/company-department', title: 'จัดการแผนก', type: 'link', permission: 'departments.read' },
          { path: '/company/company-position', title: 'จัดการตำแหน่ง', type: 'link', permission: 'positions.read' },
          { path: '/company/company-emp', title: 'ทะเบียนพนักงาน & ใบหน้า', type: 'link', permission: 'employees.read' },
        ],
      },

      { headTitle: 'ATTENDANCE — ลงเวลาทำงาน', moduleId: 'ATTENDANCE' },
      {
        title: 'โมดูลลงเวลาทำงาน',
        icon: 'time',
        type: 'sub',
        active: false,
        moduleId: 'ATTENDANCE',
        permission: 'attendance.read',
        children: [
          {
            path: '/company/scan/attendance',
            title: 'จุดสแกนลงเวลาสด',
            type: 'link',
            permission: 'attendance.read',
          },
          { path: '/company/timestamp-log', title: 'ประวัติการลงเวลา', type: 'link', permission: 'attendance.read' },
          {
            path: '/company/warning-timestamp-log',
            title: 'อนุมัติการลงเวลา (Warning)',
            type: 'link',
            permission: 'attendance.approve',
          },
          {
            path: '/company/approval-inbox',
            title: 'กล่องอนุมัติ (Approval Inbox)',
            type: 'link',
            permission: 'attendance.approve',
          },
          {
            path: '/company/reports',
            title: 'รายงานการลงเวลา',
            type: 'link',
            permission: 'attendance.read',
          },
          {
            path: '/company/self-service',
            title: 'บริการตนเอง (Self-Service)',
            type: 'link',
            permission: 'attendance.read',
          },
          {
            path: '/company/company-location',
            title: 'สถานที่ลงเวลา (GPS)',
            type: 'link',
            permission: 'company.settings',
          },
          {
            path: '/company/hr-schedule',
            title: 'ตั้งค่ากะงาน / วันลา / อุปกรณ์ Kiosk',
            type: 'link',
            permission: 'hr.shifts',
          },
        ],
      },

      { headTitle: 'ACCESS_CONTROL — ควบคุมประตู', moduleId: 'ACCESS_CONTROL', permission: 'sentinel.manage' },
      {
        title: 'โมดูลควบคุมประตู',
        icon: 'lock-alt',
        type: 'sub',
        active: false,
        moduleId: 'ACCESS_CONTROL',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/access-control',
            title: 'จุดสแกนหน้าประตูสด',
            type: 'link',
          },
          {
            path: '/company/access-control/zones',
            title: 'จัดการโซนประตู & สั่งเปิดประตู',
            type: 'link',
          },
          {
            path: '/company/access-control/logs',
            title: 'ประวัติการผ่านประตู',
            type: 'link',
          },
          {
            path: '/company/access-control/settings',
            title: 'ตั้งค่า Access Control & IoT Relay',
            type: 'link',
          },
        ],
      },

      { headTitle: 'WATCHLIST — เฝ้าระวัง & VIP', moduleId: 'WATCHLIST', permission: 'sentinel.manage' },
      {
        title: 'โมดูลเฝ้าระวัง & VIP',
        icon: 'shield-quarter',
        type: 'sub',
        active: false,
        moduleId: 'WATCHLIST',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/watchlist',
            title: 'กล้องเฝ้าระวังสด',
            type: 'link',
          },
          {
            path: '/company/watchlist/identities',
            title: 'บัญชีเฝ้าระวัง Blacklist / POI / VIP',
            type: 'link',
          },
          {
            path: '/company/watchlist/incidents',
            title: 'รายการแจ้งเตือนเหตุการณ์',
            type: 'link',
          },
          {
            path: '/company/watchlist/settings',
            title: 'ตั้งค่าการแจ้งเตือนความปลอดภัย',
            type: 'link',
          },
        ],
      },

      { headTitle: 'VISITOR — ผู้มาติดต่อ & อาคาร', moduleId: 'VISITOR', permission: 'sentinel.manage' },
      {
        title: 'โมดูลผู้มาติดต่อ & อาคาร',
        icon: 'user-check',
        type: 'sub',
        active: false,
        moduleId: 'VISITOR',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/visitor',
            title: 'จุดสแกนผู้มาติดต่อสด',
            type: 'link',
          },
          {
            path: '/company/visitors/passes',
            title: 'ออกบัตรผู้มาติดต่อ (Visitor Pass)',
            type: 'link',
          },
          {
            path: '/company/visitors/muster-roll',
            title: 'เช็คยอดคนในอาคาร (Muster Roll)',
            type: 'link',
          },
          {
            path: '/company/visitors/settings',
            title: 'ตั้งค่า Visitor & PDPA',
            type: 'link',
          },
        ],
      },

      { headTitle: 'EVENTS — งานอีเวนต์ & สัมมนา', moduleId: 'EVENTS', permission: 'sentinel.manage' },
      {
        title: 'โมดูลงานอีเวนต์ & สัมมนา',
        icon: 'calendar',
        type: 'sub',
        active: false,
        moduleId: 'EVENTS',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/event',
            title: 'จุดสแกนหน้างานอีเวนต์สด',
            type: 'link',
          },
          {
            path: '/company/events/campaigns',
            title: 'จัดการแคมเปญงานอีเวนต์ & ผู้ร่วมงาน',
            type: 'link',
          },
          {
            path: '/company/events/checkins',
            title: 'สถิติผู้เข้างานสด',
            type: 'link',
          },
          {
            path: '/company/events/settings',
            title: 'ตั้งค่างานอีเวนต์',
            type: 'link',
          },
        ],
      },

      { headTitle: 'GOVERNANCE — ธรรมาภิบาล', moduleId: 'GOVERNANCE', permission: 'audit.read' },
      {
        icon: 'file-list',
        path: '/company/audit-log',
        title: 'ประวัติการใช้งาน (Audit Log)',
        type: 'link',
        moduleId: 'GOVERNANCE',
        permission: 'audit.read',
      },
      {
        icon: 'tablet',
        path: '/company/devices',
        title: 'จัดการอุปกรณ์ Kiosk',
        type: 'link',
        moduleId: 'GOVERNANCE',
      },
      {
        icon: 'notification',
        path: '/company/notification-center',
        title: 'ศูนย์แจ้งเตือน (Notification Center)',
        type: 'link',
        moduleId: 'GOVERNANCE',
      },
      {
        icon: 'shield-user',
        path: '/company/profile-security',
        title: 'โปรไฟล์และความปลอดภัย',
        type: 'link',
        moduleId: 'GOVERNANCE',
      },
    ];
  }

  /**
   * Keep COMMAND + CORE + GOVERNANCE always; keep toggleable modules only when
   * present in `enabledModules`. Drops orphaned headTitles with no following items.
   */
  filterCompanyMenuByModules(
    items: Menu[],
    enabledModules: readonly string[] | null | undefined
  ): Menu[] {
    const enabled = new Set<string>([
      ...ALWAYS_ON_MODULES,
      'COMMAND',
      ...(enabledModules ?? [...TOGGLEABLE_COMPANY_MODULES]),
    ]);

    const kept = items.filter((item) => {
      const moduleId = item.moduleId || 'COMMAND';
      return enabled.has(moduleId);
    });

    const result: Menu[] = [];
    for (let i = 0; i < kept.length; i++) {
      const item = kept[i];
      if (item.headTitle) {
        const next = kept[i + 1];
        if (next && !next.headTitle) {
          result.push(item);
        }
        continue;
      }
      result.push(item);
    }
    return result;
  }

  /**
   * Hide menu entries the caller lacks permission for (server-driven snapshot).
   * Headings without a following visible item are dropped.
   */
  filterMenuByPermissions(
    items: Menu[],
    hasPermission: (code: string) => boolean,
  ): Menu[] {
    const mapItem = (item: Menu): Menu | null => {
      if (item.permission && !hasPermission(item.permission)) {
        return null;
      }
      if (item.children?.length) {
        const children = item.children
          .map((c) => mapItem(c))
          .filter((c): c is Menu => c != null);
        if (!children.length && item.type === 'sub') {
          return null;
        }
        return { ...item, children };
      }
      return item;
    };

    const mapped = items.map((i) => mapItem(i)).filter((i): i is Menu => i != null);
    const result: Menu[] = [];
    for (let i = 0; i < mapped.length; i++) {
      const item = mapped[i];
      if (item.headTitle) {
        const next = mapped[i + 1];
        if (next && !next.headTitle) {
          result.push(item);
        }
        continue;
      }
      result.push(item);
    }
    return result;
  }

  items = new BehaviorSubject<Menu[]>(this.MENUITEMS);
}
