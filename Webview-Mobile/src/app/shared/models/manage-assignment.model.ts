import { TranslateService } from "@ngx-translate/core";
import { BaseModel } from "./base.model";

export interface ManageAssignmentMiniModel {
  jobNumberId: string
  status: string
  workName: string
}

export class ManageAssignmentMiniModel extends BaseModel implements ManageAssignmentMiniModel {
  jobNumberId: string
  status: string
  workName: string
  constructor(data: Partial<ManageAssignmentMiniModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.jobNumberId = data.jobNumberId ? data.jobNumberId : ""
    this.status = data.status ? data.status : "";
    this.workName = data.workName ? data.workName : "";
  }
}


export interface ManageAssignmentModel {
  agency: ManageAssignmentAgencyModel
  detail: string
  endDate: string
  endTime: string
  jobNumberId: string
  location: ManageAssignmentLocationModel
  manageAssignmentTeamList: ManageAssignmentTeamModel[]
  notification: string
  payType: string
  place: string
  reserveCar: string
  reserveCarNumber: string
  reserveCarStatus: string
  source: ManageAssignmentSourceModel
  startDate: string
  startTime: string
  status: string
  workLine: ManageAssignmentWorkLineModel
  workName: string
  createBy: string
}
export class ManageAssignmentModel extends BaseModel implements ManageAssignmentModel {
  agency: ManageAssignmentAgencyModel
  detail: string
  endDate: string
  endTime: string
  jobNumberId: string
  location: ManageAssignmentLocationModel
  manageAssignmentTeamList: ManageAssignmentTeamModel[]
  notification: string
  payType: string
  place: string
  reserveCar: string
  reserveCarNumber: string
  reserveCarStatus: string
  source: ManageAssignmentSourceModel
  startDate: string
  startTime: string
  status: string
  workLine: ManageAssignmentWorkLineModel
  workName: string
  createBy: string
  constructor(data: Partial<ManageAssignmentModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.agency = new ManageAssignmentAgencyModel(data.agency ? data.agency : {}, translateService)
    this.detail = data.detail ? data.detail : ""
    this.endDate = data.endDate ? data.endDate : ""
    this.endTime = data.endTime ? data.endTime : ""
    this.jobNumberId = data.jobNumberId ? data.jobNumberId : ""
    this.location = new ManageAssignmentLocationModel(data.location ? data.location : {}, translateService)
    this.manageAssignmentTeamList = data.manageAssignmentTeamList ? data.manageAssignmentTeamList.map(x => new ManageAssignmentTeamModel(x, translateService)) : []
    this.notification = data.notification ? data.notification : ""
    this.payType = data.payType ? data.payType : ""
    this.place = data.place ? data.place : ""
    this.reserveCar = data.reserveCar ? data.reserveCar : ""
    this.reserveCarNumber = data.reserveCarNumber ? data.reserveCarNumber : ""
    this.reserveCarStatus = data.reserveCarStatus ? data.reserveCarStatus : ""
    this.source = new ManageAssignmentSourceModel(data.source ? data.source : {}, translateService)
    this.startDate = data.startDate ? data.startDate : ""
    this.startTime = data.startTime ? data.startTime : ""
    this.status = data.status ? data.status : ""
    this.workLine = new ManageAssignmentWorkLineModel(data.workLine ? data.workLine : {}, translateService)
    this.workName = data.workName ? data.workName : ""
    this.createBy = data.createBy ? data.createBy : ""
  }
}

