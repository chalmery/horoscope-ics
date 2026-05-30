#!/usr/bin/env python3
"""Generate daily horoscope ICS files using DeepSeek API and upload to OSS."""

import os
import json
import math
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# 自动加载项目根目录 .env 文件
_ENV_FILE = Path(__file__).parent / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            _key, _val = _key.strip(), _val.strip().strip('"').strip("'")
            if _key not in os.environ:
                os.environ[_key] = _val

# ============================================================
# 12星座定义
# ============================================================

SIGNS = [
    {"name": "白羊座", "emoji": "♈️", "range": "3.21-4.19", "element": "火", "ruler": "火星", "color": "#ff3b30"},
    {"name": "金牛座", "emoji": "♉️", "range": "4.20-5.20", "element": "土", "ruler": "金星", "color": "#ff9500"},
    {"name": "双子座", "emoji": "♊️", "range": "5.21-6.21", "element": "风", "ruler": "水星", "color": "#ffcc00"},
    {"name": "巨蟹座", "emoji": "♋️", "range": "6.22-7.22", "element": "水", "ruler": "月亮", "color": "#34c759"},
    {"name": "狮子座", "emoji": "♌️", "range": "7.23-8.22", "element": "火", "ruler": "太阳", "color": "#ff3b30"},
    {"name": "处女座", "emoji": "♍️", "range": "8.23-9.22", "element": "土", "ruler": "水星", "color": "#af52de"},
    {"name": "天秤座", "emoji": "♎️", "range": "9.23-10.23", "element": "风", "ruler": "金星", "color": "#ff9500"},
    {"name": "天蝎座", "emoji": "♏️", "range": "10.24-11.22", "element": "水", "ruler": "冥王星", "color": "#ff3b30"},
    {"name": "射手座", "emoji": "♐️", "range": "11.23-12.21", "element": "火", "ruler": "木星", "color": "#ffcc00"},
    {"name": "摩羯座", "emoji": "♑️", "range": "12.22-1.19", "element": "土", "ruler": "土星", "color": "#af52de"},
    {"name": "水瓶座", "emoji": "♒️", "range": "1.20-2.18", "element": "风", "ruler": "天王星", "color": "#0a84ff"},
    {"name": "双鱼座", "emoji": "♓️", "range": "2.19-3.20", "element": "水", "ruler": "海王星", "color": "#34c759"},
]

# 名人名言备用库
QUOTES = [
    "「星星从不着急，它们只是亮着。」—— 村上春树 🌟",
    "「你今天受的苦，都会变成未来的糖。」—— 蔡康永 🍬",
    "「既然上了生活的贼船，那就做个快乐的海盗。」🏴‍☠️",
    "「别太较真，你看星星多放松。」🌌",
    "「今天是余生中最年轻的一天，冲！」⚡",
    "「万物皆有裂痕，那是光照进来的地方。」—— 莱昂纳德·科恩 💡",
    "「人生不像做饭，不能等万事俱备了才下锅。」—— 李安 🍳",
    "「做你自己，因为别人都有人做了。」—— 王尔德 🎭",
    "「开心是一天，不开心也是一天，不如开心。」—— 某位智者 😊",
    "「宇宙山河浪漫，生活点滴温暖。」🌠",
    "「不要慌，不要慌，太阳下山有月光。」🌙",
    "「你所热爱的，就是你的生活。」🔥",
]

# 搞怪彩蛋备用库
FUNNY_TIPS = [
    "🐱 今日幸运物：公司楼下那只流浪猫",
    "🍜 今日幸运食物：泡面加蛋，法力无边",
    "📱 今日禁忌：睡前刷手机超过30分钟",
    "☕ 今日能量来源：老板不在时偷喝的那杯奶茶",
    "💤 今日警语：闹钟响了就起吧，再睡也不会穿越",
    "🚇 今日幸运地点：地铁2号线第三节车厢",
    "🎵 今日BGM：洗澡时自己瞎哼的那首歌",
    "👟 今日幸运穿搭：穿反了也没人发现的袜子",
    "🌧️ 今日锦囊：包里常备一把伞，比男朋友靠谱",
    "🪴 今日能量动作：对着一盆绿植深呼吸三次",
    "🍰 今日小确幸：下午三点的那块蛋糕",
    "📸 今日不宜：翻前任的朋友圈",
]

