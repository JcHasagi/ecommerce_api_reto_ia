import pytest


def ids(response):
    return [product["id"] for product in response.json()]


def test_returns_product_fields(client, make_product):
    product = make_product(name="Teclado", price=80.0, stock=3)

    response = client.get("/products/")

    assert response.status_code == 200
    assert response.json() == [{"id": product.id, "name": "Teclado", "price": 80.0, "stock": 3}]


def test_default_page_has_20_products_sorted_by_id(client, make_product):
    products = [make_product(name=f"P{i}") for i in range(25)]

    response = client.get("/products/")

    assert ids(response) == [p.id for p in products[:20]]


def test_limit_and_offset(client, make_product):
    products = [make_product(name=f"P{i}") for i in range(10)]

    response = client.get("/products/", params={"limit": 3, "offset": 4})

    assert ids(response) == [p.id for p in products[4:7]]


def test_last_page_can_be_partial(client, make_product):
    products = [make_product(name=f"P{i}") for i in range(5)]

    response = client.get("/products/", params={"limit": 3, "offset": 3})

    assert ids(response) == [p.id for p in products[3:]]


def test_offset_past_the_end_returns_empty_list(client, make_product):
    make_product()

    response = client.get("/products/", params={"offset": 50})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_invalid_pagination_returns_422(client, params):
    response = client.get("/products/", params=params)

    assert response.status_code == 422
