# JXZNE AI

JXZNE AI 是一个面向开发者和小团队的 AI 模型聚合入口网站，第一阶段通过 Ofox 合作/推荐计划实现变现。

## 当前版本

- 响应式官网，支持桌面和手机
- GPT / Claude / Gemini / DeepSeek / Qwen 等模型展示
- 开发者接入说明
- 统一转化按钮
- 自定义域名文件：`CNAME -> jxzne.com`

## 联盟链接

`script.js` 里的 `PARTNER_URL` 必须保持 `https://ofox.ai/x/itoken`。页面上的 Ofox 按钮使用 `rel="noopener noreferrer sponsored"`。不要改成不带推荐码的首页，否则消费无法归因。

## Ofox API 冒烟测试

`scripts/ofox-smoke.py` 在环境变量 `OFOX_API_KEY` 非空时，各发一次请求：

- Chat Completions：`POST https://api.ofox.ai/v1/chat/completions`，`Authorization: Bearer`。默认模型是 `openai/gpt-5.4`。2026-11-12 的公开目录 `GET https://api.ofox.ai/v1/models` 包含这个 id，不包含 `openai/gpt-5.6`（目录里的 5.6 系列是 `openai/gpt-5.6-sol`、`openai/gpt-5.6-luna`、`openai/gpt-5.6-terra`）。Ofox 文档写明 `openai/gpt-5.4-pro` 和 Codex 系列只走 Responses API，所以 Chat Completions 不用它们。
- Responses：`POST https://api.ofox.ai/v1/responses`，`Authorization: Bearer`，`max_output_tokens` 16。默认模型是 `qwen/qwen-flash`。2026-11-26 的公开目录里，这是 `supported_endpoints` 含 `/v1/responses` 的最低单价 id。
- Anthropic Messages：`POST https://api.ofox.ai/anthropic/v1/messages`，请求头 `x-api-key` 和 `anthropic-version: 2023-06-01`，`max_tokens` 16。默认模型也是 `qwen/qwen-flash`。同一天的 `GET https://api.ofox.ai/anthropic/v1/models` 把它列为 Anthropic 协议可调用模型，并且单价最低。

一次失败不会跳过另外两次，进程仍以 0 退出，工作流可以记下状态文件。脚本把每项的 `status`、`httpStatus`、`model`、`latencyMs`、`timestamp`、`passedAt`、`endpoint` 和一句事实写入 `ofox-smoke-status.json`。不写入密钥、请求头或模型原文。Chat Completions 失败会清掉自己的 `passedAt`。Responses 和 Messages 失败会留下上一次成功的 `passedAt`，但 `status` 记为 `failed`，页面因此保持未验证。没有 Key 时打印 `BLOCKED_NO_OFOX_API_KEY`，退出码 0，不改状态文件。不要手工把 `overall` 或 `status` 改成通过。

脚本会去掉 Key 里的空白（含回车换行）以及明确列出的不可见粘贴字符（BOM、零宽空格等），再检查剩余内容能否放进 HTTP 头。带 `Bearer `、`Authorization:` 或 `x-api-key:` 前缀时不发请求。引号和其它标点不会被删掉，也不会做 Unicode 兼容转换。去掉这些字符修不了填错、已吊销或没配置的 Key。

这次调用不启动 Codex CLI 或 Claude Code。Ofox 有这两份配置文档，但本仓库没有跑过客户端。Cursor 直接接入仍按 Ofox 兼容性说明记为不合适。

`tests/ofox_smoke.py` 仍是单独的 Responses / Messages 检查，默认模型已改为目录中存在的 `openai/gpt-5.4` 和 `anthropic/claude-sonnet-4.6`。它不负责改写状态文件，不规范化 Key，工作流也不运行它。

### 添加 GitHub Secret 并运行

