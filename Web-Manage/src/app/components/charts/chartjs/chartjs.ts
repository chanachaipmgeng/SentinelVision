import { ChartConfiguration, ChartType, Color } from 'chart.js';

//Line Charts
export let lineChartOptions: ChartConfiguration['options'] = {

  maintainAspectRatio: false,
  responsive: true,
  plugins: {
    legend: {
      labels: {
        color: '#77778e',
      },
    },
   
  },
  scales: {
    x: {
      ticks: {
        color: '#77778e',
      },
      display: true,
      grid: {
        color: 'rgba(119, 119, 142, 0.2)',
      },
    },
    y: {
      labels:['0','5','10','15','20','25','30','35','40','45'],
      ticks: {
        color: '#77778e',
      },
      display: true,
      grid: {
        color: 'rgba(119, 119, 142, 0.2)',
      },
    },
  },
  
};

export let lineChartType: ChartType = 'line';
export let lineChartLegend = true;
export let lineChartData: ChartConfiguration['data'] = {
  datasets: [
    {
      label: 'Profits',
      data: [0, 10, 5, 2, 20, 30],
      tension: 0,
      borderWidth: 3,
      backgroundColor: 'transparent',
      borderColor: '#6259ca',
      pointBorderColor: '#6259ca',
      pointBackgroundColor: '#ffffff',
      pointRadius: 2,
    },
  ],
  labels: ['January', 'Febraury', 'March', 'April', 'May', 'June'],
};

//BarChart1
export let barChartOptions: ChartConfiguration['options'] = {
  maintainAspectRatio: false,
  responsive: true,
  plugins: {
    legend: {
      display: true,
      labels: {
        color: '#77778e',
      },
    },
  },
  scales: {
    y: {
      ticks: {
        stepSize: 150,
        color: '#77778e',
      },
      grid: {
        color: 'rgba(119, 119, 142, 0.2)',
      },
    },
    x: {
      ticks: {
        display: true,
        color: '#77778e',
      },
      grid: {
        display: false,
        color: 'rgba(119, 119, 142, 0.2)',
      },
    },
  },
};
export const labels1 = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
];
export const data1 = {
  labels: labels1,
  datasets: [{
      label: 'My First Dataset',
      data: [65, 59, 80, 81, 56, 55, 40],
      backgroundColor: [
          'rgba(132, 90, 223, 0.2)',
          'rgba(35, 183, 229, 0.2)',
          'rgba(245, 184, 73, 0.2)',
          'rgba(73, 182, 245, 0.2)',
          'rgba(230, 83, 60, 0.2)',
          'rgba(38, 191, 148, 0.2)',
          'rgba(35, 35, 35, 0.2)'
      ],
      borderColor: [
          'rgb(132, 90, 223)',
          'rgb(35, 183, 229)',
          'rgb(245, 184, 73)',
          'rgb(73, 182, 245)',
          'rgb(230, 83, 60)',
          'rgb(38, 191, 148)',
          'rgb(35, 35, 35)'
      ],
      borderWidth: 1
  }]
};
export const config1 = {
  type: 'bar',
  data: data1,
  options: {
      scales: {
          y: {
              beginAtZero: true
          }
      }
  },
};
// export const myChart1 = new Chart(
//   document.getElementById('chartjs-bar'),
//   config1
// );
export let barChartType: ChartType = 'bar';
export let barChartLegend = true;
// export let barChartPlugins = [];
// export let barChartData: ChartConfiguration['data'] = {
//   datasets: [
//     {
//       data: [200, 450, 290, 367, 256, 543, 345],
//       label: 'Sales',
//       borderWidth: 2,
//       backgroundColor: '#9877f9',
//       borderColor: '#9877f9',
//       pointBackgroundColor: '#ffffff',
//     },
//   ],
//   labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
// };

