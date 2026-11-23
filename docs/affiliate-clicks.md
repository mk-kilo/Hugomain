# 联盟点击事件

`assets/analytics.js` 在有人点击 `https://ofox.ai/x/itoken`（可带查询参数或末尾斜杠）时发送事件 `affiliate_click`。其它 `ofox.ai` 链接，例如文档页，不记为联盟点击。

配置在 `assets/analytics-config.js`：

- `ga4MeasurementId` 和 `plausibleDomain` 都为空：不加载 gtag，不加载 Plausible，不发送 `affiliate_click`。点击照常打开链接。
- 只填其中一个：只向已配置的那一家发送。

脚本不会调用 `preventDefault`，也不等待统计请求返回。统计失败不影响跳转。

## 事件字段

| 字段 | 含义 |
| --- | --- |
| `page_path` | 当前页面的路径和查询字符串，不含域名和 hash |
| `cta_position` | CTA 位置。优先读链接上的 `data-cta-position`，否则按所在区域记为 `nav`、`hero`、`footer`、`bottom` 或 `inline` |
| `cta_id` | 链接上的 `data-cta`。没有该属性时为 `unlabeled` |
| `link_url` | 点击的联盟链接，去掉 hash |
| `outbound` | 固定为 `affiliate` |

链接上的 `data-outbound="affiliate"` 用来标明这是联盟外链。新落地页的主按钮使用 `data-cta-position="after-answer"`。

## 在 GA4 里看

当前 `ga4MeasurementId` 是 `G-Z959EMH17R`，`plausibleDomain` 仍为空。加载器会插入 `https://www.googletagmanager.com/gtag/js?id=G-Z959EMH17R`。点击 `https://ofox.ai/x/itoken` 时，处理函数立刻调用 `gtag('event', 'affiliate_click', { page_path, cta_position, cta_id, ... })`。它不调用 `preventDefault`，也不等待统计请求返回，跳转不会被 GA4 拖住。

`affiliate_click` 出现在这两个地方：

1. **实时（Realtime）**：GA4 → 报告 → 实时。部署后打开页面并点击联盟链接，事件名 `affiliate_click` 会出现在实时事件里。点开该事件可以看到这次点击的页面路径，以及参数 `cta_position` 和 `cta_id`。
2. **DebugView**：GA4 → 管理 → 数据展示 → DebugView。这里只显示带调试标记的命中。用 Chrome 的 Google Analytics Debugger 扩展，或用 Tag Assistant 打开本站后再点击联盟链接。事件详情里同样有页面路径、`cta_position` 和 `cta_id`。地址栏的 `?analytics_debug=1` 只在浏览器控制台打印预览，不会单独把命中送进 DebugView。

标准报告（报告 → 互动 → 事件）里可以按事件名看到 `affiliate_click` 的次数。`cta_position` 和 `cta_id` 默认不会变成报告里的列。要把它们当维度使用，注册为事件级自定义维度：

1. GA4 → 管理 → 数据展示 → 自定义定义 → 创建自定义维度。
2. 范围选择「事件」。
3. 建两个维度。维度名称和事件参数都与参数名一致：一个是 `cta_position`，另一个是 `cta_id`。
4. 保存后只对之后新到的事件生效，不会回填注册前的命中。有新点击之后，才能在探索或标准报告里按这两个维度拆分。

`page_path` 会传给 `gtag('event', ...)`。GA4 把它记成这次点击所在的页面路径（含查询字符串）。实时和 DebugView 里它就是该事件的页面，标准报告里用自带的网页路径拆分。这不是自定义参数，不用再注册成自定义维度。

## 在 Plausible 里看

1. 填入在 Plausible 里添加的域名，例如 `jxzne.com`。
2. 本站在域名非空时加载 `script.pageview-props.tagged-events.js`，这样自定义事件可以带属性。页面浏览仍会自动记录。
3. 站点设置 → Goals → Add goal → Custom event，事件名填写 `affiliate_click`（大小写一致）。
4. 打开该目标，按属性 `cta_position` 或 `page_path` 拆分，即可看出哪个页面、哪个位置的按钮被点击。

## 本地确认“空配置不发送”

保持两个配置值为空，打开任意页面，在开发者工具的网络面板里过滤 `google-analytics`、`googletagmanager` 和 `plausible`。不应出现这些请求。再点击联盟按钮，地址应直接打开，仍然没有这些请求。
