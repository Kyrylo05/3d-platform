# 🧠 3D-Платформа для онлайн-замовлення 3D-друку

## 🎓 Дипломна робота бакалавра з комп’ютерних наук

---

## 🔍 Опис проєкту

Цей веб-застосунок — це **3D-платформа для замовлення друку моделей**, створена як мінімально життєздатний продукт (MVP).  
Користувач може:

- Зареєструватися або увійти до свого акаунта
- Завантажити STL-файл 3D-моделі (планується)
- Обрати параметри друку (матеріал, розмір, колір тощо)
- Отримати **автоматичний розрахунок вартості до друку**
- Отримати PDF-квитанцію (опціонально)
- Переглядати свої замовлення у захищеному кабінеті

Платформа покликана **спростити процес взаємодії** між замовниками та виконавцями 3D-друку.

---

## 🎯 Мета роботи

> Розробити інтуїтивно зрозумілу веб-платформу для прийому, обробки та розрахунку онлайн-замовлень на 3D-друк з базовою системою обліку користувачів.

---

## 🧱 Технології

| Компонент           | Технологія               |
|---------------------|--------------------------|
| Бекенд              | Python 3.12 + Flask      |
| База даних          | SQLite (через SQLAlchemy)|
| Авторизація         | Flask-Login              |
| Шаблони             | Jinja2                   |
| Хешування паролів   | Werkzeug                 |
| Фронтенд            | HTML5 + Bootstrap 5      |
| Обробка STL         | numpy-stl (планується)   |
| Генерація PDF       | ReportLab (опційно)      |

---

## 🔐 Реалізований функціонал

- ✅ Реєстрація користувача з валідацією
- ✅ Безпечне збереження пароля (хеш)
- ✅ Вхід і вихід (з використанням Flask-Login)
- ✅ Захищений особистий кабінет (`@login_required`)
- ✅ Адаптивна навігація (navbar)
- 🧪 Завантаження STL-файлів (на етапі реалізації)
- 🧮 Математична модель розрахунку ціни до друку (планується)
- 📃 Зберігання замовлень у базі (наступний етап)
- 📄 Генерація PDF-чеку (опціонально)

---

## 🗂 Структура проєкту
![ChatGPT Image Apr 8, 2025, 05_48_35 PM](https://github.com/user-attachments/assets/c5953eff-c884-4803-8a9c-3a94c56dc8ba)




---

## 🚀 Як запустити локально

```bash
# Клонувати репозиторій
git clone https://github.com/your-username/3d_platform.git
cd 3d_platform

# Створити та активувати віртуальне середовище
python3 -m venv venv
source venv/bin/activate

# Встановити залежності
pip install -r requirements.txt

# Запустити застосунок
python app.py
``` 
🖥️ Перейдіть у браузері на:
http://127.0.0.1:5010
---
## 🧮 Приклад математичної логіки розрахунку
    
💡 Ціна = (вага STL-файлу в грамах) × (ціна за грам для вибраного матеріалу)
    
Автоматичне визначення об’єму STL (планується)
    
Коефіцієнт складності для кольору, точності
    
Збереження в історії
---    
## 👨‍🎓 Автор проєкту
    
[Кирило Ільїнов Миколайович]
Бакалавр комп’ютерних наук
[Назва факультету / університету]
Україна, 2025
📄 Ліцензія
    
Цей проєкт ліцензовано під MIT License — вільно використовуйте в навчальних та комерційних цілях.
