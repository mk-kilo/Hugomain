/* Reads /ofox-smoke-status.json and prints only what that file supports.
   Unverified, or a null latencyMs or timestamp, stays "not yet verified"
   with no invented latency or time. */
(function () {
  var nodes = document.querySelectorAll("[data-api-status]");
  if (!nodes.length) return;

  function stateNode(node) {
    return node.querySelector("[data-api-status-state]");
  }

  function extraNode(node) {
    return node.querySelector("[data-api-status-extra]");
  }

  function showUnverified(node) {
    var state = stateNode(node);
    var extra = extraNode(node);
    if (state) state.textContent = "not yet verified";
    if (extra) {
      extra.textContent = "";
      extra.hidden = true;
    }
  }

  nodes.forEach(showUnverified);

  fetch("/ofox-smoke-status.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) throw new Error("status");
      return response.json();
    })
    .then(function (data) {
      var status = data && data.status;
      var overall = data && data.overall;
      var latency = data ? data.latencyMs : null;
      var timestamp = data ? data.timestamp : null;
      var verified = data &&
        status &&
        status !== "unverified" &&
        overall !== "unverified" &&
        latency != null &&
        timestamp != null;
      nodes.forEach(function (node) {
        if (!verified) {
          showUnverified(node);
          return;
        }
        var state = stateNode(node);
        var extra = extraNode(node);
        if (state) state.textContent = String(status);
        if (extra) {
          extra.hidden = false;
          extra.textContent = "latencyMs " + String(latency) + " · " + String(timestamp);
        }
      });
    })
    .catch(function () {
      nodes.forEach(showUnverified);
    });
})();