//Bar Chart 2
export let barChart2Options: ChartConfiguration['options'] = {
  maintainAspectRatio: false,
  responsive: true,
  plugins: {
    legend: {
      labels: {
        color: '#77778e',
      },
    },
  },
  scales: {
    x: {
      ticks: {
        color: '#77778e',
      },
      grid: {
        color: 'rgba(119, 119, 142, 0.2)',
      },
    },
    y: {
      ticks: {
        color: '#77778e',
      },
      grid: {
        color: 'rgba(119, 119, 142, 0.2)',
      },
    },
  },
};

export let barChart2Type: ChartType = 'bar';
export let barChart2Legend = true;
export let barChart2Plugins = [];
export const barChart2Data: ChartConfiguration['data']  = {
  labels: [
      'January',
      'February',
      'March',
      'April'
  ],
  datasets: [{
      type: 'bar',
      label: 'Bar Dataset',
      data: [10, 20, 30, 40],
      borderColor: 'rgb(132, 90, 223)',
      backgroundColor: 'rgba(132, 90, 223, 0.2)'
  }, {
      type: 'line',
      label: 'Line Dataset',
      data: [50, 50, 50, 50],
      fill: false,
      borderColor: 'rgb(35, 183, 229)'
  }]
};
// export let barChart2Data: ChartConfiguration['data'] = {
//   datasets: [
//     {
//       label: 'Data1',
//       data: [65, 59, 80, 81, 56, 55, 40],
//       borderColor: '#6259ca',
//       borderWidth: 0,
//       backgroundColor: '#6259ca',
//     },
//     {
//       label: 'Data2',
//       data: [28, 48, 40, 19, 86, 27, 90],
//       borderColor: '#53caed',
//       borderWidth: 0,
//       backgroundColor: '#53caed',
//     },
//   ],
//   labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
// };

//Area Chart
export let AreaChartOptions: ChartConfiguration['options'] = {
  maintainAspectRatio: false,
  responsive: true,

  scales: {
    x: {
      ticks: {
        color: '#77778e',
      },
      grid: {
        color: 'rgba(119,119,142, 0.2)',
      },
    },
    y: {
      ticks: {
        color: '#77778e',
      },
      grid: {
        color: 'rgba(119,119,142, 0.2)',
      },
    },
  },
  plugins: {
    tooltip: {
      mode: 'index',
      intersect: false,
    },
    legend: {
      labels: {
        color: '#77778e',
      },
    },
  },
};
export let AreaChartType: ChartType = 'line';
export let AreaChartData: ChartConfiguration['data'] = {
  datasets: [
    {
      label: 'Data1',
      data: [22, 44, 67, 43, 76, 45, 12],
      borderColor: 'rgba(113, 76, 190, 0.9)',
      borderWidth: 1,
      backgroundColor: 'rgba(113, 76, 190, 0.5)',
      tension: 0.5,
      fill: 'origin',
    },
    {
      label: 'Data2',
      data: [16, 32, 18, 26, 42, 33, 44],
      borderColor: 'rgba(235, 111, 51 ,0.9)',
      borderWidth: 1,
      backgroundColor: 'rgba(	235, 111, 51, 0.7)',
      tension: 0.5,
      fill: 'origin',
    },
  ],
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'July'],
};

//DoughNut Chart and Pie chart data
export const data2 = {
  labels: [
      'Red',
      'Blue',
      'Yellow'
  ],
  datasets: [{
      label: 'My First Dataset',
      data: [300, 50, 100],
      backgroundColor: [
          'rgb(132, 90, 223)',
          'rgb(35, 183, 229)',
          'rgb(245, 184, 73)'
      ],
      hoverOffset: 4
  }]
};
export const config3 = {
  type: 'pie',
  data: data2,
};
export let PieChartData: ChartConfiguration['data'] = {
  datasets: [
    {
      data: [20, 20, 30, 5, 25],
      backgroundColor: ['#6259ca', '#53caed', '#01b8ff', '#f16d75', '#29ccbb'],
    },
  ],
  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
};
export let PieChartOptions: ChartConfiguration['options'] = {
  maintainAspectRatio: false,
  responsive: true,
  plugins: {
    legend: {
      display: true,
      position:'top'
    },
  },
  // animation: {
  //   animateScale: true,
  //   animateRotate: true,
  // },
};
export let DoughnutChartType: ChartType = 'doughnut';
export let PieChartType: ChartType = 'pie';

