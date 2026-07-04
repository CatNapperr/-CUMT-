"""Populate the database with realistic mock meal data for testing."""

import uuid
from datetime import date
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.meal import Meal
from app.models.meal_item import MealItem
from app.models.meal_item_alternative import MealItemAlternative

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

# ── Meal definitions ──────────────────────────────────────────

MealDef = dict[str, object]
ItemDef = dict[str, object]


def item(
    name: str,
    calories: int,
    protein: int = 0,
    carbs: int = 0,
    fat: int = 0,
    weight_grams: int | None = None,
    weight_string: str = "",
    alternatives: list[str] | None = None,
) -> ItemDef:
    return {
        "name": name,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "weight_grams": weight_grams,
        "weight_string": weight_string,
        "alternatives": alternatives or [],
    }


def meal(
    meal_date: date,
    meal_type: str,
    time_string: str,
    title: str,
    items: list[ItemDef],
    notes: str = "",
) -> MealDef:
    total_cal = sum(i["calories"] for i in items)
    total_protein = sum(i["protein"] for i in items)
    total_carbs = sum(i["carbs"] for i in items)
    total_fat = sum(i["fat"] for i in items)
    return {
        "meal_date": meal_date,
        "meal_type": meal_type,
        "time_string": time_string,
        "title": title,
        "calories": total_cal,
        "protein": total_protein,
        "carbs": total_carbs,
        "fat": total_fat,
        "notes": notes,
        "items": items,
        "is_collected": False,
        "is_liked": None,
        "health_score": None,
        "health_message": None,
        "source": "manual_mock",
    }


# ── Data ──────────────────────────────────────────────────────

