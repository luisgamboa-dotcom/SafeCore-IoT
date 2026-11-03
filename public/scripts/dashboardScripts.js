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
  var elUmbralesNota = document.getElementById('chartUmbrales');
  var hayGrafico = !!(elChart && elTabs && elTitle);
  if (!hayGrafico && !elDevices && !elEstado) return;
  if (!hayGrafico && elEmpty) {
    // HTML viejo en cache: se avisa en el panel en vez de fallar en silencio.
    elEmpty.style.display = '';
    elEmpty.querySelector('p').textContent =
      'Recarga la página (Ctrl+Shift+R): hay una versión nueva del panel.';
  }

  // Umbrales configurados (reglas activas de la organizacion) que el servidor
  // serializa en el canvas. Sin atributo (paginas sin grafico) queda vacio.
  var umbrales = {};
  try {
    umbrales = JSON.parse((elChart && elChart.getAttribute('data-umbrales')) || '{}') || {};
  } catch (e) { umbrales = {}; }

  var TIPOS = {
    gas: {titulo: 'Niveles de gas (ppm)', unidad: 'ppm', color: '#8751F8'},
    temp: {titulo: 'Temperatura (°C)', unidad: '°C', color: '#E8590C'},
    hum: {titulo: 'Humedad (%)', unidad: '%', color: '#1971C2'}
  };
  var COLOR_SEV = {critica: '#7f1d1d', alta: '#dc2626', media: '#fbbf24', baja: '#16a34a'};
  var NOMBRE_SEV = {critica: 'Crítica', alta: 'Alta', media: 'Media', baja: 'Baja'};
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
      if (c === '&') salida += '&amp;';
      else if (c === '<') salida += '&lt;';
      else if (c === '>') salida += '&gt;';
      else if (c === '"') salida += '&quot;';
      else if (c === "'") salida += '&#39;';
      else salida += c;
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

  // --- Grafico: promedio por tiempo de los dispositivos de la organizacion ---
  var horas = new URLSearchParams(location.search).get('horas') || '1';
  if (['0', '1', '24', '168', '720'].indexOf(horas) < 0) horas = '1';
  var chart = null;
  var bucketActual = 300;
  var firma = '';
  var cargando = true;

  function dosDigitos(n) { return (n < 10 ? '0' : '') + n; }
  /* "YYYY-MM-DD HH:MM:SS" -> Date local (sin ambiguedades de zona horaria). */
  function aFecha(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/.exec(String(s));
    if (!m) return new Date(NaN);
    return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0));
  }
  function fmtCorta(d) {
    return dosDigitos(d.getDate()) + '/' + dosDigitos(d.getMonth() + 1) +
      ' ' + dosDigitos(d.getHours()) + ':' + dosDigitos(d.getMinutes());
  }
  function fmtLarga(d) {
    return dosDigitos(d.getDate()) + '/' + dosDigitos(d.getMonth() + 1) + '/' +
      d.getFullYear() + ' ' + dosDigitos(d.getHours()) + ':' +
      dosDigitos(d.getMinutes()) + ':' + dosDigitos(d.getSeconds());
  }
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

  // Etiqueta de cada umbral al borde derecho (misma logica que la ficha).
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
    if (chart || !elChart || typeof Chart === 'undefined') return chart;
    var tiempo = tieneAdaptador();
    chart = new Chart(elChart, {
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
                if (item.dataset && /^Umbral /.test(item.dataset.label || '')) {
                  return item.dataset.label + ': ' + item.parsed.y + ' ' +
                    TIPOS[tipoActivo].unidad;
                }
                var raw = item.raw || {};
                var extra = raw.dispositivos
                  ? ' (promedio de ' + raw.dispositivos + ' dispositivos)' : '';
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

  function fmtStat(v) {
    return (v == null || isNaN(v)) ? '—' : (Math.round(v * 100) / 100);
  }
  function pintarStats(stats) {
    if (!elStatMax || !elStatMin || !elStatProm) return;
    var unidad = TIPOS[tipoActivo].unidad;
    if (!stats || stats.prom == null) {
      elStatMax.textContent = elStatMin.textContent = elStatProm.textContent = '—';
      return;
    }
    elStatMax.textContent = fmtStat(stats.max) + ' ' + unidad;
    elStatMin.textContent = fmtStat(stats.min) + ' ' + unidad;
    elStatProm.textContent = fmtStat(stats.prom) + ' ' + unidad;
  }

  function mostrarVacio(texto) {
    if (elEmpty) {
      elEmpty.style.display = '';
      var p = elEmpty.querySelector('p');
      if (p) p.textContent = texto;
    }
    if (elChart) elChart.style.display = 'none';
  }

  function pintarNotaUmbrales() {
    if (!elUmbralesNota) return;
    var cfg = TIPOS[tipoActivo];
    var lista = umbrales[tipoActivo] || [];
    if (!lista.length) {
      elUmbralesNota.textContent = 'Sin umbrales configurados para ' +
        (tipoActivo === 'temp' ? 'temperatura'
          : tipoActivo === 'hum' ? 'humedad' : 'gas') + '.';
      return;
    }
    elUmbralesNota.textContent = 'Umbrales activos: ' + lista.map(function (u) {
      var sev = (u.severidad || '').toLowerCase();
      return (NOMBRE_SEV[sev] || u.severidad) + ' ' + u.operador + ' ' +
        u.valor_umbral + ' ' + cfg.unidad;
    }).join(' · ');
  }

  function renderChart(d) {
    var cfg = TIPOS[tipoActivo];
    if (elTitle) elTitle.textContent = cfg.titulo;
    pintarNotaUmbrales();
    var serie = (d && d.serie) || [];
    bucketActual = (d && d.bucket_s) || 300;
    pintarStats(d && d.stats);
    if (!serie.length) {
      mostrarVacio(cargando ? 'Cargando historial…'
        : 'Sin datos de ' + (tipoActivo === 'temp' ? 'temperatura' : tipoActivo === 'hum' ? 'humedad' : 'gas') +
          ' en el período seleccionado.');
      return;
    }
    if (elEmpty) elEmpty.style.display = 'none';
    if (elChart) elChart.style.display = '';
    if (typeof Chart === 'undefined') {
      mostrarVacio('Sin conexión para cargar Chart.js');
      return;
    }
    var c = ensureChart();
    if (!c) return;

    var puntos = serie.map(function (p) {
      return {x: aFecha(p.fecha_hora).getTime(), y: Number(p.valor),
              muestras: p.muestras, dispositivos: p.dispositivos};
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
          label: cfg.titulo + ' (' + cfg.unidad + ')',
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
    var url = '/api/historico/organizacion?horas=' + encodeURIComponent(horas) +
      '&magnitud=' + encodeURIComponent(tipoActivo);
    var r = await fetch(url, {cache: 'no-store'});
    if (!r.ok) throw new Error('http ' + r.status);
    var d = await r.json();
    if (!d.ok) throw new Error(d.error || 'sin datos');
    return d;
  }

  async function refrescarGrafico() {
    if (!hayGrafico) return;
    try {
      var d = await cargarSerie();
      var serie = d.serie || [];
      var ultimo = serie.length ? serie[serie.length - 1].valor : null;
      var nueva = [d.hasta, d.bucket_s, serie.length, ultimo, tipoActivo].join('|');
      cargando = false;
      if (nueva === firma) return;
      firma = nueva;
      renderChart(d);
    } catch (e) {
      cargando = false;
      if (firma === '') mostrarVacio('No se pudo cargar el historial.');
    }
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
      firma = '';
      refrescarGrafico();
    });
  }
  marcarTabs();

  // --- Tarjetas por dispositivo y KPI de estado (buffer en vivo) ---
  var ultimos = [];
  var APAGADO_SEG = 300;
  var COLOR_SEV = {critica: '#7f1d1d', alta: '#dc2626', media: '#b45309', baja: '#15803d'};

  function fmtValor(v) {
    var n = Number(v);
    return isNaN(n) ? String(v) : String(Math.round(n * 100) / 100);
  }

  // Ajusta el tamano del valor para que quepa en su bloque sin partir el
  // numero. El bloque es un contenedor de tamano (container-type:inline-size),
  // asi que cqw mide su ancho real. 0.62 = ancho aproximado de un digito
  // tabular respecto al font-size; 1.875rem es el tope visual y 0.75rem el
  // minimo legible (por debajo, break-all actua como ultimo recurso).
  function ajustarFuenteValor(el, texto) {
    if (!el) return;
    var n = Math.max(1, String(texto == null ? '' : texto).length);
    var cqw = Math.max(14, Math.min(42, 100 / (0.62 * n)));
    el.style.fontSize = 'clamp(0.75rem, ' + cqw.toFixed(1) + 'cqw, 1.875rem)';
  }

  function reglaExcedida(valor, reglas) {
    var v = Number(valor);
    return (reglas || []).find(function (r) {
      var u = Number(r.valor_umbral), op = r.operador;
      return (op === '>' && v > u) || (op === '>=' && v >= u) ||
             (op === '<' && v < u) || (op === '<=' && v <= u) ||
             (op === '=' && v === u) || (op === '!=' && v !== u);
    }) || null;
  }

  // Agrupa las lecturas del buffer por dispositivo y magnitud. `items` viene
  // de mas nuevo a mas viejo, asi que la primera aparicion de cada pareja es
  // la lectura vigente.
  function agruparPorMagnitud(items) {
    var porSerial = {};
    items.forEach(function (x) {
      var ser = x.codigo_serial || '';
      var mag = x.magnitud || '';
      if (!porSerial[ser]) porSerial[ser] = {};
      if (!porSerial[ser][mag]) porSerial[ser][mag] = x;
    });
    return porSerial;
  }

  // Rellena las tarjetas grandes [data-serial] con las tres magnitudes.
  // Sin datos o ultima lectura > 5 min -> Apagado.
  function actualizarTarjetas(items) {
    var grid = document.getElementById('devicesLive');
    if (!grid) return;
    var porSerial = agruparPorMagnitud(items);
    grid.querySelectorAll('[data-serial]').forEach(function (card) {
      var ser = card.getAttribute('data-serial');
      var lecturas = porSerial[ser] || {};
      var umbrales = {};
      try {
        umbrales = JSON.parse(card.getAttribute('data-umbrales') || '{}') || {};
      } catch (e) { umbrales = {}; }

      var masReciente = null;
      card.querySelectorAll('[data-mag]').forEach(function (bloque) {
        var mag = bloque.getAttribute('data-mag');
        var it = lecturas[mag];
        var elV = bloque.querySelector('[data-campo="valor"]');
        var elE = bloque.querySelector('.dev-live-edad');
        var elQ = bloque.querySelector('.dev-live-calidad');
        if (!it) {
          if (elV) {
            elV.textContent = '—';
            elV.style.color = '';
            ajustarFuenteValor(elV, '—');
          }
          if (elE) elE.textContent = 'sin datos';
          if (elQ) elQ.classList.add('hidden');
          return;
        }
        if (elV) {
          var textoValor = fmtValor(it.valor);
          elV.textContent = textoValor;
          ajustarFuenteValor(elV, textoValor);
          var regla = reglaExcedida(it.valor, umbrales[mag]);
          elV.style.color = regla
            ? (COLOR_SEV[(regla.severidad || '').toLowerCase()] || '#7f1d1d')
            : '';
        }
        if (elE) {
          var age = ageSecs(it.fecha_hora);
          elE.textContent = age >= 0 ? 'hace ' + ageFmt(age) : 'sin datos';
        }
        if (elQ) elQ.classList.toggle('hidden', it.calidad !== 'dudosa');
        if (!masReciente || String(it.fecha_hora).localeCompare(String(masReciente)) > 0) {
          masReciente = it.fecha_hora;
        }
      });

      var dot = card.querySelector('.js-dot');
      var est = card.querySelector('.js-estado');
      var texto = card.querySelector('.js-estado-texto');
      var fec = card.querySelector('.js-fecha');
      var ageUltima = masReciente ? ageSecs(masReciente) : -1;
      var apagado = !masReciente || ageUltima > APAGADO_SEG;
      if (dot) {
        dot.className = 'js-dot w-2.5 h-2.5 rounded-full ' +
          (apagado ? 'status-dot-crit' : 'status-dot-online');
      }
      if (est) {
        est.className = 'js-estado inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold whitespace-nowrap shrink-0 ' +
          (apagado ? 'bg-error-container text-error' : 'bg-green-100 text-green-800');
      }
      if (texto) texto.textContent = apagado ? 'Apagado' : 'En línea';
      if (fec) {
        fec.textContent = masReciente
          ? 'Última lectura: ' + masReciente + (ageUltima >= 0 ? ' · hace ' + ageFmt(ageUltima) : '')
          : 'Sin lecturas recientes';
        fec.title = fec.textContent;
      }
    });
  }

  async function tick() {
    var items = ultimos;
    try {
      var r = await fetch('/api/live?limit=200&agrupado=1', {cache: 'no-store'});
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
  }

  function iniciar() {
    if (hayGrafico) {
      pintarNotaUmbrales();
      mostrarVacio('Cargando historial…');
      refrescarGrafico();
      setInterval(refrescarGrafico, 20000);
    }
    tick();
    setInterval(tick, 5000);
  }
  if (typeof Chart === 'undefined' && hayGrafico) {
    window.addEventListener('load', iniciar);
  } else {
    iniciar();
  }
})();
