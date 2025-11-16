
      import { NgModule } from '@angular/core';
      import { RouterModule, Routes } from '@angular/router';
      
      export const admin: Routes = [  
       {path:'charts/apex-charts',children:[ 
        {
        path: 'line-charts',
        loadComponent: () =>
          import('./line-charts/line-charts.component').then((m) => m.LineChartsComponent),
      },
      {
        path: 'area-charts',
        loadComponent: () =>
          import('./area-charts/area-charts.component').then((m) => m.AreaChartsComponent),
      },
     {
        path: 'bar-charts',
        loadComponent: () =>
          import('./bar-charts/bar-charts.component').then((m) => m.BarChartsComponent),
      },  {
        path: 'column-charts',
        loadComponent: () =>
          import('./column-charts/column-charts.component').then((m) => m.ColumnChartsComponent),
      },  {
        path: 'mixedcharts',
        loadComponent: () =>
          import('./mixedcharts/mixedcharts.component').then((m) => m.MixedchartsComponent),
      },  {
        path: 'rangeareacharts',
        loadComponent: () =>
          import('./rangeareacharts/rangeareacharts.component').then((m) => m.RangeareachartsComponent),
      },  {
        path: 'timelinecharts',
        loadComponent: () =>
          import('./timelinecharts/timelinecharts.component').then((m) => m.TimelinechartsComponent),
      },  {
        path: 'candlestickcharts',
        loadComponent: () =>
          import('./candlestickcharts/candlestickcharts.component').then((m) => m.CandlestickchartsComponent),
      },  {
        path: 'boxplotcharts',
        loadComponent: () =>
          import('./boxplotcharts/boxplotcharts.component').then((m) => m.BoxplotchartsComponent),
      },
      {
        path: 'bubblecharts',
        loadComponent: () =>
          import('./bubblecharts/bubblecharts.component').then((m) => m.BubblechartsComponent),
      },  {
        path: 'scattercharts',
        loadComponent: () =>
          import('./scattercharts/scattercharts.component').then((m) => m.ScatterchartsComponent),
      },  {
        path: 'heatmapcharts',
        loadComponent: () =>
          import('./heatmapcharts/heatmapcharts.component').then((m) => m.HeatmapchartsComponent),
      },  {
        path: 'treemapcharts',
        loadComponent: () =>
          import('./treemapcharts/treemapcharts.component').then((m) => m.TreemapchartsComponent),
      },  {
        path: 'piecharts',
        loadComponent: () =>
          import('./piecharts/piecharts.component').then((m) => m.PiechartsComponent),
      },  {
        path: 'radialbarcharts',
        loadComponent: () =>
          import('./radialbarcharts/radialbarcharts.component').then((m) => m.RadialbarchartsComponent),
      },  {
        path: 'radarcharts',
        loadComponent: () =>
          import('./radarcharts/radarcharts.component').then((m) => m.RadarchartsComponent),
      },
      {
        path: 'polarareacharts',
        loadComponent: () =>
          import('./polarareacharts/polarareacharts.component').then((m) => m.PolarareachartsComponent),
      },
      
      ]}
      ];
      @NgModule({
        imports: [RouterModule.forChild(admin)],
        exports: [RouterModule],
      })
      export class apexchartsRoutingModule {
        static routes = admin;
      }