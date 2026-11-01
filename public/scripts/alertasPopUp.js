/**
 * HU-017 — Pop-up de alertas del panel (sin sonido).
 * Hace polling cada 5s de /api/alertas/activas y apila tarjetas emergentes
 * "¡ALERTA! dispositivo - valor" coloreadas por severidad en
 * #popupAlertas (incluido desde partials/topbar.html).
 * - Cierre manual con ✖ (queda descartada hasta que deje de estar activa).
 * - Desaparece sola cuando la alerta deja de estar activa (resuelta/suprimida).
 * - Máximo 3 visibles; de más se muestra "+N alertas más" con enlace a la
 *   bitácora (/dashboard/alertas).
 * - No repite avisos ya mostrados mientras la alerta siga activa:
 *   guarda las vistas en localStorage y refresca el badge de la campana
 *   (/api/notificaciones/no-leidas).
 */
(function () {
  "use strict";

  const POLL_MS = 5000;
  const MAX_VISIBLE = 3;
  const CLAVE_VISTAS = "safecore_alertas_vistas";
  const CLAVE_CERRADAS = "safecore_alertas_cerradas";

  const coloresSeveridad = {
    critica: "bg-red-900 text-white",
    alta: "bg-red-600 text-white",
    media: "bg-amber-400 text-red-950",
    baja: "bg-green-600 text-white",
    _: "bg-gray-600 text-white"
  };

  function leerLista(clave) {
    try { return new Set(JSON.parse(localStorage.getItem(clave) || "[]")); }
    catch (e) { return new Set(); }
  }

  function guardarLista(clave, grupo) {
    try { localStorage.setItem(clave, JSON.stringify([...grupo])); }
    catch (e) { /* localStorage lleno o bloqueado: se avisa igual en sesión */ }
  }

  function contenedor() {
    return document.getElementById("popupAlertas");
  }

  function tarjetaAlerta(alerta) {
    const tarjeta = document.createElement("div");
    tarjeta.dataset.idAlerta = alerta.id_alerta;
    tarjeta.className = `${coloresSeveridad[alerta.severidad] || coloresSeveridad._} ` +
      "rounded-xl shadow-lg p-3 flex items-start gap-2 pointer-events-auto";
    tarjeta.setAttribute("role", "alert");

    const cuerpo = document.createElement("div");
    cuerpo.className = "flex-1 min-w-0";
    const linea1 = document.createElement("p");
    linea1.className = "text-xs font-bold uppercase tracking-wide";
    linea1.textContent = "¡ALERTA!";
    const linea2 = document.createElement("p");
    linea2.className = "text-sm font-semibold";
    linea2.textContent = `${alerta.dispositivo} - ${alerta.valor}${alerta.unidad}`;
    const linea3 = document.createElement("p");
    linea3.className = "text-[11px] opacity-80";
    linea3.textContent = `${alerta.mensaje} · ${alerta.fecha}`;
    cuerpo.append(linea1, linea2, linea3);

    const boton = document.createElement("button");
    boton.type = "button";
    boton.setAttribute("aria-label", "Cerrar alerta");
    boton.title = "Cerrar";
    boton.className = "p-1 rounded-md bg-white/20 hover:bg-white/40 transition-colors flex-shrink-0";
    boton.textContent = "✖";
    boton.addEventListener("click", () => {
      const cerradas = leerLista(CLAVE_CERRADAS);
      cerradas.add(alerta.id_alerta);
      guardarLista(CLAVE_CERRADAS, cerradas);
      tarjeta.remove();
      recalcularVisibles();
    });

    tarjeta.append(cuerpo, boton);
    return tarjeta;
  }

  function enlaceMas(N) {
    const enlace = document.createElement("a");
    enlace.id = "popupAlertasMas";
    enlace.href = "/dashboard/alertas";
    enlace.className = "pointer-events-auto self-end bg-white text-primary " +
      "border border-outline-variant rounded-lg px-3 py-1.5 text-xs font-semibold " +
      "shadow hover:bg-surface-container-low transition-colors";
    enlace.textContent = `+${N} alerta${N === 1 ? "" : "s"} más · Ver bitácora`;
    return enlace;
  }

  function recalcularVisibles() {
    const cont = document.getElementById("popupAlertas");
    if (!cont) { return; }
    const tarjetas = [...cont.querySelectorAll("[data-id-alerta]")];
    let ocultas = 0;
    tarjetas.forEach((t, i) => {
      const visible = i < MAX_VISIBLE;
      t.classList.toggle("hidden", !visible);
      if (!visible) { ocultas++; }
    });
    let contador = cont.querySelector("#popupAlertasMas");
    if (ocultas > 0) {
      if (!contador) {
        contador = enlaceMas(0);
        cont.appendChild(contador);
      }
      contador.textContent = `+${ocultas} alerta${ocultas === 1 ? "" : "s"} más · Ver bitácora`;
    } else if (contador) {
      contador.remove();
    }
    cont.classList.toggle("hidden", cont.children.length === 0);
  }

  async function refrescarBadgeCampana() {
    const campana = document.querySelector('#popupAlertasBell') ||
      document.querySelector('a[aria-label="Notificaciones"]');
    if (!campana) { return; }
    try {
      const r = await fetch("/api/notificaciones/no-leidas");
      if (!r.ok) { return; }
      const d = await r.json();
      let badge = document.getElementById("badgeNotificaciones");
      const n = d.no_leidas || 0;
      if (n > 0) {
        if (!badge) {
          badge = document.createElement("span");
          badge.id = "badgeNotificaciones";
          badge.className = "absolute -top-1 -right-1 min-w-[20px] h-5 px-1.5 " +
            "rounded-full bg-error text-white text-[11px] font-bold " +
            "flex items-center justify-center";
          campana.appendChild(badge);
        }
        badge.textContent = n > 99 ? "99+" : n;
      } else if (badge) {
        badge.remove();
      }
    } catch (e) { /* badge con el conteo del servidor */ }
  }

  async function encuesta() {
    const cont = contenedor();
    if (!cont) { return; }
    let alertas = [];
    try {
      const r = await fetch("/api/alertas/activas");
      if (!r.ok) { return; }
      const d = await r.json();
      if (d.ok) { alertas = d.alertas || []; }
    } catch (e) { return; }

    const activas = new Set(alertas.map(a => String(a.id_alerta)));
    const vistas = leerLista(CLAVE_VISTAS);
    const cerradas = leerLista(CLAVE_CERRADAS);
    // Limpieza: se olvida lo que ya no está activo (permite avisar de nuevo
    // si la misma regla vuelve a abrirse con otro id).
    [...vistas, ...cerradas].forEach(id => {
      if (!activas.has(id)) { vistas.delete(id); cerradas.delete(id); }
    });

    const presentes = new Set(
      [...cont.querySelectorAll("[data-id-alerta]")].map(t => t.dataset.idAlerta));

    // Limpieza de tarjetas cuya alerta dejó de estar activa.
    [...cont.children].forEach(t => {
      const id = t.dataset && t.dataset.idAlerta;
      if (id && !activas.has(id)) { t.remove(); }
    });

    alertas.forEach(alerta => {
      const id = String(alerta.id_alerta);
      if (vistas.has(id) && presentes.has(id)) { return; }
      if (vistas.has(id) && !presentes.has(id)) {
        // Reaparece (recarga de página): tarjeta nueva, sigue siendo notificada.
      } else if (!vistas.has(id)) {
        vistas.add(id);
      }
      // Las cerradas manualmente no vuelven mientras sigan activas.
      if (cerradas.has(id)) { return; }
      if (!presentes.has(id)) {
        cont.insertBefore(tarjetaAlerta(alerta), cont.firstChild);
      }
    });
    guardarLista(CLAVE_VISTAS, vistas);
    guardarLista(CLAVE_CERRADAS, cerradas);
    recalcularVisibles();
    await refrescarBadgeCampana();
  }

  if (!document.getElementById("popupAlertas") &&
      !document.querySelector('a[aria-label="Notificaciones"]')) {
    return;
  }
  encuesta();
  setInterval(encuesta, POLL_MS);
})();
