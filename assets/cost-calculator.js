/* Client-side monthly token cost.
   Ofox rates are filled only after the visitor picks a model from
   ofox-public-prices.json. Official lab rates are never filled in.
   The difference line is subtraction. It is not a savings claim. */
(function () {
  var root = document.getElementById("cost-calc");
  if (!root) return;

  function field(id) {
    return document.getElementById(id);
  }

  function read(id) {
    var el = field(id);
    if (!el) return null;
    var raw = String(el.value || "").trim().replace(/,/g, "");
    if (raw === "") return null;
    var value = Number(raw);
    if (!isFinite(value) || value < 0) return NaN;
    return value;
  }

  function format(value) {
    return value.toLocaleString(undefined, {maximumFractionDigits: 6});
  }

  function text(id, value) {
    var el = field(id);
    if (el) el.textContent = value;
  }

  function scenarioName(id, fallback) {
    var el = field(id);
    var name = el ? String(el.value || "").trim() : "";
    return name || fallback;
  }

  function cost(tokensIn, tokensOut, priceIn, priceOut) {
    var parts = [tokensIn, tokensOut, priceIn, priceOut];
    if (parts.some(function (part) { return Number.isNaN(part); })) return NaN;
    if (parts.some(function (part) { return part == null; })) return null;
    return (tokensIn / 1000000) * priceIn + (tokensOut / 1000000) * priceOut;
  }

  function render() {
    var tokensIn = read("cost-in");
    var tokensOut = read("cost-out");
    var costA = cost(tokensIn, tokensOut, read("cost-a-in"), read("cost-a-out"));
    var costB = cost(tokensIn, tokensOut, read("cost-b-in"), read("cost-b-out"));
    var bad = Number.isNaN(tokensIn) || Number.isNaN(tokensOut) || Number.isNaN(costA) || Number.isNaN(costB);
    var empty = root.getAttribute("data-msg-empty") || "—";
    var invalid = root.getAttribute("data-msg-bad") || "—";
    var pending = root.getAttribute("data-msg-pending") || "—";

    text("cost-a-total", costA == null ? pending : Number.isNaN(costA) ? invalid : format(costA));
    text("cost-b-total", costB == null ? pending : Number.isNaN(costB) ? invalid : format(costB));

    var diffEl = field("cost-diff");
    var noteEl = field("cost-compare");
    if (!diffEl || !noteEl) return;
    if (bad) {
      diffEl.textContent = invalid;
      noteEl.textContent = invalid;
      return;
    }
    if (costA == null || costB == null) {
      diffEl.textContent = pending;
      noteEl.textContent = empty;
      return;
    }
    var delta = costA - costB;
    diffEl.textContent = format(delta);
    var nameA = scenarioName("cost-a-name", root.getAttribute("data-name-a") || "A");
    var nameB = scenarioName("cost-b-name", root.getAttribute("data-name-b") || "B");
    if (delta === 0) {
      noteEl.textContent = root.getAttribute("data-msg-same") || "";
      return;
    }
    var template = root.getAttribute("data-msg-lower") || "";
    var lower = delta < 0 ? nameA : nameB;
    noteEl.textContent = template.replace("{low}", lower).replace("{diff}", format(Math.abs(delta)));
  }

  root.addEventListener("input", render);

  var catalog = null;
  var select = field("cost-ofox-model");
  var sourceNote = field("cost-ofox-source");

  function sisterCampaign() {
    var parts = location.pathname.split("/").filter(Boolean);
    if (parts[0] === "en") parts.shift();
    var cleaned = parts.map(function (part) { return part.replace(/\.html$/, ""); }).filter(Boolean);
    if (!cleaned.length || cleaned[cleaned.length - 1] === "index") return "home";
    if (cleaned.length >= 2 && cleaned[0] === "ai-pricing") return "ai-pricing-" + cleaned[cleaned.length - 1];
    return cleaned[cleaned.length - 1];
  }

  function sisterHref(modelId) {
    var params = ["utm_source=jxzne", "utm_medium=referral", "utm_campaign=" + encodeURIComponent(sisterCampaign())];
    if (modelId) params.unshift("model=" + encodeURIComponent(modelId));
    return "https://tokenhubs.dev/?" + params.join("&");
  }

  var sisterHolder = null;
  var sisterLink = null;
  if (select && sourceNote && sourceNote.parentNode) {
    var zhCalc = (document.documentElement.lang || "").toLowerCase().indexOf("zh") === 0;
    sisterHolder = document.createElement("p");
    sisterHolder.className = "calc-note";
    sisterHolder.hidden = true;
    sisterLink = document.createElement("a");
    sisterLink.className = "row-estimate";
    sisterLink.target = "_blank";
    sisterLink.rel = "noopener";
    sisterLink.textContent = zhCalc ? "算成本" : "Estimate";
    sisterHolder.appendChild(sisterLink);
    sourceNote.parentNode.insertBefore(sisterHolder, sourceNote.nextSibling);
  }

  function setSister(modelId) {
    if (!sisterHolder || !sisterLink) return;
    if (!modelId) {
      sisterHolder.hidden = true;
      sisterLink.removeAttribute("href");
      return;
    }
    sisterHolder.hidden = false;
    sisterLink.href = sisterHref(modelId);
  }

  function rateString(value) {
    if (typeof value !== "number" || !isFinite(value) || value < 0) return "";
    return String(Math.round(value * 1000000) / 1000000);
  }

  function applyCatalogModel() {
    if (!select || !catalog) return;
    var id = select.value;
    if (!id) {
      var blankName = field("cost-a-name");
      var blankIn = field("cost-a-in");
      var blankOut = field("cost-a-out");
      if (blankName) blankName.value = "";
      if (blankIn) blankIn.value = "";
      if (blankOut) blankOut.value = "";
      if (sourceNote) sourceNote.textContent = root.getAttribute("data-ofox-idle") || "";
      setSister("");
      render();
      return;
    }
    var model = null;
    for (var i = 0; i < catalog.models.length; i++) {
      if (catalog.models[i] && catalog.models[i].id === id) model = catalog.models[i];
    }
    var inputRate = model ? rateString(model.promptPerMillion) : "";
    var outputRate = model ? rateString(model.completionPerMillion) : "";
    if (!model || inputRate === "" || outputRate === "") {
      if (sourceNote) sourceNote.textContent = root.getAttribute("data-ofox-missing") || "";
      setSister(id);
      return;
    }
    var name = field("cost-a-name");
    var input = field("cost-a-in");
    var output = field("cost-a-out");
    if (name) name.value = id;
    if (input) input.value = inputRate;
    if (output) output.value = outputRate;
    var template = root.getAttribute("data-ofox-filled") || "";
    if (sourceNote) {
      sourceNote.textContent = template
        .replace("{id}", id)
        .replace("{date}", catalog.fetchedAt)
        .replace("{input}", inputRate)
        .replace("{output}", outputRate);
    }
    setSister(id);
    render();
  }

  if (select) {
    var pricesUrl = root.getAttribute("data-prices") || "/ofox-public-prices.json";
    fetch(pricesUrl, { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("prices");
        return response.json();
      })
      .then(function (data) {
        if (!data || !Array.isArray(data.models) || !data.fetchedAt) throw new Error("prices");
        catalog = data;
        data.models.forEach(function (model) {
          if (!model || typeof model.id !== "string" || !model.id) return;
          var option = document.createElement("option");
          option.value = model.id;
          option.textContent = model.id;
          select.appendChild(option);
        });
        select.addEventListener("change", applyCatalogModel);
        if (sourceNote && !select.value) sourceNote.textContent = root.getAttribute("data-ofox-idle") || sourceNote.textContent;
      })
      .catch(function () {
        if (sourceNote) sourceNote.textContent = root.getAttribute("data-ofox-error") || "";
      });
  }

  var example = field("cost-example-tokens");
  if (example) {
    example.addEventListener("click", function () {
      var input = field("cost-in");
      var output = field("cost-out");
      if (input) input.value = "1000000";
      if (output) output.value = "200000";
      var note = field("cost-example-note");
      if (note) note.hidden = false;
      render();
    });
  }

  render();
})();
