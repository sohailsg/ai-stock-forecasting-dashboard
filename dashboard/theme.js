/**
 * theme.js — shared light/dark theme. Respects prefers-color-scheme,
 * persists override in localStorage. Must load before page scripts so
 * charts pick up the right Chart.defaults colors.
 */
(function () {
  const KEY = "sd-theme";
  function preferred() {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === "light" || saved === "dark") return saved;
    } catch (e) { /* private mode */ }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function applyChartTheme() {
    if (!window.Chart) return;
    Chart.defaults.color = cssVar("--chart-tick") || "#667085";
    Chart.defaults.borderColor = cssVar("--chart-grid") || "rgba(16,24,40,0.08)";
    Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
  }
  function apply(theme) {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem(KEY, theme); } catch (e) { /* ignore */ }
    applyChartTheme();
    document.querySelectorAll("[data-theme-toggle]").forEach((btn) => {
      btn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      const label = btn.querySelector(".toggle-label");
      if (label) label.textContent = theme === "dark" ? "Light" : "Dark";
      else btn.textContent = theme === "dark" ? "☀ Light" : "🌙 Dark";
    });
  }
  window.__theme = {
    current: preferred(),
    apply,
    toggle() {
      this.current = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      apply(this.current);
      return this.current;
    },
  };
  apply(window.__theme.current);
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-theme-toggle]").forEach((btn) =>
      btn.addEventListener("click", () => {
        window.__theme.toggle();
        if (typeof window.__onThemeChange === "function") window.__onThemeChange();
      })
    );
  });
})();
