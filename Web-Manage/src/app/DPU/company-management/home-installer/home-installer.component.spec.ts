import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';

import { HomeInstallerComponent } from './home-installer.component';
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';

describe('HomeInstallerComponent', () => {
  let fixture: ComponentFixture<HomeInstallerComponent>;

  beforeEach(async () => {
    window.localStorage.clear();
    await TestBed.configureTestingModule({
    imports: [HomeInstallerComponent, RouterTestingModule, TranslateModule.forRoot()],
    providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({}) } } },
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
    ]
}).compileComponents();
    fixture = TestBed.createComponent(HomeInstallerComponent);
    fixture.detectChanges();
  });

  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('creates and reports a missing companyId instead of calling the API', () => {
    const cmp = fixture.componentInstance;
    expect(cmp).toBeTruthy();
    expect(cmp.companyId).toBe('');
    expect(cmp.loading).toBeFalse();
    expect(cmp.error).toBeTruthy();
  });
});
