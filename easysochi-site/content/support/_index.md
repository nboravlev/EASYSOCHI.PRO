---
title: "Рубль"
description: "Поддержите развитие литературного ассистента — проекта о смыслах, внимании и чтении."
draft: false
---
{{< css src="/css/support.css" >}}

# Литературный ассистент

ИИ может быть не просто инструментом, а **собеседником, который помогает думать глубже**.  
Проект «Литературный ассистент» создаёт пространство, где технологии усиливают способность человека **осмыслять прочитанное**, структурировать идеи и делать выводы.

---

{{< respimg
  src="/images/blog/reader_post_300.png" 
  alt="EASYSOCHI ассистент для чтения"
>}}

---

## Почему это важно

Мы верим, что осознанное чтение — это не просто навык, а **форма внутренней свободы**.  
Мы хотим, чтобы каждый мог использовать искусственный интеллект как инструмент размышления, а не как замену мышлению.

Проект открыт, без рекламы и платных барьеров. Чтобы он развивался — нам нужна поддержка.

---

## Этапы проекта

Каждая пожертвованная сумма помогает пройти один из следующих шагов:

1. **Подключение LLM** — интеграция большой языковой модели, чтобы диалоги стали живыми, связными и умными.  
2. **Подключение базы данных** — создание внутренней памяти: история чтений, заметок и ответов, чтобы собеседник "помнил" контекст.  
3. **Веб-интерфейс для тестирования** — откроем доступ первым поддержавшим, чтобы они могли попробовать раннюю версию и дать обратную связь.  
4. **Чатбот-приложение** — выведем ассистента в Telegram (и другие мессенджеры), чтобы общаться с ним было легко и естественно.  
5. **Память и ментальный портрет** — будем записывать и анализировать общение, постепенно формируя индивидуальный “ментальный след”:  
   помощник станет не просто умным, а **понимающим вас** — с вашим темпом, тоном и смысловыми приоритетами.

---

## Поддержите проект

Ваш вклад помогает оплачивать хостинг, разработку и развитие новых инструментов.  
Любая сумма — это сигнал, что проект нужен людям.  

<div id="donation-container">
  <p><strong>Выберите сумму:</strong></p>

  <div id="donation-options">
    <button class="donate-btn" data-amount="100">100 ₽</button>
    <button class="donate-btn" data-amount="500">500 ₽</button>
    <button class="donate-btn" data-amount="1000">1000 ₽</button>
    <button class="donate-btn" data-amount="5000">5000 ₽</button>
    <input type="number" id="custom-amount" placeholder="Другая сумма" min="50" step="50">
  </div>

  <button id="donate-submit">Поддержать</button>
  
  <p id="donation-message" style="display:none; margin-top:10px;"></p>
</div>

<section id="donation-progress">
  <h2>Прогресс сбора</h2>

  <div class="progress-bar-container">
    <div class="progress-bar">
      <div class="progress-fill" style="width: 0%"></div>
    </div>
    <p id="progress-text">Загрузка данных...</p>
  </div>

  <h3>Последние меценаты</h3>
  <ul id="donor-list">
    <li style="color: #888;">Загрузка списка...</li>
  </ul>
</section>

<div id="donation-modal" class="modal-overlay" style="display: none;">
  <div class="modal-content">
  <span class="close-modal">&times;</span>
    <h3>Почти готово!</h3>
      <p>Введите данные для получения чека и отображения в списке спонсоров.</p>
    
  <div class="form-group">
      <input type="text" id="donor-name" placeholder="Иван Иванов (можно просто Иван)">
    </div>
    <div class="form-group">
      <label>Email (обязательно для чека)</label>
      <input type="email" id="donor-email" placeholder="example@mail.ru">
    </div>
    
  <div class="modal-footer">
      <p class="selected-sum-text">Сумма: <span id="modal-sum-display">0</span> ₽</p>
      <button id="final-pay-btn">Перейти к оплате</button>
    </div>
  </div>
</div>

