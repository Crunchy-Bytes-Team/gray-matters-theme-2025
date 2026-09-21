(() => {
  "use strict";

  const initFilters = () => {
    const panel = document.querySelector("[data-filter-panel]");
    const items = [...document.querySelectorAll("[data-filter-item]")];
    if (!panel || !items.length) return;

    const selects = [...panel.querySelectorAll("[data-filter]")];
    const params = new URLSearchParams(window.location.search);

    selects.forEach((select) => {
      const key = select.dataset.filter;
      const values = [...new Set(
        items.map((item) => item.getAttribute(`data-${key}`)).filter(Boolean)
      )]
        .sort((a, b) => a.localeCompare(b, "it"));
      values.forEach((value) => select.add(new Option(value, value)));
      select.value = params.get(key) || "";
    });

    const apply = (writeUrl = true) => {
      const active = Object.fromEntries(
        selects.filter((select) => select.value).map((select) => [select.dataset.filter, select.value])
      );
      let visible = 0;
      items.forEach((item) => {
        const matches = Object.entries(active).every(
          ([key, value]) => item.getAttribute(`data-${key}`) === value
        );
        item.hidden = !matches;
        if (matches) visible += 1;
      });
      const count = panel.querySelector("[data-filter-count]");
      if (count) count.textContent = `${visible} elementi visibili su ${items.length}`;
      if (writeUrl) {
        const next = new URLSearchParams();
        Object.entries(active).forEach(([key, value]) => next.set(key, value));
        const query = next.toString();
        history.replaceState(null, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
      }
    };

    selects.forEach((select) => select.addEventListener("change", () => apply()));
    panel.querySelector("[data-filter-reset]")?.addEventListener("click", () => {
      selects.forEach((select) => { select.value = ""; });
      apply();
    });
    panel.querySelector("[data-filter-toggle]")?.addEventListener("click", () => {
      panel.toggleAttribute("data-open");
    });
    window.addEventListener("popstate", () => {
      const current = new URLSearchParams(location.search);
      selects.forEach((select) => { select.value = current.get(select.dataset.filter) || ""; });
      apply(false);
    });
    apply(false);
  };

  const initTabs = () => {
    document.querySelectorAll("[data-tabs]").forEach((tabs) => {
      tabs.addEventListener("click", (event) => {
        const button = event.target.closest("[data-tab]");
        if (!button) return;
        tabs.querySelectorAll("[data-tab]").forEach((item) => {
          item.setAttribute("aria-selected", String(item === button));
        });
        tabs.querySelectorAll("[data-panel]").forEach((panel) => {
          panel.hidden = panel.dataset.panel !== button.dataset.tab;
        });
      });
    });
  };

  const initViewer = (viewer) => {
    const stage = viewer.querySelector("[data-view-stage]");
    const images = [...viewer.querySelectorAll(".image-layer img")];
    const zoom = viewer.querySelector("[data-zoom]");
    const slider = viewer.querySelector("[data-compare-slider]");
    if (!stage || !images.length) return;

    let scale = 1;
    let x = 0;
    let y = 0;
    let dragging = false;
    let startX = 0;
    let startY = 0;

    const transform = () => {
      images.forEach((image) => {
        image.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
      });
    };

    viewer.querySelectorAll("[data-view-mode]").forEach((button) => {
      button.addEventListener("click", () => {
        viewer.dataset.mode = button.dataset.viewMode;
        viewer.querySelectorAll("[data-view-mode]").forEach((item) => {
          item.setAttribute("aria-pressed", String(item === button));
        });
      });
    });

    zoom?.addEventListener("input", () => {
      scale = Number(zoom.value) / 100;
      transform();
    });
    slider?.addEventListener("input", () => {
      const preview = viewer.querySelector(".layer-preview");
      if (preview) preview.style.clipPath = `inset(0 0 0 ${slider.value}%)`;
    });
    viewer.querySelector("[data-reset-view]")?.addEventListener("click", () => {
      scale = 1; x = 0; y = 0;
      if (zoom) zoom.value = "100";
      transform();
    });

    stage.addEventListener("pointerdown", (event) => {
      if (event.target === slider) return;
      dragging = true;
      startX = event.clientX - x;
      startY = event.clientY - y;
      stage.setPointerCapture(event.pointerId);
    });
    stage.addEventListener("pointermove", (event) => {
      if (!dragging) return;
      x = event.clientX - startX;
      y = event.clientY - startY;
      transform();
    });
    stage.addEventListener("pointerup", () => { dragging = false; });
    stage.addEventListener("pointercancel", () => { dragging = false; });
    stage.addEventListener("wheel", (event) => {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      scale = Math.min(3, Math.max(.5, scale + (event.deltaY < 0 ? .1 : -.1)));
      if (zoom) zoom.value = String(Math.round(scale * 100));
      transform();
    }, { passive: false });
  };

  const init = () => {
    initFilters();
    initTabs();
    document.querySelectorAll("[data-viewer]").forEach(initViewer);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
