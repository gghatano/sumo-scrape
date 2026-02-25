/* ========================================
   SUMO DATA LAB - Main Script
   ======================================== */

// --- Kimarite Japanese name mapping ---
const KIMARITE_JA = {
  yorikiri: '寄り切り',
  oshidashi: '押し出し',
  hatakikomi: 'はたき込み',
  yoritaoshi: '寄り倒し',
  uwatenage: '上手投げ',
  tsukiotoshi: '突き落とし',
  hikiotoshi: '引き落とし',
  oshitaoshi: '押し倒し',
  okuridashi: '送り出し',
  shitatenage: '下手投げ',
  tsukidashi: '突き出し',
  sukuinage: 'すくい投げ',
  kotenage: '小手投げ',
  uwatedashinage: '上手出し投げ',
  katasukashi: '肩透かし',
};

// --- Chart color palette ---
const COLORS = {
  gold: '#e6b422',
  purple: '#7b2d8b',
  pink: '#d4447c',
  teal: '#4ecdc4',
  orange: '#f39c12',
  blue: '#3498db',
  red: '#e74c3c',
  green: '#2ecc71',
};

const CHART_COLORS = [
  COLORS.gold, COLORS.purple, COLORS.pink, COLORS.teal, COLORS.orange,
  COLORS.blue, COLORS.red, COLORS.green, '#9b59b6', '#1abc9c',
  '#e67e22', '#2980b9', '#c0392b', '#27ae60', '#8e44ad',
];

// --- Chart.js global defaults ---
Chart.defaults.color = '#888';
Chart.defaults.font.family = "'Noto Sans JP', 'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyleWidth = 12;

// --- Utilities ---
function formatBasho(code) {
  const y = code.slice(0, 4);
  const m = parseInt(code.slice(4), 10);
  return y + '/' + m;
}

function formatNumber(n) {
  return n.toLocaleString('ja-JP');
}

async function fetchJSON(path) {
  const res = await fetch(path);
  return res.json();
}

// --- Intersection Observer for fade-in ---
function setupScrollAnimations() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    },
    { threshold: 0.08 }
  );
  document.querySelectorAll('.section').forEach((el) => observer.observe(el));
}

// --- Mobile nav toggle ---
function setupNav() {
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  toggle.addEventListener('click', () => {
    links.classList.toggle('open');
  });
  links.querySelectorAll('a').forEach((a) => {
    a.addEventListener('click', () => links.classList.remove('open'));
  });
}

// --- Section 1: Hero stats ---
function renderHero(stats) {
  const cards = [
    { value: formatNumber(stats.total_bouts), label: '総取組数' },
    { value: stats.total_basho, label: '場所数' },
    { value: formatNumber(stats.total_rikishi), label: '力士数' },
    { value: stats.year_range, label: '対象期間' },
  ];
  const container = document.getElementById('stat-cards');
  container.innerHTML = cards
    .map(
      (c) => `
    <div class="stat-card">
      <div class="stat-value">${c.value}</div>
      <div class="stat-label">${c.label}</div>
    </div>`
    )
    .join('');
}

// --- Section 2: Kimarite ranking ---
function renderKimariteChart(data) {
  const items = data.makuuchi.slice(0, 15).reverse();
  const labels = items.map((d) => {
    const ja = KIMARITE_JA[d.kimarite];
    return ja ? d.kimarite + ' (' + ja + ')' : d.kimarite;
  });
  const values = items.map((d) => d.count);
  const pcts = items.map((d) => d.pct);

  new Chart(document.getElementById('kimariteChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: items.map((_, i) => {
            const idx = items.length - 1 - i;
            if (idx === 0) return COLORS.gold;
            if (idx === 1) return COLORS.purple;
            return 'rgba(230, 180, 34, ' + (0.15 + 0.55 * (1 - idx / 14)) + ')';
          }),
          borderRadius: 4,
          barThickness: 22,
        },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const i = ctx.dataIndex;
              return formatNumber(values[i]) + '回 (' + pcts[i] + '%)';
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { font: { family: 'Inter' } },
        },
        y: {
          grid: { display: false },
          ticks: { font: { size: 11 } },
        },
      },
    },
  });

  // Insight
  const top2pct = data.makuuchi[0].pct + data.makuuchi[1].pct;
  document.getElementById('kimarite-insight').innerHTML =
    '<strong>寄り切り</strong>と<strong>押し出し</strong>だけで幕内の取組の約<strong>' +
    top2pct.toFixed(1) +
    '%</strong>を占めています。' +
    '上位2つの決まり手で約半数が決着 ── シンプルに見えて、この2技を極めることこそが勝利への最短路です。';
}

