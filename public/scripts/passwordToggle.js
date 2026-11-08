/* Botón de mostrar/ocultar contraseña en login, registro y restablecer. */
(function () {
    "use strict";

    const ICON_HIDDEN = "visibility";
    const ICON_VISIBLE = "visibility_off";
    const LABEL_HIDDEN = "Mostrar contraseña";
    const LABEL_VISIBLE = "Ocultar contraseña";

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-password-toggle]");
        if (!button) return;

        const targetId = button.getAttribute("data-target");
        const input = targetId
            ? document.getElementById(targetId)
            : button.closest(".relative")?.querySelector("input");

        if (!input) return;

        const show = input.type === "password";
        input.type = show ? "text" : "password";
        button.setAttribute("aria-pressed", String(show));
        button.setAttribute("aria-label", show ? LABEL_VISIBLE : LABEL_HIDDEN);

        const icon = button.querySelector(".material-symbols-outlined");
        if (icon) icon.textContent = show ? ICON_VISIBLE : ICON_HIDDEN;

        // Mantiene el foco en el botón tras el clic.
        button.focus({ preventScroll: true });
    });
})();
