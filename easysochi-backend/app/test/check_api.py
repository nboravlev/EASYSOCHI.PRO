import httpx
import sys

# Настройки для проверки
BASE_URL = "http://localhost:8000/api/v2"

def test_api():
    print(f"🚀 Начинаем проверку API: {BASE_URL}")
    results = []

    with httpx.Client(timeout=10.0) as client:
        # 1. Проверка статистики донатов (GET)
        try:
            r = client.get(f"{BASE_URL}/donations/stats")
            if r.status_code == 200 and "raised" in r.json():
                print("✅ [GET] Stats: OK")
                results.append(True)
            else:
                print(f"❌ [GET] Stats: Failed ({r.status_code})")
                results.append(False)
        except Exception as e:
            print(f"❌ [GET] Stats: Error {e}")
            results.append(False)

        # 2. Проверка формы (POST - негативный тест на пустые данные)
        try:
            r = client.post(f"{BASE_URL}/form/", json={})
            if r.status_code == 400: # Ожидаем 400, так как данные пустые
                print("✅ [POST] Form Validation: OK")
                results.append(True)
            else:
                print(f"❌ [POST] Form Validation: Unexpected status {r.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ [POST] Form: Error {e}")
            results.append(False)

    if all(results):
        print("\n🎉 Все системы в норме!")
        sys.exit(0)
    else:
        print("\n⚠️ Обнаружены проблемы!")
        sys.exit(1)

if __name__ == "__main__":
    test_api()