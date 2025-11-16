export class Datum {
    employeeid: string;
    fname: string;
    lname: string;
    welid: string;
    tdesc: string;
    budget: string;
    used: string;
    remain: string;
}

export class RootCostDetail {
    welgid: string;
    data: Datum[];
    tdesc: string;
    sumbudget?:string
    sumused?:string
    sumremain?:string
}

export class RootObjectCost {
    complainid: string;
    weltid: string;
    casedesc: string;
    cost: string;
}

export class RootObjectCostMaster {
    weltid: string;
    tdesc: string;
}

export class SysModel {
    sitewelid: string;
    tdesc: string;
    latitude: string;
    longitude: string;
}