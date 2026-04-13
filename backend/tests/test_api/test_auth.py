"""Tests for /api/v1/auth endpoints."""
import pytest


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@docflow.dev",
            "username": "newuser",
            "password": "SecurePass1!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@docflow.dev"
        assert "id" in data
        assert "hashed_password" not in data  # never expose hash

    def test_register_duplicate_email(self, client, sample_user):
        resp = client.post("/api/v1/auth/register", json={
            "email": sample_user.email,
            "username": "other",
            "password": "SecurePass1!",
        })
        assert resp.status_code == 400

    def test_register_weak_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "weak@docflow.dev",
            "username": "weakuser",
            "password": "123",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, sample_user):
        resp = client.post("/api/v1/auth/login", data={
            "username": sample_user.email,
            "password": "TestPass123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, sample_user):
        resp = client.post("/api/v1/auth/login", data={
            "username": sample_user.email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "ghost@docflow.dev",
            "password": "whatever",
        })
        assert resp.status_code == 401

    def test_me_authenticated(self, client, auth_headers, sample_user):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == sample_user.email

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
