def place_order(client, user, *products):
    response = client.post("/orders/", json={"user_id": user.id, "product_ids": [p.id for p in products]})
    assert response.status_code == 201
    return response.json()["order_id"]


def test_history_lists_most_recent_first_with_product_names(client, make_user, make_product):
    ana = make_user()
    keyboard = make_product(name="Teclado", price=50.0)
    monitor = make_product(name="Monitor", price=150.0)
    first = place_order(client, ana, keyboard, keyboard)
    second = place_order(client, ana, monitor)

    response = client.get(f"/users/{ana.id}/orders")

    assert response.status_code == 200
    history = response.json()
    assert [order["id"] for order in history] == [second, first]
    assert history[0]["total_price"] == 135.0
    assert history[0]["items"] == [
        {"product_id": monitor.id, "product_name": "Monitor", "quantity": 1, "unit_price": 135.0}
    ]
    assert history[1]["items"] == [
        {"product_id": keyboard.id, "product_name": "Teclado", "quantity": 2, "unit_price": 50.0}
    ]
    assert all(order["created_at"] for order in history)


def test_history_only_includes_the_users_own_orders(client, make_user, make_product):
    ana = make_user(name="Ana", email="ana@example.com")
    beto = make_user(name="Beto", email="beto@example.com")
    keyboard = make_product()
    own = place_order(client, ana, keyboard)
    place_order(client, beto, keyboard)

    response = client.get(f"/users/{ana.id}/orders")

    assert [order["id"] for order in response.json()] == [own]


def test_user_without_orders_gets_empty_list(client, make_user):
    ana = make_user()

    response = client.get(f"/users/{ana.id}/orders")

    assert response.status_code == 200
    assert response.json() == []


def test_unknown_user_returns_404(client):
    response = client.get("/users/999/orders")

    assert response.status_code == 404


def test_query_count_does_not_grow_with_orders(client, make_user, make_product, count_queries):
    ana = make_user()
    keyboard = make_product(stock=100)
    for _ in range(2):
        place_order(client, ana, keyboard)
    count_queries["n"] = 0
    client.get(f"/users/{ana.id}/orders")
    with_two_orders = count_queries["n"]

    for _ in range(10):
        place_order(client, ana, keyboard)
    count_queries["n"] = 0
    client.get(f"/users/{ana.id}/orders")

    assert count_queries["n"] == with_two_orders
