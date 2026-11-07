import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule } from '@ngx-translate/core';

import { HomeCommonComponent } from './home-common.component';

describe('HomeCommonComponent', () => {
  let fixture: ComponentFixture<HomeCommonComponent>;

  beforeEach(async () => {
    window.localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [HomeCommonComponent, HttpClientTestingModule, RouterTestingModule, TranslateModule.forRoot()],
    }).compileComponents();
    fixture = TestBed.createComponent(HomeCommonComponent);
    fixture.detectChanges();
  });

  it('creates and renders its admin links', () => {
    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.componentInstance.links.length).toBeGreaterThan(0);
  });
});
