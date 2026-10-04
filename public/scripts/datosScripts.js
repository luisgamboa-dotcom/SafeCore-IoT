/* public/scripts/datosScripts.js — auto-refresh de datos/index.html cada 5 s */
async function refrescar() {
    try {
        const r = await fetch('/api/ultimas?limit=50');
        const j = await r.json();
        const tb = document.getElementById('filas');
        tb.innerHTML = j.lecturas.map(l =>
            `<tr><td>${l.id_lectura}</td><td>${l.fecha_hora}</td><td>${l.codigo_serial}</td>` +
            `<td>${l.dispositivo ?? ''}</td><td>${l.magnitud}</td><td>${l.valor}</td>` +
            `<td>${l.calidad}</td></tr>`).join('');
        document.getElementById('estado').textContent =
            'Actualizado: ' + new Date().toLocaleTimeString() + ' (' + j.lecturas.length + ' filas)';
    } catch (e) {
        document.getElementById('estado').textContent = 'Sin conexion con /api/ultimas';
    }
}
setInterval(refrescar, 5000);