// --- Section 3: Kimarite trend ---
function renderTrendChart(data) {
  const techNames = Object.keys(data.techniques);
  const datasets = techNames.map((name, i) => ({
    label: KIMARITE_JA[name] || name,
    data: data.techniques[name],
    borderColor: CHART_COLORS[i],
    backgroundColor: CHART_COLORS[i] + '20',
    borderWidth: 2.5,
    pointRadius: 3,
    pointHoverRadius: 6,
    tension: 0.3,
  }));

  new Chart(document.getElementById('trendChart'), {
    type: 'line',
    data: { labels: data.years, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        tooltip: {
          callbacks: { label: (ctx) => ctx.dataset.label + ': ' + ctx.parsed.y + '%' },
        },
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' } },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: (v) => v + '%' },
        },
      },
    },
  });

  const yori = data.techniques.yorikiri;
  const oshi = data.techniques.oshidashi;
  const yoriDiff = (yori[yori.length - 1] - yori[0]).toFixed(1);
  const oshiDiff = (oshi[oshi.length - 1] - oshi[0]).toFixed(1);
  document.getElementById('trend-insight').innerHTML =
    '25年間で<strong>寄り切り</strong>の割合は' +
    (yoriDiff > 0 ? '+' : '') + yoriDiff +
    'pt、<strong>押し出し</strong>は' +
    (oshiDiff > 0 ? '+' : '') + oshiDiff +
    'pt変化。近年は押し出しが増加傾向にあり、パワー・スピード重視の「押し相撲」時代が到来しつつあります。';
}

// --- Section 4: Rikishi ranking ---
function renderRikishiChart(data) {
  const top15 = data.slice(0, 15).reverse();
  new Chart(document.getElementById('rikishiChart'), {
    type: 'bar',
    data: {
      labels: top15.map((d) => d.shikona),
      datasets: [
        {
          data: top15.map((d) => d.wins),
          backgroundColor: top15.map((d) =>
            d.shikona === '白鵬' ? COLORS.gold : 'rgba(123, 45, 139, 0.6)'
          ),
          borderRadius: 4,
          barThickness: 22,
        },
      ],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const d = top15[ctx.dataIndex];
              return d.wins + '勝 ' + d.losses + '敗 (勝率' + d.win_rate + '%)';
            },
          },
        },
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { grid: { display: false }, ticks: { font: { size: 12 } } },
      },
    },
  });

  // Win rate table (sorted by win_rate, min 50 basho)
  const byRate = [...data].filter((d) => d.basho_count >= 40).sort((a, b) => b.win_rate - a.win_rate).slice(0, 15);
  const tbody = document.querySelector('#winRateTable tbody');
  tbody.innerHTML = byRate
    .map((d, i) => {
      const isHakuho = d.shikona === '白鵬';
      const barW = Math.round(d.win_rate);
      return (
        '<tr class="' + (isHakuho ? 'highlight-row' : '') + '">' +
        '<td>' + (i + 1) + '</td>' +
        '<td>' + d.shikona + '</td>' +
        '<td><span class="win-rate-bar" style="width:' + barW + 'px"></span>' + d.win_rate + '%</td>' +
        '<td>' + d.wins + '-' + d.losses + '</td>' +
        '</tr>'
      );
    })
    .join('');

  const hakuho = data.find((d) => d.shikona === '白鵬');
  const second = data[1];
  document.getElementById('rikishi-insight').innerHTML =
    '<strong>白鵬</strong>は通算<strong>' +
    formatNumber(hakuho.wins) +
    '勝</strong>、勝率<strong>' +
    hakuho.win_rate +
    '%</strong>で2位の' +
    second.shikona +
    '(' +
    second.wins +
    '勝)に<strong>' +
    (hakuho.wins - second.wins) +
    '勝差</strong>をつける圧倒的な記録。勝利数も勝率も歴代トップの「平成の大横綱」です。';
}

