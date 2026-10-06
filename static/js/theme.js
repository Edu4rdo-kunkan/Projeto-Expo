/* Aplica o tema salvo (ou o do sistema) antes da página aparecer. */
(function () {
  var saved = null;
  try { saved = localStorage.getItem('ae-theme'); } catch (e) {}
  var dark = saved ? saved === 'dark' : window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  window.AETheme = {
    toggle: function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('ae-theme', next); } catch (e) {}
      window.dispatchEvent(new Event('themechange'));
      return next;
    }
  };
})();
