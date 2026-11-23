/* Searchable model ids from /ofox-public-prices.json. Click copies the id only. */
(function () {
  var root = document.getElementById("model-id-list");
  if (!root) return;

  var zh = (document.documentElement.lang || "").toLowerCase().indexOf("zh") === 0;
  var refreshed = root.querySelector("[data-model-refreshed]");
  var count = root.querySelector("[data-model-count]");
  var list = root.querySelector("[data-model-results]");
  var search = root.querySelector("[data-model-search]");
  var models = [];

  function text(node, value) {
    if (node) node.textContent = value;
  }

  function fail(message) {
    text(refreshed, message);
    text(count, "");
    if (list) list.replaceChildren();
  }

  function rate(value) {
    if (typeof value !== "number" || !isFinite(value)) return "";
    return String(Math.round(value * 1000000) / 1000000);
  }

  function rowId(id, index) {
    return "model-id-" + index + "-" + String(id).replace(/[^a-zA-Z0-9_-]/g, "-");
  }

  function render() {
    if (!list) return;
    var query = search ? String(search.value || "").trim().toLowerCase() : "";
    var matched = models.filter(function (model) {
      return !query || String(model.id).toLowerCase().indexOf(query) !== -1;
    });
    var shown = matched.slice(0, 40);
    list.replaceChildren();
    shown.forEach(function (model, index) {
      var item = document.createElement("li");
      item.className = "model-id-row";
      var idNode = document.createElement("code");
      var domId = rowId(model.id, index);
      idNode.id = domId;
      idNode.textContent = model.id;
      var meta = document.createElement("span");
      meta.className = "model-id-meta";
      var input = rate(model.promptPerMillion);
      var output = rate(model.completionPerMillion);
      meta.textContent = input && output
        ? (zh ? "输入 " + input + " · 输出 " + output + " / 百万 token" : "in " + input + " · out " + output + " / 1M tokens")
        : "";
      var button = document.createElement("button");
      button.type = "button";
      button.className = "copy-code";
      button.setAttribute("data-copy", domId);
      button.textContent = zh ? "复制" : "Copy";
      item.append(idNode, meta, button);
      list.appendChild(item);
    });
    var summary = zh
      ? "显示 " + shown.length + " / 匹配 " + matched.length + " / 文件中有文本单价的 " + models.length + " 个 id"
      : "Showing " + shown.length + " of " + matched.length + " matches, " + models.length + " ids with a text rate in the file";
    if (matched.length > shown.length) {
      summary += zh ? "。继续输入以缩小列表。" : ". Keep typing to narrow the list.";
    }
    text(count, summary);
  }

  var url = root.getAttribute("data-prices") || "/ofox-public-prices.json";
  fetch(url, { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("prices");
      return response.json();
    })
    .then(function (data) {
      var rows = data && Array.isArray(data.models) ? data.models : null;
      var when = data && data.fetchedAt ? String(data.fetchedAt) : "";
      if (!rows || !when) {
        fail(zh
          ? "价格文件没有模型列表或刷新时间。本页不补写模型 id。"
          : "The price file has no model list or refresh time. This page does not invent model ids.");
        return;
      }
      models = rows.filter(function (model) {
        return model && typeof model.id === "string" && model.id;
      });
      var catalog = typeof data.catalogCount === "number" ? String(data.catalogCount) : "";
      text(refreshed, zh
        ? "数据刷新时间：" + when + (catalog ? "。该次目录响应共 " + catalog + " 个模型；下面只列出文件中带文本输入和输出单价的 id。" : "。")
        : "Data refreshed: " + when + (catalog ? ". That catalog response had " + catalog + " models. The list below is only ids in the file that have a text input and output rate." : "."));
      if (search) search.addEventListener("input", render);
      render();
    })
    .catch(function () {
      fail(zh
        ? "没有读到 /ofox-public-prices.json。列表留空，不补写模型 id。"
        : "Could not read /ofox-public-prices.json. The list stays empty. No model ids were invented.");
    });
})();