SEED_MEALS: list[MealDef] = [
    # ── Monday May 25 ──
    meal(date(2026, 5, 25), "breakfast", "08:15", "全麦无糖高纤燕麦包 + 豆浆", [
        item("全麦燕麦包", 195, 8, 36, 3, 120, "1个, 120克", ["杂粮馒头", "蒸红薯"]),
        item("无糖豆浆", 65, 6, 3, 3, 300, "1杯, 300毫升"),
    ]),
    meal(date(2026, 5, 25), "lunch", "12:30", "番茄鸡蛋面 + 凉拌黄瓜", [
        item("番茄鸡蛋面", 380, 14, 58, 8, 400, "1碗, 400克", ["荞麦面版", "米线版"]),
        item("凉拌黄瓜", 35, 1, 4, 2, 100, "1份, 100克"),
    ]),
    meal(date(2026, 5, 25), "dinner", "18:45", "香煎鸡胸肉 + 西兰花 + 杂粮饭", [
        item("香煎鸡胸肉", 220, 42, 2, 5, 150, "1份, 150克", ["烤三文鱼", "卤牛肉"]),
        item("蒜蓉西兰花", 55, 4, 8, 1, 120, "1份, 120克"),
        item("杂粮饭", 170, 4, 36, 1, 180, "1碗, 180克"),
    ]),

    # ── Tuesday May 26 ──
    meal(date(2026, 5, 26), "breakfast", "07:50", "鸡蛋灌饼 + 小米粥", [
        item("鸡蛋灌饼", 280, 10, 30, 12, 150, "1个, 150克"),
        item("小米粥", 90, 2, 18, 1, 250, "1碗, 250毫升"),
    ]),
    meal(date(2026, 5, 26), "lunch", "12:15", "红烧牛肉面 + 卤蛋", [
        item("红烧牛肉面", 450, 28, 52, 14, 500, "1碗, 500克"),
        item("卤蛋", 70, 6, 1, 5, 50, "1个, 50克"),
    ]),
    meal(date(2026, 5, 26), "dinner", "19:00", "清蒸鲈鱼 + 炒时蔬 + 米饭", [
        item("清蒸鲈鱼", 180, 32, 0, 5, 200, "1条, 200克", ["清蒸鳕鱼", "葱油鸦片鱼"]),
        item("炒时蔬", 60, 2, 8, 2, 150, "1份, 150克"),
        item("白米饭", 185, 4, 42, 1, 150, "1碗, 150克"),
    ]),

    # ── Wednesday May 27 ──
    meal(date(2026, 5, 27), "breakfast", "08:05", "希腊酸奶水果碗 + 坚果", [
        item("希腊酸奶", 120, 15, 8, 3, 200, "1杯, 200克"),
        item("混合莓果", 45, 1, 10, 0, 80, "80克"),
        item("坚果混合物", 110, 4, 4, 10, 20, "20克"),
    ]),
    meal(date(2026, 5, 27), "lunch", "12:00", "精选牛油果大虾轻食沙拉", [
        item("牛油果大虾沙拉", 340, 24, 18, 15, 350, "1份, 350克", ["鸡肉沙拉", "金枪鱼沙拉"]),
    ]),
    meal(date(2026, 5, 27), "dinner", "18:30", "豆腐木耳热汤 + 煎饺", [
        item("豆腐木耳热汤", 131, 11, 12, 5, 300, "1碗, 300克", ["蛋花汤", "味噌汤"]),
        item("煎饺(6个)", 280, 12, 30, 12, 180, "6个, 180克"),
    ]),

    # ── Thursday May 28 ──
    meal(date(2026, 5, 28), "breakfast", "08:30", "牛油果吐司 + 煎蛋", [
        item("牛油果吐司", 220, 7, 22, 12, 120, "1片, 120克"),
        item("煎蛋", 90, 7, 1, 7, 50, "1个, 50克"),
        item("黑咖啡", 5, 0, 0, 0, 200, "1杯, 200毫升"),
    ]),
    meal(date(2026, 5, 28), "lunch", "12:45", "日式亲子丼 + 味噌汤", [
        item("亲子丼", 420, 24, 48, 14, 400, "1碗, 400克"),
        item("味噌汤", 35, 2, 3, 1, 200, "1碗, 200毫升"),
    ]),
    meal(date(2026, 5, 28), "snack", "15:30", "蛋白棒 + 香蕉", [
        item("蛋白棒", 180, 20, 18, 4, 60, "1根, 60克"),
        item("香蕉", 105, 1, 27, 0, 120, "1根, 120克"),
    ]),
    meal(date(2026, 5, 28), "dinner", "19:15", "烤鸡腿 + 烤蔬菜 + 藜麦", [
        item("烤鸡腿(去皮)", 240, 36, 0, 10, 180, "1只, 180克", ["烤鸭胸", "蜜汁叉烧"]),
        item("烤蔬菜拼盘", 80, 3, 12, 3, 200, "1份, 200克"),
        item("藜麦饭", 180, 6, 34, 3, 160, "1碗, 160克"),
    ]),

    # ── Friday May 29 ──
    meal(date(2026, 5, 29), "breakfast", "08:00", "隔夜燕麦杯 + 美式", [
        item("隔夜燕麦杯", 240, 10, 38, 6, 200, "1杯, 200克"),
        item("美式咖啡", 10, 0, 1, 0, 300, "1杯, 300毫升"),
    ]),
    meal(date(2026, 5, 29), "lunch", "12:20", "麻婆豆腐饭 + 酸辣汤", [
        item("麻婆豆腐饭", 420, 18, 54, 14, 450, "1份, 450克"),
        item("酸辣汤", 65, 3, 6, 3, 200, "1碗, 200毫升"),
    ]),
    meal(date(2026, 5, 29), "dinner", "18:11", "豆腐木耳热汤（晚餐加餐）", [
        item("豆腐", 66, 8, 3, 4, 80, "1份, 80克", ["丹贝", "印度芝士"]),
        item("木耳", 8, 1, 2, 0, 30, "1份, 30克", ["香菇", "口蘑"]),
        item("酸辣汤底", 58, 2, 5, 3, 240, "1杯, 240克", ["蛋花汤底", "味噌汤底"]),
    ]),
    meal(date(2026, 5, 29), "dinner", "17:58", "烤鸡 + 白米饭 + 炒青菜（晚餐加餐）", [
        item("嫩煎烤鸡胸肉", 210, 40, 0, 5, 120, "1份, 120克", ["白切鸡", "慢炖鸡胸肉"]),
        item("白米饭", 185, 4, 42, 1, 150, "150克", ["红米饭", "燕麦大麦"]),
        item("炒青菜(油菜)", 66, 3, 8, 2, 100, "1份, 100克", ["清汤生菜", "蒸西兰花"]),
    ]),

    # ── Saturday May 30 ──
    meal(date(2026, 5, 30), "breakfast", "09:00", "法式吐司 + 蜂蜜 + 拿铁", [
        item("法式吐司(2片)", 310, 12, 36, 14, 150, "2片, 150克"),
        item("蜂蜜", 30, 0, 8, 0, 10, "1勺, 10克"),
        item("拿铁咖啡", 120, 8, 9, 6, 250, "1杯, 250毫升"),
    ]),
    meal(date(2026, 5, 30), "lunch", "13:00", "韩式拌饭 + 泡菜", [
        item("韩式拌饭", 480, 22, 62, 16, 500, "1碗, 500克", ["越南米粉", "日式拉面"]),
        item("泡菜", 15, 1, 2, 0, 50, "1份, 50克"),
    ]),
    meal(date(2026, 5, 30), "dinner", "20:00", "香煎安格斯慢烤西冷牛排 + 红酒", [
        item("安格斯西冷牛排", 480, 38, 5, 28, 250, "1份, 250克", ["菲力牛排", "肉眼牛排"]),
        item("烤芦笋", 40, 3, 4, 1, 100, "1份, 100克"),
        item("红酒", 120, 0, 4, 0, 150, "1杯, 150毫升"),
    ]),

    # ── Sunday May 31 ──
    meal(date(2026, 5, 31), "breakfast", "09:30", "班尼迪克蛋 + 橙汁", [
        item("班尼迪克蛋", 350, 18, 28, 20, 200, "1份, 200克"),
        item("鲜榨橙汁", 110, 2, 26, 0, 250, "1杯, 250毫升"),
    ]),
    meal(date(2026, 5, 31), "lunch", "12:10", "泰式绿咖喱鸡 + 米饭", [
        item("泰式绿咖喱鸡", 400, 26, 28, 22, 350, "1份, 350克"),
        item("茉莉香米饭", 200, 4, 46, 1, 180, "1碗, 180克"),
    ]),
    meal(date(2026, 5, 31), "dinner", "18:00", "涮火锅（家庭版）", [
        item("火锅牛肉片", 280, 32, 0, 16, 150, "1盘, 150克"),
        item("火锅蔬菜拼盘", 80, 4, 12, 2, 300, "1份, 300克"),
        item("火锅豆腐", 70, 8, 2, 4, 100, "1份, 100克"),
        item("蘸料", 120, 2, 6, 10, 50, "1碟, 50克"),
    ]),

    # ── Monday June 1 (today) ──
    meal(date(2026, 6, 1), "breakfast", "08:30", "全麦无糖高纤燕麦包", [
        item("全麦燕麦包", 195, 8, 36, 3, 120, "1个, 120克", ["全麦馒头", "蒸紫薯"]),
    ]),
]


