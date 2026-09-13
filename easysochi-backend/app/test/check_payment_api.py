#!/usr/bin/env python3
"""Проверка API easysochi.pro.

Это ОБЫЧНЫЙ СКРИПТ, а не набор для pytest. Имена файла и функций намеренно
не начинаются с test_, чтобы pytest их не подбирал: скрипт завершается через
sys.exit(), а pytest считает SystemExit провалом теста даже при нулевом коде,
и его вердикт в таком случае не несёт никакой информации.

Зависимостей сверх боевых нет — используется только httpx, который и так
входит в requirements.txt. Ставить pytest в контейнер не нужно.

ЧТО ПРОВЕРЯЕТСЯ
  1. GET  /api/v2/donations/stats    — статистика отдаёт raised, goal, donors
  2. POST /api/v2/donations/create   — создание платежа:
       2.1 анонимный, 100 ₽
       2.2 с пользователем, 500 ₽ (заодно создаётся запись в users)
       2.3 минимальная сумма 50 ₽
       2.4 сумма 10 ₽ отклоняется валидацией (ge=50)
  3. POST /api/v2/donations/webhook  — приём уведомления об оплате:
       3.1 корректная подпись: ответ должен быть ровно "OK<InvId>"
           открытым текстом, как требует ResultURL Robokassa
       3.2 неверная подпись: ответ 400 и без подтверждающего "OK"
  4. Форма обратной связи:
       4.0 GET  /api/v2/form/topics отдаёт список тем обращения
       4.1 POST /api/v2/form/ с пустыми данными отклоняется
       4.2 то же с полями не из схемы
       4.3 контакт не соответствует выбранному способу связи
       4.4 тема вне списка
     Только негативные проверки: валидная заявка создала бы запись в боевой
     таблице и слала бы уведомление в Telegram при каждой сборке. Код ответа
     на невалидный ввод — 422: валидацию делает pydantic-схема.
  5. Время ответа /donations/stats

ЧЕГО СКРИПТ НЕ ПРОВЕРЯЕТ
  Запросы идут на localhost:8000 изнутри контейнера, минуя nginx. Значит
  geo-фильтр вебхуков ($is_payment_service) и подмена реального IP клиента
  (real_ip) не задействованы — их проверяют только настоящие уведомления
  от платёжной системы.

  Тесты 2.1-2.3 создают НАСТОЯЩИЕ записи в таблице payments со статусом
  pending. На публичный счётчик они не влияют (/stats считает только
  succeeded), но при каждом прогоне таблица прирастает.

ЗАПУСК
  Обычно скрипт запускается сам, последним шагом ./scripts/build.sh.
  Отдельно, не копируя файл в контейнер:

      docker exec -i easysochi_contact_api python3 - \
          < easysochi-backend/app/test/check_payment_api.py

  Ручная проверка вебхука реальными данными — нужен файл внутри контейнера:

      docker exec -it easysochi_contact_api \
          python3 app/test/check_payment_api.py --manual-webhook

КОД ВОЗВРАТА
  0 — все проверки пройдены
  1 — хотя бы одна не пройдена; перед выходом печатается список упавших
      проверок с телом ответа сервера

ТРЕБОВАНИЯ К ОКРУЖЕНИЮ
  Раздел 3 работает только при заданном ROBOKASSA_PASSWORD_2 — без него
  подпись вебхука не собрать, и проверки вебхука пропускаются.
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

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

# Сюда попадает каждая упавшая проверка, чтобы в конце показать их списком,
# а не заставлять искать красные строки в длинной простыне вывода.
FAILURES = []


def print_error(msg: str):
    FAILURES.append(msg.strip())
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg: str):
    print(f"{Colors.BLUE}📌 {msg}{Colors.RESET}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️ {msg}{Colors.RESET}")

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

def run_checks():
    """Прогон всех проверок. Возвращать ничего не нужно — завершает процесс."""
    print_info(f"Начинаем проверку API: {BASE_URL}")
    print_info(f"Платёжная система: {settings.PAYMENT_PROVIDER}")
    print_info(f"Robokassa Shop ID: {settings.ROBOKASSA_SHOP_ID}")
    print_info(f"Test Mode: {settings.ROBOKASSA_TEST_MODE}")

    # Сначала убеждаемся, что приложение вообще отвечает. Без этой проверки
    # неподнятый API даёт два десятка одинаковых ConnectError, и настоящая
    # причина теряется в выводе.
    try:
        health = httpx.get("http://localhost:8000/health", timeout=5.0)
        if health.status_code != 200:
            print_error(f"/health ответил {health.status_code}, ожидался 200")
            sys.exit(1)
    except Exception as exc:
        print_error(f"API не отвечает на http://localhost:8000/health: {exc}")
        print("\nСкорее всего контейнер не поднялся. Что смотреть:")
        print("  docker compose ps")
        print("  docker logs easysochi_contact_api --tail 100")
        sys.exit(1)
    
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
                print_error(f"Stats failed with status {r.status_code}: {r.text[:300]}")
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
                print_error(f"  Failed with status {r.status_code}: {r.text[:300]}")
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
                    print_error(f"  Webhook failed with status {r.status_code}: {r.text[:300]}")
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
        # 4. ТЕСТ ФОРМЫ (GET /form/topics и негативные проверки POST /form/)
        # ============================================
        print_info("\n4. Тестирование формы обратной связи...")

        # Тест 4.0: список тем обращения
        print_info("  4.0 Список тем обращения...")
        try:
            r = client.get(f"{BASE_URL}/form/topics")
            topics = r.json() if r.status_code == 200 else None
            if isinstance(topics, list) and "Другое" in topics:
                print_success(f"  Тем получено: {len(topics)}")
                results.append(True)
            else:
                print_error(f"  Неожиданный ответ {r.status_code}: {r.text[:300]}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)

        # Дальше только негативные проверки: валидная заявка создала бы запись
        # в боевой таблице и отправила бы уведомление в Telegram при каждом
        # прогоне сборки.
        #
        # Код ответа именно 422, а не 400: валидацию делает pydantic-схема
        # ContactFormCreate, и FastAPI по стандарту отвечает 422. Раньше
        # роутер разбирал сырой JSON вручную и возвращал 400.

        # Тест 4.1: Пустые данные
        print_info("  4.1 Пустые данные...")
        try:
            r = client.post(f"{BASE_URL}/form/", json={})
            if r.status_code == 422:
                print_success("  Пустые данные отклонены")
                results.append(True)
            else:
                print_error(f"  Ожидался 422, получен {r.status_code}: {r.text[:300]}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)

        # Тест 4.2: Полей схемы нет вовсе
        print_info("  4.2 Неверный формат данных...")
        try:
            payload = {"invalid": "data", "something": "wrong"}
            r = client.post(f"{BASE_URL}/form/", json=payload)
            if r.status_code == 422:
                print_success("  Неверный формат отклонен")
                results.append(True)
            else:
                print_error(f"  Ожидался 422, получен {r.status_code}: {r.text[:300]}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)

        # Тест 4.3: контакт не соответствует выбранному способу связи —
        # проверяет field_validator, а не только объявленные типы полей
        print_info("  4.3 Email не похож на адрес...")
        try:
            payload = {
                "name": "Тест",
                "contact_type": "email",
                "contact_value": "это-не-почта",
                "topic": "Другое",
                "message": "Проверка валидации контакта",
            }
            r = client.post(f"{BASE_URL}/form/", json=payload)
            if r.status_code == 422 and "email" in r.text.lower():
                print_success("  Некорректный email отклонён")
                results.append(True)
            else:
                print_error(f"  Ожидался 422 с упоминанием email, получен {r.status_code}: {r.text[:300]}")
                results.append(False)
        except Exception as e:
            print_error(f"  Error: {e}")
            results.append(False)

        # Тест 4.4: тема вне списка
        print_info("  4.4 Неизвестная тема обращения...")
        try:
            payload = {
                "name": "Тест",
                "contact_type": "email",
                "contact_value": "test@example.com",
                "topic": "Темы такой нет",
                "message": "Проверка валидации темы",
            }
            r = client.post(f"{BASE_URL}/form/", json=payload)
            if r.status_code == 422:
                print_success("  Неизвестная тема отклонена")
                results.append(True)
            else:
                print_error(f"  Ожидался 422, получен {r.status_code}: {r.text[:300]}")
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
    print(f"  Пройдено: {Colors.GREEN}{passed_tests}{Colors.RESET}")
    print(f"  Не пройдено: {Colors.RED}{total_tests - passed_tests}{Colors.RESET}")
    
    if all(results):
        print_success("\nВсе проверки пройдены успешно!")
        sys.exit(0)

    # Упавшие проверки выводим отдельным списком: при прогоне из ./scripts/build.sh
    # вывод длинный, и выискивать в нём красные строки глазами неудобно.
    bar = "=" * 60
    print(f"\n{Colors.RED}{bar}")
    print(f"НЕ ПРОЙДЕНО — {len(FAILURES)} проверок:{Colors.RESET}")
    for i, failure in enumerate(FAILURES, 1):
        print(f"  {i}. {failure}")
    print(f"{Colors.RED}{bar}{Colors.RESET}")
    print("\nЧто смотреть дальше:")
    print("  docker compose ps")
    print("  docker logs easysochi_contact_api --tail 100")
    sys.exit(1)

def manual_webhook_check():
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
        manual_webhook_check()
    else:
        run_checks()