export interface ManageAssignmentLocationModel {
  alwaDay: string
  district: ManageAssignmentDistrictModel
  edesc: string
  latitude: string
  locationId: string
  longitude: string
  province: ManageAssignmentProvinceModel
  radius: string
  tdesc: string
}
export class ManageAssignmentLocationModel extends BaseModel implements ManageAssignmentLocationModel {
  alwaDay: string
  district: ManageAssignmentDistrictModel
  edesc: string
  latitude: string
  locationId: string
  longitude: string
  province: ManageAssignmentProvinceModel
  radius: string
  tdesc: string
  constructor(data: Partial<ManageAssignmentLocationModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.alwaDay = data.alwaDay ? data.alwaDay : ""
    this.district = new ManageAssignmentDistrictModel(data.district ? data.district : {}, translateService)
    this.edesc = data.edesc ? data.edesc : "";
    this.latitude = data.latitude ? data.latitude : "";
    this.locationId = data.locationId ? data.locationId : "";
    this.longitude = data.longitude ? data.longitude : "";
    this.province = new ManageAssignmentProvinceModel(data.province ? data.province : {}, translateService)
    this.radius = data.radius ? data.radius : "";
    this.tdesc = data.tdesc ? data.tdesc : "";
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}

export interface ManageAssignmentDistrictModel {
  districtId: string
  edesc: string
  province: ManageAssignmentProvinceModel
  tdesc: string
}
export class ManageAssignmentDistrictModel extends BaseModel implements ManageAssignmentDistrictModel {
  districtId: string
  edesc: string
  province: ManageAssignmentProvinceModel
  tdesc: string
  constructor(data: Partial<ManageAssignmentDistrictModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.districtId = data.districtId ? data.districtId : ""
    this.tdesc = data.tdesc ? data.tdesc : "";
    this.edesc = data.edesc ? data.edesc : "";
    this.province = new ManageAssignmentProvinceModel(data.province ? data.province : {}, translateService)
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}

export interface ManageAssignmentProvinceModel {
  longEname: string
  longTname: string
  provinceId: string
}
export class ManageAssignmentProvinceModel extends BaseModel implements ManageAssignmentProvinceModel {
  longEname: string
  longTname: string
  provinceId: string
  constructor(data: Partial<ManageAssignmentProvinceModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.provinceId = data.provinceId ? data.provinceId : ""
    this.longTname = data.longTname ? data.longTname : "";
    this.longEname = data.longEname ? data.longEname : "";
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.longTname ? this.longTname : (this.longEname ? this.longEname : "")) : (this.longEname ? this.longEname : (this.longTname ? this.longTname : ""))
  }
}

export interface ManageAssignmentSourceModel {
  edesc: string
  sourceId: string
  tdesc: string
}
export class ManageAssignmentSourceModel extends BaseModel implements ManageAssignmentSourceModel {
  edesc: string
  sourceId: string
  tdesc: string
  constructor(data: Partial<ManageAssignmentSourceModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.sourceId = data.sourceId ? data.sourceId : ""
    this.tdesc = data.tdesc ? data.tdesc : "";
    this.edesc = data.edesc ? data.edesc : "";
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}

export interface ManageAssignmentWorkLineModel {
  edesc: string
  workLineId: string
  tdesc: string
  email1: string
  email2: string
  email3: string
  email4: string
  email5: string
  workType: ManageAssignmentWorkTypeModel
}
export class ManageAssignmentWorkLineModel extends BaseModel implements ManageAssignmentWorkLineModel {
  edesc: string
  workLineId: string
  tdesc: string
  email1: string
  email2: string
  email3: string
  email4: string
  email5: string
  workType: ManageAssignmentWorkTypeModel
  constructor(data: Partial<ManageAssignmentWorkLineModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.workLineId = data.workLineId ? data.workLineId : ""
    this.tdesc = data.tdesc ? data.tdesc : "";
    this.edesc = data.edesc ? data.edesc : "";
    this.email1 = data.email1 ? data.email1 : "";
    this.email2 = data.email2 ? data.email2 : "";
    this.email3 = data.email3 ? data.email3 : "";
    this.email4 = data.email4 ? data.email4 : "";
    this.email5 = data.email5 ? data.email5 : "";
    this.workType = new ManageAssignmentWorkTypeModel(data.workType ? data.workType : {}, translateService)
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}

export interface ManageAssignmentWorkTypeModel {
  edesc: string
  jobTypeId: string
  tdesc: string
  email1: string
  email2: string
  email3: string
  email4: string
  email5: string
}
export class ManageAssignmentWorkTypeModel extends BaseModel implements ManageAssignmentWorkTypeModel {
  edesc: string
  jobTypeId: string
  tdesc: string
  email1: string
  email2: string
  email3: string
  email4: string
  email5: string
  constructor(data: Partial<ManageAssignmentWorkTypeModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.jobTypeId = data.jobTypeId ? data.jobTypeId : ""
    this.tdesc = data.tdesc ? data.tdesc : "";
    this.edesc = data.edesc ? data.edesc : "";
    this.email1 = data.email1 ? data.email1 : "";
    this.email2 = data.email2 ? data.email2 : "";
    this.email3 = data.email3 ? data.email3 : "";
    this.email4 = data.email4 ? data.email4 : "";
    this.email5 = data.email5 ? data.email5 : "";
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}

export interface ManageAssignmentAgencyModel {
  carAgencyId: string
  tdesc: string
  edesc: string
  email1: string
  email2: string
  email3: string
  email4: string
  email5: string
}
export class ManageAssignmentAgencyModel extends BaseModel implements ManageAssignmentAgencyModel {
  carAgencyId: string
  tdesc: string
  edesc: string
  email1: string
  email2: string
  email3: string
  email4: string
  email5: string
  constructor(data: Partial<ManageAssignmentAgencyModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.carAgencyId = data.carAgencyId ? data.carAgencyId : ""
    this.tdesc = data.tdesc ? data.tdesc : "";
    this.edesc = data.edesc ? data.edesc : "";
    this.email1 = data.email1 ? data.email1 : "";
    this.email2 = data.email2 ? data.email2 : "";
    this.email3 = data.email3 ? data.email3 : "";
    this.email4 = data.email4 ? data.email4 : "";
    this.email5 = data.email5 ? data.email5 : "";
  }

  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}


export interface ManageAssignmentTeamModel {
  duty: ManageAssignmentDutyModel
  employee: ManageAssignmentEmployeeModel
  endDate: string
  endTime: string
  notification: string
  startDate: string
  startTime: string
}
export class ManageAssignmentTeamModel extends BaseModel implements ManageAssignmentTeamModel {
  duty: ManageAssignmentDutyModel
  employee: ManageAssignmentEmployeeModel
  endDate: string
  endTime: string
  notification: string
  startDate: string
  startTime: string
  constructor(data: Partial<ManageAssignmentTeamModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.duty = new ManageAssignmentDutyModel(data.duty ? data.duty : {}, translateService)
    this.employee = new ManageAssignmentEmployeeModel(data.employee ? data.employee : {}, translateService)
    this.endDate = data.endDate ? data.endDate : ""
    this.endTime = data.endTime ? data.endTime : "";
    this.notification = data.notification ? data.notification : "";
    this.startDate = data.startDate ? data.startDate : "";
    this.startTime = data.startTime ? data.startTime : "";
  }
}

export interface ManageAssignmentDutyModel {
  dutyId: string
  tdesc: string
  edesc: string
}
export class ManageAssignmentDutyModel extends BaseModel implements ManageAssignmentDutyModel {
  dutyId: string
  tdesc: string
  edesc: string
  constructor(data: Partial<ManageAssignmentDutyModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.dutyId = data.dutyId ? data.dutyId : ""
    this.tdesc = data.tdesc ? data.tdesc : "";
    this.edesc = data.edesc ? data.edesc : "";
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}


export interface ManageAssignmentEmployeeModel {
  efname: string
  elname: string
  employeeId: string
  fname: string
  lname: string
  prefix: ManageAssignmentPrefixModel
  email: string
  thFullName: string
  engFullName: string
}
export class ManageAssignmentEmployeeModel extends BaseModel implements ManageAssignmentEmployeeModel {
  efname: string
  elname: string
  employeeId: string
  fname: string
  lname: string
  prefix: ManageAssignmentPrefixModel
  email: string
  thFullName: string
  engFullName: string
  constructor(data: Partial<ManageAssignmentEmployeeModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.efname = data.efname ? data.efname : ""
    this.elname = data.elname ? data.elname : "";
    this.employeeId = data.employeeId ? data.employeeId : "";
    this.fname = data.fname ? data.fname : "";
    this.lname = data.lname ? data.lname : "";
    this.prefix = new ManageAssignmentPrefixModel(data.prefix ? data.prefix : {}, translateService)
    this.email = data.email ? data.email : "";
    this.thFullName = data.thFullName ? data.thFullName : "";
    this.engFullName = data.engFullName ? data.engFullName : "";
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.getNameTH() ? this.getNameTH() : (this.getNameENG() ? this.getNameENG() : "")) : (this.getNameENG() ? this.getNameENG() : (this.getNameTH() ? this.getNameTH() : ""))
  }
  getNameTH() {
    return this.fname + (this.fname && this.lname ? " " : "") + this.lname
  }
  getNameENG() {
    return this.efname + (this.efname && this.elname ? " " : "") + this.elname
  }
}

export interface ManageAssignmentPrefixModel {
  edesc: string
  prefixId: string
  tdesc: string
}
export class ManageAssignmentPrefixModel extends BaseModel implements ManageAssignmentPrefixModel {
  edesc: string
  prefixId: string
  tdesc: string
  constructor(data: Partial<ManageAssignmentPrefixModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.prefixId = data.prefixId ? data.prefixId : ""
    this.tdesc = data.tdesc ? data.tdesc : "";
    this.edesc = data.edesc ? data.edesc : "";
  }
  getName() {
    return this.translateService?.currentLang == 'th' ? (this.tdesc ? this.tdesc : (this.edesc ? this.edesc : "")) : (this.edesc ? this.edesc : (this.tdesc ? this.tdesc : ""))
  }
}



export interface ManageAssignmentCloseNewsModel {
  agency: ManageAssignmentAgencyModel
  carInformation: ManageAssignmentCarInformationModel
  detail: string
  endDate: string
  endTime: string
  jobNumberId: string
  location: ManageAssignmentLocationModel
  notification: string
  payType: string
  place: string
  reserveCar: string
  reserveCarNumber: string
  reserveCarStatus: string
  source: ManageAssignmentSourceModel
  startDate: string
  startTime: string
  status: string
  teamHeader: ManageAssignmentTeamHeaderModel[]
  workLine: ManageAssignmentWorkLineModel
  workName: string
}
export class ManageAssignmentCloseNewsModel extends BaseModel implements ManageAssignmentCloseNewsModel {
  agency: ManageAssignmentAgencyModel
  carInformation: ManageAssignmentCarInformationModel
  detail: string
  endDate: string
  endTime: string
  jobNumberId: string
  location: ManageAssignmentLocationModel
  notification: string
  payType: string
  place: string
  reserveCar: string
  reserveCarNumber: string
  reserveCarStatus: string
  source: ManageAssignmentSourceModel
  startDate: string
  startTime: string
  status: string
  teamHeader: ManageAssignmentTeamHeaderModel[]
  workLine: ManageAssignmentWorkLineModel
  workName: string
  constructor(data: Partial<ManageAssignmentCloseNewsModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.agency = new ManageAssignmentAgencyModel(data.agency ? data.agency : {}, translateService)
    this.carInformation = new ManageAssignmentCarInformationModel(data.carInformation ? data.carInformation : {}, translateService)
    this.detail = data.detail ? data.detail : ""
    this.endDate = data.endDate ? data.endDate : ""
    this.endTime = data.endTime ? data.endTime : ""
    this.jobNumberId = data.jobNumberId ? data.jobNumberId : ""
    this.location = new ManageAssignmentLocationModel(data.location ? data.location : {}, translateService)
    this.notification = data.notification ? data.notification : ""
    this.payType = data.payType ? data.payType : ""
    this.place = data.place ? data.place : ""
    this.reserveCar = data.reserveCar ? data.reserveCar : ""
    this.reserveCarNumber = data.reserveCarNumber ? data.reserveCarNumber : ""
    this.reserveCarStatus = data.reserveCarStatus ? data.reserveCarStatus : ""
    this.source = new ManageAssignmentSourceModel(data.source ? data.source : {}, translateService)
    this.startDate = data.startDate ? data.startDate : ""
    this.startTime = data.startTime ? data.startTime : ""
    this.status = data.status ? data.status : ""
    this.teamHeader = data.teamHeader ? data.teamHeader.map(x => new ManageAssignmentTeamHeaderModel(x, translateService)) : []
    this.workLine = new ManageAssignmentWorkLineModel(data.workLine ? data.workLine : {}, translateService)
    this.workName = data.workName ? data.workName : ""
  }
}
export interface ManageAssignmentTeamHeaderModel {
  duty: ManageAssignmentDutyModel
  employee: ManageAssignmentEmployeeModel
  notification: string
  readCheck: string
  teamDetailList: ManageAssignmentTeamDetailModel[]
}
export class ManageAssignmentTeamHeaderModel extends BaseModel implements ManageAssignmentTeamHeaderModel {
  duty: ManageAssignmentDutyModel
  employee: ManageAssignmentEmployeeModel
  notification: string
  readCheck: string
  teamDetailList: ManageAssignmentTeamDetailModel[]
  constructor(data: Partial<ManageAssignmentTeamHeaderModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.duty = new ManageAssignmentDutyModel(data.duty ? data.duty : {}, translateService)
    this.employee = new ManageAssignmentEmployeeModel(data.employee ? data.employee : {}, translateService)
    this.notification = data.notification ? data.notification : "";
    this.readCheck = data.readCheck ? data.readCheck : "0";
    this.teamDetailList = data.teamDetailList ? data.teamDetailList.map(x => new ManageAssignmentTeamDetailModel(x, translateService)) : []
  }
}

export interface ManageAssignmentTeamDetailModel {
  date: string
  endTime: string
  startTime: string
  swipeTimeIn: number
  swipeTimeOut: number
}
export class ManageAssignmentTeamDetailModel extends BaseModel implements ManageAssignmentTeamDetailModel {
  date: string
  endTime: string
  startTime: string
  swipeTimeIn: number
  swipeTimeOut: number
  constructor(data: Partial<ManageAssignmentTeamDetailModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.date = data.date ? data.date : "";
    this.endTime = data.endTime ? data.endTime : "";
    this.startTime = data.startTime ? data.startTime : "";
    this.swipeTimeIn = data.swipeTimeIn ? data.swipeTimeIn : 0;
    this.swipeTimeOut = data.swipeTimeOut ? data.swipeTimeOut : 0;
  }
}

export interface ManageAssignmentCarInformationModel {
  carId: string
  carAgency: ManageAssignmentAgencyModel
  carRegis: string
  carModel: string
  seat: string
  carType: string
  driver: string
  remarks: string
}
export class ManageAssignmentCarInformationModel extends BaseModel implements ManageAssignmentCarInformationModel {
  carId: string
  carAgency: ManageAssignmentAgencyModel
  carRegis: string
  carModel: string
  seat: string
  carType: string
  driver: string
  remarks: string
  constructor(data: Partial<ManageAssignmentCarInformationModel>, translateService?: TranslateService) {
    super(data, translateService);
    this.carId = data.carId ? data.carId : ""
    this.carAgency = new ManageAssignmentAgencyModel(data.carAgency ? data.carAgency : {}, translateService)
    this.carRegis = data.carRegis ? data.carRegis : ""
    this.carModel = data.carModel ? data.carModel : ""
    this.seat = data.seat ? data.seat : ""
    this.carType = data.carType ? data.carType : ""
    this.driver = data.driver ? data.driver : ""
    this.remarks = data.remarks ? data.remarks : ""
  }
}