// --- Section 5: Yokozuna dominance ---
function renderYokozunaChart(yokoData) {
  const rikishiList = yokoData.rikishi;
  const datasets = rikishiList.map((r, i) => ({
    label: r.shikona,
    data: r.data.map((d) => ({ x: d.basho, y: d.win_rate })),
    borderColor: CHART_COLORS[i % CHART_COLORS.length],
    backgroundColor: CHART_COLORS[i % CHART_COLORS.length] + '30',
    borderWidth: 2,
    pointRadius: 2,
    pointHoverRadius: 5,
    tension: 0.3,
    hidden: false,
  }));

  // Collect all basho labels
  const allBasho = new Set();
  rikishiList.forEach((r) => r.data.forEach((d) => allBasho.add(d.basho)));
  const labels = [...allBasho].sort();

  // Remap data to common labels
  datasets.forEach((ds, i) => {
    const map = {};
    rikishiList[i].data.forEach((d) => { map[d.basho] = d.win_rate; });
    ds.data = labels.map((b) => (map[b] !== undefined ? map[b] : null));
  });

  new Chart(document.getElementById('yokozunaChart'), {
    type: 'line',
    data: { labels: labels.map(formatBasho), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      spanGaps: false,
      plugins: {
        legend: {
          position: 'top',
          labels: { padding: 16, font: { size: 12 } },
          onClick: function (e, legendItem, legend) {
            const index = legendItem.datasetIndex;
            const ci = legend.chart;
            const meta = ci.getDatasetMeta(index);
            meta.hidden = meta.hidden === null ? true : !meta.hidden;
            ci.update();
          },
        },
        tooltip: {
          callbacks: { label: (ctx) => ctx.dataset.label + ': ' + (ctx.parsed.y !== null ? ctx.parsed.y + '%' : '-') },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.03)' },
          ticks: {
            maxTicksLimit: 20,
            maxRotation: 45,
            font: { size: 10 },
          },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          min: 0,
          max: 100,
          ticks: { callback: (v) => v + '%' },
        },
      },
    },
  });
}

// --- Section 6: Upset index ---
function renderUpsetChart(data) {
  const labels = data.basho_list.map(formatBasho);
  const avg = data.avg_upset_rate;

  new Chart(document.getElementById('upsetChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '番狂わせ率',
          data: data.upset_rate,
          borderColor: COLORS.pink,
          backgroundColor: COLORS.pink + '18',
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 5,
          fill: true,
          tension: 0.3,
        },
        {
          label: '平均 (' + avg + '%)',
          data: Array(labels.length).fill(avg),
          borderColor: COLORS.gold,
          borderWidth: 1.5,
          borderDash: [6, 4],
          pointRadius: 0,
          pointHoverRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        tooltip: {
          callbacks: { label: (ctx) => ctx.dataset.label + ': ' + ctx.parsed.y + '%' },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.03)' },
          ticks: { maxTicksLimit: 20, maxRotation: 45, font: { size: 10 } },
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: (v) => v + '%' },
        },
      },
    },
  });

  const rates = data.upset_rate;
  const maxIdx = rates.indexOf(Math.max(...rates));
  const minIdx = rates.indexOf(Math.min(...rates));
  document.getElementById('upset-insight').innerHTML =
    '最も荒れた場所は<strong>' +
    formatBasho(data.basho_list[maxIdx]) +
    '</strong>（番狂わせ率 ' +
    rates[maxIdx] +
    '%）、最も安定した場所は<strong>' +
    formatBasho(data.basho_list[minIdx]) +
    '</strong>（' +
    rates[minIdx] +
    '%）。平均は<strong>' +
    avg +
    '%</strong>で、約4割の取組が番付上位者の敗北に終わっています。';
}

// --- Section 7: Winning streaks ---
function renderStreaks(data) {
  const top10 = data.slice(0, 10);
  const container = document.getElementById('streak-cards');
  container.innerHTML = top10
    .map((d) => {
      const isChamp = d.rank === 1;
      return (
        '<div class="streak-card' + (isChamp ? ' champion' : '') + '">' +
        '<span class="streak-rank">' + d.rank + '</span>' +
        '<div class="streak-name">' + d.shikona + '</div>' +
        '<div class="streak-number">' + d.streak + '<span style="font-size:0.9rem;color:var(--sub-text)">連勝</span></div>' +
        '<div class="streak-period">' +
        formatBasho(d.start_basho) + ' ' + d.start_day + '日目 〜 ' +
        formatBasho(d.end_basho) + ' ' + d.end_day + '日目</div>' +
        '</div>'
      );
    })
    .join('');
}

