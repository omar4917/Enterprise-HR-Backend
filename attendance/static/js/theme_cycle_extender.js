(function () {
    const storageKey = "custom_theme_state";
    const states = ["django-light", "django-dark", "colorburst", "custom-dark"];

    function setDatasetTheme(mode) {
        if (mode !== "light" && mode !== "dark") {
            mode = "light";
        }
        document.documentElement.dataset.theme = mode;
        localStorage.setItem("theme", mode);
    }

    function applyState(state) {
        const body = document.body;
        body.classList.remove("theme-colorburst", "theme-customdark");
        if (state === "django-dark") {
            setDatasetTheme("dark");
        } else if (state === "colorburst") {
            setDatasetTheme("light");
            body.classList.add("theme-colorburst");
        } else if (state === "custom-dark") {
            setDatasetTheme("dark");
            body.classList.add("theme-customdark");
        } else {
            setDatasetTheme("light");
            state = "django-light";
        }
        localStorage.setItem(storageKey, state);
        updatePdfLinks(state);
        updateToggleLabels(state);
    }

    function nextState() {
        const current = localStorage.getItem(storageKey) || "django-light";
        const idx = states.indexOf(current);
        return states[(idx + 1) % states.length];
    }

    function updatePdfLinks(state) {
        const links = document.querySelectorAll('a[href*="pdf"]');
        links.forEach((link) => {
            const url = new URL(link.href, window.location.origin);
            url.searchParams.delete("theme");
            if (state === "django-dark") {
                url.searchParams.set("theme", "dark");
            } else if (state === "colorburst") {
                url.searchParams.set("theme", "colorburst");
            } else if (state === "custom-dark") {
                url.searchParams.set("theme", "customdark");
            }
            link.href = url.toString();
        });
        const bulkBtn = document.getElementById("bulk-pdf-link");
        if (bulkBtn) {
            const baseHref = bulkBtn.getAttribute("data-base-href");
            if (baseHref) {
                const baseUrl = new URL(baseHref, window.location.origin);
                baseUrl.searchParams.delete("theme");
                if (state === "django-dark") {
                    baseUrl.searchParams.set("theme", "dark");
                } else if (state === "colorburst") {
                    baseUrl.searchParams.set("theme", "colorburst");
                } else if (state === "custom-dark") {
                    baseUrl.searchParams.set("theme", "customdark");
                }
                const updated = baseUrl.toString();
                bulkBtn.setAttribute("data-base-href", updated);
                const currentHref = new URL(bulkBtn.href, window.location.origin);
                currentHref.searchParams.delete("theme");
                if (state === "django-dark") {
                    currentHref.searchParams.set("theme", "dark");
                } else if (state === "colorburst") {
                    currentHref.searchParams.set("theme", "colorburst");
                } else if (state === "custom-dark") {
                    currentHref.searchParams.set("theme", "customdark");
                }
                bulkBtn.href = currentHref.toString();
            }
        }
    }

    function updateToggleLabels(state) {
        const button = document.querySelector(".theme-toggle");
        if (!button) {
            return;
        }
        const label = {
            "django-light": "Toggle theme (current theme: light)",
            "django-dark": "Toggle theme (current theme: dark)",
            "colorburst": "Toggle theme (current theme: colorburst)",
            "custom-dark": "Toggle theme (current theme: custom dark)",
        }[state];
        if (!label) {
            return;
        }
        const liveRegion = button.querySelector(".visually-hidden.theme-label-when-auto");
        if (liveRegion) {
            liveRegion.textContent = label;
        }
    }

    function init() {
        const toggles = document.querySelectorAll(".theme-toggle");
        toggles.forEach((btn) => {
            btn.addEventListener("click", function (ev) {
                ev.preventDefault();
                const state = nextState();
                applyState(state);
            });
        });
        
        // Force colorburst theme (clear old settings)
        localStorage.removeItem(storageKey);
        applyState("colorburst");
    }

    document.addEventListener("DOMContentLoaded", init);
})();
