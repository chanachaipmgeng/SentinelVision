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
  /**
   * Soft-hide from sidebar when the caller has any of these RBAC role codes
   * (route remains reachable by direct URL). Example: self-service for HR_ADMIN.
   */
  hideForRoles?: string[];
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
      { headTitle: 'System admin', permission: 'system.admin' },
      {
        icon: 'user',
        path: '/admin/member-manage',
        title: 'Manage members',
        type: 'link',
        permission: 'system.admin',
      },
      {
        icon: 'buildings',
        path: '/admin/manage-companys',
        title: 'Manage companies',
        type: 'link',
        permission: 'system.admin',
      },
      {
        icon: 'user-check',
        path: '/admin/admin-manage',
        title: 'Manage admin permissions',
        type: 'link',
        permission: 'system.admin',
      },
      {
        icon: 'settings',
        path: '/admin/system-setting',
        title: 'System settings / TTS',
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
        title: 'Overview dashboard',
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

      { headTitle: 'CORE — Organization', moduleId: 'CORE' },
      {
        title: 'Organization & people',
        icon: 'buildings',
        type: 'sub',
        active: false,
        moduleId: 'CORE',
        permission: 'employees.read',
        children: [
          { path: '/company/company-info', title: 'Company info', type: 'link', permission: 'company.read' },
          { path: '/company/company-department', title: 'Manage departments', type: 'link', permission: 'departments.read' },
          { path: '/company/company-position', title: 'Manage positions', type: 'link', permission: 'positions.read' },
          { path: '/company/company-emp', title: 'Employee registry & faces', type: 'link', permission: 'employees.read' },
        ],
      },

      { headTitle: 'ATTENDANCE — Time clock', moduleId: 'ATTENDANCE' },
      {
        title: 'Attendance module',
        icon: 'time',
        type: 'sub',
        active: false,
        moduleId: 'ATTENDANCE',
        permission: 'attendance.read',
        children: [
          {
            path: '/company/scan/attendance',
            title: 'Live attendance scan',
            type: 'link',
            permission: 'attendance.read',
          },
          { path: '/company/timestamp-log', title: 'Attendance history', type: 'link', permission: 'attendance.read' },
          {
            path: '/company/warning-timestamp-log',
            title: 'Approve out-of-area punches',
            type: 'link',
            permission: 'attendance.approve',
          },
          {
            path: '/company/approval-inbox',
            title: 'Approval inbox',
            type: 'link',
            permission: 'attendance.approve',
          },
          {
            path: '/company/reports',
            title: 'Attendance reports',
            type: 'link',
            permission: 'attendance.read',
          },
          {
            path: '/company/self-service',
            title: 'Self-service',
            type: 'link',
            permission: 'attendance.read',
            // Employee portal — soft-hide for company/HR admins (route still open).
            hideForRoles: ['HR_ADMIN', 'ADMIN_COMPANY'],
          },
          {
            path: '/company/company-location',
            title: 'Punch locations (GPS)',
            type: 'link',
            permission: 'company.settings',
          },
          {
            path: '/company/hr-schedule',
            title: 'Shifts / leave / kiosk devices',
            type: 'link',
            permission: 'hr.shifts',
          },
        ],
      },

      { headTitle: 'ACCESS_CONTROL — Doors', moduleId: 'ACCESS_CONTROL', permission: 'sentinel.manage' },
      {
        title: 'Access control module',
        icon: 'lock-alt',
        type: 'sub',
        active: false,
        moduleId: 'ACCESS_CONTROL',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/access-control',
            title: 'Live door scan',
            type: 'link',
          },
          {
            path: '/company/access-control/zones',
            title: 'Door zones & unlock',
            type: 'link',
          },
          {
            path: '/company/access-control/logs',
            title: 'Access logs',
            type: 'link',
          },
          {
            path: '/company/access-control/settings',
            title: 'Access Control & IoT Relay settings',
            type: 'link',
          },
        ],
      },

      { headTitle: 'WATCHLIST — Watch & VIP', moduleId: 'WATCHLIST', permission: 'sentinel.manage' },
      {
        title: 'Watchlist & VIP module',
        icon: 'shield-quarter',
        type: 'sub',
        active: false,
        moduleId: 'WATCHLIST',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/watchlist',
            title: 'Live watchlist camera',
            type: 'link',
          },
          {
            path: '/company/watchlist/identities',
            title: 'Watchlist Blacklist / POI / VIP',
            type: 'link',
          },
          {
            path: '/company/watchlist/incidents',
            title: 'Incident alerts',
            type: 'link',
          },
          {
            path: '/company/watchlist/settings',
            title: 'Security alert settings',
            type: 'link',
          },
        ],
      },

      { headTitle: 'VISITOR — Visitors & building', moduleId: 'VISITOR', permission: 'sentinel.manage' },
      {
        title: 'Visitor & building module',
        icon: 'user-check',
        type: 'sub',
        active: false,
        moduleId: 'VISITOR',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/visitor',
            title: 'Live visitor scan',
            type: 'link',
          },
          {
            path: '/company/visitors/passes',
            title: 'Visitor pass',
            type: 'link',
          },
          {
            path: '/company/visitors/muster-roll',
            title: 'Muster roll',
            type: 'link',
          },
          {
            path: '/company/visitors/settings',
            title: 'Visitor & PDPA settings',
            type: 'link',
          },
        ],
      },

      { headTitle: 'EVENTS — Events & seminars', moduleId: 'EVENTS', permission: 'sentinel.manage' },
      {
        title: 'Events & seminars module',
        icon: 'calendar',
        type: 'sub',
        active: false,
        moduleId: 'EVENTS',
        permission: 'sentinel.manage',
        children: [
          {
            path: '/company/scan/event',
            title: 'Live event scan',
            type: 'link',
          },
          {
            path: '/company/events/campaigns',
            title: 'Event campaigns & attendees',
            type: 'link',
          },
          {
            path: '/company/events/checkins',
            title: 'Live event check-in stats',
            type: 'link',
          },
          {
            path: '/company/events/settings',
            title: 'Event settings',
            type: 'link',
          },
        ],
      },

      { headTitle: 'CCTV — Cameras', moduleId: 'CCTV', permission: 'cameras.read' },
      {
        title: 'cctv.nav.module',
        icon: 'video',
        type: 'sub',
        active: false,
        moduleId: 'CCTV',
        permission: 'cameras.read',
        children: [
          {
            path: '/company/cameras',
            title: 'cctv.cameras.nav',
            type: 'link',
            permission: 'cameras.read',
          },
          {
            path: '/company/live-wall',
            title: 'cctv.liveWall.nav',
            type: 'link',
            permission: 'cameras.read',
          },
          {
            path: '/company/playback',
            title: 'cctv.playback.nav',
            type: 'link',
            permission: 'cameras.read',
          },
          {
            path: '/company/e-map',
            title: 'emap.nav',
            type: 'link',
            permission: 'cameras.read',
          },
          {
            path: '/company/face-monitor',
            title: 'faceMonitor.nav',
            type: 'link',
            permission: 'cameras.read',
          },
        ],
      },

      { headTitle: 'GOVERNANCE — Governance', moduleId: 'GOVERNANCE', permission: 'audit.read' },
      {
        icon: 'file-list',
        path: '/company/audit-log',
        title: 'Audit log',
        type: 'link',
        moduleId: 'GOVERNANCE',
        permission: 'audit.read',
      },
      {
        icon: 'tablet',
        path: '/company/devices',
        title: 'Manage kiosk devices',
        type: 'link',
        moduleId: 'GOVERNANCE',
      },
      {
        icon: 'notification',
        path: '/company/notification-center',
        title: 'Notification Center',
        type: 'link',
        moduleId: 'GOVERNANCE',
      },
      {
        icon: 'shield-user',
        path: '/company/profile-security',
        title: 'Profile & Security',
        type: 'link',
        moduleId: 'GOVERNANCE',
      },
      {
        icon: 'cog',
        path: '/company/settings',
        title: 'settingsHub.navTitle',
        type: 'link',
        moduleId: 'GOVERNANCE',
        permission: 'company.settings',
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
   * Also soft-hides items whose `hideForRoles` intersects the caller's roles.
   * Headings without a following visible item are dropped.
   */
  filterMenuByPermissions(
    items: Menu[],
    hasPermission: (code: string) => boolean,
    roleCodes: readonly string[] = [],
  ): Menu[] {
    const roles = new Set(roleCodes.map((r) => String(r).toUpperCase()));
    const mapItem = (item: Menu): Menu | null => {
      if (item.permission && !hasPermission(item.permission)) {
        return null;
      }
      if (item.hideForRoles?.length) {
        const blocked = item.hideForRoles.some((r) =>
          roles.has(String(r).toUpperCase())
        );
        if (blocked) {
          return null;
        }
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
