#!/usr/bin/env python3
"""
Установка pytest прямо в контейнер

docker compose exec contact_api pip install pytest

Тестовый скрипт для проверки API платежей Robokassa

Запуск: docker compose exec contact_api python -m pytest app/test/test_payment_api.py -v
"""

import sys
import hashlib
import uuid
from typing import Dict, Any, Optional

import httpx

# Импортируем настройки из конфига приложения
sys.path.append("/app")  # Добавляем путь к приложению
from app.core.config import settings

# Настройки для проверки
BASE_URL = "http://localhost:8000/api/v2"  # Внутри контейнера

class TestColors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg: str):
    print(f"{TestColors.GREEN}✅ {msg}{TestColors.RESET}")

def print_error(msg: str):
    print(f"{TestColors.RED}❌ {msg}{TestColors.RESET}")

def print_info(msg: str):
    print(f"{TestColors.BLUE}📌 {msg}{TestColors.RESET}")

def print_warning(msg: str):
    print(f"{TestColors.YELLOW}⚠️ {msg}{TestColors.RESET}")

def generate_robokassa_signature(out_sum: str, inv_id: str, password: str, shp_params: dict = None) -> str:
    """Генерация подписи Robokassa (для тестов)"""
    sign_str = f"{out_sum}:{inv_id}:{password}"
    
    if shp_params:
        for param_name in sorted(shp_params.keys()):
            sign_str += f":{param_name}={shp_params[param_name]}"
    
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()

def create_mock_webhook_data(inv_id: int, out_sum: float, password: str, **shp_params) -> Dict[str, Any]:
    """Создание мок-данных для вебхука Robokassa"""
    out_sum_str = f"{out_sum:.2f}"
    
    # Генерируем подпись
    signature = generate_robokassa_signature(out_sum_str, str(inv_id), password, shp_params)
    
    data = {
        "OutSum": out_sum_str,
        "InvId": str(inv_id),
        "SignatureValue": signature,
        "PaymentMethod": "BankCard",
        "Fee": "0.00",
        **shp_params
    }
    
    return data

