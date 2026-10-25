"use strict";
/* Ficha de dispositivo: grafico propio del serial (BD + en vivo), pestañas y stats. */
(function () {
  var elSerialBox = document.querySelector('[data-serial]');
  if (!elSerialBox) return;
  var serial = elSerialBox.getAttribute('data-serial');

  var TIPOS = {
    gas: {titulo: 'Niveles de gas (ADC)', unidad: 'ADC', color: '#8751F8', umbral: 200},
    temp: {titulo: 'Temperatura (°C)', unidad: '°C', color: '#E8590C', umbral: null},
    hum: {titulo: 'Humedad (%)', unidad: '%', color: '#1971C2', umbral: null}
  };
  var tipoActivo = 'gas';
  try {
    var guardado = localStorage.getItem('safecore_dev_tipo');
    if (guardado && TIPOS[guardado]) tipoActivo = guardado;
  } catch (e) {}

  var seedBD = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g,
      function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; });
  }
  function fmtStat(v) { return Math.round(v * 100) / 100; }
  function clave(x) { return x.fecha_hora + '|' + x.magnitud + '|' + x.valor; }
  function cronologico(arr) {
    return arr.slice().sort(function (a, b) {
      return String(a.fecha_hora).localeCompare(String(b.fecha_hora));
    });
  }

  async function cargarSemilla() {
    try {
      var r = await fetch('/api/historico?limit=500', {cache: 'no-store'});
      if (!r.ok) return;
      var d = await r.json();
      if (d.ok && d.lecturas) {
        seedBD = d.lecturas.filter(function (x) { return (x.codigo_serial || '') === serial; });
      }
    } catch (e) { /* se mantiene lo anterior */ }
  }
  cargarSemilla();
  setInterval(cargarSemilla, 30000);

  var elCanvas = document.getElementById('devChart');
  var elTitle = document.getElementById('devChartTitle');
  var elTabs = document.getElementById('devTabs');
  var elEmpty = document.getElementById('devChartEmpty');
  var elMax = document.getElementById('devStatMax');
  var elMin = document.getElementById('devStatMin');
  var elProm = document.getElementById('devStatProm');
  if (!elCanvas) return;

  var chart = null;
  function ensureChart() {
    if (chart || typeof Chart === 'undefined') return chart;
    chart = new Chart(elCanvas, {
      type: 'line',
      data: {labels: [], datasets: []},
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {mode: 'index', intersect: false},
        plugins: {legend: {display: false}},
        scales: {
          x: {ticks: {maxTicksLimit: 8, font: {size: 10}}},
          y: {ticks: {font: {size: 10}}}
        }
      }
    });
    return chart;
  }

  function pintar(serie) {
    var cfg = TIPOS[tipoActivo];
    if (elTitle) elTitle.textContent = cfg.titulo;
    if (elEmpty) elEmpty.style.display = serie.length ? 'none' : '';
    elCanvas.style.display = serie.length ? '' : 'none';
    pintarStats(serie);
    if (!serie.length || typeof Chart === 'undefined') return;
    var c = ensureChart();
    if (!c) return;
    var vals = serie.map(function (x) { return Number(x.valor); });
    var data = {
      labels: serie.map(function (x) { return String(x.fecha_hora || '').slice(11); }),
      datasets: [{
        label: cfg.titulo,
        data: vals,
        borderColor: cfg.color,
        backgroundColor: cfg.color + '22',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2
      }]
    };
    if (cfg.umbral != null) {
      data.datasets.push({
        label: 'Umbral ' + cfg.umbral,
        data: vals.map(function () { return cfg.umbral; }),
        borderColor: '#ba1a1a',
        borderDash: [6, 4],
        pointRadius: 0,
        borderWidth: 1.5,
        fill: false
      });
    }
    c.data = data;
    c.update('none');
  }

  function pintarStats(serie) {
    if (!elMax || !elMin || !elProm) return;
    var vals = serie.map(function (x) { return Number(x.valor); })
      .filter(function (v) { return !isNaN(v); });
    if (!vals.length) {
      elMax.textContent = elMin.textContent = elProm.textContent = '—';
      return;
    }
    var prom = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
    var unidad = TIPOS[tipoActivo].unidad;
    elMax.textContent = fmtStat(Math.max.apply(null, vals)) + ' ' + unidad;
    elMin.textContent = fmtStat(Math.min.apply(null, vals)) + ' ' + unidad;
    elProm.textContent = fmtStat(prom) + ' ' + unidad;
  }

  function marcarTabs() {
    if (!elTabs) return;
    elTabs.querySelectorAll('[data-tipo]').forEach(function (b) {
      var on = b.getAttribute('data-tipo') === tipoActivo;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.classList.toggle('bg-white', on);
      b.classList.toggle('shadow-sm', on);
      b.classList.toggle('text-primary', on);
    });
  }
  if (elTabs) {
    elTabs.addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-tipo]');
      if (!b) return;
      tipoActivo = b.getAttribute('data-tipo');
      try { localStorage.setItem('safecore_dev_tipo', tipoActivo); } catch (e) {}
      marcarTabs();
      tick();
    });
  }
  marcarTabs();

  async function tick() {
    var items = [];
    try {
      var r = await fetch('/api/live?limit=150', {cache: 'no-store'});
      if (r.ok) {
        items = (((await r.json()).lecturas) || []).filter(function (x) {
          return (x.codigo_serial || '') === serial;
        });
      }
    } catch (e) { /* sin servidor: solo semilla BD */ }
    var fusion = {};
    (seedBD || []).forEach(function (x) { fusion[clave(x)] = x; });
    cronologico(items).forEach(function (x) { if (!fusion[clave(x)]) fusion[clave(x)] = x; });
    var serie = Object.values(fusion).slice(-60)
      .filter(function (x) { return x.magnitud === tipoActivo; });
    pintar(serie);
  }

  tick();
  setInterval(tick, 5000);
})();
