import { RouterModule, Routes } from '@angular/router';
import { admin, authenticationRoutingModule } from '../../components/authentication/authentication.routes';
import { createpasswordRoutingModule } from '../../components/authentication/create-password/create-password.routes';
import { lockscreenRoutingModule } from '../../components/authentication/lock-screen/lockscreen.routes';
import { resetpasswordRoutingModule } from '../../components/authentication/reset-password/reset-password.routes';
import { signinRoutingModule } from '../../components/authentication/signin/signin.routes';
import { signupRoutingModule } from '../../components/authentication/signup/signup.routes';
import { twostepverificationRoutingModule } from '../../components/authentication/twostep-verification/twostep-verification.routes';
import { errorRoutingModule } from '../../components/error/error.routes';
import { NgModule } from '@angular/core';

export const authen: Routes = [
    { path: '', children: [
        ...authenticationRoutingModule.routes,
        ...createpasswordRoutingModule.routes,
        ...lockscreenRoutingModule.routes,
        ...resetpasswordRoutingModule.routes,
        ...signinRoutingModule.routes,
        ...signupRoutingModule.routes,
        ...twostepverificationRoutingModule.routes,
        ...errorRoutingModule.routes
 ] },
    // {
    //     path: 'auth/login',
    //     loadComponent: () =>
    //       import('../../authentication/login/login.component').then((m) => m.LoginComponent),
    //   },

 
]
@NgModule({
    imports: [RouterModule.forRoot(admin)],
    exports: [RouterModule]
})
export class AuthenticationsRoutingModule { }