1. 打开仓库 **Settings → Secrets and variables → Actions → New repository secret**。
2. Name 填 `OFOX_API_KEY`。
3. Value 填 Ofox 控制台里的原始 API Key。不要加 `Bearer ` 前缀，不要加引号。误粘贴的换行和空白由脚本去掉；Key 本身仍必须是控制台里的那一把。
4. 打开 **Actions → Ofox chat completions smoke → Run workflow**。工作流只在手动触发时运行。

Secret 为空时工作流不请求 Ofox，也不提交状态文件。有 Key 且脚本改写了状态文件时，才会把 `ofox-smoke-status.json` 提交到 `main`。

本地不要把密钥写进命令参数或提交到仓库：

```bash
read -rs OFOX_API_KEY
export OFOX_API_KEY
python3 scripts/ofox-smoke.py
```

说明页：<https://jxzne.com/case-study.html> 与 <https://jxzne.com/en/case-study.html>。在真实记录出现之前，页面标明「待实测 / pending real run」。

## 访问统计

`assets/analytics-config.js` 是全站唯一的统计配置，每个 HTML 页面都会引入它和 `assets/analytics.js`。

- `ga4MeasurementId`：GA4 衡量 ID，形如 `G-XXXXXXXX`。留空则不加载 gtag。
- `plausibleDomain`：Plausible 里配置的域名，例如 `jxzne.com`。留空则不加载 Plausible。

两个值都为空时，页面不向统计服务发请求，也不发送联盟点击事件。填上之后，指向 `https://ofox.ai/x/itoken` 的点击会发送 `affiliate_click`（带 `page_path` 和 `cta_position`），复制代码按钮和语言切换也会调用已加载的 `gtag` / `plausible`。怎么在 GA4 和 Plausible 里读这些事件：`docs/affiliate-clicks.md`。不要在这个文件里写 API Key。当前 `ga4MeasurementId` 是 `G-Z959EMH17R`，`plausibleDomain` 仍为空。

## 公开目录价格

`scripts/fetch_ofox_public_prices.py` 不使用密钥，只在 `https://api.ofox.ai/v1/models` 返回 200 和可用的按 token 单价时改写 `ofox-public-prices.json`。没有单价的模型放进 `missing`，不会补一个数字。浏览器若被跨域拦住，开发者页面会标明这份带时间的观察；两次都失败时输入框保持空白，并给出 Ofox 链接。

### 2. 启用 GitHub Pages

在 GitHub 仓库：

`Settings -> Pages -> Build and deployment -> Deploy from a branch`

选择：

- Branch: `main`
- Folder: `/ (root)`

### 3. 配置 jxzne.com DNS

推荐将域名 DNS 指向 GitHub Pages。具体记录以 GitHub Pages Custom Domain 页面实时提示为准。常见配置是：

- `www` 使用 CNAME 指向 GitHub Pages 主机名
- 根域名使用 GitHub Pages 官方提供的 A / AAAA 记录

启用后，在 GitHub Pages 中填写 Custom domain：`jxzne.com`，并开启 HTTPS。

## 本地预览

在仓库根目录启动静态服务，然后打开这些地址：

```bash
python3 -m http.server 8765
```

- <http://127.0.0.1:8765/>
- <http://127.0.0.1:8765/en/>
- <http://127.0.0.1:8765/en/developers.html>
- <http://127.0.0.1:8765/en/guides.html>
- <http://127.0.0.1:8765/compare-aggregators.html>
- <http://127.0.0.1:8765/developers.html#price-compare>

浏览器语言是英文、且没有把本站语言存成中文时，首页会进入 `/en/`。中文入口是 <http://127.0.0.1:8765/?lang=zh>。

## 第二阶段建议

当网站开始有流量后，再升级为真正的 AI API 分销平台：

- 用户注册 / 登录
- 自有 API Key
- 余额充值
- 套餐与加价计费
- 用量统计
- 上游模型路由
- 管理后台
- Stripe / 支付宝 / 微信支付
- 邀请返佣

这一阶段需要后端和数据库，不应该把上游 API Key 放在静态网页中。
