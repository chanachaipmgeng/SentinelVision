import { EmployeeModel } from "./employee.model";

export class SubWarningModel {
    companyId: string;
    memberId: string;
    employeeCode: string;
    firstName: string;
    lastName: string;
    positionName: string;
    departmentName: string;
    profilePhotoFileName: string;
    tel: string;
    totalWarningTimeStamp: number;
  }

  export class SubWarningDailyModel {
    datas: DataModel[];
    employeeDatas: EmployeeModel[];
  }

  export class DataModel {
    companyId: string;
    memberId: string;
    memberName: string;
    employeeCode: string;
    timeStampImage?: any;
    stampFileName: string;
    dateTimeMilliSecond: number;
    swipeType: number;
    swipeTypeName: string;
    swipeDate?: any;
    swipeTime?: any;
    lat: string;
    lng: string;
    mobile: string;
    dayType: string;
    errorType: number;
    remark: string;
    sourceType: string;
    stampFlag: string;
    timeStampType: number;
    deviceId: string;
    authenBy: number;
    reason: string;
    timeStampStatus: number;
    swipeDateTime: string;
    contractNo?: any;
    siteNo?: any;
    customerId?: any;
    siteName?: any;
  }

  export class SubWarningTimeListModel {
    swipeDate: string;
    items: DataModel[];
  }