// HU-022: advertencia en vivo "No recibirás ninguna notificación."
function actualizarAdvertenciaCanales() {
    const toggles = document.querySelectorAll('input[data-toggle]');
    const advertencia = document.getElementById('advertenciaSinCanales');
    if (!toggles.length || !advertencia) return;
    const ninguno = Array.from(toggles).every(t => !t.checked);
    advertencia.classList.toggle('hidden', !ninguno);
}

document.querySelectorAll('input[data-toggle]')
    .forEach(t => t.addEventListener('change', actualizarAdvertenciaCanales));
actualizarAdvertenciaCanales();
