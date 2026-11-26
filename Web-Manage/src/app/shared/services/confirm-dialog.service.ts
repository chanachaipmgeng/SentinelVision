import { Injectable, signal } from '@angular/core';

export type ConfirmDialogVariant = 'info' | 'success' | 'warning' | 'danger';
export type ConfirmDialogMode = 'alert' | 'confirm' | 'prompt';

export interface ConfirmDialogAction {
  text: string;
  value: unknown;
  variant?: ConfirmDialogVariant | 'ghost';
}

export interface ConfirmDialogOptions {
  title: string;
  message?: string;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmDialogVariant;
  mode?: ConfirmDialogMode;
  placeholder?: string;
  defaultValue?: string;
  inputType?: 'text' | 'password';
  icon?: string;
  actions?: ConfirmDialogAction[];
}

export interface ActiveConfirmDialog {
  options: ConfirmDialogOptions;
  inputValue: string;
  resolve: (result: unknown) => void;
}

let globalConfirmDialogService: ConfirmDialogService | null = null;

export function registerConfirmDialogService(svc: ConfirmDialogService): void {
  globalConfirmDialogService = svc;
}

export function getConfirmDialogService(): ConfirmDialogService | null {
  return globalConfirmDialogService;
}

@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  private readonly queue: ActiveConfirmDialog[] = [];
  readonly activeDialog = signal<ActiveConfirmDialog | null>(null);

  constructor() {
    registerConfirmDialogService(this);
  }

  alert(options: ConfirmDialogOptions | string, message?: string): Promise<void> {
    const opts: ConfirmDialogOptions =
      typeof options === 'string' ? { title: options, message } : options;
    return this.enqueue({
      mode: 'alert',
      variant: 'info',
      ...opts,
    }).then(() => undefined);
  }

  confirm(options: ConfirmDialogOptions | string, message?: string): Promise<boolean> {
    const opts: ConfirmDialogOptions =
      typeof options === 'string' ? { title: options, message } : options;
    return this.enqueue({
      mode: 'confirm',
      variant: 'warning',
      ...opts,
    }).then((res) => Boolean(res));
  }

  prompt(options: ConfirmDialogOptions | string, message?: string): Promise<string | null> {
    const opts: ConfirmDialogOptions =
      typeof options === 'string' ? { title: options, message } : options;
    return this.enqueue({
      mode: 'prompt',
      variant: 'info',
      ...opts,
    }).then((res) => (typeof res === 'string' ? res : null));
  }

  custom<T = unknown>(options: ConfirmDialogOptions): Promise<T> {
    return this.enqueue(options) as Promise<T>;
  }

  close(result: unknown): void {
    const current = this.activeDialog();
    if (!current) return;
    current.resolve(result);
    const next = this.queue.shift() || null;
    this.activeDialog.set(next);
  }

  private enqueue(options: ConfirmDialogOptions): Promise<unknown> {
    return new Promise((resolve) => {
      const entry: ActiveConfirmDialog = {
        options,
        inputValue: options.defaultValue ?? '',
        resolve,
      };
      if (!this.activeDialog()) {
        this.activeDialog.set(entry);
      } else {
        this.queue.push(entry);
      }
    });
  }
}
