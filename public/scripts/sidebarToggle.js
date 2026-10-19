/* Sidebar colapsable: requiere IDs sidebar, sidebarToggle, edgeZone, backdrop, mainWrap. */
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
