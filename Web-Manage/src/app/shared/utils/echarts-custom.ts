import * as echarts from 'echarts/core';
import {
  BarChart,
  GraphChart,
  HeatmapChart,
  LineChart,
  PieChart,
} from 'echarts/charts';
import {
  GridComponent,
  LegendComponent,
  TitleComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([
  BarChart,
  PieChart,
  HeatmapChart,
  LineChart,
  GraphChart,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  VisualMapComponent,
  TitleComponent,
  CanvasRenderer,
]);

export default echarts;
