---
title: "Связь"
description: "Для связи используйте форму внизу страницы."
draft: false
---

{{< css src="/css/contact.css" >}}

# Кто мы?

{{< respimg
  src="/images/tomodify/director.jpg" 
  alt="EASYSOCHI чатбот сайт приложение"
>}}

**Николай Боравлев**, основатель и директор студии EasySochi  
Живу в горах, катаюсь на сноуборде и создаю умные системы для автоматизации.  
Пишите — обсудим ваш проект!


## Напишите нам

<form id="contact-form" style="max-width: 500px; margin:auto;">
  <label for="name">Имя:</label><br>
  <input type="text" id="name" name="name" required style="width:100%; padding:8px;"><br><br>

  <label for="email">Email:</label><br>
  <input type="email" id="email" name="email" required style="width:100%; padding:8px;"><br><br>

  <label for="message">Сообщение:</label><br>
  <textarea id="message" name="message" rows="5" required style="width:100%; padding:8px;"></textarea><br><br>

  <p style="font-size: 0.9rem; color:#555;">
    Нажимая на кнопку <strong>«Отправить»</strong>, вы соглашаетесь на обработку персональных данных (Имя и Email).
  </p>

  <button type="submit" style="padding:10px 20px;">Отправить</button>
</form>

<script>
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("contact-form");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target).entries());

    // Проверка email
    if (!data.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      alert("Введите корректный адрес электронной почты.");
      return;
    }

    try {
      const response = await fetch("/api/v2/form/", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
      });

      console.log("Fetch completed, status:", response.status, response.statusText);

      if (response.ok) {
        alert("✅ Спасибо! Мы получили вашу заявку.");
        e.target.reset();
      } else {
        const text = await response.text();
        console.error("Server returned error:", response.status, text);
        alert(`❌ Ошибка отправки. Статус: ${response.status}\n${text}`);
      }
    } catch (err) {
      console.error("Fetch failed:", err);
      alert(`⚠️ Не удалось отправить сообщение.\nПодробности в консоли браузера.`);
    }
  });
});
</script>