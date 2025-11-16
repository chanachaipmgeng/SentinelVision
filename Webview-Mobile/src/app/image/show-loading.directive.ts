import { Directive, ElementRef, ViewContainerRef } from '@angular/core';
import { fromEvent, race, timer, zip } from 'rxjs';
import { first, map, tap } from 'rxjs/operators';
import { LoadingSpinnerComponent } from './loading-spinner/loading-spinner.component';

@Directive({
  selector: '[appShowLoading]'
})
export class ShowLoadingDirective {

  get imageElement() {
    return this.el.nativeElement
  }
  constructor(private el:ElementRef<HTMLImageElement>,
    private vc: ViewContainerRef) {

    // const div = document.createElement('div');
    // div.textContent = '...กำลังโหลด';
    // this.imageElement.parentElement?.appendChild(div);
    const componentRef = this.vc.createComponent(LoadingSpinnerComponent);


    const div = document.createElement("div");
    // div.className = "lds-dual-ring";

    div.style.width = this.imageElement.width.toString() + "px";
    div.style.height = this.imageElement.width.toString() + "px";
    this.imageElement.parentElement?.appendChild(div);
    this.imageElement.hidden = true;
    const load$ = fromEvent(this.imageElement,'load').pipe(map(()=>true))
    const error$ = fromEvent(this.imageElement,'error').pipe(map(()=>false))

    const loaded$ = race(load$, error$)
    const delay$ = timer(500);
    zip(loaded$, delay$).pipe(
      first(),
      tap(([isSuccess]) =>{
        if (isSuccess){
          this.imageElement.hidden = false;
          // div.remove();
          componentRef.destroy();
        }else{
          this.imageElement.hidden = false;
          this.imageElement.src = 'assets/img/icon/person.png'
          // div.remove();
          componentRef.destroy();
        }
      })
    ).subscribe();
   }
}
