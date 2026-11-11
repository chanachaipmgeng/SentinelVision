
export function handleThemeUpdate(cssVars: Record<string, string | null | undefined>): void {
  const root = document.documentElement;
  const keys = Object.keys(cssVars);

  keys.forEach((key) => {
    const value = cssVars[key];
    if (value != null) {
      root.style.setProperty(key, value);
    }
  });
}

const isValidHex = (hexValue: string): boolean =>
  /^#([A-Fa-f0-9]{3,4}){1,2}$/.test(hexValue);

const getChunksFromString = (st: string, chunkSize: number): string[] | null =>
  st.match(new RegExp(`.{${chunkSize}}`, 'g'));

const convertHexUnitTo256 = (hexStr: string): number =>
  parseInt(hexStr.repeat(2 / hexStr.length), 16);

const _getAlphafloat = (a: string | undefined, alpha: number | undefined): number => {
  if (typeof a !== 'undefined') {
    return parseInt(a, 10) / 255;
  }
  if (typeof alpha !== 'number' || alpha < 0 || alpha > 1) {
    return 1;
  }
  return alpha;
};

export function hexToRgba(hexValue: string): string | null {
  if (!isValidHex(hexValue)) {
    return null;
  }
  const chunkSize = Math.floor((hexValue.length - 1) / 3);
  const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
  if (!hexArr) return null;
  const [r, g, b] = hexArr.map(convertHexUnitTo256);
  return `${r} ${g} ${b}`;
}

export function hexToRgba1(hexValue: string): string | null {
  if (!isValidHex(hexValue)) {
    return null;
  }
  const chunkSize = Math.floor((hexValue.length - 1) / 3);
  const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
  if (!hexArr) return null;
  const [r, g, b] = hexArr.map(convertHexUnitTo256);
  return `${r} ${g} ${b}`;
}

export function hexToRgba2(hexValue: string): string | null {
  if (!isValidHex(hexValue)) {
    return null;
  }
  const chunkSize = Math.floor((hexValue.length - 1) / 3);
  const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
  if (!hexArr) return null;
  const [r, g, b] = hexArr.map(convertHexUnitTo256);
  return `${r - 14}, ${g - 14}, ${b - 14}`;
}

export function hexToRgba3(hexValue: string): string | null {
  if (!isValidHex(hexValue)) {
    return null;
  }
  const chunkSize = Math.floor((hexValue.length - 1) / 3);
  const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
  if (!hexArr) return null;
  const [r, g, b] = hexArr.map(convertHexUnitTo256);
  return `${r - 9}, ${g - 9}, ${b - 9}`;
}

type ThemeColorSwatch = HTMLElement & {
  getAttribute(name: 'data-id' | 'data-id1' | 'data-id3' | 'data-id5' | 'data-id6'): string | null;
};

export function dynamicLightPrimaryColor(
  primaryColor: NodeListOf<Element> | ThemeColorSwatch[],
  color: string,
): void {
  Array.from(primaryColor).forEach((item) => {
    const el = item as ThemeColorSwatch;
    const cssPropName = `--${el.getAttribute('data-id')}`;
    const cssPropName1 = `--color-${el.getAttribute('data-id1')}`;

    handleThemeUpdate({
      [cssPropName]: hexToRgba1(color) ?? undefined,
      [cssPropName1]: hexToRgba(color) ?? undefined,
    });
  });
}

export function dynamicBgTrasnsparentPrimaryColor(
  primaryColor: NodeListOf<Element> | ThemeColorSwatch[],
  color: string,
): void {
  Array.from(primaryColor).forEach((item) => {
    const el = item as ThemeColorSwatch;
    const cssPropName3 = `--${el.getAttribute('data-id3')}`;
    const cssPropName1 = `--body-${el.getAttribute('data-id5')}`;
    const cssPropName2 = `--dark-${el.getAttribute('data-id6')}`;
    handleThemeUpdate({
      [cssPropName1]: hexToRgba(color) ?? undefined,
      [cssPropName2]: hexToRgba2(color) ?? undefined,
      [cssPropName3]: hexToRgba3(color) ?? undefined,
    });
  });
}

