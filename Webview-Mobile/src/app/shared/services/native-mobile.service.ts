import { Injectable } from '@angular/core';
// import { EWOULDBLOCK } from 'constants';

declare const Android: any;
@Injectable({
  providedIn: 'root',
})
export class NativeMobileService {
  checkDevice = 'unknown';
  constructor() {
    this.checkPlatflom();
  }

  checkPlatflom() {
    const userAgent = navigator.userAgent || navigator.vendor;
    // Windows Phone must come first because its UA also contains "Android"
    if (/windows phone/i.test(userAgent)) {
      this.checkDevice = 'Windows Phone';
      window.localStorage.setItem('device', this.checkDevice);
    }
    if (/android/i.test(userAgent)) {
      this.checkDevice = 'Android';
      window.localStorage.setItem('device', this.checkDevice);
    }
    if (/iPhone/i.test(userAgent)) {
      this.checkDevice = 'ios';
      window.localStorage.setItem('device', this.checkDevice);
    }
  }

  enrollCompany(companyId: string, memberId: string) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.getUpdateEnrollPersonal(companyId, memberId);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        companyId: companyId,
        memberId: memberId,
      };
      try {
        (
          window as any
        ).webkit.messageHandlers.getUpdateEnrollPersonal.postMessage(
          JSON.stringify(body)
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  setToken(token: any) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.sentTokenMobile(token);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        token: token,
      };
      try {
        (window as any).webkit.messageHandlers.sentTokenMobile.postMessage(
          JSON.stringify(body)
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  mobileLogin(memberId: string, token: any) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.mobileLogin(memberId, token);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        memberId: memberId,
        token: token,
      };
      try {
        (window as any).webkit.messageHandlers.mobileLogin.postMessage(
          JSON.stringify(body)
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  mobileLogout() {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.mobileLogout();
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      try {
        (window as any).webkit.messageHandlers.mobileLogout.postMessage();
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  goTimestamp(companyId: string, memberId: string) {
    const jsonData = JSON.stringify({
      companyId: companyId,
      memberId: memberId,
    });
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.goTimestamp(companyId, memberId);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      try {
        (window as any).webkit.messageHandlers.goTimestamp.postMessage(
          jsonData
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  goEnrollment(companyId: string, memberId: string) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.goEnrollment(companyId, memberId);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        companyId: companyId,
        memberId: memberId,
      };
      try {
        (window as any).webkit.messageHandlers.goEnrollment.postMessage(
          JSON.stringify(body)
        );
      } catch { }
    }
  }

  downloadFile(link: string, token: string) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.downloadFile(link, token);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        link: link,
        token: token,
      };
      try {
        (window as any).webkit.messageHandlers.downloadFile.postMessage(
          JSON.stringify(body)
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  getVersionApp() {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        return Android.getVersion();
      } catch {
        console.log('Android Function => Error');
      }
    } else {

      try {
        alert("iOS")
        this.callIosFunction().then(result => {
          alert(result)
          setTimeout(() => {
            return result
          }, 1000);
        }).catch(error => {
          alert(error)
          console.error('Error:', error);
        });
      } catch (err) {
        alert(err)
        console.log('ios Function => Error');
      }
    }

  }

  callIosFunction(): Promise<string> {
    return new Promise((resolve, reject) => {
      if ((window as any).webkit && (window as any).webkit.messageHandlers) {
        // เรียกใช้ฟังก์ชัน iOS
        // alert("ssss")
        (window as any).webkit.messageHandlers.getVersion.postMessage(null);

        // รอการรีเทิร์นผลลัพธ์จาก iOS
        (window as any)['returnVersion'] = (result: string) => {
          resolve(result);
        };
      } else {
        reject('iOS function not available');
      }
    });
  }


  setTimestampDisplayDelay(time: number) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.setTimestampDisplayDelay(time);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        time: time,
      };
      try {
        (
          window as any
        ).webkit.messageHandlers.setTimestampDisplayDelay.postMessage(
          JSON.stringify(body)
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  getTimestampDisplayDelay(): number {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        return Android.getTimestampDisplayDelay()
          ? Android.getTimestampDisplayDelay()
          : 0;
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      try {
        (
          window as any
        ).webkit.messageHandlers.getTimestampDisplayDelay.postMessage();
        (window as any).callJSFuncNew = async function (theParameter: any) {
          return theParameter;
        };
      } catch {
        console.log('ios Function => Error');
      }
    }
    return 0;
  }

  setCameraDistance(time: number) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.setCameraDistance(time);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        time: time,
      };
      try {
        (window as any).webkit.messageHandlers.setCameraDistance.postMessage(
          body
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  getCameraDistance(): number {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        return Android.getCameraDistance() ? Android.getCameraDistance() : 1;
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      try {
        (window as any).webkit.messageHandlers.getCameraDistance.postMessage();
        (window as any).callJSFuncNew = async function (theParameter: any) {
          return theParameter;
        };
      } catch {
        console.log('ios Function => Error');
      }
    }
    return 40;
  }

  setTimestampSound() {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.setTimestampSound();
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      try {
        (window as any).webkit.messageHandlers.setTimestampSound.postMessage();
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  changeLanguage(language: string) {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.changeLanguage(language);
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      let body = {
        language: language,
      };
      try {
        (window as any).webkit.messageHandlers.changeLanguage.postMessage(
          JSON.stringify(body)
        );
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  callShowPin(){
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        Android.showPinPad()
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      try {
        (window as any).webkit.messageHandlers.getLocation.postMessage();
        (window as any).callJSFuncNew = async function (theParameter: any) {
          return theParameter;
        };
      } catch {
        console.log('ios Function => Error');
      }
    }
  }

  getLocation() {
    this.checkPlatflom();
    if (this.checkDevice === 'Android') {
      try {
        return Android.getLocation() ? Android.getLocation() : '0,0';
      } catch {
        console.log('Android Function => Error');
      }
    } else {
      try {
        (window as any).webkit.messageHandlers.getLocation.postMessage();
        (window as any).callJSFuncNew = async function (theParameter: any) {
          return theParameter;
        };
      } catch {
        console.log('ios Function => Error');
      }
    }
    return '0,0';
  }
}
