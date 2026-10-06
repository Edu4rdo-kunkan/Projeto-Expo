/* Gráficos em canvas: rosquinha, barras horizontais e barras verticais.
   Sem bibliotecas externas, funciona offline. */
(function (root) {
  'use strict';

  var PALETTE = ['#3D5AFE', '#12B5A6', '#FFB020', '#FF6B57', '#8B5CF6', '#38BDF8', '#E879A9', '#84CC16'];
  var SEMANTIC = { 'Em uso': '#12B981', 'Não em uso': '#FFB020', 'Sim': '#FF5A67', 'Não': '#8B93B8', 'Nenhuma': '#3D5AFE' };
  var ROW = 48;

  var charts = [];
  var tipEl = null;
  var theme = null;

  // Respeita a opção "reduzir movimento" do sistema; fora isso, sempre anima.
  var reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var animar = !reduced;
  var DURACAO = 950;

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function ease(t) { return 1 - Math.pow(1 - t, 3); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // Cores e fonte são lidas uma vez e guardadas, em vez de a cada quadro.
  function getTheme() {
    if (!theme) {
      var cs = getComputedStyle(document.documentElement);
      var v = function (n) { return cs.getPropertyValue(n).trim(); };
      theme = {
        text: v('--text'), muted: v('--muted'), track: v('--surface-2'), line: v('--line'),
        font: getComputedStyle(document.body).fontFamily
      };
    }
    return theme;
  }

  function shade(hex, amt) {
    var n = parseInt(hex.replace('#', ''), 16);
    var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    function f(c) { return Math.round(amt >= 0 ? c + (255 - c) * amt : c * (1 + amt)); }
    return 'rgb(' + f(r) + ',' + f(g) + ',' + f(b) + ')';
  }
  function colorOf(item, i, opts) {
    return item.color || (opts.colorFor && opts.colorFor(item, i)) || SEMANTIC[item.chave] || PALETTE[i % PALETTE.length];
  }

  /* Tooltip */
  function showTip(html, x, y) {
    if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'chart-tip'; document.body.appendChild(tipEl); }
    tipEl.innerHTML = html; tipEl.classList.add('show');
    var w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    tipEl.style.left = clamp(x + 14, 8, window.innerWidth - w - 8) + 'px';
    tipEl.style.top = clamp(y - h - 12, 8, window.innerHeight - h - 8) + 'px';
  }
  function hideTip() { if (tipEl) tipEl.classList.remove('show'); }

  /* Agendador: um único requestAnimationFrame para todos os gráficos */
  var emAnimacao = [], rafAnim = 0, sujos = [], rafSujo = 0;

  function tick(ts) {
    rafAnim = 0;
    var prox = [];
    emAnimacao.forEach(function (c) {
      if (!c.canvas.isConnected) return;
      if (c.t0 === null) c.t0 = ts;
      c.p = clamp((ts - c.t0) / DURACAO, 0, 1);
      c.paint();
      if (c.p < 1) prox.push(c);
    });
    emAnimacao = prox;
    if (emAnimacao.length) rafAnim = requestAnimationFrame(tick);
  }
  function iniciar(c) {
    if (!animar) { c.p = 1; c.paint(); return; }
    c.t0 = null; c.p = 0;
    if (emAnimacao.indexOf(c) < 0) emAnimacao.push(c);
    if (!rafAnim) rafAnim = requestAnimationFrame(tick);
  }
  function redesenhar(c) {   // pede um novo desenho no próximo quadro (hover, redimensionar)
    if (c.p < 1) return;
    if (sujos.indexOf(c) < 0) sujos.push(c);
    if (rafSujo) return;
    rafSujo = requestAnimationFrame(function () {
      rafSujo = 0;
      var lista = sujos; sujos = [];
      lista.forEach(function (x) { if (x.canvas.isConnected) x.paint(); });
    });
  }

  /* Canvas: só redimensiona quando o tamanho realmente muda */
  function prep(c, h) {
    var canvas = c.canvas;
    if (!c.w) c.w = canvas.parentElement.clientWidth;
    var w = Math.max(c.w, 120);
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pw = Math.round(w * dpr), ph = Math.round(h * dpr);
    if (canvas.width !== pw || canvas.height !== ph) { canvas.width = pw; canvas.height = ph; }
    if (c.hAplicada !== h) { canvas.style.height = h + 'px'; c.hAplicada = h; }
    var ctx = c.ctx || (c.ctx = canvas.getContext('2d'));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx: ctx, w: w, h: h };
  }

  function roundRect(ctx, x, y, w, h, r) {
    r = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
  }
  function fit(c, ctx, text, maxW) {
    if (text.length * 12 <= maxW) return text;   // cabe com folga, não precisa medir
    var k = text + '|' + Math.round(maxW) + '|' + c.fonteAtual;
    if (c.fitCache[k] !== undefined) return c.fitCache[k];
    var t = text;
    if (ctx.measureText(t).width > maxW) {
      while (t.length > 1 && ctx.measureText(t + '…').width > maxW) t = t.slice(0, -1);
      t += '…';
    }
    c.fitCache[k] = t;
    return t;
  }

  /* Gráfico */
  function Chart(canvas, items, opts, kind) {
    if (canvas._chart) canvas._chart.destroy();
    this.canvas = canvas; this.items = items || []; this.opts = opts || {}; this.kind = kind;
    this.fonteAtual = ''; this.p = 0; this.t0 = null; this.hover = -1; this.geo = null; this.w = 0; this.fitCache = {};
    canvas._chart = this;
    var self = this;

    // Reserva a altura antes de desenhar, para a página não "pular" depois.
    var alturaFixa = kind === 'donut' ? (this.opts.size || 210)
      : kind === 'hbar' ? Math.max(this.items.length, 1) * ROW + 4 : (this.opts.height || 250);
    canvas.style.height = alturaFixa + 'px'; this.hAplicada = alturaFixa;

    this.onMove = function (ev) {
      var r = canvas.getBoundingClientRect();
      var pt = ev.touches ? ev.touches[0] : ev;
      var i = self.hit(pt.clientX - r.left, pt.clientY - r.top);
      if (i !== self.hover) {
        self.hover = i; redesenhar(self);
        if (self.opts.onHover) self.opts.onHover(i);
      }
      if (i >= 0) self.tip(i, pt.clientX, pt.clientY); else hideTip();
    };
    this.onLeave = function () {
      if (self.hover !== -1) { self.hover = -1; redesenhar(self); if (self.opts.onHover) self.opts.onHover(-1); }
      hideTip();
    };
    this.onEnd = function () { setTimeout(self.onLeave, 1600); };
    canvas.addEventListener('mousemove', this.onMove);
    canvas.addEventListener('mouseleave', this.onLeave);
    canvas.addEventListener('touchstart', this.onMove, { passive: true });
    canvas.addEventListener('touchend', this.onEnd);

    // Só redesenha se a LARGURA mudou. A barra de endereço do celular altera
    // só a altura da janela, e isso não deve refazer os gráficos.
    if (window.ResizeObserver) {
      this.ro = new ResizeObserver(function () {
        var w = canvas.parentElement.clientWidth;
        if (w > 0 && w !== self.w) { self.w = w; self.fitCache = {}; redesenhar(self); }
      });
      this.ro.observe(canvas.parentElement);
    }

    // Gráficos fora da tela só são desenhados quando aparecem.
    if (window.IntersectionObserver) {
      this.io = new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting && !self.iniciado) { self.iniciado = true; self.io.disconnect(); iniciar(self); }
      }, { rootMargin: '120px' });
      this.io.observe(canvas);
    } else { this.iniciado = true; iniciar(this); }
    charts.push(this);
  }

  Chart.prototype.total = function () {
    return this.items.reduce(function (s, i) { return s + i.total; }, 0);
  };
  Chart.prototype.tip = function (i, x, y) {
    var it = this.items[i], tot = this.total();
    var pct = tot ? Math.round(it.total * 100 / tot) : 0;
    showTip('<span>' + esc(it.chave) + '</span><br><b>' + it.total + '</b>' +
      (this.kind === 'donut' || this.opts.pct ? ' · ' + pct + '%' : ''), x, y);
  };
  Chart.prototype.setHover = function (i) {
    if (this.hover !== i) { this.hover = i; redesenhar(this); }
  };
  Chart.prototype.paint = function () {
    if (!this.canvas.isConnected) return;
    if (!this.w) this.w = this.canvas.parentElement.clientWidth;
    if (this.w <= 0) return;
    this['draw_' + this.kind]();
  };
  Chart.prototype.hit = function (x, y) { return this['hit_' + this.kind](x, y); };
  Chart.prototype.destroy = function () {
    var self = this;
    this.canvas.removeEventListener('mousemove', this.onMove);
    this.canvas.removeEventListener('mouseleave', this.onLeave);
    this.canvas.removeEventListener('touchstart', this.onMove);
    this.canvas.removeEventListener('touchend', this.onEnd);
    if (this.ro) this.ro.disconnect();
    if (this.io) this.io.disconnect();
    emAnimacao = emAnimacao.filter(function (c) { return c !== self; });
    sujos = sujos.filter(function (c) { return c !== self; });
    charts = charts.filter(function (c) { return c !== self; });
    this.canvas._chart = null;
  };

  /* Rosquinha */
  Chart.prototype.draw_donut = function () {
    var T = getTheme(), size = this.opts.size || 210;
    var g = prep(this, size), ctx = g.ctx;
    var cx = g.w / 2, cy = g.h / 2, R = Math.min(g.w, g.h) / 2 - 10, thick = R * 0.3, r = R - thick / 2;
    var tot = this.total(), items = this.items, self = this;
    this.geo = { cx: cx, cy: cy, R: R, thick: thick, segs: [] };
    var sweep = ease(this.p) * Math.PI * 2;

    ctx.lineWidth = thick; ctx.lineCap = 'butt'; ctx.strokeStyle = T.track;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke();

    if (tot > 0) {
      var nonZero = items.filter(function (i) { return i.total > 0; }).length;
      var gap = nonZero > 1 ? 0.05 : 0, ang = -Math.PI / 2;
      var inset = nonZero > 1 ? (thick / 2) / r * 0.55 + gap / 2 : 0;
      items.forEach(function (it, i) {
        var a = it.total / tot * Math.PI * 2, s = ang, e = ang + a;
        ang = e;
        self.geo.segs.push({ s: s + Math.PI / 2, e: e + Math.PI / 2 });
        if (!it.total) return;
        var vis = Math.min(e, -Math.PI / 2 + sweep);
        if (vis <= s) return;
        var col = colorOf(it, i, self.opts), on = self.hover === i, dim = self.hover >= 0 && !on;
        var gr = ctx.createLinearGradient(cx - R, cy - R, cx + R, cy + R);
        gr.addColorStop(0, shade(col, 0.22)); gr.addColorStop(1, shade(col, -0.12));
        ctx.save();
        ctx.globalAlpha = dim ? 0.38 : 1;
        ctx.strokeStyle = gr; ctx.lineWidth = thick + (on ? 9 : 0);
        var s2 = s + inset, e2 = vis - (vis === e ? inset : 0);
        if (nonZero === 1) { s2 = s; e2 = vis; ctx.lineCap = 'butt'; }
        else if (e2 - s2 > 0.04) ctx.lineCap = 'round';
        else { ctx.lineCap = 'butt'; s2 = s + gap / 2; e2 = vis - gap / 2; }
        if (e2 > s2) { ctx.beginPath(); ctx.arc(cx, cy, r, s2, e2); ctx.stroke(); }
        ctx.restore();
      });
    }

    var show = this.hover >= 0 && items[this.hover] ? items[this.hover] : null;
    var val = show ? show.total : Math.round(tot * ease(this.p));
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = T.text; ctx.font = '700 ' + Math.round(R * 0.46) + 'px ' + T.font;
    ctx.fillText(String(val), cx, cy - R * 0.08);
    ctx.fillStyle = T.muted; ctx.font = '500 ' + Math.max(11, Math.round(R * 0.15)) + 'px ' + T.font;
    this.fonteAtual = ctx.font; ctx.fillText(fit(this, ctx, show ? show.chave : (this.opts.centerLabel || 'total'), r * 1.45), cx, cy + R * 0.3);
  };
  Chart.prototype.hit_donut = function (x, y) {
    var gm = this.geo; if (!gm) return -1;
    var dx = x - gm.cx, dy = y - gm.cy, d = Math.sqrt(dx * dx + dy * dy);
    if (d < gm.R - gm.thick - 6 || d > gm.R + 8) return -1;
    var a = Math.atan2(dy, dx) + Math.PI / 2; if (a < 0) a += Math.PI * 2;
    for (var i = 0; i < gm.segs.length; i++) {
      if (this.items[i].total > 0 && a >= gm.segs[i].s && a <= gm.segs[i].e) return i;
    }
    return -1;
  };

  /* Barras horizontais (rótulo em cima, barra embaixo) */
  Chart.prototype.draw_hbar = function () {
    var T = getTheme(), items = this.items, self = this, n = items.length;
    var g = prep(this, Math.max(n, 1) * ROW + 4), ctx = g.ctx, w = g.w;
    var max = Math.max.apply(null, items.map(function (i) { return i.total; }).concat([1]));
    this.geo = { w: w };
    items.forEach(function (it, i) {
      var y = i * ROW + 2, col = colorOf(it, i, self.opts), on = self.hover === i, dim = self.hover >= 0 && !on;
      var pr = ease(clamp(self.p * 1.3 - i * 0.07, 0, 1));
      ctx.globalAlpha = dim ? 0.45 : 1;
      ctx.textBaseline = 'alphabetic';
      ctx.font = (on ? '650 ' : '550 ') + '13.5px ' + T.font;
      ctx.textAlign = 'right'; ctx.fillStyle = T.text;
      var val = String(Math.round(it.total * pr));
      ctx.fillText(val, w, y + 17);
      var vw = ctx.measureText(String(it.total)).width + 12;
      ctx.textAlign = 'left'; ctx.fillStyle = on ? T.text : T.muted;
      self.fonteAtual = ctx.font;
      ctx.fillText(fit(self, ctx, it.chave, w - vw), 0, y + 17);
      var bh = 12, by = y + 26;
      ctx.fillStyle = T.track; roundRect(ctx, 0, by, w, bh, bh / 2); ctx.fill();
      ctx.strokeStyle = T.line; ctx.lineWidth = 1; roundRect(ctx, 0.5, by + 0.5, w - 1, bh - 1, bh / 2); ctx.stroke();
      var bw = (it.total / max) * w * pr;
      if (bw > 0.5) {
        var gr = ctx.createLinearGradient(0, 0, Math.max(bw, 40), 0);
        gr.addColorStop(0, shade(col, 0.18)); gr.addColorStop(1, shade(col, -0.1));
        ctx.fillStyle = gr; roundRect(ctx, 0, by, Math.max(bw, bh), bh, bh / 2); ctx.fill();
      }
      ctx.globalAlpha = 1;
    });
  };
  Chart.prototype.hit_hbar = function (x, y) {
    var i = Math.floor((y - 2) / ROW);
    return i >= 0 && i < this.items.length ? i : -1;
  };

  /* Barras verticais */
  Chart.prototype.draw_vbar = function () {
    var T = getTheme(), items = this.items, self = this, n = items.length;
    var h = this.opts.height || 250, g = prep(this, h), ctx = g.ctx, w = g.w;
    var padT = 26, padB = 44, areaH = h - padT - padB, slot = w / Math.max(n, 1), bw = Math.min(54, slot * 0.58);
    var max = Math.max.apply(null, items.map(function (i) { return i.total; }).concat([1]));
    this.geo = { slot: slot, bw: bw, w: w };
    ctx.strokeStyle = T.line; ctx.lineWidth = 1; ctx.setLineDash([3, 5]);
    [0.25, 0.5, 0.75, 1].forEach(function (f) {
      var yy = padT + areaH * (1 - f) + 0.5; ctx.beginPath(); ctx.moveTo(0, yy); ctx.lineTo(w, yy); ctx.stroke();
    });
    ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(0, padT + areaH + 0.5); ctx.lineTo(w, padT + areaH + 0.5); ctx.stroke();
    items.forEach(function (it, i) {
      var col = colorOf(it, i, self.opts), on = self.hover === i, dim = self.hover >= 0 && !on;
      var pr = ease(clamp(self.p * 1.3 - i * 0.08, 0, 1));
      var bh = (it.total / max) * areaH * pr, x = i * slot + (slot - bw) / 2, y = padT + areaH - bh;
      ctx.globalAlpha = dim ? 0.45 : 1;
      if (bh > 0.5) {
        var gr = ctx.createLinearGradient(0, y, 0, y + bh);
        gr.addColorStop(0, shade(col, 0.2)); gr.addColorStop(1, shade(col, -0.12));
        ctx.fillStyle = gr; roundRect(ctx, x, y, bw, Math.max(bh, 3), Math.min(10, bw / 2)); ctx.fill();
        ctx.fillRect(x, padT + areaH - Math.min(8, bh), bw, Math.min(8, bh));   // base reta
      }
      ctx.textAlign = 'center'; ctx.fillStyle = T.text; ctx.font = '650 13.5px ' + T.font; ctx.textBaseline = 'alphabetic';
      ctx.fillText(String(Math.round(it.total * pr)), x + bw / 2, Math.max(16, y - 8));
      ctx.fillStyle = on ? T.text : T.muted; ctx.font = '550 12.5px ' + T.font;
      self.fonteAtual = ctx.font;
      ctx.fillText(fit(self, ctx, it.short || it.chave, slot - 6), x + bw / 2, padT + areaH + 20);
      ctx.globalAlpha = 1;
    });
  };
  Chart.prototype.hit_vbar = function (x) {
    var gm = this.geo; if (!gm) return -1;
    var i = Math.floor(x / gm.slot);
    return i >= 0 && i < this.items.length ? i : -1;
  };

  /* Legenda (HTML) ligada ao gráfico */
  function legend(container, items, chart, opts) {
    opts = opts || {};
    container.textContent = '';
    var tot = items.reduce(function (s, i) { return s + i.total; }, 0);
    var frag = document.createDocumentFragment();
    items.forEach(function (it, i) {
      var row = document.createElement('div'); row.className = 'legend-item';
      var dot = document.createElement('span'); dot.className = 'dot'; dot.style.background = colorOf(it, i, opts);
      var nm = document.createElement('span'); nm.className = 'lname'; nm.textContent = it.chave; nm.title = it.chave;
      var v = document.createElement('span'); v.className = 'lval'; v.textContent = it.total;
      var p = document.createElement('span'); p.className = 'lpct'; p.textContent = tot ? Math.round(it.total * 100 / tot) + '%' : '0%';
      row.append(dot, nm, v, p);
      row.addEventListener('mouseenter', function () { chart.setHover(i); });
      row.addEventListener('mouseleave', function () { chart.setHover(-1); });
      frag.appendChild(row);
    });
    container.appendChild(frag);
    if (chart && chart.opts) chart.opts.onHover = function (i) {
      Array.prototype.forEach.call(container.children, function (c, k) { c.classList.toggle('on', k === i); });
    };
  }

  window.addEventListener('themechange', function () {
    theme = null;
    charts.forEach(function (c) { c.fitCache = {}; if (c.p >= 1) c.paint(); });
  });

  root.Charts = {
    donut: function (canvas, items, opts) { return new Chart(canvas, items, opts, 'donut'); },
    hbar: function (canvas, items, opts) { return new Chart(canvas, items, opts, 'hbar'); },
    vbar: function (canvas, items, opts) { return new Chart(canvas, items, opts, 'vbar'); },
    legend: legend,
    PALETTE: PALETTE
  };
})(window);
