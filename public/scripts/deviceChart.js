"use strict";
/* Ficha de dispositivo: grafico propio del serial (BD + en vivo), pestañas y stats. */
(function () {
  var elSerialBox = document.querySelector('[data-serial]');
  if (!elSerialBox) return;
  var serial = elSerialBox.getAttribute('data-serial');
  var horas = new URLSearchParams(location.search).get('horas') || '24';
  if (['0', '24', '168', '720'].indexOf(horas) < 0) horas = '24';

  var TIPOS = {
    gas: {titulo: 'Niveles de gas (ppm)', unidad: 'ppm', color: '#8751F8'},
    temp: {titulo: 'Temperatura (°C)', unidad: '°C', color: '#E8590C'},
    hum: {titulo: 'Humedad (%)', unidad: '%', color: '#1971C2'}
  };
  var umbrales = {};
  try {
    umbrales = JSON.parse(elSerialBox.getAttribute('data-umbrales') || '{}') || {};
  } catch (e) {}
  var COLOR_SEV = {critica: '#7f1d1d', alta: '#dc2626', media: '#fbbf24', baja: '#16a34a'};
  var NOMBRE_SEV = {critica: 'Crítica', alta: 'Alta', media: 'Media', baja: 'Baja'};
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
      var limite = horas === '0' ? 2000 : 1000;
      var r = await fetch('/api/historico?limit=' + limite
        + '&serial=' + encodeURIComponent(serial) + '&horas=' + horas,
        {cache: 'no-store'});
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
  var pluginUmbral = {
    id: 'umbralLabels',
    afterDatasetsDraw: function (c) {
      var lista = umbrales[tipoActivo] || [];
      if (!lista.length) return;
      var ctx = c.ctx, area = c.chartArea, prevY = null;
      ctx.save();
      ctx.font = '600 10px Inter, sans-serif';
      lista.forEach(function (u) {
        var sev = (u.severidad || '').toLowerCase();
        var y = c.scales.y.getPixelForValue(u.valor_umbral);
        if (isNaN(y) || y < area.top + 10 || y > area.bottom) return;
        var texto = (NOMBRE_SEV[sev] || u.severidad) + ' ' + u.operador + ' ' + u.valor_umbral;
        var w = Math.ceil(ctx.measureText(texto).width) + 10;
        var x = area.right - w - 2;
        var ey = (prevY != null && Math.abs(y - prevY) < 13) ? prevY - 14 : y;
        prevY = ey;
        ctx.fillStyle = COLOR_SEV[sev] || '#6b7280';
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(x, ey - 8, w, 15, 4); else ctx.rect(x, ey - 8, w, 15);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = sev === 'media' ? '#7f1d1d' : '#fff';
        ctx.fillText(texto, x + 5, ey + 3.5);
      });
      ctx.restore();
    }
  };
  function ensureChart() {
    if (chart || typeof Chart === 'undefined') return chart;
    chart = new Chart(elCanvas, {
      type: 'line',
      data: {labels: [], datasets: []},
      plugins: [pluginUmbral],
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
    (umbrales[tipoActivo] || []).forEach(function (u) {
      var sev = (u.severidad || '').toLowerCase();
      data.datasets.push({
        label: 'Umbral ' + u.valor_umbral,
        data: vals.map(function () { return u.valor_umbral; }),
        borderColor: COLOR_SEV[sev] || '#6b7280',
        borderDash: [6, 4],
        pointRadius: 0,
        borderWidth: 1.5,
        fill: false
      });
    });
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
    var serie = Object.values(fusion).slice(-300)
      .filter(function (x) { return x.magnitud === tipoActivo; });
    pintar(serie);
  }

  tick();
  setInterval(tick, 5000);
})();
