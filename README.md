# 🔮 星座每日运势 ICS

AI 生成12星座每日运势，托管到阿里云 OSS，iPhone 日历订阅即可每天查看。

## 工作流程

```
GitHub Actions (每日 6:00 UTC+8)
    │
    ├── 计算当日天象（太阳星座、月相）
    ├── 并发调用 DeepSeek API（12星座）
    ├── 生成 12 个 .ics 文件
    └── 上传阿里云 OSS（公共读）
```

## 快速开始

### 1. 环境变量

本地调试创建 `.env`：

```bash
DEEPSEEK_API_KEY=sk-xxx
OSS_ACCESS_KEY_ID=xxx          # 可选，不上传 OSS 可省略
OSS_ACCESS_KEY_SECRET=xxx
OSS_BUCKET_NAME=xxx
OSS_ENDPOINT=oss-cn-xxx.aliyuncs.com
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 本地运行

```bash
python generate_ics.py
# ICS 文件输出到 output/ 目录
```

### 4. iPhone 订阅

1. 将 ICS 文件上传到公网可访问的位置（如阿里云 OSS）
2. iPhone 打开 **设置 → 日历 → 账户 → 添加账户 → 其他 → 添加已订阅的日历**
3. 输入 ICS 文件 URL，如 `https://your-bucket.oss-cn-xxx.aliyuncs.com/白羊座.ics`

## GitHub Actions

在仓库 Settings → Secrets and variables → Actions → Secrets 添加：

| Secret | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `OSS_ACCESS_KEY_ID` | 阿里云 AccessKey ID |
| `OSS_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret |
| `OSS_BUCKET_NAME` | OSS Bucket 名称 |
| `OSS_ENDPOINT` | OSS Endpoint |

每天北京时间 6:00 自动触发，也可在 Actions 页面手动触发。

## ICS 订阅地址

```
https://<bucket>.<endpoint>/白羊座.ics
https://<bucket>.<endpoint>/金牛座.ics
...
https://<bucket>.<endpoint>/双鱼座.ics
```
