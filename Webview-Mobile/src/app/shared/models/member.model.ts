export class MemberModel {
    memberId: string;
    firstName: string;
    lastName: string;
    email: string;
    mobileNumber: string;
    idCard: string;
    sex: number;
    birthDate: string;
    passportNo?: any;
    nationality?: any;
    profilePhotoFileName: string;
    enrollPhotoFileName?: any;
    password?: any;
    faceTemplate: FaceTemplate;
    faceTemplateV65: FaceTemplate;
  }
  
  export class FaceTemplate {
    eyesTemplate1?: any;
    eyesTemplate2?: any;
    eyesTemplate3?: any;
    facialTemplate1?: any;
    facialTemplate2?: any;
    facialTemplate3?: any;
    enrollPhoto?: any;
    enrollPhotoFileName: string;
    eyesTemplate1FileName: string;
    eyesTemplate2FileName: string;
    eyesTemplate3FileName: string;
    facialTemplate1FileName: string;
    facialTemplate2FileName: string;
    facialTemplate3FileName: string;
  }

  export class DeviceModel {
    success: boolean;
    items: DeviceItem[];
  }
  
  export class DeviceItem {
    deviceModel: string;
    deviceName: string;
    hostName: string;
    addedDate: string;
    deviceNo: string;
    deviceVersion: string;
    devicePhone: string;
    deviceEmail: string;
    deviceImei: string;
  }