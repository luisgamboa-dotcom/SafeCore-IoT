/* Ficha de dispositivo: inyecta el ultimo dato vivo del serial desde /api/live. */
(function () {
  var box = document.querySelector('[data-serial] .dev-live');
  if (!box) return;
  var serial = document.querySelector('[data-serial]').getAttribute('data-serial');

  function fmt(ts) {
    if (!ts) return '—';
    var d = (Date.now() - new Date(ts.replace(' ', 'T')).getTime()) / 1000;
    return ts + (d >= 0 ? ' · hace ' + (d < 60 ? Math.round(d) + ' s'
      : Math.round(d / 60) + ' min') : '');
  }

  async function tick() {
    try {
      var r = await fetch('/api/live?limit=150', {cache: 'no-store'});
      if (!r.ok) throw 0;
      var items = ((await r.json()).lecturas) || [];
      var it = items.find(function (x) { return (x.codigo_serial || '') === serial; });
      if (!it) {
        box.textContent = '—';
        return;
      }
      box.textContent = it.magnitud + ': ' + it.valor + ' · ' + fmt(it.fecha_hora);
    } catch (e) { /* sin servidor: se deja el ultimo texto */ }
  }

  tick();
  setInterval(tick, 5000);
})();
