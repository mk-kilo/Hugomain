# JXZNE AI

JXZNE AI 是一个面向开发者和小团队的 AI 模型聚合入口网站，第一阶段通过 Ofox 合作/推荐计划实现变现。

## 当前版本

- 响应式官网，支持桌面和手机
- GPT / Claude / Gemini / DeepSeek / Qwen 等模型展示
- 开发者接入说明
- 统一转化按钮
- 自定义域名文件：`CNAME -> jxzne.com`

## 变现前必须完成

### 1. 替换 Ofox 推荐链接

打开 `script.js`：

```js
const PARTNER_URL = 'https://ofox.ai/';
```

把它替换成你在 Ofox 后台获得的个人推荐/合作链接。只有这样，从 jxzne.com 注册并消费的用户才可能归因到你的账户并产生佣金。

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
