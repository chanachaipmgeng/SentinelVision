export class MyHRConfigModel {
  companyID: string;
  companyCode: string;
  companyName: string;
  myhrUrl: string;
  database: string;
  myHrCode: string;
  token: string;
  sendTimeType: number;
  payslipCurrentTemplate: string;
  payslipCurrentJasperTemplate: string;
  payslipHistoryTemplate: string;
  payslipHistoryJasperTemplate: string;
  payslipEncrypt: number;
}

export class MyHRLoginModel {
  memberId: string;
  companyId: string;
  dbName: string;
  dbcomp: string;
  lang: string;
}
