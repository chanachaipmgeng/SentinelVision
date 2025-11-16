export interface PayslipMyhrModel {
  salaType: SalaType
  genDate: string
  payDate: any
  month: string
  year: string
  prgCode: string
  showSlip: string
  period: string,
  periodSeq: string
}

export interface SalaType {
  codeId: string
  tdesc: string
  edesc: string
}