def seed_data(db: Session) -> int:
    """Insert seed meals. Returns number of meals inserted."""
    existing = db.query(Meal).filter(Meal.user_id == TEST_USER_ID).count()
    if existing > 5:
        print(f"User already has {existing} meals — skipping seed (delete first to re-seed).")
        return 0

    count = 0
    for md in SEED_MEALS:
        meal_id = str(uuid.uuid4())
        meal_obj = Meal(
            id=meal_id,
            user_id=TEST_USER_ID,
            title=md["title"],
            meal_type=md["meal_type"],
            meal_date=md["meal_date"],
            time_string=md["time_string"],
            calories=md["calories"],
            protein=md["protein"],
            carbs=md["carbs"],
            fat=md["fat"],
            notes=md["notes"],
            is_collected=md["is_collected"],
            is_liked=md["is_liked"],
            health_score=md["health_score"],
            health_message=md["health_message"],
            source=md["source"],
        )
        db.add(meal_obj)

        for i, it in enumerate(md["items"]):
            item_id = str(uuid.uuid4())
            item_obj = MealItem(
                id=item_id,
                meal_id=meal_id,
                name=it["name"],
                calories=it["calories"],
                protein=it["protein"],
                carbs=it["carbs"],
                fat=it["fat"],
                weight_grams=it.get("weight_grams"),
                weight_string=it.get("weight_string", ""),
                sort_order=i,
            )
            db.add(item_obj)

            for j, alt_name in enumerate(it.get("alternatives", [])):
                alt_obj = MealItemAlternative(
                    id=str(uuid.uuid4()),
                    meal_item_id=item_id,
                    name=alt_name,
                    sort_order=j,
                )
                db.add(alt_obj)

        count += 1

    db.commit()
    print(f"Inserted {count} meals with items and alternatives.")
    return count


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()
