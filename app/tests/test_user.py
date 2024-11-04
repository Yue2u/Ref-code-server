from datetime import timedelta

from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
from pydantic import TypeAdapter

from app.db.models.user import User

timedelta_adapter = TypeAdapter(timedelta)


def td_to_iso(t: timedelta):
    return timedelta_adapter.dump_python(t, mode="json")


def get_auth_header(client: TestClient, email: str, password: str):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
        files={"none": ""},
    )

    assert (
        resp.status_code == 200
    ), f"Login with {email}:{password} failed, status_code {resp.status_code}"
    data = resp.json()

    return {"Authorization": f"Bearer {data['access_token']}"}


def test_login(client: TestClient, verified_user: User):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": verified_user.email, "password": "password1234"},
        files={"none": ""},
    )

    assert resp.status_code == 200, "Login with verified user failed"

    json_data = resp.json()
    assert json_data.get("access_token") is not None


def test_users_me_unverified(client: TestClient, unverified_user: User):
    auth_header = get_auth_header(client, unverified_user.email, "password1234")

    resp = client.get("/api/v1/users/me", headers=auth_header)

    assert resp.status_code == 200, "Can't get user info"

    data = resp.json()

    assert data["id"] == str(unverified_user.id)
    assert data["email"] == unverified_user.email
    assert data["name"] == unverified_user.name
    assert data["surname"] == unverified_user.surname


def test_users_me_verified(client: TestClient, verified_user: User):
    auth_header = get_auth_header(client, verified_user.email, "password1234")
    resp = client.get("/api/v1/users/me", headers=auth_header)

    assert resp.status_code == 200, "Can't get user info"

    data = resp.json()

    assert data["id"] == str(verified_user.id)
    assert data["email"] == verified_user.email
    assert data["name"] == verified_user.name
    assert data["surname"] == verified_user.surname


def test_create_ref_code(client: TestClient, verified_user: User):
    auth_header = get_auth_header(client, verified_user.email, "password1234")
    resp = client.post(
        "/api/v1/users/me/referral_code",
        headers=auth_header,
        json={"expires_in_seconds": 100},
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data.get("referral_code") is not None
    assert data.get("expires_in") == td_to_iso(timedelta(seconds=100))


def test_get_ref_code(client: TestClient, verified_user: User):
    auth_header = get_auth_header(client, verified_user.email, "password1234")

    resp = client.post(
        "/api/v1/users/me/referral_code",
        headers=auth_header,
        json={"expires_in_seconds": 100},
    )

    resp = client.get("/api/v1/users/me/referral_code", headers=auth_header)

    assert resp.status_code == 200

    data = resp.json()

    assert data.get("referral_code") is not None
    assert data.get("expires_in") is not None


def test_create_if_exists(client: TestClient, verified_user: User):
    auth_header = get_auth_header(client, verified_user.email, "password1234")
    client.post(
        "/api/v1/users/me/referral_code",
        headers=auth_header,
        json={"expires_in_seconds": 100},
    )

    resp = client.post(
        "/api/v1/users/me/referral_code",
        headers=auth_header,
        json={"expires_in_seconds": 100},
    )

    assert resp.status_code == 400


def test_delete_ref_code(client: TestClient, verified_user: User):
    auth_header = get_auth_header(client, verified_user.email, "password1234")

    client.post(
        "/api/v1/users/me/referral_code",
        headers=auth_header,
        json={"expires_in_seconds": 100},
    )

    client.get("/api/v1/users/me/referral_code", headers=auth_header)

    resp = client.delete("/api/v1/users/me/referral_code", headers=auth_header)

    assert resp.status_code == 204

    resp = client.get("/api/v1/users/me/referral_code", headers=auth_header)

    assert resp.status_code == 400


def test_register_without_ref_code(client: TestClient):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "user_create": {
                "email": "mymail@mail.com",
                "password": "somepass",
                "name": "MyName",
                "surname": "MySurname",
            }
        },
    )

    assert resp.status_code == 201

    data = resp.json()

    assert data["email"] == "mymail@mail.com"
    assert data["name"] == "MyName"
    assert data["surname"] == "MySurname"
    assert data.get("referrer_id") is None


