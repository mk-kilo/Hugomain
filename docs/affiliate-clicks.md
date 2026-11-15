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
| `link_url` | 点击的联盟链接，去掉 hash |
| `outbound` | 固定为 `affiliate` |

链接上的 `data-outbound="affiliate"` 用来标明这是联盟外链。新落地页的主按钮使用 `data-cta-position="after-answer"`。

## 在 GA4 里看

1. 填入衡量 ID 并部署页面。
2. 打开 GA4 → 报告 → 实时，或 报告 → 互动 → 事件。
3. 找到事件名 `affiliate_click`。
4. `page_path` 和 `cta_position` 会随事件进入。若要在标准报告里当列使用，把它们注册为事件级自定义维度，维度名称与参数名一致。

## 在 Plausible 里看

1. 填入在 Plausible 里添加的域名，例如 `jxzne.com`。
2. 本站在域名非空时加载 `script.pageview-props.tagged-events.js`，这样自定义事件可以带属性。页面浏览仍会自动记录。
3. 站点设置 → Goals → Add goal → Custom event，事件名填写 `affiliate_click`（大小写一致）。
4. 打开该目标，按属性 `cta_position` 或 `page_path` 拆分，即可看出哪个页面、哪个位置的按钮被点击。

## 本地确认“空配置不发送”

保持两个配置值为空，打开任意页面，在开发者工具的网络面板里过滤 `google-analytics`、`googletagmanager` 和 `plausible`。不应出现这些请求。再点击联盟按钮，地址应直接打开，仍然没有这些请求。
