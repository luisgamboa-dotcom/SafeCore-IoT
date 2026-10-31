(function () {
  var elEstado = document.getElementById('estadoGeneral');
  var elDevices = document.getElementById('devicesLive');
  var elChart = document.getElementById('sensorChart');
  var elEmpty = document.getElementById('chartEmpty');
  var elTitle = document.getElementById('chartTitle');
  var elTabs = document.getElementById('sensorTabs');
  var elStatMax = document.getElementById('chartStatsMax');
  var elStatMin = document.getElementById('chartStatsMin');
  var elStatProm = document.getElementById('chartStatsProm');
  if (!elChart || !elTabs || !elTitle) {
    // HTML viejo en cache: se avisa en el panel en vez de fallar en silencio.
    var aviso = document.getElementById('chartEmpty');
    if (aviso) {
      aviso.style.display = '';
      aviso.querySelector('p').textContent = 'Recarga la página (Ctrl+Shift+R): hay una versión nueva del panel.';
    }
    // La pagina resumen (/dashboard) ya no tiene grafico ni tarjetas: sigue
    // solo para actualizar el KPI de estado con lo fresco del buffer.
    if (!elDevices && !elEstado) return;
  }

  var TIPOS = {
    gas: {titulo: 'Niveles de gas (ppm)', unidad: 'ppm', color: '#8751F8', umbral: 1139},
    temp: {titulo: 'Temperatura (°C)', unidad: '°C', color: '#E8590C', umbral: null},
    hum: {titulo: 'Humedad (%)', unidad: '%', color: '#1971C2', umbral: null}
  };
  var tipoActivo = 'gas';
  try {
    var guardado = localStorage.getItem('safecore_tipo');
    if (guardado && TIPOS[guardado]) tipoActivo = guardado;
  } catch (e) {}

  function esc(s) {
    var texto = String(s == null ? '' : s);
    var salida = '';
    for (var i = 0; i < texto.length; i++) {
      var c = texto[i];
      if (c === '&') {
        salida += '&amp;';
      } else if (c === '<') {
        salida += '&lt;';
      } else if (c === '>') {
        salida += '&gt;';
      } else if (c === '"') {
        salida += '&quot;';
      } else if (c === "'") {
        salida += '&#39;';
      } else {
        salida += c;
      }
    }
    return salida;
  }

  // Antiguedad del ultimo dato (formato servidor "YYYY-MM-DD HH:MM:SS").
  function ageSecs(fechaHora) {
    var t = Date.parse(String(fechaHora).replace(' ', 'T'));
    if (isNaN(t)) return -1;
    return Math.max(0, Math.round((Date.now() - t) / 1000));
  }
  function ageFmt(s) {
    if (s < 60) return s + ' s';
    var m = Math.floor(s / 60);
    return m >= 60 ? Math.floor(m / 60) + ' h ' + (m % 60) + ' min' : m + ' min';
  }

  // --- Chart.js (un solo grafico reutilizado por pestana) ---
  var chart = null;
  function ensureChart() {
    if (chart || !elChart || typeof Chart === 'undefined') return chart;
    chart = new Chart(elChart, {
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

  function renderChart(serie) {
    var cfg = TIPOS[tipoActivo];
    if (elTitle) elTitle.textContent = cfg.titulo;
    var vals = serie.map(function (x) { return Number(x.valor); });
    var labels = serie.map(function (x) { return String(x.fecha_hora || '').slice(11) || String(x.seq); });
    if (elEmpty) {
      if (!serie.length) {
        elEmpty.style.display = '';
        elEmpty.querySelector('p').textContent = tipoActivo === 'gas'
          ? 'En espera de lecturas…'
          : 'Sin datos de ' + (tipoActivo === 'temp' ? 'temperatura' : 'humedad') + ' todavía…';
      } else {
        elEmpty.style.display = 'none';
      }
    }
    if (elChart) elChart.style.display = serie.length ? '' : 'none';
    if (!serie.length) return;
    if (typeof Chart === 'undefined') {
      if (elEmpty) {
        elEmpty.style.display = '';
        elEmpty.querySelector('p').textContent = 'Sin conexión para cargar Chart.js';
      }
      return;
    }
    var c = ensureChart();
    if (!c) return;
    var data = {
      labels: labels,
      datasets: [{
        label: cfg.titulo + ' (' + cfg.unidad + ')',
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

  function fmtStat(v) { return Math.round(v * 100) / 100; }

  function pintarStats(serie) {
    if (!elStatMax || !elStatMin || !elStatProm) return;
    var vals = serie.map(function (x) { return Number(x.valor); })
      .filter(function (v) { return !isNaN(v); });
    if (!vals.length) {
      elStatMax.textContent = elStatMin.textContent = elStatProm.textContent = '—';
      return;
    }
    var prom = vals.reduce(function (a, b) { return a + b; }, 0) / vals.length;
    var unidad = TIPOS[tipoActivo].unidad;
    elStatMax.textContent = fmtStat(Math.max.apply(null, vals)) + ' ' + unidad;
    elStatMin.textContent = fmtStat(Math.min.apply(null, vals)) + ' ' + unidad;
    elStatProm.textContent = fmtStat(prom) + ' ' + unidad;
  }

  function marcarTabs() {
    if (!elTabs) return;
    var btns = elTabs.querySelectorAll('.sensor-tab');
    btns.forEach(function (b) {
      var on = b.getAttribute('data-tipo') === tipoActivo;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.classList.toggle('bg-white', on);
      b.classList.toggle('shadow-sm', on);
      b.classList.toggle('text-primary', on);
    });
  }
  if (elTabs) {
    elTabs.addEventListener('click', function (ev) {
      var b = ev.target.closest('.sensor-tab');
      if (!b) return;
      tipoActivo = b.getAttribute('data-tipo');
      try { localStorage.setItem('safecore_tipo', tipoActivo); } catch (e) {}
      marcarTabs();
      tick();
    });
  }
  marcarTabs();

  var ultimos = [];
  var semillaBD = null;
  var APAGADO_SEG = 300;

  // Semilla del grafico: historial desde la base de datos (cronologico).
  async function cargarSemilla() {
    try {
      var r = await fetch('/api/historico?limit=150', {cache: 'no-store'});
      if (!r.ok) return;
      var d = await r.json();
      if (d.ok && d.lecturas) semillaBD = d.lecturas;
    } catch (e) { /* se mantiene la semilla anterior */ }
  }
  cargarSemilla();
  setInterval(cargarSemilla, 30000);

  function clave(item) {
    return item.fecha_hora + '|' + item.magnitud + '|' + item.valor;
  }

  function serieDelGrafico(items) {
    var viva = items.filter(function (x) { return x.magnitud === tipoActivo; }).slice(0, 50).reverse();
    if (!semillaBD) return viva;
    var fusion = {};
    semillaBD.filter(function (x) { return x.magnitud === tipoActivo; })
      .forEach(function (x) { fusion[clave(x)] = x; });
    viva.forEach(function (x) { if (!fusion[clave(x)]) fusion[clave(x)] = x; });
    return Object.values(fusion)
      .sort(function (a, b) { return String(a.fecha_hora).localeCompare(String(b.fecha_hora)); })
      .slice(-60);
  }

  // Rellena las tarjetas [data-serial] con lo fresco del buffer: items viene
  // ordenado de mas nuevo a mas viejo, el primer item de un serial es su
  // paquete mas reciente. Sin items -> Apagado. Edad > 5 min -> Apagado.
  function actualizarTarjetas(items) {
    var grid = document.getElementById('devicesLive');
    if (!grid) return;
    var porSerial = {};
    items.forEach(function (x) {
      var ser = x.codigo_serial || '';
      if (!porSerial[ser]) porSerial[ser] = x;
    });
    grid.querySelectorAll('[data-serial]').forEach(function (card) {
      var ser = card.getAttribute('data-serial');
      var it = porSerial[ser];
      var dot = card.querySelector('.js-dot');
      var est = card.querySelector('.js-estado');
      var lec = card.querySelector('.js-lectura');
      var fec = card.querySelector('.js-fecha');
      if (!dot || !est || !lec || !fec) return;
      if (!it) {
        dot.className = 'js-dot w-3 h-3 rounded-full status-dot-crit';
        est.className = 'js-estado inline-flex items-center px-2.5 py-1 rounded-full bg-surface-container-low text-xs font-semibold text-error';
        est.textContent = 'Apagado';
        lec.textContent = '—';
        fec.textContent = '—';
        return;
      }
      var age = ageSecs(it.fecha_hora);
      lec.textContent = esc(it.magnitud) + ': ' + esc(it.valor);
      fec.textContent = esc(it.fecha_hora) + (age >= 0 ? ' · hace ' + ageFmt(age) : '');
      if (age > APAGADO_SEG) {
        dot.className = 'js-dot w-3 h-3 rounded-full status-dot-crit';
        est.className = 'js-estado inline-flex items-center px-2.5 py-1 rounded-full bg-surface-container-low text-xs font-semibold text-error';
        est.textContent = 'Apagado';
      } else {
        dot.className = 'js-dot w-3 h-3 rounded-full status-dot-online';
        est.className = 'js-estado inline-flex items-center px-2.5 py-1 rounded-full bg-surface-container-low text-xs font-semibold';
        est.textContent = 'online';
      }
    });
  }

  async function tick() {
    var items = ultimos;
    try {
      var r = await fetch('/api/live?limit=150', {cache: 'no-store'});
      if (!r.ok) throw new Error('http ' + r.status);
      items = ((await r.json()).lecturas) || [];
      ultimos = items;
    } catch (e) {
      if (items.length) {
        // Sin servidor pero con datos previos: se muestra lo ultimo.
      } else {
        if (elEstado) elEstado.textContent = 'Sin conexión al servidor';
        return;
      }
    }
    var dud = items.filter(function (x) { return x.calidad === 'dudosa'; });

    if (elEstado) {
      var ageS = items.length ? ageSecs(items[0].fecha_hora) : -1;
      if (!items.length) { elEstado.textContent = 'En espera'; }
      else if (ageS >= 90) {
        elEstado.textContent = 'Sin lecturas hace ' + ageFmt(ageS) + ' — revisa conexión de los nodos';
      }
      else elEstado.textContent = dud.length ? 'Revisar (' + dud.length + ' dudosa)' : 'En vivo';
    }

    // Tarjetas por dispositivo: identidad la sirve el servidor y los valores
    // vivos se inyectan aqui desde el buffer (dashboard en modo test, sin DB).
    actualizarTarjetas(items);

    // Grafico del tipo activo: semilla de BD + puntos en vivo.
    var serie = serieDelGrafico(items);
    renderChart(serie);
    pintarStats(serie);
  }
  tick();
  setInterval(tick, 5000);
})();
