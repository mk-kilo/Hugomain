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

`tests/ofox_smoke.py` 只在环境变量 `OFOX_API_KEY` 非空时请求 Ofox。它覆盖 OpenAI Responses 和 Anthropic Messages 各一次，**不启动 Codex CLI 或 Claude Code**。仓库里的 `ofox-smoke-status.json` 默认是 `unverified`。测试失败、密钥为空或密钥格式不对时，工作流不会把状态改成通过。

本仓库当前没有记录到成功的认证调用。在 Actions 真正通过之前，页面徽章保持未验证。不要手工把 `overall` 改成 `api_smoke_passed`。

### 添加 GitHub Secret 并运行

1. 打开仓库 **Settings → Secrets and variables → Actions → New repository secret**。
2. Name 填 `OFOX_API_KEY`。
3. Value 填 Ofox 控制台里的原始 API Key。不要加 `Bearer ` 前缀，不要带引号或换行。
4. 打开 **Actions → Ofox API Compatibility Smoke Test → Run workflow**。

工作流只在 `tests/ofox_smoke.py` 退出码为 0 之后运行 `scripts/record_smoke_status.py`。那一步只把 `openai_responses` 和 `anthropic_messages` 写成 `passed`，并提交 `ofox-smoke-status.json`。`codex_cli` 和 `claude_code` 保持 `unverified`。Cursor 保持 Ofox 文档中的不兼容说明。

密钥缺失时脚本打印 `BLOCKED_NO_OFOX_API_KEY` 并以状态码 2 退出，状态文件不动。

本地不要把密钥写进命令参数或提交到仓库。在当前 shell 里导出后再跑：

```bash
read -rs OFOX_API_KEY
export OFOX_API_KEY
python3 tests/ofox_smoke.py
```

工作流里的默认模型是 `openai/gpt-5.6` 和 `anthropic/claude-sonnet-4.6`。2026-10-29 的未登录公开目录里没有这两个 id（Claude 的文本单价也没有被记录）。如果冒烟测试返回模型不存在，在仓库变量或工作流环境里把 `OFOX_RESPONSES_MODEL` / `OFOX_ANTHROPIC_MODEL` 改成 Ofox 当前在售的 id，而不是把失败改成通过。

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
