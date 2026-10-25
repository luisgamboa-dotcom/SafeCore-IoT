"use strict";
/* Página temporal /datos/live: pinta el lote en curso y el historial de envíos contra /api/buffer. */

const magNombre = { gas: "Gas (ADC)", temp: "Temperatura (°C)", hum: "Humedad (%)" };
let segundosRestantes = null;
let intervalo = 60;

const el = (id) => document.getElementById(id);
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const chipCalidad = (calidad) =>
  `<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium ${calidad === "valida" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}">${esc(calidad)}</span>`;

function pintarModo(modo) {
  const chip = el("modoChip");
  if (modo === "persistente") {
    chip.className = "inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-green-100 text-green-800";
    chip.textContent = "Modo persistente: se envía a la BD por lote";
  } else {
    chip.className = "inline-flex items-center px-3 py-1.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800";
    chip.textContent = "Modo test: visual en vivo, sin escritura en BD";
  }
}

function filasDe(items) {
  return items.map((it) => `
    <tr class="border-b border-outline-variant/60">
      <td class="py-2 pr-4 text-on-surface-variant">${esc((it.fecha_hora || "").slice(11))}</td>
      <td class="py-2 pr-4 font-semibold">${esc(it.codigo_serial)}</td>
      <td class="py-2 pr-4">${esc(magNombre[it.magnitud] || it.magnitud)}</td>
      <td class="py-2 pr-4 font-bold text-primary">${esc(it.valor)}</td>
      <td class="py-2 pr-4">${esc(it.calidad)}</td>
      <td class="py-2 text-xs text-on-surface-variant">#${esc(it.seq)}${it.fw ? " · " + esc(it.fw) : ""}</td>
    </tr>`).join("");
}

function pintarLote(data) {
  const lista = el("loteLista");
  if (!data.lote_actual || data.lote_actual.length === 0) {
    lista.innerHTML = `<tr><td colspan="6" class="py-4 text-center text-on-surface-variant">Sin lecturas acumuladas todavía…</td></tr>`;
  } else {
    lista.innerHTML = filasDe(data.lote_actual);
  }
  const chip = el("pendientesChip");
  const n = data.pendientes || 0;
  chip.textContent = `${n} lectura${n === 1 ? "" : "s"} acumulada${n === 1 ? "" : "s"}`;
}

function pintarHistorial(historial) {
  const cont = el("historialLista");
  if (!historial || historial.length === 0) return;
  cont.innerHTML = historial.map((h) => {
    const resultado = h.resultado === "bd"
      ? `<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium bg-green-100 text-green-800">Enviado a la BD</span>`
      : h.resultado === "error"
        ? `<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium bg-error-container text-error">Error de envío</span>`
        : `<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-medium bg-yellow-100 text-yellow-800">Sin envío (modo vivo)</span>`;
    const promedios = (h.promedios || []).map((p) =>
      `<li>${esc(p.dispositivo)} · ${esc(magNombre[p.magnitud] || p.magnitud)}: <strong>${esc(p.promedio)}</strong> (${esc(p.calidad)}, ${esc(p.muestras)} muestras)</li>`).join("");
    const detalle = (h.detalle || []).map((it) => filasDe([it])).join("");
    return `<article class="rounded-xl border border-outline-variant overflow-hidden">
      <div class="flex flex-wrap justify-between items-center gap-2 p-4 bg-surface-container-low">
        <div class="flex flex-wrap items-center gap-3">
          ${resultado}
          <span class="text-sm font-semibold text-on-surface">${esc(h.cuando)}</span>
          <span class="text-xs text-on-surface-variant">${h.recibidas} lecturas en el ciclo</span>
        </div>
        <details class="text-xs text-secondary">
          <summary class="cursor-pointer select-none">Ver detalle</summary>
          <div class="mt-2 overflow-x-auto bg-white rounded-lg p-3 border border-outline-variant">
            <table class="w-full text-sm"><tbody>${detalle}</tbody></table>
          </div>
        </details>
      </div>
      ${(h.nota || h.errores) ? `<div class="px-4 py-2 text-xs text-on-surface-variant">${esc(h.nota || "")}${(h.errores || []).map(esc).join("<br>")}</div>` : ""}
      ${promedios ? `<ul class="px-4 py-3 text-sm space-y-1">${promedios}</ul>` : ""}
    </article>`;
  }).join("");
}

function pintarCuenta(data) {
  intervalo = data.intervalo_s || intervalo;
  segundosRestantes = data.segundos_para_envio;
}

function tic() {
  if (segundosRestantes === null) return;
  const s = Math.max(0, segundosRestantes - 1);
  segundosRestantes = Math.max(0, segundosRestantes - 1);
  el("envioEn").textContent = s;
  el("envioBarra").style.width = `${Math.round(100 * (1 - s / intervalo))}%`;
}

async function actualizar() {
  try {
    const r = await fetch("/api/buffer");
    const data = await r.json();
    if (!data.ok) return;
    pintarModo(data.modo);
    pintarLote(data);
    pintarHistorial(data.historial);
    pintarCuenta(data);
  } catch (e) { /* reintenta en el siguiente tick */ }
}

actualizar();
setInterval(actualizar, 2000);
setInterval(tic, 1000);
