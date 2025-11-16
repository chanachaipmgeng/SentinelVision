import { HttpClient, HttpResponse } from '@angular/common/http';
import { ChangeDetectorRef, OnDestroy, Pipe, PipeTransform } from '@angular/core';
import { SafeUrl, DomSanitizer } from '@angular/platform-browser';
import { BehaviorSubject } from 'rxjs';
import { Subscription } from 'rxjs/internal/Subscription';
import { filter, distinctUntilChanged, switchMap, map, tap } from 'rxjs/operators';


@Pipe({
  name: 'useHttpImgSrc',
  pure: false,
})
export class UseHttpImageSourcePipe implements PipeTransform, OnDestroy {
  private subscription = new Subscription();
  private transformValue = new BehaviorSubject<string>('');

  private latestValue!: string | SafeUrl;

  constructor(private httpClient: HttpClient,
              private domSanitizer: DomSanitizer,
              private cdr: ChangeDetectorRef) {
    // every pipe instance will set up their subscription
    this.setUpSubscription();
  }

  // ...

  transform(imagePath: string): string | SafeUrl {
    // we emit a new value
    this.transformValue.next(imagePath);

    // we always return the latest value
    return this.latestValue;
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  private setUpSubscription(): void {
    const transformSubscription = this.transformValue
      .asObservable()
      .pipe(
        filter((v): v is string => !!v),
        distinctUntilChanged(),
        // we use switchMap, so the previous subscription gets torn down
        switchMap((imagePath: string) => this.httpClient
          // we get the imagePath, observing the response and getting it as a 'blob'
          .get(imagePath, { observe: 'response', responseType: 'blob' })
          .pipe(
            // we map our blob into an ObjectURL
            map((response: HttpResponse<Blob>) => URL.createObjectURL(response.body!)),
            // we bypass Angular's security mechanisms
            map((unsafeBlobUrl: string) => this.domSanitizer.bypassSecurityTrustUrl(unsafeBlobUrl)),
            // we trigger it only when there is a change in the result
            filter((blobUrl) => blobUrl !== this.latestValue),
          )
        ),
        tap((imagePath: string | SafeUrl) => {
          this.latestValue = imagePath;
          this.cdr.markForCheck();
        })
      )
      .subscribe();
    this.subscription.add(transformSubscription);
  }
}

