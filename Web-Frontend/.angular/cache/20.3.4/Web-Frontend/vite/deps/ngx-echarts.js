import {
  DestroyRef,
  Directive,
  ElementRef,
  InjectionToken,
  NgModule,
  NgZone,
  RuntimeError,
  assertInInjectionContext,
  getOutputDestroyRef,
  inject,
  input,
  output,
  setClassMetadata,
  ɵɵNgOnChangesFeature,
  ɵɵdefineDirective,
  ɵɵdefineInjector,
  ɵɵdefineNgModule
} from "./chunk-MFRKL5ZE.js";
import "./chunk-HWYXSU2G.js";
import "./chunk-JRFR6BLO.js";
import {
  Observable,
  ReplaySubject,
  Subject,
  Subscription,
  asyncScheduler,
  switchMap,
  takeUntil,
  throttleTime
} from "./chunk-MARUHEWW.js";
import {
  __async
} from "./chunk-3OV72XIM.js";

// node_modules/@angular/core/fesm2022/rxjs-interop.mjs
function takeUntilDestroyed(destroyRef) {
  if (!destroyRef) {
    ngDevMode && assertInInjectionContext(takeUntilDestroyed);
    destroyRef = inject(DestroyRef);
  }
  const destroyed$ = new Observable((subscriber) => {
    if (destroyRef.destroyed) {
      subscriber.next();
      return;
    }
    const unregisterFn = destroyRef.onDestroy(subscriber.next.bind(subscriber));
    return unregisterFn;
  });
  return (source) => {
    return source.pipe(takeUntil(destroyed$));
  };
}
var OutputFromObservableRef = class {
  source;
  destroyed = false;
  destroyRef = inject(DestroyRef);
  constructor(source) {
    this.source = source;
    this.destroyRef.onDestroy(() => {
      this.destroyed = true;
    });
  }
  subscribe(callbackFn) {
    if (this.destroyed) {
      throw new RuntimeError(953, ngDevMode && "Unexpected subscription to destroyed `OutputRef`. The owning directive/component is destroyed.");
    }
    const subscription = this.source.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (value) => callbackFn(value)
    });
    return {
      unsubscribe: () => subscription.unsubscribe()
    };
  }
};
function outputFromObservable(observable, opts) {
  ngDevMode && assertInInjectionContext(outputFromObservable);
  return new OutputFromObservableRef(observable);
}
function outputToObservable(ref) {
  const destroyRef = getOutputDestroyRef(ref);
  return new Observable((observer) => {
    const unregisterOnDestroy = destroyRef?.onDestroy(() => observer.complete());
    const subscription = ref.subscribe((v) => observer.next(v));
    return () => {
      subscription.unsubscribe();
      unregisterOnDestroy?.();
    };
  });
}