// --- Section 8: Nanahachi (7-7 on Day 15) ---
function renderNanahachi(data) {
  // Big stat display
  const overall = data.overall;
  document.getElementById('nanahachi-big-stat').innerHTML =
    '<div class="big-stat-item">' +
      '<div class="big-stat-value highlight">' + overall.win_rate + '%</div>' +
      '<div class="big-stat-label">7-7力士の千秋楽勝率</div>' +
    '</div>' +
    '<div class="big-stat-vs">vs</div>' +
    '<div class="big-stat-item">' +
      '<div class="big-stat-value dim">' + overall.expected_rate + '%</div>' +
      '<div class="big-stat-label">期待値</div>' +
    '</div>';

  // Description
  document.getElementById('nanahachi-description').innerHTML =
    '千秋楽（15日目）を7勝7敗で迎えた力士の勝率は' + overall.win_rate + '%。' +
    '勝てば勝ち越し（8-7）、負ければ負け越し（7-8）── この一番は来場所の番付を左右する。' +
    '期待される50%を大きく上回るこの数字は何を意味するのか？';

  // Bar chart: by_opponent_record (top 8 by bouts)
  var byOpp = data.by_opponent_record
    .filter(function(d) { return d.bouts >= 10; })
    .sort(function(a, b) { return b.bouts - a.bouts; })
    .slice(0, 8)
    .reverse();

  new Chart(document.getElementById('nanahachi-bar-chart'), {
    type: 'bar',
    data: {
      labels: byOpp.map(function(d) { return '対 ' + d.opp_record; }),
      datasets: [{
        label: '勝率 (%)',
        data: byOpp.map(function(d) { return d.win_rate; }),
        backgroundColor: byOpp.map(function(d) {
          return d.win_rate >= 50 ? 'rgba(230, 180, 34, 0.7)' : 'rgba(231, 76, 60, 0.7)';
        }),
        borderRadius: 4,
        barThickness: 22,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              var d = byOpp[ctx.dataIndex];
              return d.win_rate + '% (' + d.wins + '勝 / ' + d.bouts + '番)';
            },
          },
        },
      },
      scales: {
        x: {
          min: 0,
          max: 100,
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: function(v) { return v + '%'; } },
        },
        y: {
          grid: { display: false },
          ticks: { font: { size: 12 } },
        },
      },
    },
    plugins: [{
      id: 'nanahachi-baseline',
      afterDraw: function(chart) {
        var xScale = chart.scales.x;
        var yScale = chart.scales.y;
        var ctx = chart.ctx;
        var x = xScale.getPixelForValue(50);
        ctx.save();
        ctx.strokeStyle = '#e74c3c';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(x, yScale.top);
        ctx.lineTo(x, yScale.bottom);
        ctx.stroke();
        ctx.restore();
      },
    }],
  });

  // Line chart: by_year
  var byYear = data.by_year;
  new Chart(document.getElementById('nanahachi-line-chart'), {
    type: 'line',
    data: {
      labels: byYear.map(function(d) { return d.year; }),
      datasets: [
        {
          label: '7-7力士の勝率',
          data: byYear.map(function(d) { return d.win_rate; }),
          borderColor: COLORS.gold,
          backgroundColor: COLORS.gold + '20',
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 6,
          tension: 0.3,
          fill: true,
        },
        {
          label: '基準線 (50%)',
          data: byYear.map(function() { return 50; }),
          borderColor: '#e74c3c',
          borderWidth: 1.5,
          borderDash: [6, 4],
          pointRadius: 0,
          pointHoverRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(ctx) {
              if (ctx.datasetIndex === 1) return '基準線: 50%';
              var d = byYear[ctx.dataIndex];
              return d.win_rate + '% (' + d.wins + '勝 / ' + d.bouts + '番)';
            },
          },
        },
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' } },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: function(v) { return v + '%'; } },
          min: 20,
          max: 80,
        },
      },
    },
  });

  // Insight box
  var opp86 = data.by_opponent_record.find(function(d) { return d.opp_record === '8-6'; });
  var both77 = data.both_77;
  var eastPct = (both77.east_wins / both77.total_bouts * 100).toFixed(0);
  document.getElementById('nanahachi-insight').innerHTML =
    '対戦相手が8勝6敗（既に勝ち越しを決めている）場合、7-7力士の勝率は<strong>' + opp86.win_rate + '%</strong>まで跳ね上がる。' +
    '一方、両者7-7の対戦は' + both77.total_bouts + '番中東方' + both77.east_wins + '勝（約' + eastPct + '%）でほぼ期待通り。' +
    '勝ち越しがかかっていない相手ほど、7-7力士に有利な結果が出ている。';
}

