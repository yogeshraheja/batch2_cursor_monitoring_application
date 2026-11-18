/**
 * Soft reload for overview / detail.
 * Uses GET via location.reload so refresh never re-POSTs forms.
 * Auth is the session cookie only — no tokens in the query string.
 */
(function () {
  // Meta refresh is the primary mechanism; this only avoids bfcache surprises.
  if (window.performance && performance.getEntriesByType) {
    var nav = performance.getEntriesByType("navigation")[0];
    if (nav && nav.type === "back_forward") {
      window.location.reload();
    }
  }
})();
