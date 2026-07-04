import base64
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_REST_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

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
    """Send an image to Gemini and return structured meal analysis as a dict.

    Raises:
        ValueError: If the API key is not configured.
        httpx.HTTPStatusError: If the Gemini API returns an error.
        (KeyError / json.JSONDecodeError): If the response format is unexpected.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in backend .env")

    image_b64 = base64.b64encode(image_bytes).decode()
    url = GEMINI_REST_URL.format(model=settings.GEMINI_MODEL_NAME)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": USER_PROMPT},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": image_b64,
                        }
                    },
                ]
            }
        ],
        "systemInstruction": {
            "parts": [{"text": IMAGE_SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{url}?key={settings.GEMINI_API_KEY}",
            json=payload,
        )
        print("Gemini Status:", resp.status_code)
        print("Gemini Response:", resp.text[:5000])
        resp.raise_for_status()
        data = resp.json()

    # Navigate Gemini response structure to extract the text JSON
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    # Remove possible markdown code fence artifacts
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```")
        cleaned = cleaned.strip()

    return json.loads(cleaned)