// --- Section 9: Star Trading Detection ---
function renderStarTrade(data) {
  // Description
  document.getElementById('startrade-description').innerHTML =
    '大相撲では「星の貸し借り」── つまり勝敗のやり取り ── の存在が長年噂されてきました。' +
    '2011年には実際に八百長問題が発覚し、力士の処分が行われました。' +
    'ここでは統計的な視点からこの問題にアプローチします。';

  // Main trend chart
  var trend = data.yearly_trend;
  new Chart(document.getElementById('startrade-trend-chart'), {
    type: 'line',
    data: {
      labels: trend.map(function(d) { return d.year; }),
      datasets: [
        {
          label: '7-7 vs 勝ち越し勝率',
          data: trend.map(function(d) { return d.nanahachi_vs_kachikoshi_rate; }),
          borderColor: COLORS.gold,
          backgroundColor: COLORS.gold + '18',
          borderWidth: 2.5,
          pointRadius: 3,
          pointHoverRadius: 6,
          tension: 0.3,
          fill: true,
        },
        {
          label: 'baseline（通常対戦での番付下位勝率）',
          data: trend.map(function(d) { return d.baseline_rate; }),
          borderColor: '#888',
          backgroundColor: 'rgba(136,136,136,0.08)',
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 5,
          tension: 0.3,
          borderDash: [4, 3],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        tooltip: {
          callbacks: {
            label: function(ctx) {
              var d = trend[ctx.dataIndex];
              if (ctx.datasetIndex === 0) {
                return '7-7 vs 勝ち越し: ' + d.nanahachi_vs_kachikoshi_rate + '% (' + d.nanahachi_vs_kachikoshi_bouts + '番)';
              }
              return 'baseline: ' + d.baseline_rate + '%';
            },
          },
        },
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' } },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: function(v) { return v + '%'; } },
          min: 20,
          max: 100,
        },
      },
    },
    plugins: [{
      id: 'startrade-annotation',
      afterDraw: function(chart) {
        var xScale = chart.scales.x;
        var yScale = chart.scales.y;
        var ctx = chart.ctx;
        // Find the pixel position for year 2011
        var idx2011 = trend.findIndex(function(d) { return d.year === 2011; });
        if (idx2011 < 0) return;
        var x = xScale.getPixelForValue(idx2011);
        ctx.save();
        ctx.strokeStyle = '#e74c3c';
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(x, yScale.top);
        ctx.lineTo(x, yScale.bottom);
        ctx.stroke();
        // Label
        ctx.setLineDash([]);
        ctx.fillStyle = '#e74c3c';
        ctx.font = '11px "Noto Sans JP", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('2011年', x, yScale.top - 14);
        ctx.fillText('八百長問題発覚', x, yScale.top - 2);
        ctx.restore();
      },
    }],
  });

  // Heatmap matrix
  var matrix = data.record_matchup_matrix;
  // Build a focused set: rows where wrestler is 7-7, plus a few key matchups
  var focusRecords = ['7-7', '8-6', '6-8', '9-5', '5-9', '10-4', '4-10'];
  var rowRecords = ['7-7', '8-6', '9-5', '6-8', '5-9', '10-4', '4-10'];
  var colRecords = ['4-10', '5-9', '6-8', '7-7', '8-6', '9-5', '10-4'];

  // Build lookup
  var lookup = {};
  matrix.forEach(function(d) {
    var key = d.wrestler_record + '|' + d.opponent_record;
    lookup[key] = d;
  });

  var thead = document.querySelector('#startrade-matrix thead');
  var tbody = document.querySelector('#startrade-matrix tbody');
  thead.innerHTML = '<tr><th>自分 \\ 相手</th>' + colRecords.map(function(r) { return '<th>' + r + '</th>'; }).join('') + '</tr>';

  tbody.innerHTML = rowRecords.map(function(wr) {
    return '<tr><td style="font-weight:700;color:var(--text);">' + wr + '</td>' +
      colRecords.map(function(or) {
        var key = wr + '|' + or;
        var d = lookup[key];
        if (!d || d.bouts < 10) return '<td style="color:var(--sub-text);">-</td>';
        var rate = d.win_rate;
        var bg;
        if (rate >= 50) {
          var intensity = Math.min((rate - 50) / 30, 1);
          bg = 'rgba(230, 180, 34, ' + (0.08 + intensity * 0.35) + ')';
        } else {
          var intensity2 = Math.min((50 - rate) / 30, 1);
          bg = 'rgba(231, 76, 60, ' + (0.08 + intensity2 * 0.3) + ')';
        }
        return '<td style="background:' + bg + ';" title="' + d.wrestler_wins + '勝/' + d.bouts + '番">' + rate + '%</td>';
      }).join('') +
    '</tr>';
  }).join('');

  // Reciprocity cards
  var recip = data.reciprocity;
  var container = document.getElementById('startrade-reciprocity');
  container.innerHTML = recip.top_pairs.map(function(p) {
    return '<div class="reciprocity-card">' +
      '<div class="reciprocity-names">' +
        p.rikishi_a + '<span class="reciprocity-arrow">&harr;</span>' + p.rikishi_b +
      '</div>' +
      '<div class="reciprocity-detail">' +
        '互いに' + Math.min(p.a_favors_b, p.b_favors_a) + '〜' + Math.max(p.a_favors_b, p.b_favors_a) + '回の"貸し" / 計' + p.total + '番' +
      '</div>' +
    '</div>';
  }).join('');

  // Insight box - dynamic values
  var pre2011 = trend.filter(function(d) { return d.year < 2011; });
  var post2016 = trend.filter(function(d) { return d.year >= 2016; });
  var pre2011Avg = pre2011.length > 0 ? (pre2011.reduce(function(s, d) { return s + d.nanahachi_vs_kachikoshi_rate; }, 0) / pre2011.length).toFixed(1) : '-';
  var post2016Avg = post2016.length > 0 ? (post2016.reduce(function(s, d) { return s + d.nanahachi_vs_kachikoshi_rate; }, 0) / post2016.length).toFixed(1) : '-';
  var baselineRates = trend.map(function(d) { return d.baseline_rate; });
  var baselineMin = Math.min.apply(null, baselineRates).toFixed(0);
  var baselineMax = Math.max.apply(null, baselineRates).toFixed(0);

  document.getElementById('startrade-insight').innerHTML =
    '2000年代は7-7力士の勝率が60-70%台と不自然に高い年が散見される（2011年以前の平均: <strong>' + pre2011Avg + '%</strong>）が、' +
    '2011年の八百長問題発覚後、特に2016年以降は勝率が低下傾向にある（2016年以降の平均: <strong>' + post2016Avg + '%</strong>）。' +
    'baselineの番付下位勝率が約' + baselineMin + '-' + baselineMax + '%であることを考えると、7-7力士の高勝率は統計的に有意な偏りと言える。' +
    'ただし、「勝ち越しがかかるモチベーションの差」という合理的な説明も成立し得る。';
}

// --- Init ---
async function init() {
  setupNav();
  setupScrollAnimations();

  const [summary, kimarite, trend, rikishi, yokozuna, upset, nanahachi, startrade, streaks] = await Promise.all([
    fetchJSON('data/summary_stats.json'),
    fetchJSON('data/kimarite_ranking.json'),
    fetchJSON('data/kimarite_trend.json'),
    fetchJSON('data/rikishi_wins.json'),
    fetchJSON('data/yokozuna_dominance.json'),
    fetchJSON('data/upset_index.json'),
    fetchJSON('data/nanahachi_analysis.json'),
    fetchJSON('data/star_trading_analysis.json'),
    fetchJSON('data/winning_streaks.json'),
  ]);

  renderHero(summary);
  renderKimariteChart(kimarite);
  renderTrendChart(trend);
  renderRikishiChart(rikishi);
  renderYokozunaChart(yokozuna);
  renderUpsetChart(upset);
  renderNanahachi(nanahachi);
  renderStarTrade(startrade);
  renderStreaks(streaks);
}

document.addEventListener('DOMContentLoaded', init);
