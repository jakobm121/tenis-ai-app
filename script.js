// Chart.js for confidence %
const charts = [
  { id: 'chart1', percent: 75, color: '#28a745' },
  { id: 'chart2', percent: 65, color: '#007bff' }
];

charts.forEach(c => {
  const ctx = document.getElementById(c.id);
  if (ctx) {
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        datasets: [{
          data: [c.percent, 100 - c.percent],
          backgroundColor: [c.color, '#eaeaea'],
          borderWidth: 0
        }]
      },
      options: {
        cutout: '75%',
        plugins: {
          tooltip: { enabled: false },
          legend: { display: false },
          beforeDraw: (chart) => {
            const { ctx, width } = chart;
            const txt = `${c.percent}%`;
            ctx.save();
            ctx.font = 'bold 16px Poppins';
            ctx.fillStyle = '#333';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(txt, width / 2, chart.chartArea.top + (chart.chartArea.height / 2));
            ctx.restore();
          }
        }
      }
    });
  }
});

// Toggle strategy content
document.querySelectorAll('.strategy-header').forEach(header => {
  header.addEventListener('click', () => {
    header.parentElement.classList.toggle('active');
  });
});