import { HTTP_INTERCEPTORS, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpHandler, HttpRequest } from '@angular/common/http';

import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, filter, switchMap, take } from 'rxjs/operators';
import { TokenService } from './token.service';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';



const TOKEN_HEADER_KEY = 'Authorization';    // for Node.js Expre
@Injectable()
export class HttpRequestInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject: BehaviorSubject<any> = new BehaviorSubject<any>(null);
  constructor(private tokenService: TokenService, private authService: AuthService) { }

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    if (req.url.startsWith("./")) {
      return next.handle(req);
    } else {
      let authReq = req;
      const fullUrl = req.url.startsWith("http") ? req.url : environment.baseUrl + req.url;
      const token = "Bearer "+this.tokenService.getToken()
      console.log(fullUrl)
      if (token != null) {
        authReq = this.addTokenHeader(req, token ,fullUrl);
      }else{
        const overideReq = {
          url: fullUrl,
        };
        authReq = req.clone(overideReq);
      }
      console.log("full url : ",fullUrl)
      return next.handle(authReq).pipe(catchError(error => {
        console.log("error",error)
        if (error instanceof HttpErrorResponse && error.status === 403 && !fullUrl.includes("login")) {
          console.log("error",403)
          return this.handle403Error(authReq, next ,fullUrl);
        }
        return throwError(error);
      }));
    }

  }

  private handle403Error(request: HttpRequest<any>, next: HttpHandler , fullUrl : string) {
    if (!this.isRefreshing) {
      this.isRefreshing = true;
      this.refreshTokenSubject.next(null);

      const token = this.tokenService.getRefreshToken();

      if (token)
        return this.authService.refreshToken(token.replace("Bearer ","")).pipe(
          switchMap((token: any) => {
            this.isRefreshing = false;

            this.tokenService.saveToken(token.accessToken);
            this.tokenService.saveRefreshToken(token.refreshToken);
            this.refreshTokenSubject.next(token.accessToken);

            return next.handle(this.addTokenHeader(request, token.accessToken ,fullUrl));
          }),
          catchError((err) => {
            this.isRefreshing = false;

            this.tokenService.signOut();
            return throwError(err);
          })
        );
    }

    return this.refreshTokenSubject.pipe(
      filter(token => token !== null),
      take(1),
      switchMap((token) => next.handle(this.addTokenHeader(request, token ,fullUrl)))
    );
  }



  private addTokenHeader(request: HttpRequest<any>, token: string ,fullUrl :string) {
    /* for Spring Boot back-end */
    // return request.clone({ headers: request.headers.set(TOKEN_HEADER_KEY, 'Bearer ' + token) });

    /* for Node.js Express back-end */
    return request.clone({ headers: request.headers.set(TOKEN_HEADER_KEY, token) , url : fullUrl });
  }
}
