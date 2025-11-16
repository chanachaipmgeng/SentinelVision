
export function handleThemeUpdate(cssVars: any) {
    const root: any = document.querySelector(':root');
    const keys = Object.keys(cssVars);
  
    keys.forEach((key) => {
      root.style.setProperty(key, cssVars[key]);
    });
  }
  // to check the value is hexa or not
  const isValidHex = (hexValue: any) =>
    /^#([A-Fa-f0-9]{3,4}){1,2}$/.test(hexValue);
  
  const getChunksFromString = (st: any, chunkSize: any) =>
    st.match(new RegExp(`.{${chunkSize}}`, 'g'));
  // convert hex value to 256
  const convertHexUnitTo256 = (hexStr: any) =>
    parseInt(hexStr.repeat(2 / hexStr.length), 16);
  // get alpha value is equla to 1 if there was no value is asigned to alpha in function
  const getAlphafloat = (a: any, alpha: any) => {
    if (typeof a !== 'undefined') {
      return a / 255;
    }
    if (typeof alpha != 'number' || alpha < 0 || alpha > 1) {
      return 1;
    }
    return alpha;
  };
  // convertion of hex code to rgba code
  export function hexToRgba(hexValue: any) {
    if (!isValidHex(hexValue)) {
      return null;
    }
    const chunkSize = Math.floor((hexValue.length - 1) / 3);
    const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
    const [r, g, b, a] = hexArr.map(convertHexUnitTo256);
    return `${r} ${g} ${b}`;
  }
  export function hexToRgba1(hexValue: any) {
    if (!isValidHex(hexValue)) {
      return null;
    }
    const chunkSize = Math.floor((hexValue.length - 1) / 3);
    const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
    const [r, g, b, ] = hexArr.map(convertHexUnitTo256);
    return `${r} ${g} ${b}`;
  }
  export function hexToRgba2(hexValue: any) {
    if (!isValidHex(hexValue)) {
      return null;
    }
    const chunkSize = Math.floor((hexValue.length - 1) / 3);
    const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
    const [r, g, b, a] = hexArr.map(convertHexUnitTo256);
    return `${r - 14}, ${g - 14}, ${b - 14}`;
  }
  export function hexToRgba3(hexValue: any) {
    if (!isValidHex(hexValue)) {
      return null;
    }
    const chunkSize = Math.floor((hexValue.length - 1) / 3);
    const hexArr = getChunksFromString(hexValue.slice(1), chunkSize);
    const [r, g, b, a] = hexArr.map(convertHexUnitTo256);
    return `${r - 9}, ${g - 9}, ${b - 9}`;
  }
  //primary theme color
  export function dynamicLightPrimaryColor(primaryColor: any, color: any) {
    primaryColor.forEach((item: any) => {
      const cssPropName = `--${item.getAttribute('data-id')}`;
      const cssPropName1 = `--color-${item.getAttribute('data-id1')}`;
  
      handleThemeUpdate({
        [cssPropName]: hexToRgba1(color),
        [cssPropName1]: hexToRgba(color),
      });
    });
  }
  
  //background theme color
  export function dynamicBgTrasnsparentPrimaryColor(
    primaryColor: any,
    color: any
  ) {
    primaryColor.forEach((item: any) => {
      const cssPropName3 = `--${item.getAttribute('data-id3')}`;
      const cssPropName1 = `--body-${item.getAttribute('data-id5')}`;
      const cssPropName2 = `--dark-${item.getAttribute('data-id6')}`;
      handleThemeUpdate({
        [cssPropName1]: hexToRgba(color),
        [cssPropName2]: hexToRgba2(color),
        [cssPropName3]: hexToRgba3(color),
  
      });
    });
  }
  
  export function localStorageBackUp() {
    let html = document.querySelector('html');
    if (localStorage.getItem('data-header-styles') == 'dark') {
      if (localStorage.getItem('ynex-theme-mode')) {
        const type: any = localStorage.getItem('ynex-theme-mode');
        html?.setAttribute('class', type);
      }
      if (html?.setAttribute('class', 'dark')) {
        const light = document.getElementById(
          'switcher-light'
        ) as HTMLInputElement;
        light.checked = true;
      } else {
        if (html?.setAttribute('class', 'light')) {
          const light = document.getElementById(
            'switcher-light'
          ) as HTMLInputElement;
          light.checked = true;
        }
      }
    }
  
    if (localStorage.getItem('ynex-dir') == 'rtl') {
      html?.setAttribute("dir", 'rtl');
    }
    if (localStorage.getItem('ynex-theme-mode')) {
      const type: any = localStorage.getItem('ynex-theme-mode');
      html?.setAttribute('class', type);
    }
    if (localStorage.getItem('ynex-nav-mode')) {
      const type: any = localStorage.getItem('ynex-nav-mode');
      html?.setAttribute('data-nav-layout', type);
      if(type == 'horizontal'){
        html?.setAttribute('data-nav-style', 'menu-click');
        html?.removeAttribute( 'data-vertical-style');
      }
    }
    if (localStorage.getItem('ynex-page-mode')) {
      const type: any = localStorage.getItem('ynex-page-mode');
      html?.setAttribute('data-page-style', type);
    }
    if (localStorage.getItem('ynex-width-mode')) {
      const type: any = localStorage.getItem('ynex-width-mode');
      html?.setAttribute('data-width', type);
    }
    if (localStorage.getItem('ynex-menu-position')) {
      const type: any = localStorage.getItem('ynex-menu-position');
      html?.setAttribute('data-menu-position', type);
    }
    if (localStorage.getItem('ynex-menu-mode')) {
      const type: any = localStorage.getItem('ynex-menu-mode');
      html?.setAttribute('data-menu-styles', type);
    }
    if (localStorage.getItem('ynex-header-position')) {
      const type: any = localStorage.getItem('ynex-header-position');
      html?.setAttribute('data-header-position', type);
    }
    if (localStorage.getItem('ynex-loader')) {
      const type: any = localStorage.getItem('ynex-loader');
      html?.setAttribute('loader', type);
    }
    if (localStorage.getItem('ynex-header-mode')) {
      const type: any = localStorage.getItem('ynex-header-mode');
      html?.setAttribute('data-header-styles', type);
    }
  
    if (localStorage.getItem("ynex-background-mode-body")) {
      const bodytype: any = localStorage.getItem("ynex-background-mode-body")
      const darktype: any = localStorage.getItem("ynex-background-mode-dark")
      const lighttype: any = localStorage.getItem("ynex-background-mode-light")
      const event: any = localStorage.getItem("ynex-theme-mode");
      html?.style.setProperty('--body-bg', bodytype);
      html?.style.setProperty('--dark-bg', darktype);
      html?.style.setProperty('--light', lighttype);
  
      html?.setAttribute("class", event);
    }
    if (localStorage.getItem("ynexlight-background-body")) {
      const bodytype: any = localStorage.getItem("ynexlight-background-body")
      const darktype: any = localStorage.getItem("ynexlight-background-dark")
      const lighttype: any = localStorage.getItem("ynexlight-background-light")
  
      html?.style.setProperty('--body-bg', bodytype);
      html?.style.setProperty('--dark-bg', darktype);
      html?.style.setProperty('--light', lighttype);
      html?.classList.add('dark');
    }
    if (localStorage.getItem("ynexlight-background-light")) {
      const bodytype: any = localStorage.getItem("ynexlight-background-body")
      const darktype: any = localStorage.getItem("ynexlight-background-dark")
      const lighttype: any = localStorage.getItem("ynexlight-background-light")
  
      html?.style.setProperty('--body-bg', bodytype);
      html?.style.setProperty('--dark-bg', darktype);
      html?.style.setProperty('--light', lighttype);
      html?.classList.add('dark');
    }
    if (localStorage.getItem("ynex-menu-style")) {
      const type1: any = localStorage.getItem("ynex-menu-style");
      html?.setAttribute("data-nav-style", type1);
      const type: any = localStorage.getItem('ynex-menu-style-toggled');
      html?.setAttribute('data-toggled', type);
    }
    if (localStorage.getItem("ynex-sidemenu-styles")) {
      const type1: any = localStorage.getItem("ynex-sidemenu-styles");
      html?.setAttribute("data-vertical-style", type1);
      const type: any = localStorage.getItem('ynex-sidemenu-styles-toggled');
      html?.setAttribute('data-toggled', type);
    }
    if (localStorage.getItem("ynex-sidemenu-styles-toggled")) {
      const type1: any = localStorage.getItem("ynex-sidemenu-styles");
      html?.setAttribute("data-vertical-style", type1);
      const type: any = localStorage.getItem('ynex-sidemenu-styles-toggled');
      html?.setAttribute('data-toggled', type);
    }
    if (localStorage.getItem("ynex-image")) {
      const type: any = localStorage.getItem("ynex-image");
      html?.setAttribute('bg-img', type);
    }
    if (localStorage.getItem("ynex-primary-mode")) {
      const type: any = localStorage.getItem("ynex-primary-mode");
      html?.style.setProperty('--primary-rgb', type);
      html?.style.setProperty('--primary', type);
    }
    if (localStorage.getItem("ynexlight-primary-color")) {
      const type: any = localStorage.getItem("ynexlight-primary-color");
  
  
      html?.style.setProperty('--primary-rgb', type);
      html?.style.setProperty('-primary', type);
    }
    if (localStorage.getItem("ynexlight-primary-color1")) {
      const type: any = localStorage.getItem("ynexlight-primary-color1");
      // html?.style.setProperty('--primary-rgb', type);
      html?.style.setProperty('--primary', type);
    }
  }
  