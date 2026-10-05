/* public/scripts/datosScripts.js — auto-refresh de datos/index.html cada 5 s */
const UMBRAL_LINEA_SEG = 90;  // sin datos nuevos en 90 segundos entonces fuera de línea

function formatearEdad(seg) {
    if (seg < 60) return `hace ${Math.floor(seg)} s`;
    if (seg < 3600) return `hace ${Math.floor(seg / 60)} min`;
    return `hace ${Math.floor(seg / 3600)} h`;
}

async function refrescar() {
    const estado = document.getElementById('estado');
    try {
        const r = await fetch('/api/ultimas?limit=10');
        const j = await r.json();
        const tb = document.getElementById('filas');
        tb.innerHTML = j.lecturas.map(l =>
            `<tr><td>${l.id_lectura}</td><td>${l.fecha_hora}</td><td>${l.codigo_serial}</td>` +
            `<td>${l.dispositivo ?? ''}</td><td>${l.magnitud}</td><td>${l.valor}</td>` +
            `<td>${l.calidad}</td></tr>`).join('');
        if (!j.lecturas.length) {
            estado.textContent = '⚫ Fuera de línea — sin datos registrados';
            return;
        }
        const edadSeg = (Date.now() - new Date(j.lecturas[0].fecha_hora).getTime()) / 1000;
        if (edadSeg <= UMBRAL_LINEA_SEG) {
            estado.textContent =
                '🟢 En línea - actualizado: ' + new Date().toLocaleTimeString() + ' (' + j.lecturas.length + ' filas)';
        } else {
            estado.textContent =
                '⚫ Fuera de línea — últimos datos ' + formatearEdad(edadSeg) + ' (' + j.lecturas.length + ' filas)';
        }
    } catch (e) {
        estado.textContent = 'Fuera de línea — sin conexión con /api/ultimas';
    }
}
setInterval(refrescar, 10000);