//Radar Chart
export let radarChartOptions: ChartConfiguration['options'] = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position:'top'
    },
  },
 
};

export let radarChartType: ChartType = 'radar';

export const radarChartData: ChartConfiguration['data']= {
  labels: [
      'Eating',
      'Drinking',
      'Sleeping',
      'Designing',
      'Coding',
      'Cycling',
      'Running'
  ],
  datasets: [{
      label: 'My First Dataset',
      data: [65, 59, 90, 81, 56, 55, 40],
      fill: true,
      backgroundColor: 'rgba(132, 90, 223, 0.2)',
      borderColor: 'rgb(132, 90, 223)',
      pointBackgroundColor: 'rgb(132, 90, 223)',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: 'rgb(132, 90, 223)'
  }, {
      label: 'My Second Dataset',
      data: [28, 48, 40, 19, 96, 27, 100],
      fill: true,
      backgroundColor: 'rgba(35, 183, 229, 0.2)',
      borderColor: 'rgb(35, 183, 229)',
      pointBackgroundColor: 'rgb(35, 183, 229)',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: 'rgb(35, 183, 229)'
  }]
};

//Polar Chart
export let polarChartOptions: ChartConfiguration['options'] = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: '#77778e',
      },
    },
  },

};
export let polarChartType: ChartType = 'polarArea';
export const  polarChartData: ChartConfiguration['data']= {
  labels: [
      'Red',
      'Green',
      'Yellow',
      'Grey',
      'Blue'
  ],
  datasets: [{
      label: 'My First Dataset',
      data: [11, 16, 7, 3, 14],
      backgroundColor: [
          'rgb(132, 90, 223)',
          'rgb(75, 192, 192)',
          'rgb(245, 184, 73)',
          'rgb(201, 203, 207)',
          'rgb(35, 183, 229)'
      ]
  }]
};
// export let polarChartData: ChartConfiguration['data'] = {
//   datasets: [
//     {
//       data: [18, 15, 9, 6, 19],
//       backgroundColor: ['#6259ca', '#53caed', '#01b8ff', '#f16d75', '#29ccbb'],
//       hoverBackgroundColor: [
//         '#6259ca',
//         '#53caed',
//         '#01b8ff',
//         '#f16d75',
//         '#29ccbb',
//       ],
//       borderColor: 'transparent',
//     },
//   ],
//   labels: ['Data1', 'Data2', 'Data3', 'Data4'],
// };

// bubble chart

export let bubblechartOptions: ChartConfiguration['options'] = {
  maintainAspectRatio: false,
  responsive: true,
  plugins: {
    legend: {
      display: true,
      labels: {
        color: 'rgb(132, 90, 223)',
      },
    },
  },
  scales: {
    x: {
        type: 'linear',
        position: 'bottom'
    }
}
};
export let bubblechartType: ChartType = 'bubble';

export let bubblechartData: ChartConfiguration['data'] = {
  datasets: [{
    label: 'First Dataset',
    data: [{
        x: 20,
        y: 30,
        r: 15
    }, {
        x: 40,
        y: 10,
        r: 10
    }],
    backgroundColor: 'rgb(132, 90, 223)'
}]
}
// scatterd chart
export let ScatterchartOptions: ChartConfiguration['options'] = {
  maintainAspectRatio: false,
  responsive: true,
  plugins: {
    legend: {
      display: true,
      labels: {
        color: '#77778e',
      },
    },
  },
  scales: {
    x: {
        type: 'linear',
        position: 'bottom'
    }
}
};

export let ScatterchartType: ChartType = 'bubble';

export let scatterchartData: ChartConfiguration['data'] = {
  datasets: [
    {
      label: 'Scatter Dataset',
      data: [{
          x: -10,
          y: 0
      }, {
          x: 0,
          y: 10
      }, {
          x: 10,
          y: 5
      }, {
          x: 0.5,
          y: 5.5
      }],
      backgroundColor: 'rgb(132, 90, 223)'
  }],
  labels: ['First Dataset'],


};
