import {
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  ViewChild,
  effect,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';
import { Menu, NavService } from '../../services/nav.service';
import { PermissionService } from '../../services/permission.service';
import { TokenService } from '../../services/token.service';
import { ShellUiService } from '../../services/shell-ui.service';
import { CompanyModuleConfigService } from '../../../DPU/services/company-module-config.service';
import {
  CHORD_ROUTES,
  PaletteEntry,
  filterPaletteEntries,
  flattenMenu,
  isTypingTarget,
} from './command-palette.model';

const KIOSK_MODE_CLASS = 'dpu-kiosk-mode';
const CHORD_TIMEOUT_MS = 1200;
const LANGS = ['th', 'en'] as const;

@Component({
  selector: 'app-command-palette',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './command-palette.component.html',
  styleUrl: './command-palette.component.css',
})
export class CommandPaletteComponent implements OnDestroy {
  @ViewChild('searchInput') searchInput?: ElementRef<HTMLInputElement>;

  query = '';
  entries: PaletteEntry[] = [];
  results: PaletteEntry[] = [];
  activeIndex = 0;
  loading = false;

  readonly chordHints = [
    { keys: 'g d', label: 'shell.shortcuts.goDashboard' },
    { keys: 'g t', label: 'shell.shortcuts.goTimestampLog' },
    { keys: 'g a', label: 'shell.shortcuts.goApprovalInbox' },
    { keys: 'g s', label: 'shell.shortcuts.goSentinelCenter' },
  ];

  private chordUntil = 0;
  private langCache: Partial<Record<string, Record<string, string>>> = {};

  constructor(
    readonly ui: ShellUiService,
    private router: Router,
    private nav: NavService,
    private permissions: PermissionService,
    private tokenService: TokenService,
    private moduleConfig: CompanyModuleConfigService,
    private translate: TranslateService,
    private http: HttpClient,
  ) {
    effect(() => {
      if (this.ui.paletteOpen()) {
        this.onOpen();
      }
    });
  }

  ngOnDestroy(): void {
    this.ui.closeAll();
  }

  get isMac(): boolean {
    return /Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent || '');
  }

  @HostListener('document:keydown', ['$event'])
  onKeydown(ev: KeyboardEvent): void {
    if (document.documentElement.classList.contains(KIOSK_MODE_CLASS)) {
      return;
    }

    const mod = ev.ctrlKey || ev.metaKey;
    if (mod && !ev.altKey && (ev.key === 'k' || ev.key === 'K')) {
      ev.preventDefault();
      if (this.ui.paletteOpen()) {
        this.ui.closeAll();
      } else {
        this.ui.openPalette();
      }
      return;
    }

    if (
      ev.key === 'Escape' &&
      (this.ui.paletteOpen() || this.ui.shortcutsOpen() || this.ui.notificationsOpen())
    ) {
      ev.preventDefault();
      this.ui.closeAll();
      return;
    }

    if (this.ui.paletteOpen()) {
      this.handlePaletteKeys(ev);
      return;
    }

    if (mod || ev.altKey || isTypingTarget(ev.target) || this.ui.shortcutsOpen()) {
      return;
    }

    if (ev.key === '/') {
      ev.preventDefault();
      this.ui.openPalette();
      return;
    }
    if (ev.key === '?') {
      ev.preventDefault();
      this.ui.openShortcuts();
      return;
    }

    const now = Date.now();
    if (now < this.chordUntil) {
      this.chordUntil = 0;
      const target = CHORD_ROUTES[ev.key.toLowerCase()];
      if (target) {
        ev.preventDefault();
        this.router.navigateByUrl(target);
      }
      return;
    }
    if (ev.key === 'g' || ev.key === 'G') {
      this.chordUntil = now + CHORD_TIMEOUT_MS;
    }
  }

  onQueryChange(): void {
    this.results = filterPaletteEntries(this.entries, this.query);
    this.activeIndex = 0;
  }

  go(entry: PaletteEntry | undefined): void {
    if (!entry) return;
    this.ui.closeAll();
    this.router.navigateByUrl(entry.path);
  }

  close(): void {
    this.ui.closeAll();
  }

  private handlePaletteKeys(ev: KeyboardEvent): void {
    if (ev.key === 'ArrowDown') {
      ev.preventDefault();
      if (this.results.length) {
        this.activeIndex = (this.activeIndex + 1) % this.results.length;
        this.scrollActiveIntoView();
      }
    } else if (ev.key === 'ArrowUp') {
      ev.preventDefault();
      if (this.results.length) {
        this.activeIndex = (this.activeIndex - 1 + this.results.length) % this.results.length;
        this.scrollActiveIntoView();
      }
    } else if (ev.key === 'Enter') {
      ev.preventDefault();
      this.go(this.results[this.activeIndex]);
    }
  }

  private scrollActiveIntoView(): void {
    setTimeout(() => {
      document
        .querySelector(`#sv-palette-item-${this.activeIndex}`)
        ?.scrollIntoView({ block: 'nearest' });
    });
  }

  private onOpen(): void {
    this.query = '';
    this.activeIndex = 0;
    setTimeout(() => this.searchInput?.nativeElement.focus(), 0);
    this.loading = true;
    this.loadMenu().subscribe((menu) => {
      this.entries = flattenMenu(
        menu,
        (key) => this.translate.instant(key) || key,
        (key) => LANGS.map((l) => this.langCache[l]?.[key]).filter((v): v is string => !!v),
      );
      this.loading = false;
      this.onQueryChange();
    });
  }

  /** Permission + module filtered menus visible to the caller (same rules as the sidebar). */
  private loadMenu() {
    const companyId = this.tokenService.getSelectCompany()?.companyId
      ? String(this.tokenService.getSelectCompany().companyId)
      : null;

    const langs$ = forkJoin(
      LANGS.map((lang) =>
        this.langCache[lang]
          ? of(this.langCache[lang]!)
          : this.http.get<Record<string, string>>(`./assets/i18n/${lang}.json`).pipe(
              catchError(() => of({} as Record<string, string>)),
              map((dict) => (this.langCache[lang] = dict)),
            ),
      ),
    );

    const company$ = companyId
      ? this.permissions.load(companyId).pipe(
          switchMap(() => this.moduleConfig.getModuleConfig(companyId)),
          map((cfg) =>
            this.nav.filterCompanyMenuByModules(this.nav.getCompanyMenu(), cfg.enabledModules),
          ),
          catchError(() => of(this.nav.getCompanyMenu())),
          map((menu) => this.filterByPermission(menu)),
        )
      : of([] as Menu[]);

    return forkJoin([langs$, company$]).pipe(
      map(([, companyMenu]) => {
        const admin = this.permissions.isSystemAdmin()
          ? this.filterByPermission(this.nav.getCommonMenu())
          : [];
        return [...companyMenu, ...admin];
      }),
    );
  }

  private filterByPermission(items: Menu[]): Menu[] {
    return this.nav.filterMenuByPermissions(
      items,
      (code) => this.permissions.has(code),
      this.permissions.roleCodesForNav(),
    );
  }
}
