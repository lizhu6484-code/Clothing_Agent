# 穿搭 Agent（合并版）

三合一穿搭助手：穿搭推荐 + 线上购衣 + 线下购衣。

## 快速启动

```powershell
cd backend
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv/Scripts/python.exe
cp .env.example .env   # 然后填入 API Key
cd ..
powershell -ExecutionPolicy Bypass -File start.ps1
```

打开 http://localhost:3030 即可使用。

## 必填 API Key

| Key | 用途 | 获取 |
|-----|------|------|
| `SENSENOVA_API_KEY` | 衣物识别 + 推荐生成 | https://platform.sensenova.cn |
| `QWEATHER_API_KEY` | GPS天气 | https://dev.qweather.com |

## 可选 Key（不填则对应功能降级）

| Key | 功能 |
|-----|------|
| `PDD_CLIENT_ID` / `SECRET` / `PID` | 线上购衣商品搜索 |
| `BAIDU_MAP_AK` | 线下购衣附近店铺 |
| `DASHSCOPE_API_KEY` | 配图集AI生图兜底 |

## 功能结构

- **穿搭推荐**：衣橱（拍照识别）+ 推荐（衣柜/自由模式，天气联动，配图集）
- **购衣推荐**：线上（LLM方案+拼多多商品）+ 线下（AI建议+附近店铺）
- **知识卡片**：占位，后续接入

## 端口

- 后端：8080
- 前端：3030

## 技术栈

FastAPI + SQLite + 静态前端（vanilla JS），Python 3.12。
