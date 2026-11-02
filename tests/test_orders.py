import models


def place_order(client, user, *products):
    return client.post("/orders/", json={"user_id": user.id, "product_ids": [p.id for p in products]})


def test_order_discounts_stock_and_saves_items(client, db, make_user, make_product):
    user = make_user()
    keyboard = make_product(name="Teclado", price=50.0, stock=5)

    response = place_order(client, user, keyboard, keyboard)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ok"
    assert body["total"] == 100.0
    db.refresh(keyboard)
    assert keyboard.stock == 3
    order = db.get(models.Order, body["order_id"])
    assert [(i.product_id, i.quantity, i.unit_price) for i in order.items] == [(keyboard.id, 2, 50.0)]


def test_products_over_100_get_10_percent_discount(client, make_user, make_product):
    user = make_user()
    monitor = make_product(name="Monitor", price=150.0)

    response = place_order(client, user, monitor)

    assert response.json()["total"] == 135.0


def test_product_at_exactly_100_has_no_discount(client, make_user, make_product):
    user = make_user()
    chair = make_product(name="Silla", price=100.0)

    response = place_order(client, user, chair)

    assert response.json()["total"] == 100.0


def test_total_combines_quantities_and_discounts(client, make_user, make_product):
    user = make_user()
    keyboard = make_product(name="Teclado", price=50.0)
    monitor = make_product(name="Monitor", price=150.0)

    response = place_order(client, user, keyboard, monitor, keyboard)

    assert response.json()["total"] == 50.0 * 2 + 135.0


def test_insufficient_stock_returns_409_and_changes_nothing(client, db, make_user, make_product):
    user = make_user()
    keyboard = make_product(name="Teclado", stock=1)

    response = place_order(client, user, keyboard, keyboard)

    assert response.status_code == 409
    db.refresh(keyboard)
    assert keyboard.stock == 1
    assert db.query(models.Order).count() == 0


def test_out_of_stock_product_cannot_be_ordered(client, db, make_user, make_product):
    user = make_user()
    keyboard = make_product(name="Teclado", stock=0)

    response = place_order(client, user, keyboard)

    assert response.status_code == 409
    db.refresh(keyboard)
    assert keyboard.stock == 0


def test_unknown_product_returns_400_without_partial_changes(client, db, make_user, make_product):
    user = make_user()
    keyboard = make_product(name="Teclado", stock=5)

    response = client.post("/orders/", json={"user_id": user.id, "product_ids": [keyboard.id, 999]})

    assert response.status_code == 400
    assert "999" in response.json()["detail"]
    db.refresh(keyboard)
    assert keyboard.stock == 5
    assert db.query(models.Order).count() == 0


def test_unknown_user_returns_404(client, make_product):
    keyboard = make_product()

    response = client.post("/orders/", json={"user_id": 999, "product_ids": [keyboard.id]})

    assert response.status_code == 404
