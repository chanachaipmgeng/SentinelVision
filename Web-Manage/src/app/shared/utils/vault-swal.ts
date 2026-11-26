import {
  ConfirmDialogAction,
  ConfirmDialogVariant,
  getConfirmDialogService,
} from '../services/confirm-dialog.service';

export interface LegacySwalOptions {
  title?: string;
  text?: string;
  icon?: string;
  dangerMode?: boolean;
  buttons?:
    | boolean
    | Array<string | boolean>
    | Record<string, { text?: string; value?: unknown; visible?: boolean; className?: string }>;
  content?:
    | string
    | {
        element?: string;
        attributes?: {
          type?: string;
          placeholder?: string;
          value?: string;
        };
      };
}

function mapVariant(icon?: string, dangerMode?: boolean): ConfirmDialogVariant {
  if (dangerMode || icon === 'error') return 'danger';
  if (icon === 'warning') return 'warning';
  if (icon === 'success') return 'success';
  return 'info';
}

/**
 * Drop-in Promise-based replacement for legacy `sweetalert` routed through
 * the theme-aware `ConfirmDialogService` (`SurfaceModalComponent`).
 */
export default function swal(
  titleOrOptions: string | LegacySwalOptions,
  text?: string,
  icon?: string,
): Promise<unknown> {
  const svc = getConfirmDialogService();
  if (typeof titleOrOptions === 'string') {
    const opts: LegacySwalOptions = { title: titleOrOptions, text, icon };
    if (!svc) return Promise.resolve(true);
    return svc.alert({
      title: opts.title || '',
      message: opts.text || '',
      variant: mapVariant(opts.icon),
    });
  }

  const opts = titleOrOptions || {};
  if (!svc) return Promise.resolve(opts.buttons ? false : true);
  const variant = mapVariant(opts.icon, opts.dangerMode);

  if (opts.content) {
    const cfg = typeof opts.content === 'string' ? { element: opts.content } : opts.content;
    if (cfg.element === 'input') {
      const btnArr = Array.isArray(opts.buttons) ? opts.buttons : [];
      return svc.prompt({
        title: opts.title || '',
        message: opts.text || '',
        variant,
        placeholder: cfg.attributes?.placeholder || '',
        defaultValue: cfg.attributes?.value || '',
        inputType: cfg.attributes?.type === 'password' ? 'password' : 'text',
        cancelText: typeof btnArr[0] === 'string' ? btnArr[0] : undefined,
        confirmText: typeof btnArr[1] === 'string' ? btnArr[1] : undefined,
      });
    }
  }

  if (opts.buttons && typeof opts.buttons === 'object' && !Array.isArray(opts.buttons)) {
    const actions: ConfirmDialogAction[] = Object.entries(opts.buttons).map(([key, cfg]) => ({
      text: cfg?.text || key,
      value: cfg?.value !== undefined ? cfg.value : key,
      variant: key === 'cancel' ? 'ghost' : variant,
    }));
    return svc.custom({
      title: opts.title || '',
      message: opts.text || '',
      variant,
      mode: 'confirm',
      actions,
    });
  }

  if (opts.buttons) {
    const btnArr = Array.isArray(opts.buttons) ? opts.buttons : [];
    return svc.confirm({
      title: opts.title || '',
      message: opts.text || '',
      variant,
      cancelText: typeof btnArr[0] === 'string' ? btnArr[0] : undefined,
      confirmText: typeof btnArr[1] === 'string' ? btnArr[1] : undefined,
    });
  }

  return svc.alert({
    title: opts.title || '',
    message: opts.text || '',
    variant,
  });
}
