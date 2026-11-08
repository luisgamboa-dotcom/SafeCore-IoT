/* Menú móvil, sombra del header y scroll spy de la landing pública. */
(function () {
    "use strict";

    const header = document.getElementById("publicHeader");
    const toggle = document.getElementById("publicNavToggle");
    const closeBtn = document.getElementById("publicNavClose");
    const drawer = document.getElementById("publicNavDrawer");
    const backdrop = document.getElementById("publicNavBackdrop");

    if (!header || !toggle || !drawer || !backdrop) return;

    const setOpen = (open) => {
        drawer.classList.toggle("translate-x-full", !open);
        drawer.setAttribute("aria-hidden", String(!open));
        drawer.toggleAttribute("inert", !open);
        backdrop.classList.toggle("hidden", !open);
        toggle.setAttribute("aria-expanded", String(open));
        document.body.classList.toggle("nav-open", open);
    };

    const openNav = () => {
        setOpen(true);
        if (closeBtn) closeBtn.focus();
    };

    const closeNav = (restoreFocus) => {
        setOpen(false);
        if (restoreFocus !== false) toggle.focus();
    };

    toggle.addEventListener("click", openNav);
    if (closeBtn) closeBtn.addEventListener("click", () => closeNav(true));
    backdrop.addEventListener("click", () => closeNav(true));

    drawer.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => closeNav(false));
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !drawer.classList.contains("translate-x-full")) {
            closeNav(true);
        }
    });

    // Sombra del header al hacer scroll.
    const onScroll = () => {
        header.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    // Scroll spy: resalta la sección visible en la landing.
    const links = Array.from(document.querySelectorAll("[data-nav-section]"));
    const sections = links
        .map((link) => document.getElementById(link.dataset.navSection))
        .filter(Boolean);

    if (sections.length && "IntersectionObserver" in window) {
        const setActive = (id) => {
            links.forEach((link) => {
                const active = link.dataset.navSection === id;
                link.classList.toggle("is-active", active);
                if (active) link.setAttribute("aria-current", "true");
                else link.removeAttribute("aria-current");
            });
        };

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) setActive(entry.target.id);
                });
            },
            { rootMargin: "-45% 0px -50% 0px", threshold: 0 }
        );

        sections.forEach((section) => observer.observe(section));
    }
})();
