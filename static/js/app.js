(function () {
  'use strict';

  // Utilidades
  var body = document.body;
  var ROLE = body.dataset.role, IS_ADMIN = ROLE === 'admin', USER = body.dataset.user || '';
  var ESCOLA = body.dataset.escola || '', SIGLA = body.dataset.escolaSigla || ESCOLA;
  var $ = function (id) { return document.getElementById(id); };
  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function icon(name, cls) { return '<svg class="ic ' + (cls || '') + '" aria-hidden="true"><use href="#i-' + name + '"/></svg>'; }
  function dash(v) { return v ? esc(v) : '<span class="dim">—</span>'; }
  function fmtDate(s) { return s ? s.slice(8, 10) + '/' + s.slice(5, 7) + '/' + s.slice(0, 4) + ' às ' + s.slice(11, 16) : ''; }
  function plural(n, um, varios) { return n + ' ' + (n === 1 ? um : varios); }

  var SERIES = {
    '2A': { label: '2º Ano (2A)', short: '2A', icon: 'laptop' },
    '3A': { label: '3º Ano (3A)', short: '3A', icon: 'laptop' },
    'SETUPS': { label: 'Setups', short: 'Setups', icon: 'monitor' },
    'CARRINHOS': { label: 'Carrinhos', short: 'Carrinhos', icon: 'cart' },
    'TABLETS': { label: 'Tablets', short: 'Tablets', icon: 'tablet' },
    'TELEVISAO': { label: 'Televisão', short: 'TVs', icon: 'tv' }
  };
  var SERIES_ORDER = ['2A', '3A', 'SETUPS', 'CARRINHOS', 'TABLETS', 'TELEVISAO'];
  var TIPOS_PADRAO = ['Notebook', 'Tablet', 'Setup', 'Televisão'];
  function tipoIcon(tipo, serie) {
    var t = (tipo || '').toLowerCase();
    if (t.indexOf('tablet') >= 0) return 'tablet';
    if (t.indexOf('tele') >= 0 || t === 'tv') return 'tv';
    if (t.indexOf('setup') >= 0) return 'monitor';
    if (t.indexOf('note') >= 0) return 'laptop';
    return (SERIES[serie] || {}).icon || 'box';
  }

  // Notificações
  function toast(msg, type, ms) {
    type = type || 'info';
    var ic = { ok: 'check', bad: 'alert', warn: 'alert', info: 'info' }[type];
    var el = document.createElement('div');
    el.className = 'toast ' + type; el.setAttribute('role', type === 'bad' ? 'alert' : 'status');
    el.innerHTML = '<span class="t-ic">' + icon(ic, 'sm') + '</span><span class="t-msg">' + esc(msg) + '</span>';
    $('toasts').appendChild(el);
    function out() { el.classList.add('out'); setTimeout(function () { el.remove(); }, 260); }
    el.addEventListener('click', out);
    setTimeout(out, ms || (type === 'bad' ? 6000 : 3800));
  }

  // Comunicação com o servidor
  function ApiError(msg, status) { this.message = msg; this.status = status; }
  var sessionEnded = false;
  async function api(url, opts) {
    var o = Object.assign({ credentials: 'same-origin', headers: { 'Accept': 'application/json' } }, opts || {});
    if (o.body && typeof o.body !== 'string') { o.body = JSON.stringify(o.body); o.headers['Content-Type'] = 'application/json'; }
    var res;
    try { res = await fetch(url, o); }
    catch (e) { throw new ApiError('Sem conexão com o servidor. Verifique a rede e tente de novo.', 0); }
    if (res.status === 401) {
      if (!sessionEnded) {
        sessionEnded = true;
        toast('Sua sessão expirou. Faça login novamente.', 'warn', 4000);
        setTimeout(function () { location.href = '/login?expirada=1'; }, 1200);
      }
      throw new ApiError('Sua sessão expirou. Faça login novamente.', 401);
    }
    var data = null;
    try { data = await res.json(); } catch (e) { /* resposta sem JSON */ }
    if (!res.ok || (data && data.ok === false)) {
      throw new ApiError((data && data.msg) || 'Não foi possível concluir a operação. Tente novamente.', res.status);
    }
    return data;
  }

  // Janelas (modais)
  var modalStack = [];
  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])';
  function openModal(el) {
    el._opener = document.activeElement;
    el.classList.add('show');
    // O desfoque do fundo entra quando a janela termina de aparecer; assim a animação não trava.
    clearTimeout(el._blurT);
    el._blurT = setTimeout(function () { el.classList.add('blur'); }, 230);
    if (modalStack.indexOf(el) < 0) modalStack.push(el);
    body.style.overflow = 'hidden';
    setTimeout(function () {
      var f = el.querySelector('[autofocus],.modal-b input,.modal-b select') || el.querySelector(FOCUSABLE);
      if (f) f.focus();
    }, 30);
  }
  function closeModal(el) {
    if (el._cancel) { var c = el._cancel; el._cancel = null; c(); }
    clearTimeout(el._blurT);
    el.classList.remove('show', 'blur');
    modalStack = modalStack.filter(function (m) { return m !== el; });
    if (!modalStack.length) body.style.overflow = '';
    if (el._opener && el._opener.focus && document.contains(el._opener)) el._opener.focus();
    if (el.id === 'modal-detail') { detailItem = null; }
  }
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') {
      if (modalStack.length) closeModal(modalStack[modalStack.length - 1]);
      else if ($('chat').classList.contains('open')) toggleChat(false);
      else if (body.classList.contains('nav-open')) body.classList.remove('nav-open');
    }
    if (ev.key === 'Tab' && modalStack.length) {   // mantém o foco dentro da janela
      var items = Array.prototype.filter.call(modalStack[modalStack.length - 1].querySelectorAll(FOCUSABLE), function (n) { return n.offsetParent !== null; });
      if (!items.length) return;
      var first = items[0], last = items[items.length - 1];
      if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
      else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
    }
  });

  function confirmBox(opts) {
    return new Promise(function (resolve) {
      var ov = $('modal-confirm');
      $('confirm-box').innerHTML =
        '<div class="modal-h"><h2 id="confirm-title">' + esc(opts.title) + '</h2></div>' +
        '<div class="modal-b"><p>' + opts.message + '</p></div>' +
        '<div class="modal-f"><button class="btn btn-secondary" type="button" id="cf-no">Cancelar</button>' +
        '<button class="btn ' + (opts.danger ? 'btn-danger solid' : 'btn-primary') + '" type="button" id="cf-yes" autofocus>' + esc(opts.confirmText || 'Confirmar') + '</button></div>';
      var done = false;
      function end(v) { if (done) return; done = true; closeModal(ov); resolve(v); }
      $('cf-no').onclick = function () { end(false); };
      $('cf-yes').onclick = function () { end(true); };
      ov._cancel = function () { end(false); };
      openModal(ov);
    });
  }
  $('modal-confirm').addEventListener('click', function (e) { if (e.target === this && this._cancel) this._cancel(); });

  // Estado
  var state = {
    view: null, opcoes: { tipos: [], marcas: [], modelos: [], locais: [] },
    inv: { q: '', serie: '', tipo: '', local: '', situacao: '', criticidade: '', mochila: '', sort: '', dir: 'asc', page: 1, per_page: 15 },
    invBuilt: false, invFiltersOpen: false, invReq: 0, hist: { operacao: '', page: 1 }, histBuilt: false,
    pre: {}   // dados já pedidos ao servidor durante a abertura
  };
  var detailItem = null;

  async function carregarOpcoes(estrito) {
    try { state.opcoes = await api('/api/opcoes'); }
    catch (e) { if (estrito) throw e; /* senão mantém as opções anteriores */ }
  }

  // Navegação
  var VIEWS = {
    dashboard: { title: 'Painel', load: loadDashboard },
    inventario: { title: 'Inventário', load: loadInventario },
    estatisticas: { title: 'Estatísticas', load: loadEstatisticas },
    historico: { title: 'Histórico', load: loadHistorico },
    admin: { title: 'Administração', load: loadAdmin }
  };
  function routeFromHash() {
    var v = (location.hash.replace(/^#\/?/, '') || 'dashboard').split('?')[0];
    if (!VIEWS[v] || (v === 'admin' && !IS_ADMIN)) v = 'dashboard';
    return v;
  }
  function show(v) {
    state.view = v;
    document.querySelectorAll('.view').forEach(function (s) { s.classList.toggle('active', s.id === 'view-' + v); });
    document.querySelectorAll('.nav-item').forEach(function (n) { n.classList.toggle('active', n.dataset.view === v); });
    $('tb-title').textContent = VIEWS[v].title;
    $('tb-sub').textContent = '';
    document.title = VIEWS[v].title + ' · ' + SIGLA;
    body.classList.remove('nav-open');
    window.scrollTo(0, 0);
    VIEWS[v].load();
  }
  function go(v) {
    if (location.hash === '#/' + v) show(v); else location.hash = '#/' + v;
  }
  window.addEventListener('hashchange', function () { if (!sessionEnded) show(routeFromHash()); });
  function setSub(t) { if (state.view) $('tb-sub').textContent = t; }

  // Peças de interface reutilizáveis
  function errBox(msg, retry) {
    return '<div class="errbox" role="alert">' + icon('alert') + '<span style="flex:1">' + esc(msg) + '</span>' +
      '<button class="btn btn-sm btn-secondary" type="button" data-act="retry" data-view="' + retry + '">Tentar novamente</button></div>';
  }
  function emptyBox(ic, title, text, actionHtml) {
    return '<div class="empty"><div class="e-ic">' + icon(ic, 'lg') + '</div><h3>' + esc(title) + '</h3><p>' + esc(text) + '</p>' + (actionHtml || '') + '</div>';
  }
  function skelRows(n) {
    var h = '';
    for (var i = 0; i < n; i++) h += '<div class="sk-row"><div class="skeleton" style="width:38px;height:38px"></div><div class="skeleton" style="flex:2"></div><div class="skeleton" style="flex:1"></div><div class="skeleton" style="flex:1"></div></div>';
    return h;
  }
  function badgeSituacao(s) {
    if (s === 'Em uso') return '<span class="badge b-ok">Em uso</span>';
    if (s === 'Não em uso') return '<span class="badge b-warn">Não em uso</span>';
    return '<span class="dim">—</span>';
  }
  function badgeCrit(c) {
    if (c === 'Sim') return '<span class="badge b-bad">Crítico</span>';
    return '<span class="badge b-muted plain">' + esc(c || '—') + '</span>';
  }
  function tag(id, big) { return '<span class="tag' + (big ? ' big' : '') + '">' + esc(id) + '</span>'; }
  function countUp(el, n) {
    var suf = el.dataset.suffix || '';
    if (reduced || !n) { el.textContent = n + suf; return; }
    var t0 = null;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var p = Math.min((ts - t0) / 900, 1);
      el.textContent = Math.round(n * (1 - Math.pow(1 - p, 3))) + suf;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  function countAll(root) { root.querySelectorAll('[data-count]').forEach(function (el) { countUp(el, +el.dataset.count); }); }

  function kpi(opts) {
    var tagName = opts.go ? 'button' : 'div';
    return '<' + tagName + ' class="card kpi ' + (opts.cls || '') + '" type="' + (opts.go ? 'button' : '') + '"' +
      (opts.go ? ' data-act="go-filter" data-filter="' + esc(opts.go) + '"' : '') + '>' +
      '<span class="kpi-ic">' + icon(opts.icon, 'lg') + '</span><span style="min-width:0;flex:1">' +
      '<span class="kpi-label">' + esc(opts.label) + '</span><br>' +
      '<span class="kpi-value" data-count="' + opts.value + '"' + (opts.suffix ? ' data-suffix="' + opts.suffix + '"' : '') + '>0' + (opts.suffix || '') + '</span>' +
      '<span class="kpi-foot" style="display:block">' + esc(opts.foot || '') + '</span>' +
      (opts.bar != null ? '<span class="progress ' + (opts.barCls || '') + '" style="display:block"><i data-w="' + opts.bar + '"></i></span>' : '') +
      '</span></' + tagName + '>';
  }
  function animateBars(root) {
    requestAnimationFrame(function () { requestAnimationFrame(function () {
      root.querySelectorAll('.progress i[data-w]').forEach(function (i) { i.style.width = i.dataset.w + '%'; });
    }); });
  }

  var cid = 0;
  function chartCard(opts) {   // retorna { html, mount }
    var id = 'ch' + (++cid), items = opts.items || [];
    var total = items.reduce(function (s, i) { return s + i.total; }, 0);
    var inner;
    if (!items.length || (opts.needTotal !== false && !total)) {
      inner = '<div class="chart-empty">' + icon('info', 'lg') + '<span>' + esc(opts.emptyText || 'Ainda não há dados para este gráfico.') + '</span></div>';
    } else if (opts.kind === 'donut') {
      inner = '<div class="chart-split"><div class="chart-box"><canvas id="' + id + '" role="img" aria-label="' + esc(opts.title) + '"></canvas></div><div class="legend" id="' + id + 'l"></div></div>';
    } else {
      inner = '<div class="chart-box"><canvas id="' + id + '" role="img" aria-label="' + esc(opts.title) + '"></canvas></div>';
    }
    var html = '<div class="card' + (opts.cls ? ' ' + opts.cls : '') + '"><div class="card-h"><div><div class="card-title">' + esc(opts.title) + '</div>' +
      (opts.sub ? '<div class="card-sub">' + esc(opts.sub) + '</div>' : '') + '</div>' + (opts.head || '') + '</div><div class="card-b">' + inner + '</div></div>';
    return {
      html: html,
      mount: function () {
        var cv = $(id); if (!cv) return;
        var ch = Charts[opts.kind](cv, items, { centerLabel: opts.center, pct: opts.pct, height: opts.height });
        if (opts.kind === 'donut') Charts.legend($(id + 'l'), items, ch, {});
      }
    };
  }
  function listaRank(items, total) {
    if (!items.length) return '<div class="chart-empty"><span>Sem dados.</span></div>';
    return '<ol class="rank">' + items.map(function (i) {
      return '<li><span class="rname">' + esc(i.chave) + '</span><span class="rval">' + i.total + '</span><span class="rsub">' + (total ? Math.round(i.total * 100 / total) : 0) + '%</span></li>';
    }).join('') + '</ol>';
  }
  function serieItems(d) {
    return d.por_serie.map(function (s) { return { chave: s.chave, short: (SERIES[s.id] || {}).short || s.chave, total: s.total }; });
  }

  // Painel
  function skelDash() {
    return '<div class="grid grid-kpi">' + [1, 2, 3, 4].map(function () { return '<div class="card kpi"><div class="skeleton" style="width:46px;height:46px;border-radius:13px"></div><div style="flex:1"><div class="skeleton" style="height:12px;width:60%"></div><div class="skeleton" style="height:26px;width:40%;margin-top:8px"></div></div></div>'; }).join('') +
      '</div><div class="grid grid-2">' + [1, 2].map(function () { return '<div class="card"><div class="card-b"><div class="skeleton" style="height:230px"></div></div></div>'; }).join('') + '</div>';
  }
  async function loadDashboard() {
    var root = $('root-dashboard');
    if (!root.dataset.ready) root.innerHTML = skelDash();
    try {
      var d = await (state.pre.dashboard || api('/api/dashboard'));
      delete state.pre.dashboard;
      if (state.view !== 'dashboard') return;
      renderDashboard(root, d); root.dataset.ready = '1';
    } catch (e) { if (e.status !== 401) root.innerHTML = errBox(e.message, 'dashboard'); }
  }
  function histTexto(h) {
    var nome = ((h.tipo || 'equipamento') + ' ' + h.id_computer).trim();
    if (h.operacao === 'criacao') return { t: 'Cadastrou ' + nome, ic: 'plus', cls: 'criacao' };
    if (h.operacao === 'exclusao') return { t: 'Excluiu ' + nome, ic: 'trash', cls: 'exclusao' };
    return { t: 'Alterou ' + (h.campo || 'dados').toLowerCase() + ' de ' + nome, ic: 'edit', cls: 'edicao' };
  }
  function renderDashboard(root, d) {
    setSub(d.total ? 'Visão geral de ' + plural(d.total, 'equipamento', 'equipamentos') : 'Nenhum equipamento cadastrado');
    if (!d.total) {
      root.innerHTML = emptyBox('box', 'Nenhum equipamento cadastrado', IS_ADMIN ? 'Cadastre o primeiro equipamento para ver o painel ganhar vida.' : 'Quando houver equipamentos cadastrados, o painel aparecerá aqui.',
        IS_ADMIN ? '<button class="btn btn-primary" type="button" data-act="new">' + icon('plus', 'sm') + 'Novo ativo</button>' : '');
      return;
    }
    var cards = [];
    var sit = chartCard({ kind: 'donut', title: 'Situação dos equipamentos', sub: 'Em uso e guardados', items: d.por_situacao, center: 'equipamentos' });
    var tip = chartCard({ kind: 'donut', title: 'Tipos de equipamento', sub: 'O que existe no inventário', items: d.por_tipo, center: 'equipamentos' });
    var loc = chartCard({ kind: 'hbar', title: 'Equipamentos por local', sub: 'Onde estão distribuídos', items: d.por_local, cls: '' });
    var ser = chartCard({ kind: 'vbar', title: 'Equipamentos por categoria', sub: 'Quantidade em cada grupo', items: serieItems(d), height: 250 });
    var crit = d.criticos
      ? chartCard({ kind: 'hbar', title: 'Equipamentos críticos', sub: 'Por tipo', items: d.criticos_por_tipo })
      : { html: '<div class="card"><div class="card-h"><div><div class="card-title">Equipamentos críticos</div><div class="card-sub">Por tipo</div></div></div><div class="card-b"><div class="chart-empty">' + icon('check', 'lg') + '<span>Nenhum equipamento está marcado como crítico.</span></div></div></div>', mount: function () {} };
    cards = [sit, tip, loc, ser, crit];

    var recentes = d.recentes.length
      ? '<div class="mini-list">' + d.recentes.map(function (h) {
        var x = histTexto(h);
        return '<div class="mini-item"><span class="mi-dot tl-dot ' + x.cls + '" style="width:32px;height:32px">' + icon(x.ic, 'sm') + '</span><div><div class="mi-t">' + esc(x.t) + '</div><div class="mi-m">' + esc(h.usuario) + ' · ' + fmtDate(h.criado_em) + '</div></div></div>';
      }).join('') + '</div>'
      : '<div class="chart-empty">' + icon('clock', 'lg') + '<span>Nenhuma alteração registrada ainda.</span></div>';

    root.innerHTML =
      '<div class="grid grid-kpi">' +
      kpi({ icon: 'box', label: 'Total de ativos', value: d.total, foot: 'cadastrados no sistema', go: 'all' }) +
      kpi({ icon: 'pulse', cls: 'k-ok', label: 'Em uso', value: d.em_uso, foot: d.pct_em_uso + '% do total', go: 'situacao=Em uso' }) +
      kpi({ icon: 'clock', cls: 'k-warn', label: 'Não em uso', value: d.nao_em_uso, foot: d.pct_nao_em_uso + '% do total', go: 'situacao=Não em uso' }) +
      kpi({ icon: 'flag', cls: 'k-bad', label: 'Críticos', value: d.criticos, foot: d.criticos ? d.pct_criticos + '% do total' : 'nenhum marcado', go: 'criticidade=Sim' }) +
      '</div>' +
      '<div class="grid grid-2">' + sit.html + tip.html + '</div>' +
      '<div class="grid grid-32">' + loc.html +
      '<div class="card"><div class="card-h"><div><div class="card-title">Últimas alterações</div><div class="card-sub">O que mudou por último</div></div>' +
      '<button class="btn btn-sm btn-secondary" type="button" data-act="nav" data-view="historico">Ver tudo</button></div><div class="card-b">' + recentes + '</div></div></div>' +
      '<div class="grid grid-2">' + ser.html + crit.html + '</div>';
    cards.forEach(function (c) { c.mount(); });
    countAll(root);
  }

  // Estatísticas
  async function loadEstatisticas() {
    var root = $('root-estatisticas');
    if (!root.dataset.ready) root.innerHTML = skelDash();
    try {
      var d = await api('/api/estatisticas');
      if (state.view !== 'estatisticas') return;
      renderStats(root, d); root.dataset.ready = '1';
    } catch (e) { if (e.status !== 401) root.innerHTML = errBox(e.message, 'estatisticas'); }
  }
  function renderStats(root, d) {
    setSub('Números e percentuais sempre atualizados');
    if (!d.total) { root.innerHTML = emptyBox('chart', 'Sem dados para analisar', 'As estatísticas aparecem assim que houver equipamentos cadastrados.'); return; }
    var sit = chartCard({ kind: 'donut', title: 'Distribuição por situação', sub: 'Quanto do parque está em uso', items: d.por_situacao, center: 'equipamentos' });
    var cri = chartCard({ kind: 'donut', title: 'Distribuição por criticidade', sub: 'Quais equipamentos não podem faltar', items: d.por_criticidade, center: 'equipamentos' });
    var tip = chartCard({ kind: 'hbar', title: 'Ranking por tipo', sub: 'Do mais comum ao menos comum', items: d.por_tipo, pct: true });
    var loc = chartCard({ kind: 'hbar', title: 'Ranking por local', sub: 'Onde há mais equipamentos', items: d.por_local, pct: true });
    var ser = chartCard({ kind: 'vbar', title: 'Equipamentos por categoria', sub: 'Quantidade em cada grupo', items: serieItems(d), height: 380 });
    root.innerHTML =
      '<div class="grid grid-kpi">' +
      kpi({ icon: 'box', label: 'Total de ativos', value: d.total, foot: 'no inventário' }) +
      kpi({ icon: 'pulse', cls: 'k-ok', label: 'Percentual em uso', suffix: '%', value: Math.round(d.pct_em_uso), foot: d.em_uso + ' de ' + d.total + ' equipamentos', bar: d.pct_em_uso, barCls: 'ok' }) +
      kpi({ icon: 'clock', cls: 'k-warn', label: 'Percentual não em uso', suffix: '%', value: Math.round(d.pct_nao_em_uso), foot: d.nao_em_uso + ' de ' + d.total + ' equipamentos', bar: d.pct_nao_em_uso, barCls: 'warn' }) +
      kpi({ icon: 'flag', cls: 'k-bad', label: 'Percentual crítico', suffix: '%', value: Math.round(d.pct_criticos), foot: d.criticos + ' de ' + d.total + ' equipamentos', bar: d.pct_criticos, barCls: 'bad' }) +
      '</div>' +
      '<div class="grid grid-2">' + sit.html + cri.html + '</div>' +
      '<div class="grid grid-2">' + tip.html + loc.html + '</div>' +
      '<div class="grid grid-32">' + ser.html +
      '<div class="grid" style="gap:18px;align-content:start">' +
      '<div class="card"><div class="card-h"><div><div class="card-title">Locais com mais equipamentos</div><div class="card-sub">Os três primeiros</div></div></div><div class="card-b">' + listaRank(d.top_locais, d.total) + '</div></div>' +
      '<div class="card"><div class="card-h"><div><div class="card-title">Tipos mais comuns</div><div class="card-sub">Os três primeiros</div></div></div><div class="card-b">' + listaRank(d.top_tipos, d.total) + '</div></div>' +
      '</div></div>';
    [sit, cri, tip, loc, ser].forEach(function (c) { c.mount(); });
    countAll(root); animateBars(root);
  }

  // Inventário
  function opts(list, sel, first) {
    return '<option value="">' + esc(first) + '</option>' + list.map(function (v) {
      return '<option value="' + esc(v) + '"' + (v === sel ? ' selected' : '') + '>' + esc(v) + '</option>';
    }).join('');
  }
  function flabel(k) {   // rótulo do filtro: curto no celular, descritivo no desktop
    var curto = window.innerWidth < 640;
    return { tipo: curto ? 'Tipo' : 'Tipo: todos', local: curto ? 'Local' : 'Local: todos', situacao: curto ? 'Situação' : 'Situação: todas',
      criticidade: curto ? 'Criticidade' : 'Criticidade: todas', mochila: curto ? 'Mochila' : 'Mochila: todas' }[k];
  }
  var FILTROS = [['serie', 'Categoria'], ['tipo', 'Tipo'], ['local', 'Local'], ['situacao', 'Situação'], ['criticidade', 'Criticidade'], ['mochila', 'Mochila']];
  var ORDENAR_POR = [['', 'Padrão (categoria e ID)'], ['id_computer', 'ID do equipamento'], ['serie_id', 'Categoria'], ['tipo', 'Tipo'], ['marca', 'Marca'],
    ['modelo', 'Modelo'], ['owner_1', 'Responsável'], ['local', 'Local'], ['situacao', 'Situação'], ['criticidade', 'Criticidade']];
  function buildInventario(root) {
    var f = state.inv, aberto = state.invFiltersOpen;
    var chips = '<button class="chip' + (!f.serie ? ' active' : '') + '" type="button" data-act="serie" data-serie="">Todas</button>' +
      SERIES_ORDER.map(function (s) {
        return '<button class="chip' + (f.serie === s ? ' active' : '') + '" type="button" data-act="serie" data-serie="' + s + '">' + icon(SERIES[s].icon, 'sm') + esc(SERIES[s].label) + '</button>';
      }).join('');
    root.innerHTML =
      '<div class="card"><div class="toolbar">' +
      '<div class="tool-row"><div class="search">' + icon('search') + '<input class="input" id="inv-q" type="search" placeholder="' + (window.innerWidth < 640 ? 'Buscar equipamentos…' : 'Buscar por ID, responsável, marca, modelo, local…') + '" value="' + esc(f.q) + '" aria-label="Buscar equipamentos" autocomplete="off"></div>' +
      '<button class="btn btn-secondary filter-toggle" type="button" id="filter-toggle" data-act="toggle-filters" aria-expanded="' + aberto + '" aria-controls="filter-panel">' +
      icon('filter', 'sm') + '<span>Filtros</span><span class="fbadge" id="filter-badge" hidden>0</span>' + icon('chevron', 'sm caret') + '</button>' +
      (IS_ADMIN ? '<button class="btn btn-secondary" type="button" data-act="export" id="inv-export">' + icon('down', 'sm') + 'Exportar Excel</button>' : '') + '</div>' +
      '<div class="active-filters" id="active-filters"></div>' +
      '<div class="filter-panel' + (aberto ? ' open' : '') + '" id="filter-panel"><div class="filter-panel-in"><div class="filter-card">' +
      '<div><div class="fgroup-label">Categoria</div><div class="chips" id="inv-chips">' + chips + '</div></div>' +
      '<div><div class="fgroup-label">Detalhes</div><div class="filters">' +
      '<select class="select" id="f-tipo" aria-label="Filtrar por tipo">' + opts(state.opcoes.tipos, f.tipo, flabel('tipo')) + '</select>' +
      '<select class="select" id="f-local" aria-label="Filtrar por local">' + opts(state.opcoes.locais, f.local, flabel('local')) + '</select>' +
      '<select class="select" id="f-situacao" aria-label="Filtrar por situação">' + opts(['Em uso', 'Não em uso'], f.situacao, flabel('situacao')) + '</select>' +
      '<select class="select" id="f-criticidade" aria-label="Filtrar por criticidade">' + opts(['Sim', 'Nenhuma', 'Não'], f.criticidade, flabel('criticidade')) + '</select>' +
      '<select class="select" id="f-mochila" aria-label="Filtrar por mochila">' + opts(['Sim', 'Não'], f.mochila, flabel('mochila')) + '</select></div></div>' +
      '<div><div class="fgroup-label">Ordenação</div><div class="filters sort-row">' +
      '<select class="select" id="f-sort" aria-label="Ordenar por">' + ORDENAR_POR.map(function (o) { return '<option value="' + o[0] + '"' + (o[0] === f.sort ? ' selected' : '') + '>' + esc(o[0] ? 'Ordenar por: ' + o[1] : o[1]) + '</option>'; }).join('') + '</select>' +
      '<select class="select" id="f-dir" aria-label="Sentido da ordenação"><option value="asc"' + (f.dir !== 'desc' ? ' selected' : '') + '>Crescente (A a Z)</option><option value="desc"' + (f.dir === 'desc' ? ' selected' : '') + '>Decrescente (Z a A)</option></select></div></div>' +
      '<div class="filter-actions"><button class="btn btn-secondary btn-sm" type="button" data-act="clear-filters">Limpar filtros</button>' +
      '<button class="btn btn-primary btn-sm" type="button" data-act="toggle-filters">Pronto</button></div>' +
      '</div></div></div></div>' +
      '<div class="result-line" id="inv-result"></div>' +
      '<div id="inv-table" class="tbl-cards"></div><div id="inv-pager"></div></div>';
    state.invBuilt = true;
    updateFilterUI();
  }
  // Mostra quantos filtros estão ligados e uma etiqueta removível para cada um.
  function updateFilterUI() {
    var f = state.inv, ativos = FILTROS.filter(function (x) { return f[x[0]]; });
    var badge = $('filter-badge'), btn = $('filter-toggle'), box = $('active-filters');
    if (badge) { badge.hidden = !ativos.length; badge.textContent = ativos.length; }
    if (btn) btn.classList.toggle('on', ativos.length > 0);
    if (!box) return;
    box.innerHTML = ativos.map(function (x) {
      var v = x[0] === 'serie' ? ((SERIES[f.serie] || {}).label || f.serie) : f[x[0]];
      return '<button class="fchip" type="button" data-act="rm-filter" data-key="' + x[0] + '" aria-label="Remover filtro ' + esc(x[1] + ': ' + v) + '">' + esc(x[1] + ': ' + v) + icon('x') + '</button>';
    }).join('') + (ativos.length > 1 ? '<button class="link-btn" type="button" data-act="clear-filters">Limpar tudo</button>' : '');
  }
  function toggleFilters(abrir) {
    state.invFiltersOpen = typeof abrir === 'boolean' ? abrir : !state.invFiltersOpen;
    var p = $('filter-panel'), b = $('filter-toggle');
    if (p) p.classList.toggle('open', state.invFiltersOpen);
    if (b) b.setAttribute('aria-expanded', String(state.invFiltersOpen));
  }
  function syncInvControls() {
    var f = state.inv;
    ['tipo', 'local', 'situacao', 'criticidade', 'mochila', 'sort', 'dir'].forEach(function (k) {
      var el = $('f-' + k); if (el) el.value = f[k] || (k === 'dir' ? 'asc' : '');
    });
    var q = $('inv-q'); if (q && q.value !== f.q) q.value = f.q;
    document.querySelectorAll('#inv-chips .chip').forEach(function (c) { c.classList.toggle('active', c.dataset.serie === f.serie); });
    updateFilterUI();
  }
  function refreshFilterOptions() {
    var f = state.inv;
    if (!state.invBuilt) return;
    $('f-tipo').innerHTML = opts(state.opcoes.tipos, f.tipo, flabel('tipo'));
    $('f-local').innerHTML = opts(state.opcoes.locais, f.local, flabel('local'));
  }
  async function loadInventario() {
    var root = $('root-inventario');
    if (!state.invBuilt) { buildInventario(root); $('inv-table').innerHTML = skelRows(6); }
    else { refreshFilterOptions(); syncInvControls(); }
    setSub('Busque, filtre e abra qualquer equipamento');
    await fetchInventario();
  }
  function hasFilters() {
    var f = state.inv; return !!(f.q || f.serie || f.tipo || f.local || f.situacao || f.criticidade || f.mochila);
  }
  async function fetchInventario(keepScroll) {
    var req = ++state.invReq, f = state.inv, qs = new URLSearchParams();
    Object.keys(f).forEach(function (k) { if (f[k] !== '' && f[k] != null) qs.set(k, f[k]); });
    var box = $('inv-table'); if (!box) return;
    updateFilterUI();
    box.style.opacity = box.dataset.has ? '.55' : '1';
    try {
      var r = await api('/api/ativos?' + qs.toString());
      if (req !== state.invReq) return;      // resposta antiga: ignora
      box.style.opacity = '1';
      renderInvTable(r);
    } catch (e) {
      if (req !== state.invReq || e.status === 401) return;
      box.style.opacity = '1';
      box.innerHTML = errBox(e.message, 'inventario'); $('inv-pager').innerHTML = ''; $('inv-result').innerHTML = '';
    }
  }
  function th(label, key, extra) {
    var f = state.inv, on = f.sort === key;
    return '<th class="' + (extra ? extra + ' ' : '') + (on ? 'sorted' : '') + '" aria-sort="' + (on ? (f.dir === 'desc' ? 'descending' : 'ascending') : 'none') + '"><button type="button" data-act="sort" data-sort="' + key + '">' + label + '<span class="arr">' + (on ? (f.dir === 'desc' ? '▼' : '▲') : '↕') + '</span></button></th>';
  }
  function renderInvTable(r) {
    var box = $('inv-table'); box.dataset.has = '1';
    $('inv-result').innerHTML = '<span>' + (r.total === r.total_geral
      ? 'Mostrando <b>' + r.items.length + '</b> de <b>' + r.total + '</b> equipamentos'
      : '<b>' + r.total + '</b> de ' + r.total_geral + ' equipamentos correspondem à busca') + '</span>';
    if (!r.items.length) {
      box.innerHTML = hasFilters()
        ? emptyBox('search', 'Nenhum equipamento encontrado', 'Nada corresponde a essa busca ou a esses filtros. Tente outros termos ou limpe os filtros.', '<button class="btn btn-secondary" type="button" data-act="clear-filters">Limpar filtros</button>')
        : emptyBox('box', 'Nenhum equipamento cadastrado', IS_ADMIN ? 'Cadastre o primeiro equipamento do inventário.' : 'Ainda não há equipamentos cadastrados.', IS_ADMIN ? '<button class="btn btn-primary" type="button" data-act="new">' + icon('plus', 'sm') + 'Novo ativo</button>' : '');
      $('inv-pager').innerHTML = ''; return;
    }
    var rows = r.items.map(function (a) {
      var pessoas = a.owner_1 || a.owner_2
        ? '<span class="people"><span>' + dash(a.owner_1) + '</span>' + (a.owner_2 ? '<span>' + esc(a.owner_2) + '</span>' : '') + '</span>'
        : '<span class="dim">—</span>';
      return '<tr data-id="' + a.id + '" tabindex="0" aria-label="Abrir equipamento ' + esc(a.id_computer) + '">' +
        '<td class="td-eq" data-label="Equipamento"><div class="eq"><span class="eq-ic">' + icon(tipoIcon(a.tipo, a.serie_id)) + '</span><div class="eq-main">' + tag(a.id_computer) +
        '<span class="eq-sub">' + esc([a.tipo, a.marca, a.modelo].filter(Boolean).join(' · ')) + '</span></div></div></td>' +
        '<td data-label="Categoria"><span class="badge b-info plain" title="' + esc(a.serie_rotulo) + '">' + esc((SERIES[a.serie_id] || {}).short || a.serie_rotulo) + '</span></td>' +
        '<td data-label="Responsáveis">' + pessoas + '</td>' +
        '<td data-label="Local">' + dash(a.local) + '</td>' +
        '<td data-label="Situação">' + badgeSituacao(a.situacao) + '</td>' +
        '<td class="col-mochila" data-label="Mochila">' + dash(a.mochila) + '</td>' +
        '<td data-label="Criticidade">' + badgeCrit(a.criticidade) + '</td>' +
        '<td class="td-act" data-label="Ações"><div class="row-actions">' +
        '<button class="icon-btn" type="button" data-act="open" data-id="' + a.id + '" aria-label="Ver detalhes de ' + esc(a.id_computer) + '" title="Ver detalhes">' + icon('eye') + '</button>' +
        '<button class="icon-btn" type="button" data-act="qr" data-id="' + a.id + '" aria-label="QR Code de ' + esc(a.id_computer) + '" title="QR Code">' + icon('qr') + '</button>' +
        (IS_ADMIN ? '<button class="icon-btn" type="button" data-act="edit" data-id="' + a.id + '" aria-label="Editar ' + esc(a.id_computer) + '" title="Editar">' + icon('edit') + '</button>' +
          '<button class="icon-btn danger" type="button" data-act="delete" data-id="' + a.id + '" aria-label="Excluir ' + esc(a.id_computer) + '" title="Excluir">' + icon('trash') + '</button>' : '') +
        '</div></td></tr>';
    }).join('');
    box.innerHTML = '<div class="table-wrap"><table class="tbl"><thead><tr>' +
      th('Equipamento', 'id_computer') + th('Categoria', 'serie_id') + th('Responsáveis', 'owner_1') + th('Local', 'local') +
      th('Situação', 'situacao') + th('Mochila', 'mochila', 'col-mochila') + th('Criticidade', 'criticidade') + '<th></th></tr></thead><tbody>' + rows + '</tbody></table></div>';
    $('inv-pager').innerHTML = r.pages > 1
      ? '<div class="pager"><span>Página <b>' + r.page + '</b> de ' + r.pages + '</span><div class="pager-btns">' +
        '<button class="btn btn-sm btn-secondary" type="button" data-act="page" data-page="' + (r.page - 1) + '"' + (r.page <= 1 ? ' disabled' : '') + '>Anterior</button>' +
        '<button class="btn btn-sm btn-secondary" type="button" data-act="page" data-page="' + (r.page + 1) + '"' + (r.page >= r.pages ? ' disabled' : '') + '>Próxima</button></div></div>'
      : '';
  }
  function irParaInventario(filtros) {
    Object.keys(state.inv).forEach(function (k) { if (['sort', 'dir', 'per_page'].indexOf(k) < 0) state.inv[k] = k === 'page' ? 1 : ''; });
    Object.assign(state.inv, filtros || {}, { page: 1 });
    if (state.view === 'inventario') { syncInvControls(); fetchInventario(); } else go('inventario');
  }
  var qTimer = null;
  document.addEventListener('input', function (ev) {
    if (ev.target.id === 'inv-q') {
      clearTimeout(qTimer);
      qTimer = setTimeout(function () { state.inv.q = ev.target.value.trim(); state.inv.page = 1; fetchInventario(); }, 250);
    }
  });
  document.addEventListener('change', function (ev) {
    var m = /^f-(tipo|local|situacao|criticidade|mochila|sort|dir)$/.exec(ev.target.id || '');
    if (m) { state.inv[m[1]] = ev.target.value; state.inv.page = 1; fetchInventario(); }
    if (ev.target.id === 'h-op') { state.hist.operacao = ev.target.value; state.hist.page = 1; fetchHistorico(); }
  });

  // Detalhes do equipamento
  async function openDetail(id, tab) {
    try {
      var r = await api('/api/ativos/' + id);
      detailItem = r.item;
      renderDetail(tab || 'detalhes');
      openModal($('modal-detail'));
    } catch (e) { if (e.status !== 401) toast(e.status === 404 ? 'Equipamento não encontrado. Ele pode ter sido excluído.' : e.message, 'bad'); }
  }
  function dl(pairs) {
    return '<dl class="dl">' + pairs.map(function (p) {
      return '<div class="dl-item"><dt>' + esc(p[0]) + '</dt><dd>' + (p[1] ? esc(p[1]) : '<span class="dim">—</span>') + '</dd></div>';
    }).join('') + '</dl>';
  }
  function renderDetail(tab) {
    var a = detailItem; if (!a) return;
    var titulo = [a.tipo, a.marca, a.modelo].filter(Boolean).join(' ') || 'Equipamento';
    $('detail-box').innerHTML =
      '<div class="modal-h"><div class="det-head">' + tag(a.id_computer, true) + '<h2 id="detail-title">' + esc(titulo) + '</h2>' +
      '<div class="det-badges"><span class="badge b-info plain">' + esc(a.serie_rotulo) + '</span>' + badgeSituacao(a.situacao) + (a.criticidade === 'Sim' ? badgeCrit('Sim') : '') + '</div></div>' +
      '<button class="icon-btn" type="button" data-close aria-label="Fechar">' + icon('x') + '</button></div>' +
      '<div class="tabs" role="tablist">' +
      [['detalhes', 'Detalhes', 'info'], ['qr', 'QR Code', 'qr'], ['historico', 'Histórico', 'clock']].map(function (t) {
        return '<button class="tab-btn' + (tab === t[0] ? ' active' : '') + '" type="button" role="tab" aria-selected="' + (tab === t[0]) + '" data-act="tab" data-tab="' + t[0] + '">' + icon(t[2], 'sm') + t[1] + '</button>';
      }).join('') + '</div>' +
      '<div class="modal-b" id="detail-body"></div>' +
      '<div class="modal-f">' + (IS_ADMIN ? '<div class="left"><button class="btn btn-danger" type="button" data-act="delete" data-id="' + a.id + '">' + icon('trash', 'sm') + 'Excluir</button></div>' +
        '<button class="btn btn-secondary" type="button" data-act="edit" data-id="' + a.id + '">' + icon('edit', 'sm') + 'Editar</button>' : '') +
      '<button class="btn ' + (IS_ADMIN ? 'btn-primary' : 'btn-secondary') + '" type="button" data-close>Fechar</button></div>';
    var b = $('detail-body');
    if (tab === 'detalhes') {
      b.innerHTML =
        '<div class="det-sec"><h3>' + icon('box', 'sm') + 'Equipamento</h3>' + dl([['Categoria', a.serie_rotulo], ['Tipo', a.tipo], ['Marca', a.marca], ['Modelo', a.modelo], ['ID do equipamento', a.id_computer], ['Carregador', a.id_carregator]]) + '</div>' +
        '<div class="det-sec"><h3>' + icon('user', 'sm') + 'Responsáveis</h3>' + dl([['Responsável 1', a.owner_1], ['Responsável 2', a.owner_2]]) + '</div>' +
        '<div class="det-sec"><h3>' + icon('pulse', 'sm') + 'Local e situação</h3>' + dl([['Local', a.local], ['Situação', a.situacao], ['Mochila', a.mochila], ['Criticidade', a.criticidade]]) + '</div>';
    } else if (tab === 'qr') {
      renderQrTab(b, a);
    } else {
      b.innerHTML = '<div class="loading-note"><span class="spin"></span>Carregando histórico…</div>';
      loadDetailHist(b, a.id);
    }
  }
  function qrUrl(a) { return location.origin + '/equipamento/' + a.id; }
  function renderQrTab(b, a) {
    var url = qrUrl(a), local = /^(localhost|127\.|0\.0\.0\.0)/.test(location.hostname);
    b.innerHTML = '<div class="qr-box"><div class="qr-frame"><canvas id="qr-canvas" role="img" aria-label="QR Code do equipamento ' + esc(a.id_computer) + '"></canvas></div>' +
      '<div class="qr-url">' + esc(url) + '</div>' +
      '<div class="qr-actions"><button class="btn btn-primary" type="button" data-act="qr-download">' + icon('down', 'sm') + 'Baixar PNG</button>' +
      '<button class="btn btn-secondary" type="button" data-act="qr-print">' + icon('print', 'sm') + 'Imprimir</button></div>' +
      (local ? '<div class="note">' + icon('info', 'sm') + '<span>Você está abrindo o sistema por localhost. Para o QR funcionar em outros aparelhos, acesse pelo endereço de rede ou pelo domínio publicado.</span></div>' : '') +
      '<p class="card-sub">Ao escanear, o sistema abre os detalhes deste equipamento (é preciso entrar antes).</p></div>';
    try { QR.toCanvas($('qr-canvas'), url, { scale: 10, margin: 2 }); }
    catch (e) { b.innerHTML = '<div class="errbox">' + icon('alert') + '<span>Não foi possível gerar o QR Code: ' + esc(e.message) + '</span></div>'; }
  }
  function qrDownload() {
    var a = detailItem, c = $('qr-canvas'); if (!a || !c) return;
    c.toBlob(function (blob) {
      var l = document.createElement('a'); l.href = URL.createObjectURL(blob);
      l.download = 'qrcode-' + a.id_computer.replace(/[^\w\-]+/g, '_') + '-' + a.serie_id + '.png';
      document.body.appendChild(l); l.click(); l.remove(); setTimeout(function () { URL.revokeObjectURL(l.href); }, 2000);
      toast('QR Code baixado.', 'ok');
    });
  }
  function qrPrint() {
    var a = detailItem, c = $('qr-canvas'); if (!a || !c) return;
    var area = $('print-area'); area.textContent = '';
    var cv = document.createElement('canvas'); cv.width = c.width; cv.height = c.height; cv.getContext('2d').drawImage(c, 0, 0);
    var esc_ = document.createElement('div'); esc_.className = 'p-escola'; esc_.textContent = ESCOLA;
    var id = document.createElement('div'); id.className = 'p-id'; id.textContent = a.id_computer;
    var sub = document.createElement('div'); sub.className = 'p-sub'; sub.textContent = [a.tipo, a.marca, a.modelo].filter(Boolean).join(' ') + (a.local ? ' · ' + a.local : '');
    var u = document.createElement('div'); u.className = 'p-url'; u.textContent = qrUrl(a);
    area.append(esc_, id, cv, sub, u);
    window.print();
  }
  async function loadDetailHist(b, id) {
    try {
      var r = await api('/api/historico?ativo_id=' + id + '&per_page=50');
      if (!detailItem || detailItem.id !== id) return;
      b.innerHTML = r.items.length ? timeline(r.items, false) : emptyBox('clock', 'Sem alterações registradas', 'Mudanças feitas neste equipamento aparecerão aqui.');
    } catch (e) { if (e.status !== 401) b.innerHTML = errBox(e.message, 'x').replace(/<button.*<\/button>/, ''); }
  }
  function timeline(items, withLink) {
    return '<ul class="timeline">' + items.map(function (h) {
      var x = histTexto(h), change = '';
      if (h.operacao === 'edicao') change = '<div class="tl-change"><span class="old">' + (esc(h.valor_anterior) || 'vazio') + '</span> → <span class="new">' + (esc(h.valor_novo) || 'vazio') + '</span></div>';
      else if (h.operacao === 'criacao') change = '<div class="tl-change">' + esc(h.valor_novo) + '</div>';
      else change = '<div class="tl-change">' + esc(h.valor_anterior) + '</div>';
      var titulo = withLink ? esc(x.t) : (h.operacao === 'edicao' ? 'Alterou ' + esc((h.campo || '').toLowerCase()) : h.operacao === 'criacao' ? 'Cadastro do equipamento' : 'Exclusão do equipamento');
      var link = withLink && h.existe ? ' <button class="link-btn" type="button" data-act="open" data-id="' + h.ativo_id + '">Abrir</button>' : '';
      return '<li class="tl-item"><span class="tl-dot ' + x.cls + '">' + icon(x.ic, 'sm') + '</span><div class="tl-body"><div class="tl-title">' + titulo + link + '</div>' + change +
        '<div class="tl-meta">' + esc(h.usuario || 'sistema') + ' · ' + fmtDate(h.criado_em) + '</div></div></li>';
    }).join('') + '</ul>';
  }

  // Formulário (cadastro / edição)
  var REQ = ['serie_id', 'tipo', 'id_computer', 'marca', 'modelo', 'local', 'situacao', 'criticidade'];
  function fld(label, name, inner, req) {
    return '<div class="field"><label for="f_' + name + '">' + esc(label) + (req ? ' <span class="req" aria-hidden="true">*</span>' : '') + '</label>' + inner + '<span class="field-err" id="e_' + name + '" hidden></span></div>';
  }
  function inp(name, v, ph, list) {
    return '<input class="input" id="f_' + name + '" name="' + name + '" value="' + esc(v) + '" placeholder="' + esc(ph || '') + '" maxlength="120" autocomplete="off"' + (list ? ' list="dl_' + name + '"' : '') + '>';
  }
  function sel(name, list, v, first) {
    return '<select class="select" id="f_' + name + '" name="' + name + '">' + (first ? '<option value="">' + esc(first) + '</option>' : '') +
      list.map(function (o) { var val = Array.isArray(o) ? o[0] : o, lab = Array.isArray(o) ? o[1] : o; return '<option value="' + esc(val) + '"' + (val === v ? ' selected' : '') + '>' + esc(lab) + '</option>'; }).join('') + '</select>';
  }
  function dlist(name, arr) { return '<datalist id="dl_' + name + '">' + arr.map(function (v) { return '<option value="' + esc(v) + '">'; }).join('') + '</datalist>'; }

  async function openForm(id) {
    if (!IS_ADMIN) return;
    var a = null;
    if (id) {
      try { a = (await api('/api/ativos/' + id)).item; }
      catch (e) { if (e.status !== 401) toast(e.message, 'bad'); return; }
    }
    var v = a || { serie_id: '', owner_1: '', owner_2: '', id_computer: '', id_carregator: '', tipo: '', marca: '', modelo: '', local: '', situacao: 'Em uso', mochila: '', criticidade: 'Nenhuma' };
    var tipos = state.opcoes.tipos.slice();
    TIPOS_PADRAO.forEach(function (t) { if (tipos.indexOf(t) < 0) tipos.push(t); });
    $('form-box').innerHTML =
      '<form id="asset-form" novalidate><div class="modal-h"><h2 id="form-title">' + (a ? 'Editar equipamento' : 'Novo ativo') + '</h2>' +
      '<button class="icon-btn" type="button" data-close aria-label="Fechar">' + icon('x') + '</button></div>' +
      '<div class="modal-b"><div class="form-grid">' +
      '<div class="form-sec">Identificação</div>' +
      fld('Categoria', 'serie_id', sel('serie_id', SERIES_ORDER.map(function (s) { return [s, SERIES[s].label]; }), v.serie_id, 'Selecione…'), true) +
      fld('Tipo', 'tipo', sel('tipo', tipos, v.tipo, 'Selecione…'), true) +
      fld('ID do equipamento', 'id_computer', inp('id_computer', v.id_computer, 'Ex.: 07'), true) +
      fld('Carregador', 'id_carregator', inp('id_carregator', v.id_carregator, 'Ex.: 38')) +
      fld('Marca', 'marca', inp('marca', v.marca, 'Ex.: Positivo', true) + dlist('marca', state.opcoes.marcas), true) +
      fld('Modelo', 'modelo', inp('modelo', v.modelo, 'Ex.: Master N8440', true) + dlist('modelo', state.opcoes.modelos), true) +
      '<div class="form-sec">Responsáveis</div>' +
      fld('Responsável 1', 'owner_1', inp('owner_1', v.owner_1, 'Nome')) +
      fld('Responsável 2', 'owner_2', inp('owner_2', v.owner_2, 'Nome (opcional)')) +
      '<div class="form-sec">Local e situação</div>' +
      fld('Local', 'local', inp('local', v.local, 'Ex.: Sala Maker', true) + dlist('local', state.opcoes.locais), true) +
      fld('Situação', 'situacao', sel('situacao', ['Em uso', 'Não em uso'], v.situacao), true) +
      fld('Mochila', 'mochila', sel('mochila', [['Sim', 'Sim'], ['Não', 'Não'], ['N/A', 'Não se aplica']], v.mochila, 'Não informada')) +
      fld('Criticidade', 'criticidade', sel('criticidade', ['Nenhuma', 'Sim', 'Não'], v.criticidade), true) +
      '<div class="form-msg" id="form-msg" hidden></div></div></div>' +
      '<div class="modal-f"><button class="btn btn-secondary" type="button" data-close>Cancelar</button>' +
      '<button class="btn btn-primary" type="submit" id="form-save">' + (a ? 'Salvar alterações' : 'Cadastrar') + '</button></div></form>';
    var form = $('asset-form');
    form.addEventListener('submit', function (ev) { ev.preventDefault(); saveForm(a ? a.id : null); });
    form.addEventListener('input', function (ev) { ev.target.classList && ev.target.classList.remove('invalid'); var e = $('e_' + ev.target.name); if (e) e.hidden = true; });
    openModal($('modal-form'));
  }
  async function saveForm(id) {
    var form = $('asset-form'), data = {}, bad = [];
    new FormData(form).forEach(function (val, k) { data[k] = String(val).trim(); });
    REQ.forEach(function (k) {
      var el = $('f_' + k), er = $('e_' + k), miss = !data[k];
      el.classList.toggle('invalid', miss);
      er.hidden = !miss; if (miss) { er.textContent = 'Campo obrigatório.'; bad.push(el); }
    });
    var msg = $('form-msg');
    if (bad.length) { msg.hidden = false; msg.textContent = 'Preencha os campos obrigatórios marcados em vermelho.'; bad[0].focus(); return; }
    msg.hidden = true;
    var btn = $('form-save'), old = btn.innerHTML;
    btn.disabled = true; btn.classList.add('loading'); btn.innerHTML = '<span class="spin"></span> Salvando…';
    try {
      var r = await api(id ? '/api/ativos/' + id : '/api/ativos', { method: id ? 'PUT' : 'POST', body: data });
      toast(r.msg, r.alteracoes === 0 ? 'info' : 'ok');
      closeModal($('modal-form'));
      await afterChange(id || r.id);
    } catch (e) {
      if (e.status === 401) return;
      msg.hidden = false; msg.textContent = e.message;
      btn.disabled = false; btn.classList.remove('loading'); btn.innerHTML = old;
    }
  }
  async function afterChange(focusId) {
    await carregarOpcoes();
    ['dashboard', 'estatisticas', 'historico', 'admin'].forEach(function (v) { var r = $('root-' + v); if (r && v !== state.view) delete r.dataset.ready; });
    if (state.view) VIEWS[state.view].load();
    if ($('modal-detail').classList.contains('show') && focusId) {
      try { detailItem = (await api('/api/ativos/' + focusId)).item; var t = document.querySelector('#detail-box .tab-btn.active'); renderDetail(t ? t.dataset.tab : 'detalhes'); } catch (e) { /* removido */ }
    }
  }
  async function deleteAsset(id) {
    var a = detailItem && detailItem.id === id ? detailItem : null;
    if (!a) { try { a = (await api('/api/ativos/' + id)).item; } catch (e) { toast(e.message, 'bad'); return; } }
    var ok = await confirmBox({
      title: 'Excluir equipamento?', danger: true, confirmText: 'Excluir',
      message: 'Você vai excluir o equipamento <strong>' + esc(a.id_computer) + '</strong> (' + esc([a.tipo, a.marca, a.modelo].filter(Boolean).join(' ')) + '). Essa ação não pode ser desfeita, mas o registro da exclusão fica no histórico.'
    });
    if (!ok) return;
    try {
      var r = await api('/api/ativos/' + id, { method: 'DELETE' });
      toast(r.msg, 'ok');
      closeModal($('modal-detail'));
      await afterChange(null);
    } catch (e) { if (e.status !== 401) toast(e.message, 'bad'); }
  }

  // Histórico
  async function loadHistorico() {
    var root = $('root-historico');
    if (!state.histBuilt) {
      root.innerHTML = '<div class="card"><div class="toolbar"><div class="tool-row"><select class="select" id="h-op" aria-label="Filtrar por tipo de alteração" style="max-width:260px">' +
        '<option value="">Todas as alterações</option><option value="criacao">Cadastros</option><option value="edicao">Edições</option><option value="exclusao">Exclusões</option></select></div></div>' +
        '<div class="card-b" id="hist-list" style="padding-top:4px"></div><div id="hist-pager"></div></div>';
      state.histBuilt = true;
    }
    setSub('Quem mudou o quê, e quando');
    $('hist-list').innerHTML = skelRows(5);
    await fetchHistorico();
  }
  async function fetchHistorico() {
    var h = state.hist, qs = new URLSearchParams({ page: h.page, per_page: 25 });
    if (h.operacao) qs.set('operacao', h.operacao);
    try {
      var r = await api('/api/historico?' + qs.toString());
      $('hist-list').innerHTML = r.items.length ? timeline(r.items, true)
        : emptyBox('clock', 'Nenhuma alteração registrada', h.operacao ? 'Não há registros desse tipo. Tente outro filtro.' : 'Cadastros, edições e exclusões aparecerão aqui.');
      $('hist-pager').innerHTML = r.pages > 1
        ? '<div class="pager"><span>Página <b>' + r.page + '</b> de ' + r.pages + ' · ' + r.total + ' registros</span><div class="pager-btns">' +
          '<button class="btn btn-sm btn-secondary" type="button" data-act="hpage" data-page="' + (r.page - 1) + '"' + (r.page <= 1 ? ' disabled' : '') + '>Anterior</button>' +
          '<button class="btn btn-sm btn-secondary" type="button" data-act="hpage" data-page="' + (r.page + 1) + '"' + (r.page >= r.pages ? ' disabled' : '') + '>Próxima</button></div></div>' : '';
    } catch (e) { if (e.status !== 401) $('hist-list').innerHTML = errBox(e.message, 'historico'); }
  }

  // Administração
  async function loadAdmin() {
    var root = $('root-admin'); setSub('Exportação e informações do sistema');
    if (!root.dataset.ready) root.innerHTML = '<div class="card"><div class="card-b">' + skelRows(3) + '</div></div>';
    try {
      var d = await api('/api/admin/info');
      if (state.view !== 'admin') return;
      root.dataset.ready = '1';
      root.innerHTML =
        '<div class="grid grid-2"><div class="card"><div class="card-h"><div><div class="card-title">Exportar dados</div><div class="card-sub">Baixe todos os equipamentos em uma planilha</div></div></div>' +
        '<div class="card-b"><p style="margin-bottom:16px;color:var(--muted)">Gera o arquivo <b>relatorio_ativos.xlsx</b> com os dados atuais, pronto para filtrar e imprimir.</p>' +
        '<button class="btn btn-primary" type="button" data-act="export" id="adm-export">' + icon('down', 'sm') + 'Exportar Excel</button></div></div>' +
        '<div class="card"><div class="card-h"><div><div class="card-title">Informações do sistema</div><div class="card-sub">Estado atual do banco</div></div></div><div class="card-b"><div class="kv">' +
        '<div class="kv-row"><span>Escola</span><span>' + esc(d.escola || ESCOLA) + '</span></div>' +
        '<div class="kv-row"><span>Equipamentos cadastrados</span><span>' + d.total_ativos + '</span></div>' +
        '<div class="kv-row"><span>Registros no histórico</span><span>' + d.total_historico + '</span></div>' +
        '<div class="kv-row"><span>Tamanho do banco</span><span>' + d.tamanho_banco_kb + ' KB</span></div>' +
        '<div class="kv-row"><span>Assistente</span><span>' + (d.assistente_ia ? 'Conversa livre ativada' : 'Modo offline (regras)') + '</span></div></div></div></div></div>' +
        '<div class="grid grid-2"><div class="card"><div class="card-h"><div><div class="card-title">Contas de administrador</div><div class="card-sub">Quem pode alterar o inventário</div></div></div><div class="card-b"><div class="kv">' +
        d.usuarios.map(function (u) { return '<div class="kv-row"><span style="display:flex;gap:10px;align-items:center"><span class="avatar" style="width:30px;height:30px;font-size:13px">' + esc(u[0].toUpperCase()) + '</span>' + esc(u) + '</span><span>' + (u.toLowerCase() === USER.toLowerCase() ? '<span class="badge b-ok plain">Você</span>' : '') + '</span></div>'; }).join('') +
        '</div></div></div>' +
        '<div class="card"><div class="card-h"><div><div class="card-title">Segurança</div><div class="card-sub">Como as contas são protegidas</div></div></div><div class="card-b"><div class="kv">' +
        '<div class="kv-row"><span>Senhas</span><span>' + (d.senhas_por_ambiente ? 'Definidas por variável de ambiente' : 'Padrão do projeto (troque)') + '</span></div>' +
        '<div class="kv-row"><span>Sessão</span><span>Expira em 8 horas</span></div>' +
        '<div class="kv-row"><span>Permissões</span><span>Validadas no servidor</span></div></div>' +
        (d.senhas_por_ambiente ? '' : '<div class="note" style="margin-top:14px">' + icon('info', 'sm') + '<span>Defina a variável <b>ADMIN_USERS</b> no servidor para trocar as senhas sem editar o código.</span></div>') +
        '</div></div></div>';
    } catch (e) { if (e.status !== 401) root.innerHTML = errBox(e.message, 'admin'); }
  }
  async function exportar(btn) {
    var old = btn ? btn.innerHTML : '';
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Gerando…'; }
    try {
      var res = await fetch('/exportar', { credentials: 'same-origin' });
      if (res.status === 401) { await api('/api/me'); return; }
      if (!res.ok) { var j = null; try { j = await res.json(); } catch (e) { } throw new Error((j && j.msg) || 'Não foi possível gerar a planilha.'); }
      var blob = await res.blob(), l = document.createElement('a');
      l.href = URL.createObjectURL(blob); l.download = 'relatorio_ativos.xlsx';
      document.body.appendChild(l); l.click(); l.remove(); setTimeout(function () { URL.revokeObjectURL(l.href); }, 2000);
      toast('Planilha exportada com sucesso.', 'ok');
    } catch (e) { if (e.status !== 401) toast(e.message || 'Falha na exportação.', 'bad'); }
    finally { if (btn) { btn.disabled = false; btn.innerHTML = old; } }
  }

  // Assistente (chatbot)
  var chatStarted = false, chatBusy = false;
  var chatHist = [], chatCtx = null;   // conversa já feita e filtros da última pergunta
  var IA = body.dataset.ia === '1';
  function rich(text) {
    return esc(text).replace(/^\s*[-*] /gm, '• ').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  }
  function addMsg(text, who, items, links) {
    var m = document.createElement('div'); m.className = 'msg ' + who;
    if (who === 'bot') {
      m.innerHTML = rich(text);
      if (items && items.length) {
        var w = document.createElement('div'); w.className = 'msg-items';
        items.forEach(function (it) { var t = document.createElement('button'); t.type = 'button'; t.className = 'tag'; t.textContent = it.label; t.dataset.act = 'open'; t.dataset.id = it.id; w.appendChild(t); });
        m.appendChild(w);
      }
      if (links && links.length) {
        var wl = document.createElement('div'); wl.className = 'msg-items msg-links';
        links.forEach(function (l) {
          var b = document.createElement('button'); b.type = 'button'; b.className = 'link-chip'; b.textContent = l.label;
          b.dataset.act = 'chat-go'; b.dataset.go = JSON.stringify(l); wl.appendChild(b);
        });
        m.appendChild(wl);
      }
    } else m.textContent = text;
    var box = $('chat-msgs'); box.appendChild(m); box.scrollTop = box.scrollHeight;
  }
  function setSuggestions(list) {
    $('chat-sugg').innerHTML = (list || []).map(function (s) { return '<button type="button" data-act="ask" data-q="' + esc(s) + '">' + esc(s) + '</button>'; }).join('');
  }
  function toggleChat(open) {
    var c = $('chat'); c.hidden = false;
    c.classList.toggle('open', open); $('chat-fab').hidden = open;
    if (!open) { c.hidden = true; return; }
    if (!chatStarted) {
      chatStarted = true;
      if (IA) {
        c.querySelector('.chat-h small').textContent = 'Converse do seu jeito';
        $('chat-input').placeholder = 'Escreva sua mensagem…';
      }
      addMsg(IA
        ? 'Olá! Sou o assistente de ativos da ' + (SIGLA || 'escola') + '. Pode conversar comigo do seu jeito: tiro dúvidas sobre o sistema e consulto os equipamentos com dados reais.'
        : 'Olá! Sou o assistente de ativos da ' + (SIGLA || 'escola') + '. Conto e listo equipamentos, digo onde cada um está, explico o sistema e converso um pouco. Pergunte do seu jeito!', 'bot');
      setSuggestions(IA
        ? ['Faça um resumo dos equipamentos', 'Quais locais têm mais equipamentos?', 'Tem algum equipamento crítico?', 'Como cadastro um equipamento?']
        : ['Faça um resumo dos equipamentos', 'Quantos notebooks estão em uso?', 'Qual local tem mais equipamentos?', 'Como cadastrar?', 'Me conta uma curiosidade']);
    }
    setTimeout(function () { $('chat-input').focus(); }, 60);
  }
  async function ask(text) {
    text = (text || '').trim(); if (!text || chatBusy) return;
    chatBusy = true; addMsg(text, 'me'); $('chat-input').value = '';
    var typing = document.createElement('div'); typing.className = 'typing'; typing.innerHTML = '<i></i><i></i><i></i>';
    $('chat-msgs').appendChild(typing); $('chat-msgs').scrollTop = 1e6;
    try {
      var r = await api('/api/chatbot', { method: 'POST', body: { message: text, history: chatHist.slice(-8), contexto: chatCtx } });
      typing.remove(); addMsg(r.reply, 'bot', r.items, r.links); setSuggestions(r.suggestions);
      chatHist.push({ role: 'user', content: text }, { role: 'assistant', content: r.reply });
      if (chatHist.length > 16) chatHist = chatHist.slice(-16);
      chatCtx = r.contexto || chatCtx;
    } catch (e) { typing.remove(); if (e.status !== 401) addMsg('Não consegui consultar o sistema agora. ' + e.message, 'bot'); }
    finally { chatBusy = false; }
  }

  // Eventos globais
  document.addEventListener('click', function (ev) {
    var closer = ev.target.closest('[data-close]');
    if (closer) { var ov = closer.closest('.overlay'); if (ov) closeModal(ov); return; }
    if (ev.target.classList && ev.target.classList.contains('overlay') && ev.target.id !== 'modal-confirm') { closeModal(ev.target); return; }
    var el = ev.target.closest('[data-act]');
    if (!el) {
      var tr = ev.target.closest('tr[data-id]');
      if (tr && tr.closest('#root-inventario')) openDetail(+tr.dataset.id);
      var nv = ev.target.closest('.nav-item'); if (nv) go(nv.dataset.view);
      return;
    }
    var act = el.dataset.act, id = el.dataset.id ? +el.dataset.id : null;
    switch (act) {
      case 'open': openDetail(id); break;
      case 'qr': openDetail(id, 'qr'); break;
      case 'edit': openForm(id); break;
      case 'delete': deleteAsset(id); break;
      case 'new': openForm(null); break;
      case 'tab': renderDetail(el.dataset.tab); break;
      case 'qr-download': qrDownload(); break;
      case 'qr-print': qrPrint(); break;
      case 'sort':
        if (state.inv.sort === el.dataset.sort) state.inv.dir = state.inv.dir === 'asc' ? 'desc' : 'asc';
        else { state.inv.sort = el.dataset.sort; state.inv.dir = 'asc'; }
        state.inv.page = 1; fetchInventario(); break;
      case 'page': state.inv.page = +el.dataset.page; fetchInventario().then(function () { var t = $('inv-result'); if (t) t.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' }); }); break;
      case 'hpage': state.hist.page = +el.dataset.page; fetchHistorico(); break;
      case 'serie': state.inv.serie = el.dataset.serie; state.inv.page = 1; syncInvControls(); fetchInventario(); break;
      case 'toggle-filters': toggleFilters(); break;
      case 'rm-filter': state.inv[el.dataset.key] = ''; state.inv.page = 1; syncInvControls(); fetchInventario(); break;
      case 'clear-filters':
        ['q', 'serie', 'tipo', 'local', 'situacao', 'criticidade', 'mochila'].forEach(function (k) { state.inv[k] = ''; });
        state.inv.page = 1; syncInvControls(); fetchInventario(); break;
      case 'go-filter':
        var f = {}; if (el.dataset.filter && el.dataset.filter !== 'all') { var p = el.dataset.filter.split('='); f[p[0]] = p[1]; } irParaInventario(f); break;
      case 'nav': go(el.dataset.view); break;
      case 'retry': VIEWS[el.dataset.view] ? VIEWS[el.dataset.view].load() : null; break;
      case 'export': exportar(el); break;
      case 'ask': ask(el.dataset.q); break;
      case 'chat-go':
        try {
          var dest = JSON.parse(el.dataset.go);
          if (window.innerWidth <= 640) toggleChat(false);
          if (dest.filtro) irParaInventario(dest.filtro); else if (dest.view) go(dest.view);
        } catch (e) { /* atalho inválido: ignora */ }
        break;
    }
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Enter') {
      var tr = ev.target.closest && ev.target.closest('tr[data-id]');
      if (tr && ev.target === tr) openDetail(+tr.dataset.id);
    }
  });

  // Inicialização
  function setThemeIcon() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    $('theme-btn').innerHTML = icon(dark ? 'sun' : 'moon');
    $('theme-btn').setAttribute('aria-label', dark ? 'Mudar para o tema claro' : 'Mudar para o tema escuro');
  }
  function bindShell() {
    $('menu-btn').addEventListener('click', function () { body.classList.toggle('nav-open'); });
    $('scrim').addEventListener('click', function () { body.classList.remove('nav-open'); });
    $('theme-btn').addEventListener('click', function () { AETheme.toggle(); setThemeIcon(); });
    var nb = $('new-btn'); if (nb) nb.addEventListener('click', function () { openForm(null); });
    $('chat-fab').addEventListener('click', function () { toggleChat(true); });
    $('chat-close').addEventListener('click', function () { toggleChat(false); });
    $('chat-form').addEventListener('submit', function (ev) { ev.preventDefault(); ask($('chat-input').value); });
    window.addEventListener('afterprint', function () { $('print-area').textContent = ''; });
    setThemeIcon();
  }

  var splash = $('splash'), t0 = performance.now();
  function setSplashMsg(t) { $('splash-msg').textContent = t; }
  function hideSplash() {
    var wait = Math.max(0, 700 - (performance.now() - t0));
    setTimeout(function () { splash.classList.add('out'); setTimeout(function () { splash.hidden = true; }, 600); }, wait);
  }
  async function init() {
    splash.classList.remove('failed', 'out'); splash.hidden = false;
    try {
      setSplashMsg('Carregando equipamentos…');
      if (routeFromHash() === 'dashboard') {
        state.pre.dashboard = api('/api/dashboard');
        state.pre.dashboard.catch(function () { });
      }
      await carregarOpcoes(true);
      $('app').hidden = false; $('chat-fab').hidden = false;
      if (!init.bound) { bindShell(); init.bound = true; }
      show(routeFromHash());
      var abrir = body.dataset.open;
      if (abrir) { openDetail(+abrir); history.replaceState(null, '', '/' + location.hash); body.dataset.open = ''; }
      hideSplash();
    } catch (e) {
      if (e.status === 401) return;
      $('splash-err-msg').textContent = e.message || 'Não foi possível carregar o sistema.';
      splash.classList.add('failed');
    }
  }
  $('splash-retry').addEventListener('click', init);
  init();
})();