// node_modules/ngx-echarts/fesm2022/ngx-echarts.mjs
var NGX_ECHARTS_CONFIG = new InjectionToken("NGX_ECHARTS_CONFIG");
var ChangeFilterV2 = class {
  constructor() {
    this.subject = new ReplaySubject(1);
    this.subscriptions = new Subscription();
  }
  doFilter(changes) {
    this.subject.next(changes);
  }
  dispose() {
    this.subscriptions.unsubscribe();
  }
  notEmpty(key, handler) {
    this.subscriptions.add(this.subject.subscribe((changes) => {
      if (changes[key]) {
        const value = changes[key].currentValue;
        if (value !== void 0 && value !== null) {
          handler(value);
        }
      }
    }));
  }
  has(key, handler) {
    this.subscriptions.add(this.subject.subscribe((changes) => {
      if (changes[key]) {
        const value = changes[key].currentValue;
        handler(value);
      }
    }));
  }
  notFirst(key, handler) {
    this.subscriptions.add(this.subject.subscribe((changes) => {
      if (changes[key] && !changes[key].isFirstChange()) {
        const value = changes[key].currentValue;
        handler(value);
      }
    }));
  }
  notFirstAndEmpty(key, handler) {
    this.subscriptions.add(this.subject.subscribe((changes) => {
      if (changes[key] && !changes[key].isFirstChange()) {
        const value = changes[key].currentValue;
        if (value !== void 0 && value !== null) {
          handler(value);
        }
      }
    }));
  }
};
var _NgxEchartsDirective = class _NgxEchartsDirective {
  constructor() {
    this.el = inject(ElementRef);
    this.ngZone = inject(NgZone);
    this.config = inject(NGX_ECHARTS_CONFIG);
    this.options = input(null);
    this.theme = input(this.config.theme ?? null);
    this.initOpts = input(null);
    this.merge = input(null);
    this.autoResize = input(true);
    this.loading = input(false);
    this.loadingType = input("default");
    this.loadingOpts = input(null);
    this.chartInit = output();
    this.optionsError = output();
    this.chartClick = outputFromObservable(this.createLazyEvent("click"));
    this.chartDblClick = outputFromObservable(this.createLazyEvent("dblclick"));
    this.chartMouseDown = outputFromObservable(this.createLazyEvent("mousedown"));
    this.chartMouseMove = outputFromObservable(this.createLazyEvent("mousemove"));
    this.chartMouseUp = outputFromObservable(this.createLazyEvent("mouseup"));
    this.chartMouseOver = outputFromObservable(this.createLazyEvent("mouseover"));
    this.chartMouseOut = outputFromObservable(this.createLazyEvent("mouseout"));
    this.chartGlobalOut = outputFromObservable(this.createLazyEvent("globalout"));
    this.chartContextMenu = outputFromObservable(this.createLazyEvent("contextmenu"));
    this.chartHighlight = outputFromObservable(this.createLazyEvent("highlight"));
    this.chartDownplay = outputFromObservable(this.createLazyEvent("downplay"));
    this.chartSelectChanged = outputFromObservable(this.createLazyEvent("selectchanged"));
    this.chartLegendSelectChanged = outputFromObservable(this.createLazyEvent("legendselectchanged"));
    this.chartLegendSelected = outputFromObservable(this.createLazyEvent("legendselected"));
    this.chartLegendUnselected = outputFromObservable(this.createLazyEvent("legendunselected"));
    this.chartLegendLegendSelectAll = outputFromObservable(this.createLazyEvent("legendselectall"));
    this.chartLegendLegendInverseSelect = outputFromObservable(this.createLazyEvent("legendinverseselect"));
    this.chartLegendScroll = outputFromObservable(this.createLazyEvent("legendscroll"));
    this.chartDataZoom = outputFromObservable(this.createLazyEvent("datazoom"));
    this.chartDataRangeSelected = outputFromObservable(this.createLazyEvent("datarangeselected"));
    this.chartGraphRoam = outputFromObservable(this.createLazyEvent("graphroam"));
    this.chartGeoRoam = outputFromObservable(this.createLazyEvent("georoam"));
    this.chartTreeRoam = outputFromObservable(this.createLazyEvent("treeroam"));
    this.chartTimelineChanged = outputFromObservable(this.createLazyEvent("timelinechanged"));
    this.chartTimelinePlayChanged = outputFromObservable(this.createLazyEvent("timelineplaychanged"));
    this.chartRestore = outputFromObservable(this.createLazyEvent("restore"));
    this.chartDataViewChanged = outputFromObservable(this.createLazyEvent("dataviewchanged"));
    this.chartMagicTypeChanged = outputFromObservable(this.createLazyEvent("magictypechanged"));
    this.chartGeoSelectChanged = outputFromObservable(this.createLazyEvent("geoselectchanged"));
    this.chartGeoSelected = outputFromObservable(this.createLazyEvent("geoselected"));
    this.chartGeoUnselected = outputFromObservable(this.createLazyEvent("geounselected"));
    this.chartAxisAreaSelected = outputFromObservable(this.createLazyEvent("axisareaselected"));
    this.chartBrush = outputFromObservable(this.createLazyEvent("brush"));
    this.chartBrushEnd = outputFromObservable(this.createLazyEvent("brushend"));
    this.chartBrushSelected = outputFromObservable(this.createLazyEvent("brushselected"));
    this.chartGlobalCursorTaken = outputFromObservable(this.createLazyEvent("globalcursortaken"));
    this.chartRendered = outputFromObservable(this.createLazyEvent("rendered"));
    this.chartFinished = outputFromObservable(this.createLazyEvent("finished"));
    this.animationFrameID = null;
    this.chart$ = new ReplaySubject(1);
    this.resize$ = new Subject();
    this.changeFilter = new ChangeFilterV2();
    this.resizeObFired = false;
    this.echarts = this.config.echarts;
  }
  ngOnChanges(changes) {
    this.changeFilter.doFilter(changes);
  }
  ngOnInit() {
    if (!window.ResizeObserver) {
      throw new Error("please install a polyfill for ResizeObserver");
    }
    this.resizeSub = this.resize$.pipe(throttleTime(100, asyncScheduler, {
      leading: false,
      trailing: true
    })).subscribe(() => this.resize());
    if (this.autoResize()) {
      this.resizeOb = this.ngZone.runOutsideAngular(() => new window.ResizeObserver((entries) => {
        for (const entry of entries) {
          if (entry.target === this.el.nativeElement) {
            if (!this.resizeObFired) {
              this.resizeObFired = true;
            } else {
              this.animationFrameID = window.requestAnimationFrame(() => {
                this.resize$.next();
              });
            }
          }
        }
      }));
      this.resizeOb.observe(this.el.nativeElement);
    }
    this.changeFilter.notFirstAndEmpty("options", (opt) => this.onOptionsChange(opt));
    this.changeFilter.notFirstAndEmpty("merge", (opt) => this.setOption(opt));
    this.changeFilter.has("loading", (v) => this.toggleLoading(!!v));
    this.changeFilter.notFirst("theme", () => this.refreshChart());
  }
  ngOnDestroy() {
    window.clearTimeout(this.initChartTimer);
    if (this.resizeSub) {
      this.resizeSub.unsubscribe();
    }
    if (this.animationFrameID) {
      window.cancelAnimationFrame(this.animationFrameID);
    }
    if (this.resizeOb) {
      this.resizeOb.unobserve(this.el.nativeElement);
    }
    if (this.loadingSub) {
      this.loadingSub.unsubscribe();
    }
    this.changeFilter.dispose();
    this.dispose();
  }
  ngAfterViewInit() {
    this.initChartTimer = window.setTimeout(() => this.initChart());
  }
  dispose() {
    if (this.chart) {
      if (!this.chart.isDisposed()) {
        this.chart.dispose();
      }
      this.chart = null;
    }
  }
  /**
   * resize chart
   */
  resize() {
    if (this.chart) {
      this.chart.resize();
    }
  }
  toggleLoading(loading) {
    if (this.chart) {
      loading ? this.chart.showLoading(this.loadingType(), this.loadingOpts()) : this.chart.hideLoading();
    } else {
      this.loadingSub = this.chart$.subscribe((chart) => loading ? chart.showLoading(this.loadingType(), this.loadingOpts()) : chart.hideLoading());
    }
  }
  setOption(option, opts) {
    if (this.chart) {
      try {
        this.chart.setOption(option, opts);
      } catch (e) {
        console.error(e);
        this.optionsError.emit(e);
      }
    }
  }
  /**
   * dispose old chart and create a new one.
   */
  refreshChart() {
    return __async(this, null, function* () {
      this.dispose();
      yield this.initChart();
    });
  }
  createChart() {
    const dom = this.el.nativeElement;
    if (window && window.getComputedStyle) {
      const prop = window.getComputedStyle(dom, null).getPropertyValue("height");
      if ((!prop || prop === "0px") && (!dom.style.height || dom.style.height === "0px")) {
        dom.style.height = "400px";
      }
    }
    return this.ngZone.runOutsideAngular(() => {
      const load = typeof this.echarts === "function" ? this.echarts : () => Promise.resolve(this.echarts);
      return load().then(({
        init
      }) => init(dom, this.theme() ?? this.config?.theme, this.initOpts()));
    });
  }
  initChart() {
    return __async(this, null, function* () {
      yield this.onOptionsChange(this.options());
      const merge = this.merge();
      if (merge && this.chart) {
        this.setOption(merge);
      }
    });
  }
  onOptionsChange(opt) {
    return __async(this, null, function* () {
      if (!opt) {
        return;
      }
      if (this.chart) {
        this.setOption(this.options(), true);
      } else {
        this.chart = yield this.createChart();
        this.chart$.next(this.chart);
        this.chartInit.emit(this.chart);
        this.setOption(this.options(), true);
      }
    });
  }
  // allows to lazily bind to only those events that are requested through the `output()` by parent components
  // see https://stackoverflow.com/questions/51787972/optimal-reentering-the-ngzone-from-eventemitter-event for more info
  createLazyEvent(eventName) {
    return outputToObservable(this.chartInit).pipe(switchMap((chart) => new Observable((observer) => {
      chart.on(eventName, (data) => this.ngZone.run(() => observer.next(data)));
      return () => {
        if (this.chart) {
          if (!this.chart.isDisposed()) {
            chart.off(eventName);
          }
        }
      };
    })));
  }
};
_NgxEchartsDirective.ɵfac = function NgxEchartsDirective_Factory(__ngFactoryType__) {
  return new (__ngFactoryType__ || _NgxEchartsDirective)();
};
_NgxEchartsDirective.ɵdir = ɵɵdefineDirective({
  type: _NgxEchartsDirective,
  selectors: [["echarts"], ["", "echarts", ""]],
  inputs: {
    options: [1, "options"],
    theme: [1, "theme"],
    initOpts: [1, "initOpts"],
    merge: [1, "merge"],
    autoResize: [1, "autoResize"],
    loading: [1, "loading"],
    loadingType: [1, "loadingType"],
    loadingOpts: [1, "loadingOpts"]
  },
  outputs: {
    chartInit: "chartInit",
    optionsError: "optionsError",
    chartClick: "chartClick",
    chartDblClick: "chartDblClick",
    chartMouseDown: "chartMouseDown",
    chartMouseMove: "chartMouseMove",
    chartMouseUp: "chartMouseUp",
    chartMouseOver: "chartMouseOver",
    chartMouseOut: "chartMouseOut",
    chartGlobalOut: "chartGlobalOut",
    chartContextMenu: "chartContextMenu",
    chartHighlight: "chartHighlight",
    chartDownplay: "chartDownplay",
    chartSelectChanged: "chartSelectChanged",
    chartLegendSelectChanged: "chartLegendSelectChanged",
    chartLegendSelected: "chartLegendSelected",
    chartLegendUnselected: "chartLegendUnselected",
    chartLegendLegendSelectAll: "chartLegendLegendSelectAll",
    chartLegendLegendInverseSelect: "chartLegendLegendInverseSelect",
    chartLegendScroll: "chartLegendScroll",
    chartDataZoom: "chartDataZoom",
    chartDataRangeSelected: "chartDataRangeSelected",
    chartGraphRoam: "chartGraphRoam",
    chartGeoRoam: "chartGeoRoam",
    chartTreeRoam: "chartTreeRoam",
    chartTimelineChanged: "chartTimelineChanged",
    chartTimelinePlayChanged: "chartTimelinePlayChanged",
    chartRestore: "chartRestore",
    chartDataViewChanged: "chartDataViewChanged",
    chartMagicTypeChanged: "chartMagicTypeChanged",
    chartGeoSelectChanged: "chartGeoSelectChanged",
    chartGeoSelected: "chartGeoSelected",
    chartGeoUnselected: "chartGeoUnselected",
    chartAxisAreaSelected: "chartAxisAreaSelected",
    chartBrush: "chartBrush",
    chartBrushEnd: "chartBrushEnd",
    chartBrushSelected: "chartBrushSelected",
    chartGlobalCursorTaken: "chartGlobalCursorTaken",
    chartRendered: "chartRendered",
    chartFinished: "chartFinished"
  },
  exportAs: ["echarts"],
  features: [ɵɵNgOnChangesFeature]
});
var NgxEchartsDirective = _NgxEchartsDirective;
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(NgxEchartsDirective, [{
    type: Directive,
    args: [{
      standalone: true,
      selector: "echarts, [echarts]",
      exportAs: "echarts"
    }]
  }], null, null);
})();
function provideEchartsCore(config) {
  return {
    provide: NGX_ECHARTS_CONFIG,
    useValue: config
  };
}
var _NgxEchartsModule = class _NgxEchartsModule {
  static forRoot(config) {
    return {
      ngModule: _NgxEchartsModule,
      providers: [provideEchartsCore(config)]
    };
  }
  static forChild() {
    return {
      ngModule: _NgxEchartsModule
    };
  }
};
_NgxEchartsModule.ɵfac = function NgxEchartsModule_Factory(__ngFactoryType__) {
  return new (__ngFactoryType__ || _NgxEchartsModule)();
};
_NgxEchartsModule.ɵmod = ɵɵdefineNgModule({
  type: _NgxEchartsModule,
  imports: [NgxEchartsDirective],
  exports: [NgxEchartsDirective]
});
_NgxEchartsModule.ɵinj = ɵɵdefineInjector({});
var NgxEchartsModule = _NgxEchartsModule;
(() => {
  (typeof ngDevMode === "undefined" || ngDevMode) && setClassMetadata(NgxEchartsModule, [{
    type: NgModule,
    args: [{
      imports: [NgxEchartsDirective],
      exports: [NgxEchartsDirective]
    }]
  }], null, null);
})();
export {
  NGX_ECHARTS_CONFIG,
  NgxEchartsDirective,
  NgxEchartsModule,
  provideEchartsCore
};
/*! Bundled license information:

@angular/core/fesm2022/rxjs-interop.mjs:
  (**
   * @license Angular v20.3.3
   * (c) 2010-2025 Google LLC. https://angular.io/
   * License: MIT
   *)
*/
//# sourceMappingURL=ngx-echarts.js.map
