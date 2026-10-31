/**
 * NewsFlipCard Standalone Embed Widget (Alias: widget.js)
 */
(function () {
  "use strict";

  function getBaseUrl() {
    var scripts = document.getElementsByTagName("script");
    var currentScript = document.currentScript;
    if (!currentScript) {
      for (var i = scripts.length - 1; i >= 0; i--) {
        var src = scripts[i].src || "";
        if (src.indexOf("embed.js") !== -1 || src.indexOf("widget.js") !== -1) {
          currentScript = scripts[i];
          break;
        }
      }
    }
    if (currentScript && currentScript.src) {
      try {
        var a = document.createElement("a");
        a.href = currentScript.src;
        return a.protocol + "//" + a.host;
      } catch (e) {}
    }
    return "http://localhost:3000";
  }

  var BASE_URL = getBaseUrl();

  function initElement(el) {
    if (el.getAttribute("data-news-flipcard-loaded") === "true") {
      return;
    }

    var lang = el.getAttribute("data-lang") || "en";
    var theme = el.getAttribute("data-theme") || "dark";
    var auto = el.getAttribute("data-auto") || "false";
    var every = el.getAttribute("data-every") || "5";
    var height = el.getAttribute("data-height") || "520px";
    var width = el.getAttribute("data-width") || "100%";
    var bg = el.getAttribute("data-bg") || "transparent";

    var params = [
      "lang=" + encodeURIComponent(lang),
      "theme=" + encodeURIComponent(theme),
      "auto=" + encodeURIComponent(auto),
      "every=" + encodeURIComponent(every),
      "bg=" + encodeURIComponent(bg),
    ];

    var embedUrl = BASE_URL + "/embed?" + params.join("&");

    var iframe = document.createElement("iframe");
    iframe.src = embedUrl;
    iframe.style.width = width;
    iframe.style.maxWidth = "100%";
    iframe.style.height = height;
    iframe.style.border = "none";
    iframe.style.borderRadius = "12px";
    iframe.style.overflow = "hidden";
    iframe.style.display = "block";
    iframe.style.margin = "0 auto";
    iframe.style.background = "transparent";
    iframe.setAttribute("allowtransparency", "true");
    iframe.setAttribute("loading", "lazy");
    iframe.setAttribute("title", "News FlipCard Feed");

    el.innerHTML = "";
    el.appendChild(iframe);
    el.setAttribute("data-news-flipcard-loaded", "true");
  }

  function scanAndInit() {
    var targets = document.querySelectorAll(
      "#news-flipcard, .news-flipcard-widget, [data-news-flipcard]"
    );
    for (var i = 0; i < targets.length; i++) {
      initElement(targets[i]);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scanAndInit);
  } else {
    scanAndInit();
  }

  window.NewsFlipCardWidget = {
    init: scanAndInit,
    mount: function (target, options) {
      var el = typeof target === "string" ? document.querySelector(target) : target;
      if (!el) return;
      options = options || {};
      if (options.lang) el.setAttribute("data-lang", options.lang);
      if (options.theme) el.setAttribute("data-theme", options.theme);
      if (options.auto !== undefined) el.setAttribute("data-auto", String(options.auto));
      if (options.every) el.setAttribute("data-every", String(options.every));
      if (options.height) el.setAttribute("data-height", options.height);
      if (options.width) el.setAttribute("data-width", options.width);
      if (options.bg) el.setAttribute("data-bg", options.bg);
      initElement(el);
    },
    version: "1.0.0",
  };
})();

