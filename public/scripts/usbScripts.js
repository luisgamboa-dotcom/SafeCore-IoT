/* public/scripts/usbScripts.js — monitor en vivo por Wi-Fi (lee /api/ultimas) */
async function refreshUsbLive() {
    const dot = document.getElementById('usb-dot');
    const txt = document.getElementById('usb-status-text');
    const rows = document.getElementById('usb-rows');
    try {
        const r = await fetch('/api/ultimas?limit=12');
        const j = await r.json();
        if (!j.ok) throw new Error('respuesta no ok');
        dot.className = 'usb-dot on';
        txt.textContent = 'En vivo — última actualización: ' + new Date().toLocaleTimeString();
        rows.innerHTML = j.lecturas.map(l =>
            `<tr><td>${l.fecha_hora}</td><td>${l.codigo_serial}</td>` +
            `<td>${l.magnitud}</td><td>${l.valor} ${l.simbolo}</td><td>${l.calidad}</td></tr>`
        ).join('') || '<tr><td colspan="5">Sin lecturas aún.</td></tr>';
    } catch (e) {
        dot.className = 'usb-dot off';
        txt.textContent = 'Sin conexión con el servidor';
    }
}
refreshUsbLive();
setInterval(refreshUsbLive, 2000);