def test_api():
    """Основная функция тестирования"""
    print_info(f"Начинаем проверку API: {BASE_URL}")
    print_info(f"Robokassa Shop ID: {settings.ROBOKASSA_SHOP_ID}")
    print_info(f"Test Mode: {settings.ROBOKASSA_TEST_MODE}")
    
    results = []
    
    # Хранилище для данных между тестами
    test_data = {
        "created_payments": [],
        "user_emails": []
    }

    with httpx.Client(timeout=10.0) as client:
        
        # ============================================
        # 1. ТЕСТ СТАТИСТИКИ (GET /donations/stats)
        # ============================================
        print_info("\n1. Тестирование статистики донатов...")
        try:
            r = client.get(f"{BASE_URL}/donations/stats")
            if r.status_code == 200:
                data = r.json()
                if "raised" in data and "goal" in data and "donors" in data:
                    print_success(f"Stats OK: собрано {data['raised']}₽ из {data['goal']}₽, донатеров: {len(data['donors'])}")
                    results.append(True)
                else:
                    print_error(f"Stats response missing fields: {data}")
                    results.append(False)
            else:
                print_error(f"Stats failed with status {r.status_code}")
                results.append(False)
        except Exception as e:
            print_error(f"Stats error: {e}")
            results.append(False)

        # ============================================
        # 2. ТЕСТ СОЗДАНИЯ ПЛАТЕЖА (POST /donations/create)
        # ============================================
        print_info("\n2. Тестирование создания платежа...")
        
        # Тест 2.1: Создание платежа с минимальными данными
        print_info("  2.1 Создание платежа (аноним, 100₽)...")
        try:
            payload = {
                "amount": 100,
                "name": None,
                "email": None
            }
            r = client.post(f"{BASE_URL}/donations/create", json=payload)
            if r.status_code == 200:
                data = r.json()
                if "confirmation_url" in data:
                    print_success("  Анонимный платеж создан")
                    test_data["created_payments"].append({"type": "anonymous", "amount": 100})
                    results.append(True)
                else:
                    print_error(f"  Invalid response: {data}")
                    results.append(False)
            else:
                print_error(f"  Failed with status {r.status_code}: {r.text}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)
        
        # Тест 2.2: Создание платежа с данными пользователя
        print_info("  2.2 Создание платежа (пользователь test@example.com, 500₽)...")
        try:
            payload = {
                "amount": 500,
                "name": "Test User",
                "email": "test@example.com"
            }
            r = client.post(f"{BASE_URL}/donations/create", json=payload)
            if r.status_code == 200:
                data = r.json()
                if "confirmation_url" in data:
                    print_success("  Платеж с пользователем создан")
                    test_data["created_payments"].append({
                        "type": "user", 
                        "amount": 500, 
                        "email": "test1@example.com"
                    })
                    test_data["user_emails"].append("test@example.com")
                    results.append(True)
                else:
                    print_error(f"  Invalid response: {data}")
                    results.append(False)
            else:
                print_error(f"  Failed with status {r.status_code}: {r.text}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)
        
        # Тест 2.3: Создание платежа с минимальной суммой
        print_info("  2.3 Создание платежа (минимальная сумма 50₽)...")
        try:
            payload = {
                "amount": 50,
                "name": "Min donation",
                "email": "min@example.com"
            }
            r = client.post(f"{BASE_URL}/donations/create", json=payload)
            if r.status_code == 200:
                print_success("  Минимальный платеж создан")
                test_data["created_payments"].append({"type": "min", "amount": 50})
                results.append(True)
            else:
                print_error(f"  Failed with status {r.status_code}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)
        
        # Тест 2.4: Ошибка валидации (сумма меньше 50)
        print_info("  2.4 Ошибка валидации (сумма 10₽ - ожидается 400)...")
        try:
            payload = {
                "amount": 10,
                "name": "Too Small",
                "email": "small@example.com"
            }
            r = client.post(f"{BASE_URL}/donations/create", json=payload)
            if r.status_code == 422 or r.status_code == 400:
                print_success("  Валидация сработала правильно")
                results.append(True)
            else:
                print_warning(f"  Неожиданный статус {r.status_code} (должен быть 400/422)")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)

        # ============================================
        # 3. ТЕСТ ВЕБХУКА (POST /donations/webhook)
        # ============================================
        print_info("\n3. Тестирование вебхука Robokassa...")
        
        # Используем пароль #2 из конфига
        password_2 = settings.ROBOKASSA_PASSWORD_2
        
        if password_2:
            # Тест 3.1: Отправка корректного вебхука (с мок-данными)
            print_info("  3.1 Отправка тестового уведомления об оплате...")
            try:
                inv_id = 123456789
                out_sum = 100.00
                
                shp_params = {
                    "Shp_email": "test@example.com",
                    "Shp_name": "Test User",
                    "Shp_user_id": ""
                }
                
                webhook_data = create_mock_webhook_data(
                    inv_id=inv_id,
                    out_sum=out_sum,
                    password=password_2,
                    **shp_params
                )
                
                # Отправляем как form-data
                r = client.post(
                    f"{BASE_URL}/donations/webhook",
                    data=webhook_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if r.status_code == 200:
                    # Robokassa ждёт ровно "OK<InvId>" открытым текстом
                    expected = f"OK{inv_id}"
                    if r.text.strip() == expected:
                        print_success(f"  Вебхук обработан, ответ: {r.text.strip()}")
                        results.append(True)
                    else:
                        print_error(f"  Ожидался ответ {expected!r}, получен {r.text!r}")
                        results.append(False)
                else:
                    print_error(f"  Webhook failed with status {r.status_code}")
                    results.append(False)
            except Exception as e:
                print_error(f"  Webhook error: {e}")
                results.append(False)
            
            # Тест 3.2: Отправка вебхука с неверной подписью
            print_info("  3.2 Отправка вебхука с неверной подписью (ожидается ошибка)...")
            try:
                webhook_data = {
                    "OutSum": "100.00",
                    "InvId": "999999",
                    "SignatureValue": "INVALID_SIGNATURE",
                    "PaymentMethod": "BankCard"
                }
                
                r = client.post(
                    f"{BASE_URL}/donations/webhook",
                    data=webhook_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                # Подделанное уведомление не должно выглядеть принятым:
                # ожидаем 400 и отсутствие подтверждающего "OK<InvId>"
                if r.status_code == 400 and not r.text.strip().startswith("OK"):
                    print_success(f"  Неверная подпись отклонена: {r.status_code} {r.text.strip()!r}")
                    results.append(True)
                else:
                    print_error(f"  Неверная подпись принята? {r.status_code} {r.text!r}")
                    results.append(False)
            except Exception as e:
                print_error(f"  Error: {e}")
                results.append(False)
        else:
            print_warning("  Robokassa Password #2 не настроен в .env, пропуск тестов вебхука")
            results.append(True)

        # ============================================
        # 4. ТЕСТ ФОРМЫ (POST /form/ - негативные тесты)
        # ============================================
        print_info("\n4. Тестирование валидации формы...")
        
        # Тест 4.1: Пустые данные (ожидается 400)
        print_info("  4.1 Пустые данные...")
        try:
            r = client.post(f"{BASE_URL}/form/", json={})
            if r.status_code == 400:
                print_success("  Пустые данные отклонены")
                results.append(True)
            else:
                print_warning(f"  Неожиданный статус {r.status_code}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)
        
        # Тест 4.2: Неверный формат данных
        print_info("  4.2 Неверный формат данных...")
        try:
            payload = {"invalid": "data", "something": "wrong"}
            r = client.post(f"{BASE_URL}/form/", json=payload)
            if r.status_code == 400 or r.status_code == 422:
                print_success("  Неверный формат отклонен")
                results.append(True)
            else:
                print_warning(f"  Неожиданный статус {r.status_code}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)

        # ============================================
        # 5. ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ
        # ============================================
        print_info("\n5. Проверка скорости ответа...")
        try:
            import time
            start = time.time()
            r = client.get(f"{BASE_URL}/donations/stats")
            elapsed = time.time() - start
            if elapsed < 1.0:
                print_success(f"  Быстрый ответ: {elapsed:.2f} сек")
                results.append(True)
            else:
                print_warning(f"  Медленный ответ: {elapsed:.2f} сек")
                results.append(True)
        except Exception as e:
            print_error(f"  Speed test error: {e}")
            results.append(False)

    # ============================================
    # ИТОГИ ТЕСТИРОВАНИЯ
    # ============================================
    print("\n" + "="*50)
    total_tests = len(results)
    passed_tests = sum(results)
    
    print_info(f"Результаты тестирования:")
    print(f"  Всего тестов: {total_tests}")
    print(f"  Пройдено: {TestColors.GREEN}{passed_tests}{TestColors.RESET}")
    print(f"  Не пройдено: {TestColors.RED}{total_tests - passed_tests}{TestColors.RESET}")
    
    if all(results):
        print_success("\n🎉 Все тесты пройдены успешно!")
        sys.exit(0)
    else:
        print_error("\n⚠️ Некоторые тесты не пройдены!")
        sys.exit(1)

def test_webhook_manually():
    """Отдельная функция для ручного тестирования вебхука с реальными данными"""
    print_info("\n🔧 Ручное тестирование вебхука")
    
    inv_id = input("Введите InvId платежа: ")
    out_sum = input("Введите сумму платежа: ")
    email = input("Введите email (опционально): ") or ""
    name = input("Введите имя (опционально): ") or ""
    
    shp_params = {}
    if email:
        shp_params["Shp_email"] = email
    if name:
        shp_params["Shp_name"] = name
    
    # Используем пароль #2 из конфига
    password_2 = settings.ROBOKASSA_PASSWORD_2
    
    webhook_data = create_mock_webhook_data(
        inv_id=int(inv_id),
        out_sum=float(out_sum),
        password=password_2,
        **shp_params
    )
    
    print_info(f"Отправка вебхука: {webhook_data}")
    
    with httpx.Client(timeout=10.0) as client:
        r = client.post(
            f"{BASE_URL}/donations/webhook",
            data=webhook_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        print_info(f"Ответ: {r.status_code} - {r.text}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual-webhook", action="store_true", help="Ручное тестирование вебхука")
    args = parser.parse_args()
    
    if args.manual_webhook:
        test_webhook_manually()
    else:
        test_api()
