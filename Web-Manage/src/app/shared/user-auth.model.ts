import { EmployeeModel } from "../DPU/models/employee.model";
import { UserProfileModel } from "../DPU/models/user.model";

export class LoginModel {
  public username: string = "";
  public password: string = "";
  public email: string = "";
}


export class UserModel {
  public access_token: string = "";
  public token_type: string = "";
  public member : UserProfileModel = new UserProfileModel()
}

export interface ProfileModel {
  username: string;
  password: string;
  employee: EmployeeModel;
  roleId: string;
  groupId: string;
}

export class ProfileModel {
  public username: string = "";
  public password: string = "";
  public employee: EmployeeModel = new EmployeeModel()
  public roleId: string = "";
  public groupId: string = ""
}

