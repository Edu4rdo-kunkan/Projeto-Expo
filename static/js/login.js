(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };

  // Tela de carregamento: some depois de um instante. Se algo travar, some mesmo assim.
  var splash = $('splash');
  function hideSplash() { if (splash) { splash.classList.add('out'); setTimeout(function () { splash.remove(); }, 600); } }
  var t0 = performance.now();
  function ready() { setTimeout(hideSplash, Math.max(0, 750 - (performance.now() - t0))); }
  if (document.readyState === 'complete') ready(); else window.addEventListener('load', ready);
  setTimeout(hideSplash, 4000);

  var form = $('login-form'), alertBox = $('login-alert');
  function showError(msg) {
    alertBox.textContent = '';
    var d = document.createElement('div'); d.className = 'alert err'; d.setAttribute('role', 'alert');
    d.innerHTML = '<svg class="ic"><use href="#i-alert"/></svg>';
    var s = document.createElement('span'); s.textContent = msg; d.appendChild(s);
    alertBox.appendChild(d);
  }

  // Mostrar / ocultar senha
  var pw = $('password'), tg = $('pw-toggle');
  tg.addEventListener('click', function () {
    var show = pw.type === 'password';
    pw.type = show ? 'text' : 'password';
    tg.setAttribute('aria-label', show ? 'Ocultar senha' : 'Mostrar senha');
    tg.querySelector('use').setAttribute('href', show ? '#i-eye-off' : '#i-eye');
    pw.focus();
  });

  form.addEventListener('submit', function (ev) {
    var u = $('username'), p = pw;
    u.classList.toggle('invalid', !u.value.trim());
    p.classList.toggle('invalid', !p.value);
    if (!u.value.trim() || !p.value) {
      ev.preventDefault();
      showError('Informe usuário e senha.');
      (u.value.trim() ? p : u).focus();
      return;
    }
    var b = $('login-btn');
    b.disabled = true;
    b.innerHTML = '<span class="spin"></span> Entrando…';
  });
})();
