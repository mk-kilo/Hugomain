/* Loads GA4 and/or Plausible only when assets/analytics-config.js has a value.
   Empty IDs do nothing. Click tracking calls gtag/plausible when those functions exist. */
(function () {
  var cfg = window.JXZNE_ANALYTICS || {};
  var ga = String(cfg.ga4MeasurementId || "").trim();
  var domain = String(cfg.plausibleDomain || "").trim();
  var gaOk = /^G-[A-Z0-9]+$/.test(ga);
  var plausibleOk = domain.length > 0 && domain.indexOf(" ") === -1 && domain.indexOf("/") === -1;

  function track(name, params) {
    try {
      if (typeof window.gtag === "function") window.gtag("event", name, params || {});
      if (typeof window.plausible === "function") window.plausible(name, {props: params || {}});
    } catch (e) {}
  }
  window.jxzneTrack = track;

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
    var plausibleScript = document.createElement("script");
    plausibleScript.defer = true;
    plausibleScript.setAttribute("data-domain", domain);
    plausibleScript.src = "https://plausible.io/js/script.js";
    document.head.appendChild(plausibleScript);
  }

  function labelOf(node) {
    if (!node) return "";
    var explicit = node.getAttribute("data-cta") || node.getAttribute("data-copy") || node.id || "";
    if (explicit) return explicit;
    return (node.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80);
  }

  document.addEventListener("click", function (event) {
    var copy = event.target.closest && event.target.closest(".copy-code, [data-copy]");
    if (copy) {
      var copyId = copy.getAttribute("data-copy");
      var source = copyId ? document.getElementById(copyId) : null;
      if (source && navigator.clipboard && navigator.clipboard.writeText) {
        var sample = source.innerText || "";
        if (sample) {
          navigator.clipboard.writeText(sample).then(function () {
            if (!copy.getAttribute("data-copy-label")) copy.setAttribute("data-copy-label", copy.textContent);
          }).catch(function () {});
        }
      }
      track("copy_code", {event_category: "engagement", event_label: labelOf(copy)});
    }

    var langLink = event.target.closest && event.target.closest(".lang-switch a");
    if (langLink) {
      track("language_switch", {
        event_category: "engagement",
        event_label: langLink.getAttribute("hreflang") || labelOf(langLink)
      });
    }

    var link = event.target.closest && event.target.closest("a[href]");
    if (!link) return;
    var href = link.getAttribute("href") || "";
    if (/ofox\.ai/i.test(href)) {
      track("affiliate_click", {
        event_category: "affiliate",
        event_label: labelOf(link),
        link_url: href.split("#")[0]
      });
    }
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
