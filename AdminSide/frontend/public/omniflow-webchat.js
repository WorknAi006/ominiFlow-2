/*
 * Omniflow Web Chat widget — embeddable on any website.
 *
 *   <script src="https://app.example.com/omniflow-webchat.js"
 *           data-omniflow-key="wc_xxx"
 *           data-omniflow-api="https://api.example.com"></script>
 *
 * The data-omniflow-key is the channel's PUBLIC widget key (safe to expose).
 * No private credentials are ever used in the browser. The visitor identity
 * is a random id kept in localStorage; the server resolves tenant + channel
 * from the public key alone.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  if (!script) return;
  var PUBLIC_KEY = script.getAttribute("data-omniflow-key");
  if (!PUBLIC_KEY) {
    console.error("[omniflow] missing data-omniflow-key");
    return;
  }
  var API_BASE = (script.getAttribute("data-omniflow-api") || window.location.origin).replace(/\/$/, "");
  var BASE = API_BASE + "/api/v1/web-chat/" + encodeURIComponent(PUBLIC_KEY);
  var POLL_MS = 4000;
  var STORAGE_KEY = "omniflow_visitor_" + PUBLIC_KEY;

  function visitorId() {
    var id;
    try {
      id = window.localStorage.getItem(STORAGE_KEY);
    } catch (e) { id = null; }
    if (!id) {
      id = (window.crypto && window.crypto.randomUUID)
        ? window.crypto.randomUUID()
        : "v-" + Date.now() + "-" + Math.random().toString(16).slice(2);
      try { window.localStorage.setItem(STORAGE_KEY, id); } catch (e) {}
    }
    return id;
  }

  var VISITOR = visitorId();
  var seen = Object.create(null);
  var lastAfter = null;
  var open = false;
  var pollTimer = null;

  // ---------- styles ----------
  var css = "" +
    ".ofw-btn{position:fixed;right:20px;bottom:20px;width:56px;height:56px;border-radius:50%;background:#176b59;color:#fff;border:none;cursor:pointer;font-size:24px;box-shadow:0 4px 14px rgba(0,0,0,.2);z-index:2147483000}" +
    ".ofw-panel{position:fixed;right:20px;bottom:88px;width:340px;max-width:calc(100vw - 40px);height:460px;max-height:calc(100vh - 120px);background:#fff;border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.25);display:none;flex-direction:column;overflow:hidden;z-index:2147483000;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}" +
    ".ofw-panel.ofw-open{display:flex}" +
    ".ofw-head{background:#176b59;color:#fff;padding:12px 14px;font-weight:600;display:flex;justify-content:space-between;align-items:center}" +
    ".ofw-head small{display:block;font-weight:400;opacity:.8;font-size:11px}" +
    ".ofw-head button{background:transparent;border:none;color:#fff;font-size:18px;cursor:pointer}" +
    ".ofw-body{flex:1;overflow-y:auto;padding:12px;background:#f5f7f6}" +
    ".ofw-msg{max-width:80%;padding:8px 11px;border-radius:12px;margin:6px 0;font-size:14px;line-height:1.35;white-space:pre-wrap;word-wrap:break-word}" +
    ".ofw-visitor{background:#176b59;color:#fff;margin-left:auto;border-bottom-right-radius:3px}" +
    ".ofw-agent{background:#fff;color:#111;border:1px solid #e2e8e5;border-bottom-left-radius:3px}" +
    ".ofw-foot{display:flex;border-top:1px solid #e2e8e5;padding:8px;gap:8px;background:#fff}" +
    ".ofw-foot input{flex:1;border:1px solid #cdd8d3;border-radius:8px;padding:8px 10px;font-size:14px;outline:none}" +
    ".ofw-foot button{background:#176b59;color:#fff;border:none;border-radius:8px;padding:0 14px;cursor:pointer;font-size:14px}" +
    ".ofw-foot button:disabled{opacity:.5;cursor:default}" +
    ".ofw-state{font-size:11px;color:#64748b;text-align:center;padding:4px}" +
    ".ofw-state.ofw-err{color:#b91c1c}";
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  // ---------- DOM ----------
  var btn = document.createElement("button");
  btn.className = "ofw-btn";
  btn.setAttribute("aria-label", "Open chat");
  btn.innerHTML = "&#128172;";

  var panel = document.createElement("div");
  panel.className = "ofw-panel";
  panel.innerHTML =
    '<div class="ofw-head"><span>Chat with us<small id="ofw-title">We usually reply shortly</small></span><button id="ofw-close" aria-label="Close chat">&times;</button></div>' +
    '<div class="ofw-body" id="ofw-body"></div>' +
    '<div class="ofw-state" id="ofw-state"></div>' +
    '<form class="ofw-foot" id="ofw-form"><input id="ofw-input" autocomplete="off" placeholder="Type a message…" maxlength="4096" /><button type="submit" id="ofw-send">Send</button></form>';

  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var body = panel.querySelector("#ofw-body");
  var input = panel.querySelector("#ofw-input");
  var form = panel.querySelector("#ofw-form");
  var stateEl = panel.querySelector("#ofw-state");
  var titleEl = panel.querySelector("#ofw-title");

  function setState(text, isError) {
    stateEl.textContent = text || "";
    stateEl.className = "ofw-state" + (isError ? " ofw-err" : "");
  }

  function render(msg) {
    if (seen[msg.id]) return;
    seen[msg.id] = true;
    var el = document.createElement("div");
    el.className = "ofw-msg " + (msg.direction === "agent" ? "ofw-agent" : "ofw-visitor");
    el.textContent = msg.text || "";
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
    if (msg.created_at) lastAfter = msg.created_at;
  }

  function poll() {
    var url = BASE + "/messages?visitor_id=" + encodeURIComponent(VISITOR) +
      (lastAfter ? "&after=" + encodeURIComponent(lastAfter) : "");
    fetch(url, { method: "GET" })
      .then(function (r) { if (!r.ok) throw new Error("poll " + r.status); return r.json(); })
      .then(function (data) {
        (data.messages || []).forEach(render);
        setState("");
      })
      .catch(function () { setState("Reconnecting…", true); });
  }

  function startPolling() {
    if (pollTimer) return;
    poll();
    pollTimer = window.setInterval(poll, POLL_MS);
  }
  function stopPolling() {
    if (pollTimer) { window.clearInterval(pollTimer); pollTimer = null; }
  }

  function loadConfig() {
    fetch(BASE + "/config")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (cfg) { if (cfg && cfg.channel_name) titleEl.textContent = cfg.channel_name; })
      .catch(function () {});
  }

  function send(text) {
    var clientId = (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : String(Date.now());
    var sendBtn = panel.querySelector("#ofw-send");
    sendBtn.disabled = true;
    fetch(BASE + "/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visitor_id: VISITOR, text: text, client_message_id: clientId }),
    })
      .then(function (r) {
        if (!r.ok) throw new Error("send " + r.status);
        return r.json();
      })
      .then(function (data) { if (data && data.message) render(data.message); setState(""); })
      .catch(function () { setState("Message not sent. Try again.", true); })
      .then(function () { sendBtn.disabled = false; });
  }

  function toggle(show) {
    open = show;
    panel.classList.toggle("ofw-open", open);
    btn.setAttribute("aria-label", open ? "Close chat" : "Open chat");
    if (open) { startPolling(); input.focus(); } else { stopPolling(); }
  }

  btn.addEventListener("click", function () { toggle(!open); });
  panel.querySelector("#ofw-close").addEventListener("click", function () { toggle(false); });
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    send(text);
  });

  loadConfig();
})();
