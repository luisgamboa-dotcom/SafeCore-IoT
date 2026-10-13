/* SafeCore IoT Dashboard — sidebar: botón alterna y el contenido se reajusta.
   Desktop: sidebar en flujo (margin-left) -> todo lo demás cambia de tamaño.
   Móvil: sidebar como drawer fijo + backdrop. Hover solo desktop con mouse fino. */
(function () {
  var sidebar = document.getElementById('sidebar');
  var toggle = document.getElementById('sidebarToggle');
  var edge = document.getElementById('edgeZone');
  var backdrop = document.getElementById('backdrop');
  if (!sidebar) return;

  var HOVER_MIN_WIDTH = 1024;
  var hoverTimer = null;

  function isDesktop() {
    return window.innerWidth >= HOVER_MIN_WIDTH &&
      window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  }
  function isOpen() { return !sidebar.classList.contains('sidebar-hidden'); }

  function openSidebar() {
    sidebar.classList.remove('sidebar-hidden');
    if (!isDesktop() && backdrop) backdrop.classList.add('backdrop-show');
    try { localStorage.setItem('safecore_sidebar', 'open'); } catch (e) {}
  }
  function closeSidebar() {
    sidebar.classList.add('sidebar-hidden');
    if (backdrop) backdrop.classList.remove('backdrop-show');
    try { localStorage.setItem('safecore_sidebar', 'closed'); } catch (e) {}
  }

  if (toggle) toggle.addEventListener('click', function () {
    if (isOpen()) closeSidebar(); else openSidebar();
  });
  if (backdrop) backdrop.addEventListener('click', closeSidebar);
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && !isDesktop()) closeSidebar();
  });

  // Hover en borde izquierdo, solo desktop con mouse fino.
  if (edge) {
    edge.addEventListener('mouseenter', function () {
      if (!isDesktop()) return;
      if (!isOpen()) openSidebar();
    });
    sidebar.addEventListener('mouseleave', function () {
      if (!isDesktop()) return;
      clearTimeout(hoverTimer);
      hoverTimer = setTimeout(function () { closeSidebar(); }, 400);
    });
    sidebar.addEventListener('mouseenter', function () { clearTimeout(hoverTimer); });
  }

  // Estado inicial: abierto en desktop, cerrado en móvil.
  var saved = null;
  try { saved = localStorage.getItem('safecore_sidebar'); } catch (e) {}
  if (window.innerWidth < HOVER_MIN_WIDTH) closeSidebar();
  else if (saved === 'closed') closeSidebar();
  else openSidebar();

  window.addEventListener('resize', function () {
    if (window.innerWidth < HOVER_MIN_WIDTH) {
      if (backdrop && isOpen()) backdrop.classList.add('backdrop-show');
      else if (backdrop) backdrop.classList.remove('backdrop-show');
    } else if (backdrop) backdrop.classList.remove('backdrop-show');
  });

  // Toast inferior derecho: autocierre temporal.
  var toast = document.getElementById('toast');
  if (toast) {
    var t = setTimeout(function () {
      toast.classList.add('toast-hide');
      setTimeout(function () { toast.remove(); }, 350);
    }, 4500);
    var btn = toast.querySelector('[data-toast-close]');
    if (btn) btn.addEventListener('click', function () {
      clearTimeout(t);
      toast.classList.add('toast-hide');
      setTimeout(function () { toast.remove(); }, 300);
    });
  }
})();

/* SafeCore en vivo sin guardar: polling a /api/live cada 5 s.
   Refleja TODO en el dashboard: KPIs, grafico de gas, alertas y tarjetas.
   No depende de MySQL. */
