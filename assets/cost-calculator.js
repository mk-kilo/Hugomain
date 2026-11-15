/* Client-side monthly token cost. Prices are whatever the visitor types.
   This file does not contain model rates. */
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
