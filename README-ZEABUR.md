# 🚗 汽修系统 - Zeabur 部署指南

## 第一步：Zeabur 创建项目

1. 打开 https://zeabur.com 并登录
2. 点 **「新建项目」** → 取名 `garage-system`
3. 点 **「新建服务」** → 选 **「从文件夹部署」**

## 第二步：上传代码

1. 打开本文件夹（`garage-system-deploy/`）
2. **把整个文件夹拖拽** 到 Zeabur 的上传区域
3. Zeabur 会自动检测 `Dockerfile` 并开始构建
4. 等待构建完成（约 2-3 分钟）

## 第三步：添加 PostgreSQL 数据库

1. 在 Zeabur 项目里点 **「新建服务」**
2. 选 **「数据库」** → **「PostgreSQL」**
3. Zeabur 会自动把数据库连接信息注入到后端的环境变量

## 第四步：配置环境变量（如果第三步没自动注入）

在 Zeabur 后端服务的 **「环境变量」** 中设置：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `APP_NAME` | 汽修智能管理系统 | - |
| `APP_VERSION` | 0.1.0 | - |
| `DEBUG` | false | 生产环境关掉调试 |
| `VOLC_ARK_API_KEY` | ark-xxx... | 火山引擎方舟密钥（已配置） |
| `VOLC_ARK_BASE_URL` | https://ark.cn-beijing.volces.com/api/v3 | - |

## 第五步：绑定域名

1. Zeabur 会给你的服务分配 `xxx.zeabur.app` 域名
2. 点 **「域名」** → 自定义域名可选（比如 `api.你的.com`）

## ✅ 部署完成！

你的系统会跑在 `https://xxx.zeabur.app` （Zeabur 给你的域名）

### 小程序对接

拿到域名后，改 `miniprogram/app.js` 里的 `baseUrl`：

```js
baseUrl: 'https://xxx.zeabur.app/api'
```

然后在小程序后台（mp.weixin.qq.com）→ 开发 → 开发设置 → 服务器域名：
```
https://xxx.zeabur.app
```