def test_register_with_ref_code(client: TestClient, verified_user: User):
    auth_header = get_auth_header(client, verified_user.email, "password1234")
    resp = client.post(
        "/api/v1/users/me/referral_code",
        headers=auth_header,
        json={"expires_in_seconds": 100},
    )

    ref_code = resp.json()["referral_code"]

    # Change emal to avoid 400 ALREADY REGISTERED exception
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "user_create": {
                "email": "mymail2@mail.com",
                "password": "somepass",
                "name": "MyName",
                "surname": "MySurname",
            },
            "referral_code": ref_code,
        },
    )

    assert resp.status_code == 201

    data = resp.json()

    assert data["email"] == "mymail2@mail.com"
    assert data["name"] == "MyName"
    assert data["surname"] == "MySurname"
    assert data["referrer_id"] == str(verified_user.id)


def test_get_my_referrals(client: TestClient, verified_user: User, session):
    # Create user manually because we can see only verified users
    # but verification logics is hidden in fastapi-users
    # and has to be performed with email with token or other message to user
    password_helper = PasswordHelper()
    user = User(
        email="mymail3@mail.com",
        hashed_password=password_helper.hash("somepass"),
        name="MyName",
        surname="MySurname",
        is_verified=True,
        referrer_id=verified_user.id,
    )
    session.add(user)
    session.commit()

    auth_header = get_auth_header(client, verified_user.email, "password1234")
    resp = client.get("/api/v1/users/me/referrals", headers=auth_header)

    assert resp.status_code == 200

    data = resp.json()

    assert len(data["referrals"]) == 1
    assert data["referrals"][0]["email"] == "mymail3@mail.com"
    assert data["referrals"][0]["name"] == "MyName"
    assert data["referrals"][0]["surname"] == "MySurname"


def test_get_user_referrals(client: TestClient, verified_user: User, session):
    # Create user manually because we can see only verified users
    # but verification logics is hidden in fastapi-users
    # and has to be performed with email with token or other message to user
    password_helper = PasswordHelper()
    user = User(
        email="mymail4@mail.com",
        hashed_password=password_helper.hash("somepass"),
        name="MyName",
        surname="MySurname",
        is_verified=True,
        referrer_id=verified_user.id,
    )
    session.add(user)
    session.commit()

    resp = client.post(
        f"/api/v1/users/referrals/{verified_user.id}",
    )

    assert resp.status_code == 200

    data = resp.json()

    assert len(data["referrals"]) == 1
    assert data["referrals"][0]["email"] == "mymail4@mail.com"
    assert data["referrals"][0]["name"] == "MyName"
    assert data["referrals"][0]["surname"] == "MySurname"


def test_delete_referrer(
    client: TestClient, verified_user: User, admin_user: User, session
):
    # Create user manually because we can see only verified users
    # but verification logics is hidden in fastapi-users
    # and has to be performed with email with token or other message to user
    password_helper = PasswordHelper()
    user = User(
        email="mymail5@mail.com",
        hashed_password=password_helper.hash("somepass"),
        name="MyName",
        surname="MySurname",
        is_verified=True,
        referrer_id=verified_user.id,
    )
    session.add(user)
    session.commit()

    auth_header = get_auth_header(client, admin_user.email, "password1234")
    resp = client.delete(f"/api/v1/users/{verified_user.id}", headers=auth_header)

    assert resp.status_code == 204

    resp = client.post(f"/api/v1/users/referrals/{verified_user.id}")

    assert resp.status_code == 404

    auth_header = get_auth_header(client, "mymail5@mail.com", "somepass")
    resp = client.get("/api/v1/users/me", headers=auth_header)

    assert resp.status_code == 200

    data = resp.json()

    assert data.get("referrer_id") is None
