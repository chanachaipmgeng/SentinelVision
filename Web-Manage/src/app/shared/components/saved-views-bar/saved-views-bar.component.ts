import {
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import swal from 'sweetalert';
import { TokenService } from '../../services/token.service';
import {
  SAVED_VIEW_NAME_MAX,
  SavedView,
  SavedViewsScope,
  SavedViewsService,
  stableStringify,
} from '../../services/saved-views.service';

/**
 * Chips of named filter presets for one list page. The host owns the filters: it passes the
 * current JSON-serialisable filter object in and applies whatever `apply` emits.
 */
@Component({
  selector: 'app-saved-views-bar',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslateModule],
  templateUrl: './saved-views-bar.component.html',
  styleUrls: ['./saved-views-bar.component.css'],
})
export class SavedViewsBarComponent implements OnInit, OnChanges {
  @Input({ required: true }) pageKey = '';
  @Input() currentFilters: unknown = {};
  /** Defaults to the selected company from `TokenService`. */
  @Input() companyId?: string;
  /** Emit the default view's filters once after load (disable when the URL already pins filters). */
  @Input() autoApplyDefault = true;
  @Output() apply = new EventEmitter<any>();

  @ViewChild('nameInput') nameInput?: ElementRef<HTMLInputElement>;

  readonly nameMax = SAVED_VIEW_NAME_MAX;
  views: SavedView[] = [];
  menuFor: string | null = null;
  /** `'new'` while naming a new view, a view id while renaming, else null. */
  editing: string | null = null;
  draftName = '';
  private currentKey = '';
  private defaultApplied = false;

  constructor(
    private service: SavedViewsService,
    private tokens: TokenService,
    private translate: TranslateService,
    private host: ElementRef<HTMLElement>
  ) {}

  get scope(): SavedViewsScope {
    return {
      companyId: this.companyId ?? this.tokens.getSelectCompany()?.companyId ?? '',
      pageKey: this.pageKey,
    };
  }

  ngOnInit(): void {
    this.load(true);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['currentFilters']) this.currentKey = stableStringify(this.currentFilters);
    if ((changes['pageKey'] || changes['companyId']) && !changes['pageKey']?.firstChange) {
      this.load(false);
    }
  }

  isActive(view: SavedView): boolean {
    return stableStringify(view.filters) === this.currentKey;
  }

  applyView(view: SavedView): void {
    this.closeMenus();
    this.apply.emit(this.clone(view.filters));
  }

  startCreate(): void {
    this.menuFor = null;
    this.editing = 'new';
    this.draftName = '';
    this.focusName();
  }

  startRename(view: SavedView): void {
    this.menuFor = null;
    this.editing = view.id;
    this.draftName = view.name;
    this.focusName();
  }

  submitName(): void {
    const name = this.draftName.trim();
    if (!name) {
      this.focusName();
      return;
    }
    const req =
      this.editing === 'new'
        ? this.service.create(this.scope, name, this.clone(this.currentFilters))
        : this.service.rename(this.scope, this.editing || '', name);
    req.subscribe({
      next: () => {
        this.editing = null;
        this.load(false);
      },
      error: (err: Error) => {
        const key =
          err?.message === 'limit_reached' ? 'listKit.savedViews.limitReached' : 'listKit.savedViews.saveFailed';
        swal(this.translate.instant('listKit.common.error'), this.translate.instant(key), 'error');
      },
    });
  }

  cancelEdit(): void {
    this.editing = null;
    this.draftName = '';
  }

  toggleDefault(view: SavedView): void {
    this.menuFor = null;
    this.service.setDefault(this.scope, view.isDefault ? null : view.id).subscribe(() => this.load(false));
  }

  remove(view: SavedView): void {
    this.menuFor = null;
    swal({
      title: this.translate.instant('listKit.savedViews.deleteTitle'),
      text: view.name,
      icon: 'warning',
      dangerMode: true,
      buttons: [
        this.translate.instant('listKit.common.cancel'),
        this.translate.instant('listKit.common.delete'),
      ],
    }).then((ok: any) => {
      if (!ok) return;
      this.service.remove(this.scope, view.id).subscribe(() => this.load(false));
    });
  }

  toggleMenu(view: SavedView, ev: Event): void {
    ev.stopPropagation();
    this.menuFor = this.menuFor === view.id ? null : view.id;
  }

  trackById(_: number, v: SavedView): string {
    return v.id;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(ev: Event): void {
    if (this.menuFor && !this.host.nativeElement.contains(ev.target as Node)) {
      this.menuFor = null;
    }
  }

  @HostListener('keydown.escape')
  onEscape(): void {
    if (this.editing) this.cancelEdit();
    this.menuFor = null;
  }

  private load(initial: boolean): void {
    this.service.list(this.scope).subscribe((views) => {
      this.views = views;
      if (initial && this.autoApplyDefault && !this.defaultApplied) {
        this.defaultApplied = true;
        const def = views.find((v) => v.isDefault);
        // Deferred so the host is not mutated during its own change-detection pass.
        if (def) Promise.resolve().then(() => this.apply.emit(this.clone(def.filters)));
      }
    });
  }

  private closeMenus(): void {
    this.menuFor = null;
  }

  private focusName(): void {
    setTimeout(() => this.nameInput?.nativeElement.focus());
  }

  private clone<T>(value: T): T {
    return value === undefined ? value : JSON.parse(JSON.stringify(value));
  }
}