OUTPUT_DIR = Path(__file__).parent / "output"


# ============================================================
# 天象计算（简化版）
# ============================================================

def get_sun_sign(d: date) -> dict:
    """根据日期返回太阳所在的星座。"""
    md = (d.month, d.day)
    for sign in [
        ("摩羯座", "♑️", (1, 1), (1, 19)),
        ("水瓶座", "♒️", (1, 20), (2, 18)),
        ("双鱼座", "♓️", (2, 19), (3, 20)),
        ("白羊座", "♈️", (3, 21), (4, 19)),
        ("金牛座", "♉️", (4, 20), (5, 20)),
        ("双子座", "♊️", (5, 21), (6, 21)),
        ("巨蟹座", "♋️", (6, 22), (7, 22)),
        ("狮子座", "♌️", (7, 23), (8, 22)),
        ("处女座", "♍️", (8, 23), (9, 22)),
        ("天秤座", "♎️", (9, 23), (10, 23)),
        ("天蝎座", "♏️", (10, 24), (11, 22)),
        ("射手座", "♐️", (11, 23), (12, 21)),
        ("摩羯座", "♑️", (12, 22), (12, 31)),
    ]:
        name, emoji, start, end = sign
        if (d.month == start[0] and d.day >= start[1]) or \
           (d.month == end[0] and d.day <= end[1]):
            return {"name": name, "emoji": emoji}
    return {"name": "摩羯座", "emoji": "♑️"}


def calc_moon_phase(d: date) -> dict:
    """计算近似月相。参考点：2000-01-06 新月"""
    ref = date(2000, 1, 6)
    days = (d - ref).days
    cycle = 29.530588
    pct = (days % cycle) / cycle

    if pct < 0.035:
        name, emoji = "新月", "🌑"
    elif pct < 0.125:
        name, emoji = "蛾眉月", "🌒"
    elif pct < 0.215:
        name, emoji = "上弦月", "🌓"
    elif pct < 0.465:
        name, emoji = "盈凸月", "🌔"
    elif pct < 0.535:
        name, emoji = "满月", "🌕"
    elif pct < 0.785:
        name, emoji = "亏凸月", "🌖"
    elif pct < 0.875:
        name, emoji = "下弦月", "🌗"
    elif pct < 0.965:
        name, emoji = "残月", "🌘"
    else:
        name, emoji = "新月", "🌑"

    return {"name": name, "emoji": emoji, "phase_day": round(days % cycle, 1)}


def get_celestial_context(d: date) -> str:
    """构建给 AI 的天象背景描述。"""
    sun = get_sun_sign(d)
    moon = calc_moon_phase(d)

    ctx = f"日期：{d.strftime('%Y年%m月%d日')}\n"
    ctx += f"太阳位于：{sun['emoji']} {sun['name']}\n"
    ctx += f"月相：{moon['emoji']} {moon['name']}（月相周期第{moon['phase_day']}天，周期29.5天）\n"
    return ctx


# ============================================================
# DeepSeek API
# ============================================================

