import { Component } from '@angular/core';
import { ComponentFixture, TestBed, fakeAsync, flush } from '@angular/core/testing';
import { TranslateModule } from '@ngx-translate/core';
import { SideDrawerComponent } from './side-drawer.component';

@Component({
  standalone: true,
  imports: [SideDrawerComponent],
  template: `
    <button id="opener" (click)="open = true">open</button>
    <app-side-drawer [(open)]="open" title="Detail">
      <input id="first" />
      <button drawerFooter id="last">ok</button>
    </app-side-drawer>
  `,
})
class HostComponent {
  open = false;
}

describe('SideDrawerComponent', () => {
  let fixture: ComponentFixture<HostComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent, TranslateModule.forRoot()],
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    document.body.appendChild(fixture.nativeElement);
    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
    fixture.nativeElement.remove();
    document.body.style.overflow = '';
  });

  const panel = () => document.querySelector<HTMLElement>('.dpu-drawer');

  it('renders into <body> as a modal dialog and locks body scroll', fakeAsync(() => {
    fixture.componentInstance.open = true;
    fixture.detectChanges();
    flush();
    const el = panel();
    expect(el).toBeTruthy();
    expect(el!.getAttribute('role')).toBe('dialog');
    expect(el!.getAttribute('aria-modal')).toBe('true');
    expect(el!.closest('app-side-drawer')!.parentElement).toBe(document.body);
    expect(document.body.style.overflow).toBe('hidden');
    expect(el!.contains(document.activeElement)).toBeTrue();
  }));

  it('closes on Escape, updates two-way binding and restores scroll', fakeAsync(() => {
    fixture.componentInstance.open = true;
    fixture.detectChanges();
    flush();
    (document.activeElement as HTMLElement).dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
    );
    fixture.detectChanges();
    flush();
    expect(fixture.componentInstance.open).toBeFalse();
    expect(panel()).toBeNull();
    expect(document.body.style.overflow).toBe('');
  }));

  it('wraps Tab focus from the last focusable back to the first', fakeAsync(() => {
    fixture.componentInstance.open = true;
    fixture.detectChanges();
    flush();
    const last = document.getElementById('last') as HTMLElement;
    last.focus();
    const ev = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
    last.dispatchEvent(ev);
    expect(ev.defaultPrevented).toBeTrue();
    expect(document.activeElement).toBe(panel()!.querySelector('.dpu-drawer__close'));
  }));

  it('removes its host from <body> when destroyed', () => {
    fixture.destroy();
    expect(document.querySelector('app-side-drawer')).toBeNull();
  });
});
