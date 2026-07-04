import base64
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DEEPSEEK_REST_URL = "https://api.deepseek.com/v1/chat/completions"

# ── System prompt for food image analysis ────────────────────

IMAGE_SYSTEM_PROMPT = """
You are NutriAI, an expert AI nutritionist analyzing food from photos.
Inspect the food image and output a strict JSON object. Do NOT wrap in backticks or add extra text.
Follow this schema exactly:
{
  "title": "Short Chinese meal title",
  "mealType": "早餐" or "午餐" or "晚餐" or "加餐",
  "calories": total integer kcal,
  "protein": total integer grams,
  "carbs": total integer grams,
  "fat": total integer grams,
  "healthScore": "A" or "B" or "C",
  "healthMessage": "Brief Chinese nutritional assessment",
  "items": [
    {
      "name": "Chinese ingredient name",
      "calories": item kcal,
      "protein": item protein grams,
      "carbs": item carbs grams,
      "fat": item fat grams,
      "weightString": "e.g. '1 份, 150克'",
      "alternatives": ["healthier alternative 1", "alternative 2"]
    }
  ]
}
""".strip()

USER_PROMPT = (
    "Analyze this food photo. Identify each dish/ingredient visible "
    "and estimate nutritional values. "
    "Output only the JSON object with Chinese labels and realistic portion estimates."
)


async def analyze_food_image(image_bytes: bytes, mime_type: str) -> dict:
    """Send an image to DeepSeek vision and return structured meal analysis as a dict.

    Raises:
        ValueError: If the API key is not configured.
        httpx.HTTPStatusError: If the DeepSeek API returns an error.
        (KeyError / json.JSONDecodeError): If the response format is unexpected.
    """
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not configured in backend .env")

    image_b64 = base64.b64encode(image_bytes).decode()
    data_uri = f"data:{mime_type};base64,{image_b64}"

    payload = {
        "model": settings.DEEPSEEK_MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": IMAGE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri},
                    },
                ],
            },
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            DEEPSEEK_REST_URL,
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        print("DeepSeek Status:", resp.status_code)
        print("DeepSeek Response:", resp.text[:5000])
        resp.raise_for_status()
        data = resp.json()

    # Navigate OpenAI-compatible response structure
    text = data["choices"][0]["message"]["content"]

    # Remove possible markdown code fence artifacts
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```")
        cleaned = cleaned.strip()

    return json.loads(cleaned)
