def test_create_user(client):
    response = client.post("/users/", json={"name": "Ana", "email": "ana@example.com"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ana"
    assert body["email"] == "ana@example.com"
    assert isinstance(body["id"], int)


def test_create_user_requires_email(client):
    response = client.post("/users/", json={"name": "Ana"})

    assert response.status_code == 422