(function () {
  var elHora = document.getElementById('ultimaActualizacion');
  var elEstado = document.getElementById('estadoGeneral');
  var elKpiSens = document.getElementById('kpiSensores');
  var elKpiAlert = document.getElementById('kpiAlertas');
  var elAlertas = document.getElementById('alertasLive');
  var elDevices = document.getElementById('devicesLive');
  var elChart = document.getElementById('gasChart');
  var elHist = document.getElementById('gasHistory');
  var elEmpty = document.getElementById('chartEmpty');
  if (!elAlertas && !elDevices && !elChart) return;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
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
  function ageTxt(fechaHora) {
    var s = ageSecs(fechaHora);
    return s < 0 ? '' : ' (hace ' + ageFmt(s) + ')';
  }

  function drawGas(values) {
    if (!elChart) return;
    var dpr = window.devicePixelRatio || 1;
    var W = elChart.clientWidth || 600, H = 280;
    elChart.width = W * dpr; elChart.height = H * dpr;
    var ctx = elChart.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, W, H);
    if (!values.length) return;
    var min = Math.min.apply(null, values), max = Math.max.apply(null, values);
    if (max - min < 1) { max += 1; min -= 1; }
    // Umbral de alarma local (200 ADC) como linea de referencia.
    function y(v) { return H - 20 - ((v - min) / (max - min)) * (H - 50); }
    function x(i) { return 10 + (i / Math.max(1, values.length - 1)) * (W - 20); }
    ctx.strokeStyle = '#ba1a1a'; ctx.setLineDash([6, 4]); ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(0, y(200)); ctx.lineTo(W, y(200)); ctx.stroke();
    ctx.setLineDash([]);
    ctx.strokeStyle = '#8751F8'; ctx.lineWidth = 2.5; ctx.beginPath();
    values.forEach(function (v, i) { if (i === 0) ctx.moveTo(x(i), y(v)); else ctx.lineTo(x(i), y(v)); });
    ctx.stroke();
    ctx.fillStyle = '#2E1B5A'; ctx.font = '12px Inter,system-ui,sans-serif';
    ctx.fillText('max ' + Math.round(max), 10, 16);
    ctx.fillText('min ' + Math.round(min), 10, H - 6);
    ctx.fillStyle = '#ba1a1a';
    ctx.fillText('umbral 200', W - 90, y(200) - 6);
  }

  async function tick() {
    var items = [];
    try {
      var r = await fetch('/api/live?limit=50', {cache: 'no-store'});
      if (!r.ok) throw new Error('http ' + r.status);
      items = ((await r.json()).lecturas) || [];
    } catch (e) {
      if (elEstado) elEstado.textContent = 'Sin servidor (¿uvicorn con --host 0.0.0.0?)';
      return;
    }
    var dud = items.filter(function (x) { return x.calidad === 'dudosa'; });
    var devs = {};
    items.forEach(function (x) { devs[(x.codigo_serial || '') + '|' + x.magnitud] = x; });
    var nDevs = Object.keys(devs).length;

    if (elHora) elHora.textContent = items.length && items[0].fecha_hora
      ? items[0].fecha_hora + ' · en vivo · seq ' + (items[0].seq != null ? items[0].seq : '—') + ageTxt(items[0].fecha_hora)
      : 'En espera del nodo…';
    if (elEstado) {
      var ageS = items.length ? ageSecs(items[0].fecha_hora) : -1;
      if (!items.length) { elEstado.textContent = 'En espera'; }
      else if (ageS >= 90) {
        elEstado.textContent = 'Nodo sin reportar hace ' + ageFmt(ageS) + ' — revisa WiFi/IP/flasheo';
      }
      else elEstado.textContent = dud.length ? 'Revisar (' + dud.length + ' dudosa)' : 'En vivo';
    }
    if (elKpiSens) elKpiSens.textContent = items.length ? String(nDevs) : '—';
    if (elKpiAlert) elKpiAlert.textContent = String(dud.length);

    // Alertas: dudosas primero, luego las 5 mas recientes.
    if (elAlertas) {
      if (!items.length) {
        elAlertas.innerHTML = '<div class="chart-empty rounded-xl p-6 text-center">'
          + '<p class="font-semibold text-primary">Sin datos todavía</p>'
          + '<p class="mt-1">El nodo aún no reporta. Revisa WiFi, IP del servidor y que uvicorn use <code>--host 0.0.0.0</code>.</p></div>';
      } else {
        var top = dud.concat(items.filter(function (x) { return x.calidad !== 'dudosa'; })).slice(0, 5);
        elAlertas.innerHTML = '<ul class="space-y-3">' + top.map(function (l) {
          var dot = l.calidad === 'dudosa' ? 'bg-yellow-500' : 'bg-green-500';
          return '<li class="flex gap-3 p-3 rounded-lg bg-surface-container-low">'
            + '<span class="w-2 h-2 rounded-full mt-2 flex-shrink-0 ' + dot + '"></span>'
            + '<div><p class="font-semibold text-on-surface">' + esc(l.dispositivo || l.codigo_serial)
            + ' · ' + esc(l.magnitud) + ': ' + esc(l.valor) + '</p>'
            + '<p class="text-xs mt-1">' + esc(l.fecha_hora) + ' · ' + esc(l.calidad) + '</p></div></li>';
        }).join('') + '</ul>';
      }
    }

    // Tarjetas: una por (dispositivo, magnitud) con su ultima lectura.
    if (elDevices) {
      var cards = Object.values(devs).slice(0, 8);
      if (!cards.length) {
        elDevices.innerHTML = '';
      } else {
        elDevices.innerHTML = cards.map(function (l) {
          var dot = l.calidad === 'dudosa' ? 'status-dot-warn' : 'status-dot-online';
          return '<article class="bg-white rounded-xl border border-outline-variant card-shadow card-hover p-5 relative overflow-hidden">'
            + '<div class="flex justify-between items-start mb-4"><div>'
            + '<h3 class="font-semibold text-on-surface">' + esc(l.dispositivo || 'Dispositivo') + ' · ' + esc(l.codigo_serial) + '</h3>'
            + '<p class="text-xs text-on-surface-variant mt-1">' + esc(l.magnitud) + '</p></div>'
            + '<span class="w-3 h-3 rounded-full ' + dot + '"></span></div>'
            + '<div class="flex justify-between items-end"><div>'
            + '<p class="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Calidad</p>'
            + '<span class="inline-flex items-center px-2.5 py-1 rounded-full bg-surface-container-low text-xs font-semibold">' + esc(l.calidad) + '</span></div>'
            + '<div class="text-right"><p class="text-xs text-on-surface-variant uppercase tracking-wider mb-1">Lectura</p>'
            + '<p class="text-xl font-bold text-primary">' + esc(l.valor) + '</p></div></div>'
            + '<p class="text-xs text-on-surface-variant mt-3">' + esc(l.fecha_hora) + '</p></article>';
        }).join('');
      }
    }

    // Grafico de gas + ultimos valores.
    var gas = items.filter(function (x) { return x.magnitud === 'gas'; }).slice(0, 50).reverse();
    drawGas(gas.map(function (x) { return Number(x.valor); }));
    if (elHist) {
      elHist.innerHTML = gas.slice(-10).map(function (x) {
        return '<li class="px-2 py-1 rounded bg-surface-container-low">' + esc(x.valor) + ' <span class="opacity-70">· ' + esc((x.fecha_hora || '').slice(11)) + '</span></li>';
      }).join('');
    }
    if (elEmpty) elEmpty.style.display = gas.length ? 'none' : '';
  }
  tick();
  setInterval(tick, 5000);
})();