<script>
document.addEventListener("DOMContentLoaded", () => {
  // === НАСТРОЙКИ ===
  const API_BASE_URL = "/donation"; 

  // --- Получаем элементы (и сразу проверяем их существование в логике ниже) ---
  const buttons = document.querySelectorAll(".donate-btn");
  const custom = document.getElementById("custom-amount");
  const mainSubmitBtn = document.getElementById("donate-submit");
  
  const modal = document.getElementById("donation-modal");
  const closeModal = document.querySelector(".close-modal");
  const finalPayBtn = document.getElementById("final-pay-btn");
  const modalSumDisplay = document.getElementById("modal-sum-display");
  const donorNameInput = document.getElementById("donor-name");
  const donorEmailInput = document.getElementById("donor-email");

  let selectedAmount = null;

  // --- 1. Логика выбора суммы ---
  if (buttons.length > 0) {
    buttons.forEach(btn => {
      btn.addEventListener("click", () => {
        buttons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        selectedAmount = btn.dataset.amount;
        if (custom) custom.value = "";
      });
    });
  }

  if (custom) {
    custom.addEventListener("input", () => {
      buttons.forEach(b => b.classList.remove("active"));
      selectedAmount = custom.value;
    });
  }

  // --- 2. Открытие модального окна ---
  if (mainSubmitBtn) {
    mainSubmitBtn.addEventListener("click", () => {
      if (!selectedAmount || selectedAmount < 50) {
        alert("Минимальная сумма — 50 рублей.");
        return;
      }
      
      // Если HTML модалки нет, просто выводим сообщение (защита от ошибки)
      if (!modal) {
        alert("Переход к оплате...");
        return;
      }

      if (modalSumDisplay) modalSumDisplay.textContent = selectedAmount;
      
      // Показываем окно + анимация
      modal.style.display = "flex";
      setTimeout(() => modal.classList.add("open"), 10);
    });
  }

  // --- 3. Закрытие окна ---
  const closeModalFunc = () => {
    if (!modal) return;
    modal.classList.remove("open");
    setTimeout(() => modal.style.display = "none", 300);
  };

  if (closeModal) closeModal.addEventListener("click", closeModalFunc);
  
  if (modal) {
    window.addEventListener("click", (e) => {
      if (e.target === modal) closeModalFunc();
    });
  }

  // --- 4. ФИНАЛЬНАЯ ОТПРАВКА ДАННЫХ ---
  if (finalPayBtn) {
    finalPayBtn.addEventListener("click", async () => {
      const name = donorNameInput ? donorNameInput.value.trim() : "";
      const email = donorEmailInput ? donorEmailInput.value.trim() : "";

      // Валидация Email
      if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        alert("Введите корректный адрес электронной почты для отправки чека.");
        if (donorEmailInput) donorEmailInput.focus();
        return;
      }

      finalPayBtn.disabled = true;
      finalPayBtn.textContent = "Создаем платеж...";

      try {
        const response = await fetch(`${API_BASE_URL}/create`, { 
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            amount: parseInt(selectedAmount),
            name: name,
            email: email
          })
        });

        if (!response.ok) throw new Error("Ошибка сервера");

        const data = await response.json();

        if (data.confirmation_url) {
          window.location.href = data.confirmation_url;
        } else {
          alert("Ошибка: API не вернул ссылку на оплату");
          finalPayBtn.disabled = false;
        }

      } catch (error) {
        console.error("Ошибка создания платежа:", error);
        alert("Не удалось создать платеж. Проверьте соединение.");
        finalPayBtn.disabled = false;
        finalPayBtn.textContent = "Перейти к оплате";
      }
    });
  }

  // --- 5. ПОЛУЧЕНИЕ СТАТИСТИКИ (С ЗАЩИТОЙ ОТ НУЛЕЙ) ---
  async function loadStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/stats`);
      
      // Если 404 или 500, просто выходим, не ломая интерфейс
      if (!response.ok) {
        console.warn("Не удалось получить статистику, статус:", response.status);
        return;
      }

      const data = await response.json();
      
      // --- Обработка нуля ---
      // Если data.raised нет, подставим 0. Если data.goal нет или 0, ставим 1 (чтобы не делить на 0)
      const raised = data.raised || 0;
      const goal = (data.goal && data.goal > 0) ? data.goal : 100000; 
      
      // Расчет процентов (не больше 100%)
      const percent = Math.min((raised / goal) * 100, 100);
      
      // Обновляем DOM
      const fill = document.querySelector(".progress-fill");
      const text = document.getElementById("progress-text");
      
      if (fill) fill.style.width = `${percent}%`;
      if (text) {
        text.innerHTML = `<strong>Собрано:</strong> ${raised.toLocaleString('ru-RU')} ₽ из ${goal.toLocaleString('ru-RU')} ₽`;
      }

      // Список донатеров
      const list = document.getElementById("donor-list");
      if (list) {
        list.innerHTML = ""; // Очищаем "Загрузка..."

        if (data.donors && data.donors.length > 0) {
          data.donors.forEach(donor => {
            const li = document.createElement("li");
            
            const strong = document.createElement("strong");
            strong.textContent = donor.name || "Аноним";
            
            li.appendChild(strong);
            li.appendChild(document.createTextNode(` — ${donor.amount.toLocaleString('ru-RU')} ₽`));
            list.appendChild(li);
          });
        } else {
          // Если донатов нет (массив пустой)
          list.innerHTML = "<li style='text-align: center; color: #888; font-style: italic;'>Пока нет пожертвований. Станьте первым!</li>";
        }
      }

    } catch (e) {
      console.error("Ошибка JS при загрузке статистики:", e);
      // При ошибке можно оставить текст "Загрузка..." или написать "Ошибка загрузки"
      const text = document.getElementById("progress-text");
      if(text) text.textContent = "Собрано: 0 ₽";
    }
  }

  // Запускаем
  loadStats();
});
</script>