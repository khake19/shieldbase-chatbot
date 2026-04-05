(function () {
  if (window.__shieldbaseLoaded) return;
  window.__shieldbaseLoaded = true;

  var DEFAULTS = {
    url: "http://localhost:5173",
    position: "bottom-right",
    color: "#1e3a5f",
    title: "ShieldBase Chat",
  };

  // Read config from script tag data attributes
  var script =
    document.currentScript ||
    document.querySelector("script[data-shieldbase]");
  var cfg = {
    url: (script && script.getAttribute("data-url")) || DEFAULTS.url,
    position:
      (script && script.getAttribute("data-position")) || DEFAULTS.position,
    color: (script && script.getAttribute("data-color")) || DEFAULTS.color,
    title: (script && script.getAttribute("data-title")) || DEFAULTS.title,
  };

  var isRight = cfg.position.includes("right");
  var isTop = cfg.position.includes("top");

  // -- Styles --
  var style = document.createElement("style");
  style.textContent =
    "#sb-widget-btn{" +
    "position:fixed;" +
    (isRight ? "right:20px;" : "left:20px;") +
    (isTop ? "top:20px;" : "bottom:20px;") +
    "width:56px;height:56px;border-radius:50%;border:none;" +
    "background:" +
    cfg.color +
    ";" +
    "color:#fff;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);" +
    "z-index:2147483646;display:flex;align-items:center;justify-content:center;" +
    "transition:transform .2s,box-shadow .2s;}" +
    "#sb-widget-btn:hover{transform:scale(1.08);box-shadow:0 6px 20px rgba(0,0,0,.3);}" +
    "#sb-widget-btn svg{width:28px;height:28px;}" +
    "#sb-widget-frame-wrap{" +
    "position:fixed;" +
    (isRight ? "right:20px;" : "left:20px;") +
    (isTop ? "top:84px;" : "bottom:84px;") +
    "width:400px;height:600px;max-height:calc(100vh - 120px);max-width:calc(100vw - 40px);" +
    "border-radius:16px;overflow:hidden;" +
    "box-shadow:0 8px 32px rgba(0,0,0,.2);z-index:2147483647;" +
    "display:none;flex-direction:column;background:#fff;}" +
    "#sb-widget-frame-wrap.sb-open{display:flex;animation:sbSlideIn .25s ease;}" +
    "#sb-widget-header{" +
    "display:flex;align-items:center;justify-content:space-between;" +
    "padding:12px 16px;background:" +
    cfg.color +
    ";color:#fff;flex-shrink:0;}" +
    "#sb-widget-header span{font-weight:700;font-size:.95rem;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;}" +
    "#sb-widget-close{background:none;border:none;color:#fff;cursor:pointer;padding:4px;display:flex;opacity:.8;}" +
    "#sb-widget-close:hover{opacity:1;}" +
    "#sb-widget-iframe{border:none;width:100%;flex:1;}" +
    "@keyframes sbSlideIn{from{opacity:0;transform:translateY(12px);}to{opacity:1;transform:translateY(0);}}";
  document.head.appendChild(style);

  // -- Floating button --
  var btn = document.createElement("button");
  btn.id = "sb-widget-btn";
  btn.setAttribute("aria-label", "Open chat");
  btn.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
    "</svg>";
  document.body.appendChild(btn);

  // -- Frame wrapper --
  var wrap = document.createElement("div");
  wrap.id = "sb-widget-frame-wrap";

  var header = document.createElement("div");
  header.id = "sb-widget-header";

  var titleEl = document.createElement("span");
  titleEl.textContent = cfg.title;
  header.appendChild(titleEl);

  var closeBtn = document.createElement("button");
  closeBtn.id = "sb-widget-close";
  closeBtn.setAttribute("aria-label", "Close chat");
  closeBtn.innerHTML =
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' +
    "</svg>";
  header.appendChild(closeBtn);

  var iframe = document.createElement("iframe");
  iframe.id = "sb-widget-iframe";
  iframe.title = cfg.title;

  wrap.appendChild(header);
  wrap.appendChild(iframe);
  document.body.appendChild(wrap);

  // -- Toggle --
  var open = false;

  function toggle() {
    open = !open;
    if (open) {
      // Load iframe lazily on first open
      if (!iframe.src) iframe.src = cfg.url;
      wrap.classList.add("sb-open");
      btn.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' +
        "</svg>";
    } else {
      wrap.classList.remove("sb-open");
      btn.innerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
        '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>' +
        "</svg>";
    }
  }

  btn.addEventListener("click", toggle);
  closeBtn.addEventListener("click", toggle);
})();