export function localStorageBackUp(): void {
  const html = document.querySelector('html');
  if (!html) return;

  const setHtmlClass = (value: string | null) => {
    if (value != null) html.setAttribute('class', value);
  };

  if (localStorage.getItem('data-header-styles') == 'dark') {
    if (localStorage.getItem('ynex-theme-mode')) {
      setHtmlClass(localStorage.getItem('ynex-theme-mode'));
    }
    if (html.getAttribute('class') === 'dark') {
      const light = document.getElementById('switcher-light') as HTMLInputElement | null;
      if (light) light.checked = true;
    } else if (html.getAttribute('class') === 'light') {
      const light = document.getElementById('switcher-light') as HTMLInputElement | null;
      if (light) light.checked = true;
    }
  }

  if (localStorage.getItem('ynex-dir') == 'rtl') {
    html.setAttribute('dir', 'rtl');
  }
  if (localStorage.getItem('ynex-theme-mode')) {
    setHtmlClass(localStorage.getItem('ynex-theme-mode'));
  }
  if (localStorage.getItem('ynex-nav-mode')) {
    const type = localStorage.getItem('ynex-nav-mode');
    if (type) html.setAttribute('data-nav-layout', type);
    if (type == 'horizontal') {
      html.setAttribute('data-nav-style', 'menu-click');
      html.removeAttribute('data-vertical-style');
    }
  }
  if (localStorage.getItem('ynex-page-mode')) {
    const type = localStorage.getItem('ynex-page-mode');
    if (type) html.setAttribute('data-page-style', type);
  }
  if (localStorage.getItem('ynex-width-mode')) {
    const type = localStorage.getItem('ynex-width-mode');
    if (type) html.setAttribute('data-width', type);
  }
  if (localStorage.getItem('ynex-menu-position')) {
    const type = localStorage.getItem('ynex-menu-position');
    if (type) html.setAttribute('data-menu-position', type);
  }
  if (localStorage.getItem('ynex-menu-mode')) {
    const type = localStorage.getItem('ynex-menu-mode');
    if (type) html.setAttribute('data-menu-styles', type);
  }
  if (localStorage.getItem('ynex-header-position')) {
    const type = localStorage.getItem('ynex-header-position');
    if (type) html.setAttribute('data-header-position', type);
  }
  if (localStorage.getItem('ynex-loader')) {
    const type = localStorage.getItem('ynex-loader');
    if (type) html.setAttribute('loader', type);
  }
  if (localStorage.getItem('ynex-header-mode')) {
    const type = localStorage.getItem('ynex-header-mode');
    if (type) html.setAttribute('data-header-styles', type);
  }

  if (localStorage.getItem('ynex-background-mode-body')) {
    const bodytype = localStorage.getItem('ynex-background-mode-body');
    const darktype = localStorage.getItem('ynex-background-mode-dark');
    const lighttype = localStorage.getItem('ynex-background-mode-light');
    const event = localStorage.getItem('ynex-theme-mode');
    if (bodytype) html.style.setProperty('--body-bg', bodytype);
    if (darktype) html.style.setProperty('--dark-bg', darktype);
    if (lighttype) html.style.setProperty('--light', lighttype);
  if (event) setHtmlClass(event);
  }
  if (localStorage.getItem('ynexlight-background-body')) {
    const bodytype = localStorage.getItem('ynexlight-background-body');
    const darktype = localStorage.getItem('ynexlight-background-dark');
    const lighttype = localStorage.getItem('ynexlight-background-light');

    if (bodytype) html.style.setProperty('--body-bg', bodytype);
    if (darktype) html.style.setProperty('--dark-bg', darktype);
    if (lighttype) html.style.setProperty('--light', lighttype);
    html.classList.add('dark');
  }
  if (localStorage.getItem('ynexlight-background-light')) {
    const bodytype = localStorage.getItem('ynexlight-background-body');
    const darktype = localStorage.getItem('ynexlight-background-dark');
    const lighttype = localStorage.getItem('ynexlight-background-light');

    if (bodytype) html.style.setProperty('--body-bg', bodytype);
    if (darktype) html.style.setProperty('--dark-bg', darktype);
    if (lighttype) html.style.setProperty('--light', lighttype);
    html.classList.add('dark');
  }
  if (localStorage.getItem('ynex-menu-style')) {
    const type1 = localStorage.getItem('ynex-menu-style');
    if (type1) html.setAttribute('data-nav-style', type1);
    const type = localStorage.getItem('ynex-menu-style-toggled');
    if (type) html.setAttribute('data-toggled', type);
  }
  if (localStorage.getItem('ynex-sidemenu-styles')) {
    const type1 = localStorage.getItem('ynex-sidemenu-styles');
    if (type1) html.setAttribute('data-vertical-style', type1);
    const type = localStorage.getItem('ynex-sidemenu-styles-toggled');
    if (type) html.setAttribute('data-toggled', type);
  }
  if (localStorage.getItem('ynex-sidemenu-styles-toggled')) {
    const type1 = localStorage.getItem('ynex-sidemenu-styles');
    if (type1) html.setAttribute('data-vertical-style', type1);
    const type = localStorage.getItem('ynex-sidemenu-styles-toggled');
    if (type) html.setAttribute('data-toggled', type);
  }
  if (localStorage.getItem('ynex-image')) {
    const type = localStorage.getItem('ynex-image');
    if (type) html.setAttribute('bg-img', type);
  }
  if (localStorage.getItem('ynex-primary-mode')) {
    const type = localStorage.getItem('ynex-primary-mode');
    if (type) {
      html.style.setProperty('--primary-rgb', type);
      html.style.setProperty('--primary', type);
    }
  }
  if (localStorage.getItem('ynexlight-primary-color')) {
    const type = localStorage.getItem('ynexlight-primary-color');
    if (type) {
      html.style.setProperty('--primary-rgb', type);
      html.style.setProperty('-primary', type);
    }
  }
  if (localStorage.getItem('ynexlight-primary-color1')) {
    const type = localStorage.getItem('ynexlight-primary-color1');
    if (type) html.style.setProperty('--primary', type);
  }
}