def build_prompt(sign: dict, d: date, celestial: str) -> str:
    """构建生成运势的 prompt。"""
    return f"""你是一位擅长撰写「现代年轻人爱看的星座日报」的编辑。

不要机械描述星座性格。
不要重复刻板印象。

你的任务是：
根据当天星象与星座能量，
推测用户在现实生活中最可能遇到的具体场景、情绪和事件。

重点关注：
* 工作中的变化
* 社交中的互动
* 感情中的微妙信号
* 金钱与消费冲动
* 偶遇与巧合
* 当代互联网生活
* 情绪波动与内心独白

写作要求：
1. 像朋友聊天，而不是占星师讲课
2. 多写具体场景，少写抽象概念
3. 不解释星座理论
4. 不分析星座性格
5. 让读者感觉“这件事可能真的发生”
6. 允许轻微幽默和网络感
7. 每篇120~200字
8. 保持神秘感，不要下结论
9. 避免使用“你是{sign['name']}所以……”这类表达
10. 输出必须像朋友圈看到的今日运势

## 今日天象
{celestial}

## 输出 JSON 格式
```json
{{
  "stars": 3,
  "summary": "一句话摘要，8字以内",
  "trend": "【今日趋势】场景化描述，120~200字，像朋友聊天，讲可能发生的具体事件和情绪",
  "quote": "今日一句，简短有力量，不要总是名人名言，可以是有感而发的话",
  "tip": "幸运小物，有趣、生活化、略带巧合感的物品或事件"
}}
```

stars 取值 1-5。请确保输出合法 JSON。"""


def call_deepseek(sign: dict, d: date, api_key: str) -> dict:
    """调用 DeepSeek API 生成运势。"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    celestial = get_celestial_context(d)

    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": "你是一位幽默专业的占星师，总是输出合法JSON。"},
            {"role": "user", "content": build_prompt(sign, d, celestial)},
        ],
        temperature=0.9,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    result = json.loads(raw)

    # 校验必要字段
    required = ["stars", "summary", "trend", "quote", "tip"]
    for key in required:
        if key not in result:
            raise ValueError(f"DeepSeek 返回缺少字段: {key}")

    result["stars"] = max(1, min(5, int(result["stars"])))
    return result


# ============================================================
# ICS 文件生成
# ============================================================

def generate_ics(sign: dict, d: date, data: dict) -> str:
    """生成单个 ICS 文件内容。"""
    dt = d.strftime("%Y%m%d")
    dt_end = (d + timedelta(days=1)).strftime("%Y%m%d")
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    uid = f"horoscope-{sign['name']}-daily@deepseek"

    stars_line = "★" * data["stars"] + "☆" * (5 - data["stars"])
    summary = f"{sign['emoji']} {sign['name']} · {data['summary']}"

    description = f"""{stars_line}

{data['trend']}

📜 今日一句：
{data['quote']}

🎲 幸运小物：
{data['tip']}

🔮 由 DeepSeek AI 生成 · 每日更新 ✨"""

    # 转义 ICS 特殊字符
    def ics_text(s: str) -> str:
        return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    return f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Horoscope//Daily//CN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:{sign['emoji']} {sign['name']} · 每日运势
X-WR-CALDESC:AI 生成的星座每日运势
REFRESH-INTERVAL;VALUE=DURATION:PT12H
X-PUBLISHED-TTL:PT12H
BEGIN:VEVENT
DTSTART;VALUE=DATE:{dt}
DTEND;VALUE=DATE:{dt_end}
DTSTAMP:{now_utc}
UID:{uid}
SUMMARY:{ics_text(summary)}
DESCRIPTION:{ics_text(description)}
TRANSP:TRANSPARENT
CATEGORIES:星座运势
END:VEVENT
END:VCALENDAR"""


# ============================================================
# OSS 上传
# ============================================================

def upload_to_oss(file_path: Path, object_name: str, config: dict):
    """上传文件到阿里云 OSS。"""
    import oss2

    auth = oss2.Auth(config["access_key_id"], config["access_key_secret"])
    bucket = oss2.Bucket(auth, config["endpoint"], config["bucket_name"])

    bucket.put_object_from_file(
        object_name,
        str(file_path),
        headers={
            "Content-Type": "text/calendar; charset=utf-8",
            "x-oss-object-acl": "public-read",
        },
    )
    print(f"  ✅ 已上传: {object_name}")


# ============================================================
# fallback 内容（API 失败时使用）
# ============================================================

