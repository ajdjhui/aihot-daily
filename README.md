# AI HOT 每日邮件日报

每天早上 09:00（北京时间）自动发送 AI HOT 日报到你的邮箱。

## 工作原理

```
GitHub Actions (每天 01:00 UTC)
  → 拉取 aihot.virxact.com 日报 API
  → 渲染为 HTML 邮件
  → 通过 SMTP 发送
```

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd cc8AIHOT
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 SMTP 信息
```

### 3. 本地测试

```bash
pip install -r requirements.txt

# Dry run：只生成 HTML 预览，不发送
python main.py --dry

# 真实发送
python main.py
```

### 4. 部署到 GitHub Actions

1. 推送代码到 GitHub：
   ```bash
   git init && git add -A && git commit -m "AI HOT daily report bot"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. 在 GitHub 仓库 **Settings → Secrets and variables → Actions → Secrets** 中添加：

   | Secret | 说明 |
   |--------|------|
   | `SMTP_HOST` | SMTP 服务器地址 |
   | `SMTP_PORT` | SMTP 端口（如 587） |
   | `SMTP_USER` | 发件人邮箱账号 |
   | `SMTP_PASS` | 发件人邮箱密码 |
   | `TO_EMAIL` | 收件人邮箱 |
   | `FROM_EMAIL` | （可选）发件人显示地址 |

3. 手动触发测试：**Actions → AI HOT Daily Report → Run workflow**

4. 之后每天北京时间 09:00 自动发送，无需额外操作。

## 常见 SMTP 配置参考

| 邮箱 | SMTP_HOST | SMTP_PORT |
|------|-----------|-----------|
| Gmail | smtp.gmail.com | 587 |
| QQ 邮箱 | smtp.qq.com | 587 |
| 163 邮箱 | smtp.163.com | 465 |
| 企业微信 | smtp.exmail.qq.com | 587 |
| 阿里企业邮 | smtp.mxhichina.com | 587 |

> **注意**：Gmail / QQ 邮箱需要使用「应用专用密码」而非登录密码。
> Gmail: [App Passwords](https://myaccount.google.com/apppasswords)

## 项目结构

```
cc8AIHOT/
├── .github/workflows/daily-report.yml   # GitHub Actions 定时触发
├── src/
│   ├── fetch_report.py                  # 拉取 AI HOT 数据
│   ├── render_email.py                  # 渲染 HTML 邮件
│   └── send_email.py                    # SMTP 发送
├── main.py                              # 主入口
├── requirements.txt
├── .env.example
└── README.md
```

## 降级策略

- 优先拉取 AI HOT 日报（`/api/public/daily`）
- 如果当天日报尚未生成（北京时间 08:00 前），自动降级为拉取过去 24 小时精选条目
- 无数据时跳过发送（不发送空邮件）
