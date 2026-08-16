/* Compact ask panel for live tool pages. Posts to the same function as the
   front door. Does not invent figures. */
(function () {
  var root = document.getElementById("ask-starters");
  if (!root) return;
  var box = document.getElementById("toolAskQ");
  var btn = document.getElementById("toolAskBtn");
  var resp = document.getElementById("toolAskResp");
  if (!box || !btn || !resp) return;

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
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var HISTORY = [];
  var inflight = false;

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
    resp.innerHTML = '<div class="load">Checking the sources\u2026</div>';
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
      if (p.type === "answer") {
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
      } else if (p.type === "route" && p.matches && p.matches.length) {
        resp.innerHTML =
          '<div class="k">Where to find this</div><div class="det">' +
          p.matches.map(function (m) {
            return esc(m.reason || m.id);
          }).join(" ") +
          "</div>";
      } else {
        resp.innerHTML =
          '<div class="noans"><b>We do not cover this yet.</b> ' +
          esc(p.note || p.error || "Nothing we publish answers that.") +
          "</div>";
      }
    } catch (err) {
      resp.innerHTML = '<div class="noans"><b>Something went wrong.</b> Try again in a moment.</div>';
    } finally {
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