def get_fallback_data(sign: dict, idx: int) -> dict:
    """当 API 调用失败时，使用备用模板。"""
    import random
    rng = random.Random(f"{date.today().toordinal()}-{idx}")

    stars = rng.randint(3, 5)

    trends = [
        f"今天的能量有点特别。你可能会在下午三点左右收到一条消息，内容让你犹豫要不要立刻回复——先放一放，答案自己会浮现。",
        f"某个反复出现的小问题今天终于让你决定动手解决。过程比想象中顺利，可能是因为你终于愿意面对它了。",
        f"今天适合做一些「不太划算」的事。比如绕路去买一杯特定的咖啡，或者给很久没联系的人发一句「最近怎么样」。",
        f"身边某个人的情绪今天会很明显，但未必是说出来的那部分。你察觉到了，也不用点破——有时候保持沉默是更好的温柔。",
    ]

    return {
        "stars": stars,
        "summary": ["消息值得等", "动手就有转机", "绕路也有风景", "沉默也是回应"][idx % 4],
        "trend": trends[idx % len(trends)],
        "quote": QUOTES[idx % len(QUOTES)],
        "tip": FUNNY_TIPS[idx % len(FUNNY_TIPS)],
    }


# ============================================================
# 主流程
# ============================================================

def process_sign(sign: dict, idx: int, today: date, api_key: str, use_oss: bool, oss_config: dict):
    """处理单个星座：调 API → 生成 ICS → 上传（并发执行）"""
    name = sign["name"]
    prefix = f"{sign['emoji']} {name}"

    try:
        data = call_deepseek(sign, today, api_key)
        stars = "★" * data["stars"] + "☆" * (5 - data["stars"])
        print(f"  {prefix} {stars} {data['summary']}")
        print(f"    📝 {data['trend'][:60]}...")
    except Exception as e:
        print(f"  {prefix} ⚠️ API 失败: {e}")
        data = get_fallback_data(sign, idx)

    ics_content = generate_ics(sign, today, data)
    filename = f"{name}.ics"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(ics_content, encoding="utf-8")
    print(f"    📄 {filename} ({len(ics_content)} bytes)")

    if use_oss:
        try:
            upload_to_oss(filepath, filename, oss_config)
        except Exception as e:
            print(f"    ⚠️ OSS 上传失败: {e}")

    return name


def main():
    today = date.today()
    print(f"🔮 生成今日运势 ICS — {today.strftime('%Y年%m月%d日')}")
    print(f"☀️  太阳位于：{get_sun_sign(today)['emoji']} {get_sun_sign(today)['name']}")
    moon = calc_moon_phase(today)
    print(f"🌙 月相：{moon['emoji']} {moon['name']}")

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("❌ 未设置 DEEPSEEK_API_KEY 环境变量")
        return 1

    oss_config = {
        "access_key_id": os.environ.get("OSS_ACCESS_KEY_ID", ""),
        "access_key_secret": os.environ.get("OSS_ACCESS_KEY_SECRET", ""),
        "bucket_name": os.environ.get("OSS_BUCKET_NAME", ""),
        "endpoint": os.environ.get("OSS_ENDPOINT", ""),
    }
    use_oss = all(oss_config.values())

    OUTPUT_DIR.mkdir(exist_ok=True)

    # 12星座全部并发请求
    print(f"\n🚀 同时生成 12 星座运势...\n{'-'*40}")
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = {
            pool.submit(process_sign, sign, idx, today, api_key, use_oss, oss_config): sign["name"]
            for idx, sign in enumerate(SIGNS)
        }
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"  ❌ {futures[f]} 失败: {e}")

    print(f"\n{'='*40}")
    print(f"✅ 完成！生成 {len(SIGNS)} 个 ICS 文件 → {OUTPUT_DIR}")
    if use_oss:
        endpoint = oss_config["endpoint"]
        bucket = oss_config["bucket_name"]
        print(f"📤 已上传到 OSS: https://{bucket}.{endpoint}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
