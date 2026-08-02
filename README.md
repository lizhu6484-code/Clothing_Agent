# 穿搭 Agent

三合一穿搭助手：**穿搭推荐** + **线上购衣** + **线下购衣**。

基于本地运行的 FastAPI + SQLite + 原生 JavaScript 前端，调用 SenseNova VLM/LLM 完成衣物识别与搭配建议，联动天气、GPS 定位、拼多多商品搜索与百度地图附近店铺。

## 功能一览

- **衣橱管理**：拍照 / 上传衣物，VLM 自动识别（品类、颜色、面料、季节、正式度），去重入库
- **穿搭推荐**：衣柜模式（从衣橱选品搭配）+ 自由模式（AI 直接给方案），天气联动
- **配图集**：为推荐单品抓取示意图片（可选，基于图片搜索）
- **线上购衣**：LLM 生成穿搭方案 → 拼多多开放平台搜索对应商品（价格、券、销量）
- **线下购衣**：AI 购衣清单 + 百度地图附近服装店（可选）
- **多使用者档案**：身高体重年龄偏好，影响推荐

## 快速启动

环境要求：Python 3.12 + [uv](https://docs.astral.sh/uv/)

```powershell
cd backend
uv venv .venv --python 3.12
uv pip install -r requirements.txt --python .venv/Scripts/python.exe
cp .env.example .env   # 然后填入 API Key
cd ..
powershell -ExecutionPolicy Bypass -File start.ps1
```

打开 http://localhost:3030 即可使用。

## API Key 配置

### 必填 Key（不填则核心功能不可用）

| Key | 用途 | 获取 |
|-----|------|------|
| `SENSENOVA_API_KEY` | 衣物识别（VLM）+ 推荐生成（LLM） | https://platform.sensenova.cn |
| `QWEATHER_API_KEY` | GPS 天气 | https://dev.qweather.com |

### 可选 Key（不填则对应功能降级）

| Key | 功能 |
|-----|------|
| `PDD_CLIENT_ID` / `PDD_CLIENT_SECRET` / `PDD_PID` | 线上购衣商品搜索 |
| `BAIDU_MAP_AK` | 线下购衣附近店铺 |
| `DASHSCOPE_API_KEY` | 配图集 AI 生图兜底 |

## 运行测试

```powershell
pip install -r backend/requirements-dev.txt
python -m pytest
```

## 项目结构

```
├── backend/                 # FastAPI 后端（端口 8080）
│   ├── app/
│   │   ├── routers/         # API 路由：user / wardrobe / recommend / purchase / shopping
│   │   ├── services/        # LLM / VLM / 天气 / 地图 / 拼多多 / 图片搜索 / 存储
│   │   ├── models/          # Pydantic schema
│   │   └── main.py          # 应用入口
│   ├── grep/                # 配图集图片搜索模块
│   ├── tests/               # pytest 冒烟测试
│   └── .env.example         # 环境变量模板
├── frontend/                # 静态前端（端口 3030，serve.py no-store）
└── start.ps1                # 一键启动前后端
```

## 技术栈

FastAPI + SQLite + vanilla JS（无前端构建），Python 3.12。

## 免责声明

- 本项目为**技术演示 / 学习用途**，非商业产品；AI 推荐仅供参考，不构成穿搭、购物或医疗建议。
- 拼多多商品数据、百度地图店铺数据、天气数据均来自相应第三方平台/厂商，版权归各自所有者；请遵守各平台 API 使用条款。
- 各 API Key 请自行申请并妥善保管，切勿提交到公开仓库。

## 贡献者

- YuLiang Xu
- HongJian Xu ([123457890wasd-cmyk](https://github.com/123457890wasd-cmyk))

## License

[MIT](LICENSE)
