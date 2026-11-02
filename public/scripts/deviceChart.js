"use strict";
/* Ficha de dispositivo: serie historica agregada por tiempo (BD), pestañas y
   estadisticas. Un solo dibujado inicial y refresco cada 20 s sin saltos. */
(function () {
  var elSerialBox = document.querySelector('[data-serial]');
  if (!elSerialBox) return;
  var serial = elSerialBox.getAttribute('data-serial');
  var horas = new URLSearchParams(location.search).get('horas') || '1';
  if (['0', '1', '24', '168', '720'].indexOf(horas) < 0) horas = '1';

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

  var elCanvas = document.getElementById('devChart');
  var elTitle = document.getElementById('devChartTitle');
  var elTabs = document.getElementById('devTabs');
  var elEmpty = document.getElementById('devChartEmpty');
  var elMax = document.getElementById('devStatMax');
  var elMin = document.getElementById('devStatMin');
  var elProm = document.getElementById('devStatProm');
  if (!elCanvas) return;

  var chart = null;
  var bucketActual = 300;
  var firma = '';
  var cargando = true;

  function fmtStat(v) {
    return (v == null || isNaN(v)) ? '—' : (Math.round(v * 100) / 100);
  }
  /* "YYYY-MM-DD HH:MM:SS" -> Date local (evita ambiguedades de zona horaria). */
  function aFecha(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/.exec(String(s));
    if (!m) return new Date(NaN);
    return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
  }
  function dosDigitos(n) { return (n < 10 ? '0' : '') + n; }
  function fmtCorta(d) {
    return dosDigitos(d.getDate()) + '/' + dosDigitos(d.getMonth() + 1) +
      ' ' + dosDigitos(d.getHours()) + ':' + dosDigitos(d.getMinutes());
  }
  function fmtLarga(d) {
    return dosDigitos(d.getDate()) + '/' + dosDigitos(d.getMonth() + 1) + '/' +
      d.getFullYear() + ' ' + dosDigitos(d.getHours()) + ':' +
      dosDigitos(d.getMinutes()) + ':' + dosDigitos(d.getSeconds());
  }
  /* Corta la linea cuando el salto supera 2,5 buckets (minimo 3 min). */
  function conHuecos(puntos, bucketSeg) {
    var corte = Math.max(bucketSeg * 2.5, 180) * 1000;
    var salida = [];
    for (var i = 0; i < puntos.length; i++) {
      if (i > 0 && (puntos[i].x - puntos[i - 1].x) > corte) {
        salida.push({x: puntos[i - 1].x + corte / 2, y: null});
      }
      salida.push(puntos[i]);
    }
    return salida;
  }
  function tieneAdaptador() {
    try {
      return !!(typeof Chart !== 'undefined' && Chart._adapters &&
        Chart._adapters._date && Chart._adapters._date.override);
    } catch (e) { return false; }
  }

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
    var tiempo = tieneAdaptador();
    chart = new Chart(elCanvas, {
      type: 'line',
      data: {labels: [], datasets: []},
      plugins: [pluginUmbral],
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {mode: 'index', intersect: false},
        plugins: {
          legend: {display: false},
          tooltip: {
            callbacks: {
              title: function (items) {
                var x = items[0] && items[0].parsed ? items[0].parsed.x : null;
                return x == null ? '' : fmtLarga(new Date(x));
              },
              label: function (item) {
                if (item.parsed.y == null) return '';
                var extra = item.raw && item.raw.muestras
                  ? ' (' + item.raw.muestras + ' muestras)' : '';
                return TIPOS[tipoActivo].titulo + ': ' + item.parsed.y + ' ' +
                  TIPOS[tipoActivo].unidad + extra;
              }
            }
          }
        },
        scales: {
          x: tiempo ? {
            type: 'time',
            time: {
              tooltipFormat: 'dd/MM/yyyy HH:mm:ss',
              displayFormats: {minute: 'HH:mm', hour: 'HH:mm', day: 'dd/MM',
                               week: 'dd/MM', month: 'MM/yyyy'}
            },
            ticks: {maxTicksLimit: 8, font: {size: 10}}
          } : {ticks: {maxTicksLimit: 8, font: {size: 10}}},
          y: {ticks: {font: {size: 10}}}
        }
      }
    });
    chart._tiempo = tiempo;
    return chart;
  }

  function mostrarVacio(texto) {
    if (elEmpty) {
      elEmpty.style.display = '';
      var p = elEmpty.querySelector('p');
      if (p) p.textContent = texto;
    }
    elCanvas.style.display = 'none';
  }

  function pintarStats(stats) {
    if (!elMax || !elMin || !elProm) return;
    var unidad = TIPOS[tipoActivo].unidad;
    if (!stats || stats.prom == null) {
      elMax.textContent = elMin.textContent = elProm.textContent = '—';
      return;
    }
    elMax.textContent = fmtStat(stats.max) + ' ' + unidad;
    elMin.textContent = fmtStat(stats.min) + ' ' + unidad;
    elProm.textContent = fmtStat(stats.prom) + ' ' + unidad;
  }

  function pintar(d) {
    var cfg = TIPOS[tipoActivo];
    if (elTitle) elTitle.textContent = cfg.titulo;
    var serie = (d && d.serie) || [];
    bucketActual = (d && d.bucket_s) || 300;
    pintarStats(d && d.stats);

    if (!serie.length) {
      mostrarVacio(cargando ? 'Cargando historial…'
        : 'Sin datos en el período seleccionado.');
      return;
    }
    if (elEmpty) elEmpty.style.display = 'none';
    elCanvas.style.display = '';
    if (typeof Chart === 'undefined') {
      mostrarVacio('Sin conexión para cargar Chart.js.');
      return;
    }
    var c = ensureChart();
    if (!c) return;

    var puntos = serie.map(function (p) {
      return {x: aFecha(p.fecha_hora).getTime(), y: Number(p.valor),
              muestras: p.muestras};
    }).filter(function (p) { return !isNaN(p.x); });
    if (!puntos.length) {
      mostrarVacio('Sin datos en el período seleccionado.');
      return;
    }

    var data;
    if (c._tiempo) {
      var minX = puntos[0].x;
      var maxX = puntos[puntos.length - 1].x;
      data = {
        datasets: [{
          label: cfg.titulo,
          data: conHuecos(puntos, bucketActual),
          borderColor: cfg.color,
          backgroundColor: cfg.color + '22',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
          spanGaps: false
        }]
      };
      (umbrales[tipoActivo] || []).forEach(function (u) {
        var sev = (u.severidad || '').toLowerCase();
        data.datasets.push({
          label: 'Umbral ' + u.valor_umbral,
          data: [{x: minX, y: u.valor_umbral}, {x: maxX, y: u.valor_umbral}],
          borderColor: COLOR_SEV[sev] || '#6b7280',
          borderDash: [6, 4],
          pointRadius: 0,
          borderWidth: 1.5,
          fill: false
        });
      });
    } else {
      // Sin adaptador de fechas: eje categorico con fecha + hora en la etiqueta.
      var labels = [], vals = [];
      var corte = Math.max(bucketActual * 2.5, 180) * 1000;
      for (var i = 0; i < puntos.length; i++) {
        if (i > 0 && (puntos[i].x - puntos[i - 1].x) > corte) {
          labels.push('');
          vals.push(null);
        }
        labels.push(fmtCorta(new Date(puntos[i].x)));
        vals.push(puntos[i].y);
      }
      data = {
        labels: labels,
        datasets: [{
          label: cfg.titulo,
          data: vals,
          borderColor: cfg.color,
          backgroundColor: cfg.color + '22',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 2,
          spanGaps: false
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
    }
    c.data = data;
    c.update('none');
  }

  async function cargarSerie() {
    var url = '/api/historico/serie?serial=' + encodeURIComponent(serial) +
      '&horas=' + encodeURIComponent(horas) +
      '&magnitud=' + encodeURIComponent(tipoActivo);
    var r = await fetch(url, {cache: 'no-store'});
    if (!r.ok) throw new Error('http ' + r.status);
    var d = await r.json();
    if (!d.ok) throw new Error(d.error || 'sin datos');
    return d;
  }

  async function refrescar() {
    try {
      var d = await cargarSerie();
      var serie = d.serie || [];
      var ultimo = serie.length ? serie[serie.length - 1].valor : null;
      var nueva = [d.hasta, d.bucket_s, serie.length, ultimo, tipoActivo].join('|');
      cargando = false;
      if (nueva === firma) return;   // sin cambios: no se repinta (evita parpadeo)
      firma = nueva;
      pintar(d);
    } catch (e) {
      cargando = false;
      if (firma === '') mostrarVacio('No se pudo cargar el historial.');
    }
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
      firma = '';
      refrescar();
    });
  }
  marcarTabs();

  function iniciar() {
    mostrarVacio('Cargando historial…');
    refrescar();
    setInterval(refrescar, 20000);
  }
  if (typeof Chart === 'undefined') {
    window.addEventListener('load', iniciar);
  } else {
    iniciar();
  }
})();
