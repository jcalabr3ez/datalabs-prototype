/* Compact ask panel for live tool pages and the landing dock. Posts to
   the same function. Does not invent figures. */
(function () {
  var AI_DEFAULT = true;
  var AI_ENABLED = AI_DEFAULT;
  try {
    var _ai = new URLSearchParams(location.search).get("ai");
    if (_ai != null) AI_ENABLED = _ai === "1" || _ai === "true";
  } catch (e) {}
  document.body.classList.toggle("ai-off", !AI_ENABLED);
  document.body.classList.toggle("ai-on", AI_ENABLED);
  if (!AI_ENABLED) return;

  function esc(s) {
    if (typeof window.esc === "function") return window.esc(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function safeUrl(u) {
    if (typeof window.safeUrl === "function") return window.safeUrl(u);
    u = u == null ? "" : String(u).trim();
    return u.indexOf("/") === 0 && u.indexOf("//") !== 0 ? u : "";
  }

  var HISTORY = [];
  var inflight = false;
  var LOAD_STEPS = [
    { at: 0, line: "Matching your question to the catalog" },
    { at: 1400, line: "Reading the published ledgers that apply" },
    { at: 3800, line: "Checking whether those figures answer it" },
    { at: 10000, line: "Still checking. A harder match can take longer" }
  ];

  function startLoad(el) {
    var timers = [];
    var stopped = false;
    function paint(i) {
      if (stopped || !el) return;
      var step = LOAD_STEPS[i];
      el.innerHTML =
        '<div class="load"><span class="load-k">' + esc(step.line) + "\u2026</span>" +
        (i > 0 ? '<div class="slow">Only figures from this catalog</div>' : "") +
        "</div>";
    }
    paint(0);
    LOAD_STEPS.forEach(function (step, i) {
      if (!step.at) return;
      timers.push(setTimeout(function () { paint(i); }, step.at));
    });
    return function stopLoad() {
      stopped = true;
      timers.forEach(clearTimeout);
    };
  }

  function bootTool() {
    var root = document.getElementById("ask-starters");
    var box = document.getElementById("toolAskQ");
    var btn = document.getElementById("toolAskBtn");
    var resp = document.getElementById("toolAskResp");
    if (!root || !box || !btn || !resp) return;

    function setQuestion(q) {
      box.value = q;
      [].slice.call(root.querySelectorAll(".ask-chip")).forEach(function (c) {
        c.classList.toggle("is-on", c.getAttribute("data-q") === q);
      });
    }

    async function ask() {
      if (inflight) return;
      var q = (box.value || "").replace(/^\s+|\s+$/g, "");
      if (!q) return;
      inflight = true;
      btn.disabled = true;
      resp.hidden = false;
      var stopLoad = startLoad(resp);
      var ctl = new AbortController();
      var timer = setTimeout(function () { ctl.abort(); }, 35000);
      try {
        var r = await fetch("/.netlify/functions/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q, history: HISTORY.slice(-2) }),
          signal: ctl.signal
        });
        var p = await r.json();
        if (!r.ok || p.error) {
          resp.innerHTML = '<div class="noans"><b>Try again in a moment.</b> Every tool in the catalog still works.</div>';
        } else if (p.type === "answer") {
          resp.innerHTML =
            '<div class="k">Answer</div>' +
            '<div class="ans">' + esc(p.text) + "</div>" +
            (p.detail ? '<div class="det">' + esc(p.detail) + "</div>" : "") +
            (p.src ? '<div class="srcline"><b>Source:</b> ' + esc(p.src) + "</div>" : "") +
            (p.followups && p.followups.length
              ? '<div class="fups">Related: ' +
                p.followups.map(function (f) {
                  return '<a href="#" data-q="' + esc(f) + '">' + esc(f) + "</a>";
                }).join("") +
                "</div>"
              : "");
          HISTORY.push({ q: q, a: p.text });
          if (HISTORY.length > 4) HISTORY = HISTORY.slice(-4);
          [].slice.call(resp.querySelectorAll(".fups a")).forEach(function (a) {
            a.addEventListener("click", function (e) {
              e.preventDefault();
              setQuestion(a.getAttribute("data-q"));
              ask();
            });
          });
          if (p.link && window.dlHighlightExhibit) {
            try {
              var u = new URL(p.link, location.origin);
              if (u.pathname.replace(/\/$/, "") === location.pathname.replace(/\/$/, "")) {
                window.dlHighlightExhibit(u.hash || "#view-rank");
              }
            } catch (err) {}
          }
        } else if (p.type === "route" && p.matches && p.matches.length) {
          resp.innerHTML =
            '<div class="k">Where to find this</div><div class="det">' +
            p.matches.map(function (m) {
              return esc(m.reason || m.id);
            }).join(" ") +
            "</div>";
        } else {
          resp.innerHTML =
            '<div class="noans"><b>We do not have that number.</b> ' +
            esc(p.note || p.error || "Nothing we publish answers that.") +
            "</div>";
        }
      } catch (err) {
        resp.innerHTML = '<div class="noans"><b>Something went wrong.</b> Try again in a moment.</div>';
      } finally {
        stopLoad();
        clearTimeout(timer);
        btn.disabled = false;
        inflight = false;
      }
    }

    [].slice.call(root.querySelectorAll(".ask-chip[data-q]")).forEach(function (chip) {
      chip.addEventListener("click", function () {
        setQuestion(chip.getAttribute("data-q"));
        ask();
      });
    });
    btn.addEventListener("click", ask);
    box.addEventListener("keydown", function (e) {
      if (e.key === "Enter") ask();
    });
  }

  function bootLanding() {
    var box = document.getElementById("q");
    var btn = document.getElementById("askBtn");
    var resp = document.getElementById("resp");
    var respBar = document.getElementById("respBar");
    if (!box || !btn || !resp) return;
    var DISMISS = '<button class="dismiss" type="button" aria-label="Dismiss" title="Dismiss">&#215;</button>';
    var titles = window.CHART_TITLES || {};
    var tools = window.TOOLMAP || {};

    function respChrome() {
      if (!respBar) return;
      respBar.hidden = resp.innerHTML.indexOf('class="entry"') < 0 && resp.innerHTML.indexOf('class="noans"') < 0;
    }

    async function ask() {
      if (inflight) return;
      var q = (box.value || "").replace(/^\s+|\s+$/g, "");
      if (!q) return;
      btn.disabled = true;
      inflight = true;
      var stopLoad = startLoad(resp);
      var ctl = new AbortController();
      var timer = setTimeout(function () { ctl.abort(); }, 35000);
      try {
        var r = await fetch("/.netlify/functions/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q, history: HISTORY.slice(-2) }),
          signal: ctl.signal
        });
        var p = await r.json();
        if (!r.ok || p.error) {
          resp.innerHTML = '<div class="noans">' + DISMISS + "<b>Try again in a moment.</b> Every tool in the catalog still works.</div>";
        } else if (p.type === "answer") {
          var kind = p.chart && p.chart !== "none" ? p.chart : null;
          var link = safeUrl(p.link);
          var cap = kind && titles[kind] ? titles[kind] : "";
          resp.innerHTML = '<div class="entry">' + DISMISS + '<div class="k">Answer</div>' +
            '<div class="ans">' + esc(p.text) + "</div>" +
            (p.detail ? '<div class="det">' + esc(p.detail) + "</div>" : "") +
            (p.src ? '<div class="srcline"><b>Source:</b> ' + esc(p.src) + "</div>" : "") +
            (link ? '<div class="goline"><a href="' + esc(link) + '">' + (cap ? ("Open " + cap + " &#8594;") : "Open &#8594;") + "</a></div>" : "") +
            (p.see_also && p.see_also.length ? '<div class="seealso">Also relevant: ' +
              p.see_also.filter(function (s) { return safeUrl(s.url); }).map(function (s) {
                return '<a href="' + esc(safeUrl(s.url)) + '" title="' + esc(s.reason || "") + '">' + esc(s.title) + " &#8594;</a>";
              }).join(" &#183; ") + "</div>" : "") +
            (p.followups && p.followups.length ? '<div class="fups">Related: ' +
              p.followups.map(function (f) {
                return '<a href="#" data-q="' + esc(f) + '">' + esc(f) + "</a>";
              }).join("") + "</div>" : "") +
            "</div>";
          HISTORY.push({ q: q, a: p.text });
          if (HISTORY.length > 4) HISTORY = HISTORY.slice(-4);
          [].slice.call(resp.querySelectorAll(".fups a")).forEach(function (a) {
            a.addEventListener("click", function (e) {
              e.preventDefault();
              box.value = a.getAttribute("data-q");
              ask();
            });
          });
        } else if (p.type === "route" && p.matches && p.matches.length) {
          resp.innerHTML = '<div class="entry">' + DISMISS + '<div class="k">Where to find this</div><div class="routes">' +
            p.matches.map(function (m) {
              var t = tools[m.id];
              if (!t) return "";
              var url = safeUrl(t.url);
              var linkRows = url
                ? '<a class="dashlink" href="' + esc(url) + '">' +
                  (t.id ? '<span class="site">' + esc(t.id) + "</span>" : "") + esc(t.t) + " &#8594;</a>"
                : '<a class="dashlink" href="#dir-' + t.id + '">Browse this topic in the directory &#8594;</a>';
              return '<div class="rt"><div class="name">' + esc(t.t) + "</div>" +
                '<div class="why">' + esc(m.reason || t.q) + "</div>" +
                '<div class="dashlinks">' + linkRows + "</div></div>";
            }).join("") + "</div></div>";
        } else {
          resp.innerHTML = '<div class="noans">' + DISMISS + "<b>We do not have that number.</b> " +
            esc(p.note || p.error || "Nothing we publish answers that.") +
            (p.followups && p.followups.length ? '<div class="fups">We can answer: ' +
              p.followups.map(function (f) {
                return '<a href="#" data-q="' + esc(f) + '">' + esc(f) + "</a>";
              }).join("") + "</div>" : "") +
            "</div>";
          [].slice.call(resp.querySelectorAll(".fups a")).forEach(function (a) {
            a.addEventListener("click", function (e) {
              e.preventDefault();
              box.value = a.getAttribute("data-q");
              ask();
            });
          });
        }
      } catch (err) {
        resp.innerHTML = '<div class="noans">' + DISMISS + "<b>Try again in a moment.</b> Every tool in the catalog still works.</div>";
      } finally {
        stopLoad();
        clearTimeout(timer);
        btn.disabled = false;
        inflight = false;
        respChrome();
      }
    }

    window.ask = ask;
    btn.addEventListener("click", ask);
    box.addEventListener("keydown", function (e) {
      if (e.key === "Enter") ask();
    });
    resp.addEventListener("click", function (e) {
      var t = e.target;
      while (t && t.id !== "resp") {
        if ((t.className || "") === "dismiss") {
          t.parentElement.remove();
          respChrome();
          return;
        }
        t = t.parentElement;
      }
    });
    var clearBtn = document.getElementById("clearAns");
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        resp.innerHTML = "";
        respChrome();
      });
    }
  }

  if (document.getElementById("ask-starters")) bootTool();
  else if (document.getElementById("q") && document.getElementById("askBtn") && document.getElementById("resp")) bootLanding();
})();

(function () {
  document.addEventListener("click", function (ev) {
    var btn = ev.target && ev.target.closest && ev.target.closest(".cite-copy");
    if (!btn) return;
    var text = btn.getAttribute("data-cite") || "";
    if (!text) return;
    var done = function () {
      var prev = btn.textContent;
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = prev || "Copy citation"; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(function () {
        window.prompt("Copy this citation", text);
      });
    } else {
      window.prompt("Copy this citation", text);
    }
  });
})();
