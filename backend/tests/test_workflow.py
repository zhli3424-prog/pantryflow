from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.services.demo_data import seed_demo_data


def add(client, name, meal_count, unit="个", days=3):
    response = client.post("/api/v1/ingredients", json={
        "name": name,
        "meal_count": meal_count,
        "expire_at": (date.today() + timedelta(days=days)).isoformat(),
    })
    assert response.status_code == 201
    return response.json()["data"]


def test_complete_cooking_workflow_is_idempotent(client):
    add(client, "西红柿", 4, days=1)
    add(client, "鸡蛋", 6, days=4)
    add(client, "土豆", 3, days=5)
    add(client, "青椒", 3, days=2)
    add(client, "猪肉", 5, days=2)

    generated = client.post("/api/v1/recommendations")
    assert generated.status_code == 201
    recipes = generated.json()["data"]
    assert 3 <= len(recipes) <= 5
    recipe = next(item for item in recipes if item["dish_name"] == "西红柿炒鸡蛋")

    first = client.post(f"/api/v1/recommendations/{recipe['id']}/cook")
    second = client.post(f"/api/v1/recommendations/{recipe['id']}/cook")
    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]

    history = client.get("/api/v1/history").json()["data"]
    stock = client.get("/api/v1/ingredients").json()["data"]
    assert len(history) == 1
    assert next(item for item in stock if item["name"] == "西红柿")["meal_count"] == 3


def test_expired_food_is_not_recommended(client):
    add(client, "鸡蛋", 2, days=-1)
    response = client.post("/api/v1/recommendations")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NO_USABLE_INVENTORY"


def test_ingredient_crud_and_validation(client):
    created = add(client, "豆腐", 2, days=4)

    updated = client.patch(
        f"/api/v1/ingredients/{created['id']}",
        json={"meal_count": 2},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["meal_count"] == 2

    invalid = client.post(
        "/api/v1/ingredients",
        json={"name": " ", "meal_count": 0},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    deleted = client.delete(f"/api/v1/ingredients/{created['id']}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/ingredients/{created['id']}").status_code == 404


def test_recommendations_rotate_instead_of_repeating(client):
    add(client, "西红柿", 4, days=1)
    add(client, "鸡蛋", 6, days=4)
    add(client, "土豆", 4, days=5)
    add(client, "青椒", 3, days=2)
    add(client, "猪肉", 5, days=2)

    batches = [
        {recipe["dish_name"] for recipe in client.post("/api/v1/recommendations").json()["data"]}
        for _ in range(4)
    ]

    for previous, current in zip(batches, batches[1:]):
        assert previous != current
        assert previous.isdisjoint(current)


def test_coke_and_chicken_wings_produce_daily_recipes(client):
    add(client, "可乐", 1, "个", 10)
    add(client, "鸡翅", 6, "个", 2)

    recipes = client.post("/api/v1/recommendations").json()["data"]
    names = [recipe["dish_name"] for recipe in recipes]

    assert names[0] == "可乐鸡翅"
    assert all("清炒可乐" not in name and "方案" not in name for name in names)


def test_filters_pantry_and_saved_batch_detect_inventory_changes(client):
    pork = add(client, "猪肉", 5, days=2)
    add(client, "青椒", 3, "个", 2)

    response = client.post("/api/v1/recommendations", json={
        "style": "川菜",
        "spicy": "辣",
        "pantry_items": ["豆瓣酱"],
    })
    assert response.status_code == 201
    recipes = response.json()["data"]
    assert {recipe["dish_name"] for recipe in recipes} <= {
        "鱼香肉丝", "麻婆豆腐", "回锅肉", "水煮肉片", "酸辣土豆丝", "蒜泥白肉", "手撕包菜",
    }
    assert all("豆瓣酱" not in recipe["missing_ingredients"] for recipe in recipes)

    latest = client.get("/api/v1/recommendations/latest").json()["data"]
    assert latest["inventory_changed"] is False
    assert latest["preferences"]["style"] == "川菜"

    client.patch(f"/api/v1/ingredients/{pork['id']}", json={"meal_count": 4})
    latest = client.get("/api/v1/recommendations/latest").json()["data"]
    assert latest["inventory_changed"] is True


def test_each_used_ingredient_loses_one_meal_when_cooking(client):
    add(client, "西红柿", 4, "个", 2)
    add(client, "鸡蛋", 6, "个", 3)
    recipes = client.post("/api/v1/recommendations").json()["data"]
    recipe = next(item for item in recipes if item["dish_name"] == "西红柿炒鸡蛋")

    cooked = client.post(f"/api/v1/recommendations/{recipe['id']}/cook")
    assert cooked.status_code == 200
    stock = client.get("/api/v1/ingredients").json()["data"]
    assert next(item for item in stock if item["name"] == "西红柿")["meal_count"] == 3
    assert next(item for item in stock if item["name"] == "鸡蛋")["meal_count"] == 5


def test_aliases_are_normalized_and_recommended(client):
    tomato = add(client, "番茄", 3, "个", 2)
    add(client, "鸡蛋", 4, "个", 3)

    assert tomato["name"] == "西红柿"
    recipes = client.post("/api/v1/recommendations").json()["data"]
    assert "西红柿炒鸡蛋" in {recipe["dish_name"] for recipe in recipes}


def test_one_recipe_can_be_replaced_without_changing_the_batch(client):
    add(client, "西红柿", 4, "个", 2)
    add(client, "鸡蛋", 5, "个", 3)
    add(client, "土豆", 4, "个", 4)
    add(client, "青椒", 3, "个", 3)
    add(client, "猪肉", 5, days=2)
    original = client.post("/api/v1/recommendations").json()["data"]

    response = client.post(
        f"/api/v1/recommendations/{original[0]['id']}/replace",
        json={"excluded_dishes": [original[0]["dish_name"]]},
    )
    assert response.status_code == 200
    replacement = response.json()["data"]
    assert replacement["dish_name"] not in {recipe["dish_name"] for recipe in original}

    latest = client.get("/api/v1/recommendations/latest").json()["data"]["recipes"]
    assert len(latest) == len(original)
    assert latest[0]["id"] == replacement["id"]
    batch = client.get("/api/v1/recommendations/latest").json()["data"]
    assert original[0]["dish_name"] in batch["preferences"]["excluded_dishes"]


def test_same_batch_meal_counts_are_merged(client):
    first = add(client, "西红柿", 2, days=2)
    second = add(client, "番茄", 3, days=2)
    assert first["id"] == second["id"]
    assert second["meal_count"] == 5


def test_demo_seed_is_repeatable_and_only_fills_empty_database(client):
    override = client.app.dependency_overrides
    db = next(override[next(key for key in override if key.__name__ == "get_db")]())
    try:
        assert seed_demo_data(db) is True
        assert seed_demo_data(db) is False
    finally:
        db.close()

    ingredients = client.get("/api/v1/ingredients").json()["data"]
    history = client.get("/api/v1/history").json()["data"]
    assert len(ingredients) == 7
    assert len(history) == 3
    assert {item["expiry_status"] for item in ingredients} >= {"urgent", "soon", "normal"}
