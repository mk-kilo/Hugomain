/* Renders ofox-smoke-status.json. Does not invent a passing run. */
(function () {
  var en = (document.documentElement.lang || "").toLowerCase().startsWith("en");
  var root = en ? "../" : "";
  var box = document.getElementById("smoke-result");
  if (!box) return;

  function text(id, value) {
    var node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function show(data) {
    var status = data && data.status ? data.status : "unverified";
    var overall = data && data.overall ? data.overall : "unverified";
    var ran = status === "passed" || status === "failed";
    text("smoke-overall", overall);
    text("smoke-status", status);
    text("smoke-model", (data && data.model) || "openai/gpt-5.4");
    text("smoke-latency", data && data.latencyMs != null ? String(data.latencyMs) : "—");
    text("smoke-http", data && data.httpStatus != null ? String(data.httpStatus) : "—");
    text("smoke-timestamp", (data && data.timestamp) || "—");
    var banner = document.getElementById("smoke-banner");
    if (!banner) return;
    banner.classList.remove("is-pending", "is-passed", "is-failed");
    if (!ran || overall === "unverified" || status === "unverified") {
      banner.classList.add("is-pending");
      banner.textContent = en
        ? "Pending real run. No authenticated chat completion is recorded in ofox-smoke-status.json."
        : "待实测。ofox-smoke-status.json 里没有已记录的认证 Chat Completions 调用。";
      return;
    }
    if (status === "passed") {
      banner.classList.add("is-passed");
      banner.textContent = en
        ? "One recorded call returned HTTP " + data.httpStatus + " in " + data.latencyMs + " ms. This is not an uptime or savings claim."
        : "已记录一次调用：HTTP " + data.httpStatus + "，耗时 " + data.latencyMs + " ms。这不是可用性或省钱承诺。";
      return;
    }
    banner.classList.add("is-failed");
    banner.textContent = en
      ? "A real call was recorded as failed (HTTP " + (data.httpStatus == null ? "n/a" : data.httpStatus) + "). It is not shown as a pass."
      : "已记录一次失败的调用（HTTP " + (data.httpStatus == null ? "无" : data.httpStatus) + "）。没有把它写成通过。";
  }

  fetch(root + "ofox-smoke-status.json", {cache: "no-store"})
    .then(function (response) { return response.ok ? response.json() : null; })
    .then(function (data) { show(data || {overall: "unverified", status: "unverified"}); })
    .catch(function () { show({overall: "unverified", status: "unverified"}); });
})();
