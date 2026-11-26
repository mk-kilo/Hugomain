/* Renders ofox-smoke-status.json. A non-success status stays pending.
   httpStatus, latency, and the failure note are shown only after a call
   is recorded as successful. Does not invent a pass. */
(function () {
  var en = (document.documentElement.lang || "").toLowerCase().startsWith("en");
  var root = en ? "../" : "";
  var box = document.getElementById("smoke-result");
  if (!box) return;

  var pending = en
    ? "Pending. An authenticated call has not yet been recorded as successful, and this page stays pending until one is."
    : "待实测。认证调用尚未被记录为成功，在记录成功之前本页保持待实测。";

  function text(id, value) {
    var node = document.getElementById(id);
    if (node) node.textContent = value;
  }

  function recordedSuccess(data) {
    if (!data || data.status !== "passed") return false;
    if (!data.overall || data.overall === "unverified" || data.overall === "failed") return false;
    var code = Number(data.httpStatus);
    return code >= 200 && code < 300 && data.latencyMs != null && !!data.timestamp;
  }

  function showPending(data) {
    text("smoke-overall", "unverified");
    text("smoke-status", "unverified");
    text("smoke-model", (data && data.model) || "openai/gpt-5.4");
    text("smoke-latency", "—");
    text("smoke-http", "—");
    text("smoke-timestamp", "—");
    var banner = document.getElementById("smoke-banner");
    if (!banner) return;
    banner.classList.remove("is-pending", "is-passed", "is-failed");
    banner.classList.add("is-pending");
    banner.textContent = pending;
  }

  function show(data) {
    if (!recordedSuccess(data)) {
      showPending(data);
      return;
    }
    text("smoke-overall", data.overall);
    text("smoke-status", data.status);
    text("smoke-model", data.model || "openai/gpt-5.4");
    text("smoke-latency", String(data.latencyMs));
    text("smoke-http", String(data.httpStatus));
    text("smoke-timestamp", data.timestamp);
    var banner = document.getElementById("smoke-banner");
    if (!banner) return;
    banner.classList.remove("is-pending", "is-passed", "is-failed");
    banner.classList.add("is-passed");
    banner.textContent = en
      ? "One recorded call returned HTTP " + data.httpStatus + " in " + data.latencyMs + " ms. This is not an uptime or savings claim."
      : "已记录一次调用：HTTP " + data.httpStatus + "，耗时 " + data.latencyMs + " ms。这不是可用性或省钱承诺。";
  }

  fetch(root + "ofox-smoke-status.json", {cache: "no-store"})
    .then(function (response) { return response.ok ? response.json() : null; })
    .then(function (data) { show(data || {overall: "unverified", status: "unverified"}); })
    .catch(function () { show({overall: "unverified", status: "unverified"}); });
})();
