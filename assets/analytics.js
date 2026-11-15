/* Loads GA4 and/or Plausible only when assets/analytics-config.js has a value.
   Empty IDs load no vendor script and send no events.
   Affiliate clicks on https://ofox.ai/x/itoken emit affiliate_click with
   page_path and cta_position. The handler never calls preventDefault.
   See docs/affiliate-clicks.md. */
(function () {
  var cfg = window.JXZNE_ANALYTICS || {};
  var ga = String(cfg.ga4MeasurementId || "").trim();
  var domain = String(cfg.plausibleDomain || "").trim();
  var gaOk = /^G-[A-Z0-9]+$/.test(ga);
  var plausibleOk = domain.length > 0 && domain.indexOf(" ") === -1 && domain.indexOf("/") === -1;
  var analyticsOn = gaOk || plausibleOk;

  var debug = /(?:^|[?&])analytics_debug=1(?:&|$)/.test(window.location.search || "");
  function track(name, params) {
    if (debug && window.console) console.info("[JXZNE analytics preview — not a confirmed vendor event]", name, params || {});
    if (!analyticsOn) return;
    try {
      if (gaOk && typeof window.gtag === "function") window.gtag("event", name, params || {});
      if (plausibleOk && typeof window.plausible === "function") window.plausible(name, {props: params || {}});
    } catch (e) {}
  }
  window.jxzneTrack = track;
  window.jxzneAnalyticsStatus = {ga4Configured:gaOk,plausibleConfigured:plausibleOk,debugMode:debug};

  if (gaOk) {
    var gaScript = document.createElement("script");
    gaScript.async = true;
    gaScript.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(ga);
    document.head.appendChild(gaScript);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", ga, {anonymize_ip: true});
  }

  if (plausibleOk) {
    window.plausible = window.plausible || function () {
      (window.plausible.q = window.plausible.q || []).push(arguments);
    };
    var plausibleScript = document.createElement("script");
    plausibleScript.defer = true;
    plausibleScript.setAttribute("data-domain", domain);
    plausibleScript.src = "https://plausible.io/js/script.pageview-props.tagged-events.js";
    document.head.appendChild(plausibleScript);
  }

  function labelOf(node) {
    if (!node) return "";
    var explicit = node.getAttribute("data-cta") || node.getAttribute("data-copy") || node.id || "";
    if (explicit) return explicit;
    return (node.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80);
  }

  function isAffiliateHref(href) {
    try {
      var url = new URL(href, window.location.href);
      if (url.protocol !== "https:" && url.protocol !== "http:") return false;
      var host = url.hostname.toLowerCase().replace(/^www\./, "");
      if (host !== "ofox.ai") return false;
      var path = url.pathname.replace(/\/+$/, "") || "/";
      return path === "/x/itoken";
    } catch (e) {
      return false;
    }
  }

  function ctaPosition(link) {
    var explicit = (link.getAttribute("data-cta-position") || "").trim();
    if (explicit) return explicit.slice(0, 60);
    if (link.closest("header, .nav")) return "nav";
    if (link.closest("footer")) return "footer";
    if (link.closest(".hero, .guide-hero, .developer-hero, .enterprise-hero, .pricing-hub-hero")) return "hero";
    if (link.closest(".guide-bottom, .cta, .price-cta")) return "bottom";
    return "inline";
  }

  function annotateAffiliate(link) {
    var position = ctaPosition(link);
    if (!link.getAttribute("data-outbound")) link.setAttribute("data-outbound", "affiliate");
    if (!link.getAttribute("data-cta-position")) link.setAttribute("data-cta-position", position);
    return link.getAttribute("data-cta-position") || position;
  }

  function pagePath() {
    return (window.location.pathname || "/") + (window.location.search || "");
  }

  function uiLang() {
    return (document.documentElement.lang || "").toLowerCase().indexOf("zh") === 0 ? "zh" : "en";
  }

  function copyLabel(state) {
    var zh = uiLang() === "zh";
    if (state === "ok") return zh ? "已复制" : "Copied";
    if (state === "fail") return zh ? "请选择代码手动复制" : "Select the code and copy it";
    return zh ? "复制" : "Copy";
  }

  function copyText(text) {
    function legacy() {
      return new Promise(function (resolve, reject) {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.top = "0";
      area.style.left = "-9999px";
      document.body.appendChild(area);
      area.select();
      try {
        if (document.execCommand("copy")) resolve();
        else reject(new Error("copy"));
      } catch (err) {
        reject(err);
      } finally {
        document.body.removeChild(area);
      }
    });
    }
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return navigator.clipboard.writeText(text).catch(legacy);
    }
    return legacy();
  }

  function ensureCopyButtons() {
    var blocks = document.querySelectorAll("pre");
    for (var i = 0; i < blocks.length; i++) {
      var pre = blocks[i];
      var host = pre.parentElement;
      if (!host || host.querySelector(".copy-code")) continue;
      if (!pre.id) pre.id = "jxzne-code-" + (i + 1);
      var bar = document.createElement("div");
      bar.className = "code-copy-bar";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "copy-code";
      button.setAttribute("data-copy", pre.id);
      button.textContent = copyLabel();
      bar.appendChild(button);
      host.insertBefore(bar, pre);
    }
  }

  function eventTarget(event) {
    var node = event.target;
    if (node && node.nodeType !== 1) node = node.parentElement;
    if (!node || typeof node.closest !== "function") return null;
    return node;
  }

  if (analyticsOn) {
    var affiliates = document.querySelectorAll("a[href]");
    for (var n = 0; n < affiliates.length; n++) {
      if (isAffiliateHref(affiliates[n].getAttribute("href") || "")) annotateAffiliate(affiliates[n]);
    }
  }

  ensureCopyButtons();

  document.addEventListener("click", function (event) {
    try {
      var target = eventTarget(event);
      if (!target) return;

      var copy = target.closest(".copy-code, [data-copy]");
      if (copy) {
        var copyId = copy.getAttribute("data-copy");
        var source = copyId ? document.getElementById(copyId) : null;
        if (source) {
          var sample = source.innerText || "";
          if (sample) {
            if (!copy.getAttribute("data-copy-label")) copy.setAttribute("data-copy-label", copy.textContent);
            copyText(sample).then(function () {
              copy.textContent = copyLabel("ok");
            }).catch(function () {
              copy.textContent = copyLabel("fail");
            });
          }
        }
        track("copy_code", {event_category: "engagement", event_label: labelOf(copy)});
      }

      var langLink = target.closest(".lang-switch a");
      if (langLink) {
        track("language_switch", {
          event_category: "engagement",
          event_label: langLink.getAttribute("hreflang") || labelOf(langLink)
        });
      }

      var link = target.closest("a[href]");
      if (!link) return;
      var href = link.getAttribute("href") || "";
      if (/^mailto:/i.test(href)) {
        track("contact_intent", {
          event_category: "lead_intent",
          event_label: labelOf(link),
          page_path: pagePath().slice(0, 200)
        });
      }
      if (!/ofox\.ai/i.test(href)) return;
      var referral = isAffiliateHref(href);
      var position = link.getAttribute("data-cta-position") || "";
      if (referral && analyticsOn) position = annotateAffiliate(link);
      track("affiliate_click", {
        event_category: "affiliate",
        event_label: labelOf(link),
        page_path: pagePath().slice(0, 200),
        cta_position: position,
        cta_id: link.getAttribute("data-cta") || "unlabeled",
        link_url: (link.href || href).split("#")[0].slice(0, 300),
        outbound: referral ? "affiliate" : ""
      });
    } catch (e) {}
  });

  var langSelect = document.getElementById("site-lang");
  if (langSelect) {
    langSelect.addEventListener("change", function () {
      track("language_switch", {event_category: "engagement", event_label: langSelect.value});
    });
  }

  document.querySelectorAll(".nav-toggle").forEach(function (button) {
    var bar = button.closest(".nav");
    var panel = bar && (document.getElementById(button.getAttribute("aria-controls")) || bar.querySelector(".nav-links"));
    if (!bar || !panel) return;
    button.addEventListener("click", function () {
      var open = bar.classList.toggle("is-open");
      button.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && bar.classList.contains("is-open")) {
        bar.classList.remove("is-open");
        button.setAttribute("aria-expanded", "false");
        button.focus();
      }
    });
    panel.querySelectorAll("a").forEach(function (item) {
      item.addEventListener("click", function () {
        if (window.matchMedia("(max-width: 900px)").matches) {
          bar.classList.remove("is-open");
          button.setAttribute("aria-expanded", "false");
        }
      });
    });
  });
})();
