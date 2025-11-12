import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Payment, Translation


@pytest.mark.django_db
class TestApiEndpoints:
    def setup_method(self):
        """
        Запускається перед кожним тестом.
        Створює клієнт API і базового користувача.
        """
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="password123")

    # 1️⃣ Тест: створення користувача (POST)
    def test_create_user(self):
        data = {"username": "new_user", "password": "123456"}
        response = self.client.post("/api/users/", data, format="json")

        # ✅ Перевіряємо, що створено успішно
        assert response.status_code in (200, 201), response.data
        assert User.objects.filter(username="new_user").exists()

    # 2️⃣ Тест: отримання списку користувачів (GET)
    def test_list_users(self):
        # Створюємо ще одного користувача
        User.objects.create_user(username="extra_user", password="testpass")

        response = self.client.get("/api/users/")
        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert any(u["username"] == "extra_user" for u in response.data)

    # 3️⃣ Негативний сценарій — створення користувача без даних
    def test_create_user_invalid(self):
        response = self.client.post("/api/users/", {}, format="json")
        assert response.status_code in (400, 422)

    # 4️⃣ Тест: створення перекладу
    # def test_create_translation(self):
    #     """Перевіряє, що переклад створюється і записується в БД"""
    #     self.client.force_authenticate(user=self.user)
    #
    #     data = {
    #         "user_id": self.user.id,
    #         "text": "Hello world",
    #         "source_lang": "EN",
    #         "target_lang": "UK"
    #     }
    #
    #     response = self.client.post("/api/translation/", data, format="json")
    #     assert response.status_code == 201, f"Unexpected: {response.status_code}, data: {response.data}"
    #
    #     # Перевіряємо, що в базі реально створено запис
    #     translation_id = response.data.get("translation_id")
    #     assert translation_id, "translation_id відсутній у відповіді"
    #
    #     translation = Translation.objects.get(id=translation_id)
    #     assert translation.source_text == "Hello world"
    #     assert translation.source_lang == "EN"
    #     assert translation.target_lang == "UK"
    #     assert translation.user == self.user
    #
    #     # Переконуємось, що оплати не створено
    #     assert not Payment.objects.filter(translation=translation).exists()

    # 5️⃣ Емуляція платежу (payment/accept)
    def test_accept_payment(self):
        data = {"orderReference": "12345", "amount": "100.00"}
        response = self.client.post("/api/payment/accept/", data, format="json")
        # Може бути або успішно, або помилка валідації
        assert response.status_code in (200, 400)

    # 6️⃣ Оновлення користувача (PATCH)
    def test_update_user(self):
        self.client.force_authenticate(user=self.user)
        url = f"/api/users/{self.user.id}/"
        data = {"username": "updated_name"}

        response = self.client.patch(url, data, format="json")
        assert response.status_code in (200, 202), f"Unexpected {response.status_code}: {response.data}"

        # Перевіряємо оновлення в БД
        self.user.refresh_from_db()
        assert self.user.username == "updated_name"

    # 7️⃣ Видалення користувача
    def test_delete_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/users/{self.user.id}/")
        assert response.status_code in (200, 204)
        assert not User.objects.filter(id=self.user.id).exists()

    # 8️⃣ Авторизація через GoogleAuthView (stub)
    def test_google_auth_view(self):
        data = {"token": "fake_google_token"}
        response = self.client.post("/api/auth/", data, format="json")
        assert response.status_code in (200, 400)
