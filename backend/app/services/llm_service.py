import os
import asyncio
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 不设默认值，避免泄露
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # 秒
REQUEST_TIMEOUT = 30.0  # 秒


async def explain_code(file_path: str, code: str) -> str:
    """调用 DeepSeek 解释代码，带重试和降级处理。"""
    if not DEEPSEEK_API_KEY:
        logger.info("未配置 DEEPSEEK_API_KEY，使用本地解释模式")
        return local_explanation(file_path, code)

    prompt = f"""
你是资深代码导师。请用中文解释下面文件：

文件路径：{file_path}

要求：
1. 说明这个文件的职责
2. 列出关键函数/类
3. 解释主要执行流程
4. 给新手阅读建议

代码：
```text
{code[:12000]}
```
"""

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        except httpx.TimeoutException:
            last_error = f"请求超时（第 {attempt} 次）"
            logger.warning(last_error)
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}（第 {attempt} 次）"
            logger.warning(last_error)
            # 4xx 错误不重试（除了 429 限流）
            if e.response.status_code < 500 and e.response.status_code != 429:
                break
        except Exception as e:
            last_error = f"未知错误: {e}（第 {attempt} 次）"
            logger.warning(last_error)

        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY * attempt)  # 指数退避

    # 所有重试失败，降级到本地解释
    logger.warning(f"DeepSeek 调用失败，降级到本地解释: {last_error}")
    return local_explanation(file_path, code)


def local_explanation(file_path: str, code: str) -> str:
    lines = code.splitlines()
    return f"""
## 本地解释模式

当前没有配置 DeepSeek API Key，所以返回基础解释。

文件：`{file_path}`

代码行数：{len(lines)}

建议阅读方式：

1. 先看 import，了解依赖。
2. 再看类和函数定义。
3. 找入口函数，例如 main、app、handler、router。
4. 结合架构图查看它与其他文件的关系。
"""
