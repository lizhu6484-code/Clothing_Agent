import base64
import json

from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.SENSENOVA_API_KEY,
            base_url=settings.SENSENOVA_BASE_URL,
        )
    return _client

SYSTEM_PROMPT = """你是一个服装识别助手。观察图片中的单件衣物，输出结构化 JSON。

规则：
- 只识别画面中的单件衣物
- 颜色用中文描述（白色 / 深蓝 / 卡其）
- 季节用 ["春","夏","秋","冬"] 的子集
- formality 为 1-5 整数：1=运动居家，3=日常通勤，5=正式商务
- material（面料）必须填写，如：纯棉、涤纶、牛仔布、针织、雪纺、羊毛、真丝、皮革、尼龙等
- type 和 category 必须从以下预设分类中选择：
  上衣 -> 短袖、衬衫、卫衣、毛衣、外套
  下装 -> 长裤(休闲)、长裤(正式)、短裤
  鞋子 -> 运动鞋、休闲鞋
- type 填大类（上衣/下装/鞋子），category 填具体子类（如"短袖""长裤(休闲)"）
- 不确定的字段填 null，不要编造
- 只输出 JSON，不要任何额外文字"""

OUTPUT_SCHEMA_HINT = """输出格式：
{"name":"...","type":"上衣/下装/鞋子","category":"短袖/衬衫/卫衣/毛衣/外套/长裤(休闲)/长裤(正式)/短裤/运动鞋/休闲鞋","color":"...","material":"纯棉/涤纶/牛仔布/针织/...","season":["春","夏"],"formality":2,"style":["休闲"],"features":["圆领","短袖"]}"""


class VLMUnavailableError(Exception):
    pass


def recognize_clothing(image_bytes: bytes) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:image/jpeg;base64,{b64}"

    try:
        resp = _get_client().chat.completions.create(
            model=settings.SENSENOVA_VLM_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"{SYSTEM_PROMPT}\n{OUTPUT_SCHEMA_HINT}"},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": "识别这件衣物"},
                    ],
                },
            ],
        )
    except Exception as e:
        raise VLMUnavailableError(f"VLM request failed: {e}") from e

    return json.loads(resp.choices[0].message.content)
