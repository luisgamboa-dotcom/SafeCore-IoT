"use strict";
/* Ficha de dispositivo: tarjeta "En vivo" (ultima lectura por magnitud,
   estado de senal y resaltado cuando el valor excede el umbral de la regla). */
(function () {
  var root = document.querySelector('[data-serial]');
  if (!root) return;
  var serial = root.getAttribute('data-serial');
  var pillDot = document.getElementById('devLiveDot');
  var pillTexto = document.getElementById('devLiveTexto');

  var umbrales = {};
  try {
    umbrales = JSON.parse(root.getAttribute('data-umbrales') || '{}') || {};
  } catch (e) {}

  var COLOR_SEV = {critica: '#7f1d1d', alta: '#dc2626', media: '#b45309', baja: '#15803d'};
  var ESTADO = {
    online: {texto: 'En línea', color: '#16a34a'},
    senal: {texto: 'Sin señal', color: '#f59e0b'},
    vacio: {texto: 'Sin datos', color: '#9ca3af'}
  };

  function fmtValor(v) {
    var n = Number(v);
    return isNaN(n) ? String(v) : String(Math.round(n * 100) / 100);
  }

  function edad(ts) {
    var d = (Date.now() - new Date(String(ts).replace(' ', 'T')).getTime()) / 1000;
    if (!isFinite(d) || d < 0) return '—';
    if (d < 60) return 'hace ' + Math.round(d) + ' s';
    if (d < 3600) return 'hace ' + Math.round(d / 60) + ' min';
    return 'hace ' + Math.round(d / 3600) + ' h';
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

  function pintarPill(estado) {
    if (pillDot) pillDot.style.background = estado.color;
    if (pillTexto) pillTexto.textContent = estado.texto;
  }

  async function tick() {
    var items = [];
    try {
      var r = await fetch('/api/live?limit=200&agrupado=1', {cache: 'no-store'});
      if (r.ok) items = ((await r.json()).lecturas) || [];
    } catch (e) { /* sin servidor: se deja el ultimo texto */ }

    var ultimas = {};
    items.forEach(function (x) {
      if ((x.codigo_serial || '') !== serial) return;
      var prev = ultimas[x.magnitud];
      if (!prev || String(x.fecha_hora).localeCompare(String(prev.fecha_hora)) > 0) {
        ultimas[x.magnitud] = x;
      }
    });

    var ultimaTs = null;
    root.querySelectorAll('[data-mag]').forEach(function (fila) {
      var mag = fila.getAttribute('data-mag');
      var it = ultimas[mag];
      var elV = fila.querySelector('[data-campo="valor"]');
      var elE = fila.querySelector('.dev-live-edad');
      var elQ = fila.querySelector('.dev-live-calidad');
      if (!it) {
        if (elV) { elV.textContent = '—'; elV.style.color = ''; }
        if (elE) elE.textContent = 'sin datos';
        if (elQ) elQ.classList.add('hidden');
        return;
      }
      if (elV) {
        elV.textContent = fmtValor(it.valor);
        var regla = reglaExcedida(it.valor, umbrales[mag]);
        elV.style.color = regla
          ? (COLOR_SEV[(regla.severidad || '').toLowerCase()] || '#7f1d1d')
          : '';
      }
      if (elE) elE.textContent = edad(it.fecha_hora);
      if (elQ) elQ.classList.toggle('hidden', it.calidad !== 'dudosa');
      if (!ultimaTs || String(it.fecha_hora).localeCompare(String(ultimaTs)) > 0) {
        ultimaTs = it.fecha_hora;
      }
    });

    if (!ultimaTs) {
      pintarPill(ESTADO.vacio);
      return;
    }
    var d = (Date.now() - new Date(String(ultimaTs).replace(' ', 'T')).getTime()) / 1000;
    pintarPill(d < 120 ? ESTADO.online : ESTADO.senal);
  }

  tick();
  setInterval(tick, 5000);
})();
