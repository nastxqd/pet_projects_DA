# Lingua Lab

## Продуктовая аналитика AI-репетитора английского языка

Lingua Lab — локальный demo-продукт, который показывает полный цикл работы продуктового аналитика в AI-продукте:

```text
данные → пользовательская проблема → гипотеза → эксперимент → рекомендация → измеримый результат
```

Проект объединяет простой AI-интерфейс для ученика и аналитический workspace для команды продукта.

Внутри можно продемонстрировать:

- регистрацию и onboarding;
- выбор цели и уровня английского;
- AI-чат с измерением latency и стоимости ответа;
- практические задания;
- завершение задания и scoring;
- thumbs up/down для оценки AI-ответов;
- конверсию в тариф Pro;
- воронку активации;
- retention D1/D7/D30;
- сегментацию по целям пользователей;
- сравнение Free и Pro;
- причины drop-off;
- A/B-тест нового onboarding;
- экспорт raw events в CSV;
- SQL-запросы и dbt-модели для аналитического слоя.

---

## Скачать проект

После публикации репозитория на GitHub добавьте в этот раздел реальные ссылки:

```md
[Скачать проект в ZIP](https://github.com/USERNAME/REPOSITORY/archive/refs/heads/main.zip)

[Открыть репозиторий на GitHub](https://github.com/USERNAME/REPOSITORY)

[Открыть рабочее demo-приложение](https://YOUR-APP.onrender.com)
```

Замените `USERNAME`, `REPOSITORY` и `YOUR-APP` на свои значения.

Ссылки на файлы внутри репозитория оформляются относительно README:

```md
[Открыть backend](./app.py)
[Открыть схему базы данных](./schema.sql)
[Открыть SQL-запросы](./analytics_queries.sql)
```

Локальный адрес `http://localhost:8000` работает только на компьютере, где запущен сервер. Для других пользователей нужно либо дать им ZIP-ссылку на GitHub, либо разместить приложение на внешнем хостинге.

---

## Быстрый запуск на Windows

### Вариант 1. Запуск двойным кликом

1. Скачайте ZIP-архив проекта и распакуйте его.
2. Откройте распакованную папку.
3. Дважды кликните файл `run.bat`.
4. Откройте браузер и перейдите по адресу [http://localhost:8000](http://localhost:8000).

### Вариант 2. Запуск из PowerShell

```powershell
cd "ПУТЬ_К_РАСПАКОВАННОЙ_ПАПКЕ"
python app.py
```

После запуска в терминале появится:

```text
Lingua Lab is running at http://localhost:8000
```

Остановить сервер можно сочетанием `Ctrl + C`.

### Требования

- Windows 10 или Windows 11;
- Python 3.10 или новее;
- Chrome, Edge или Firefox;
- интернет не требуется для backend и demo AI.

Проверить установленный Python:

```powershell
python --version
```

Если команда `python` не найдена, установите Python и включите опцию `Add Python to PATH`.

### Если порт 8000 занят

```powershell
$env:PORT=8001
python app.py
```

После этого откройте `http://localhost:8001`.

---

## Первый сценарий демонстрации

### 1. Загрузить демо-данные

После открытия приложения нажмите **«Загрузить демо-данные»**. Будут созданы пользователи, события, AI-сообщения, задания, оценки и подписки. Даты распределены по нескольким неделям, поэтому аналитические экраны сразу заполнены.

Повторный запуск загрузки не создаёт дубликаты, если демо-данные уже присутствуют.

### 2. Создать собственного пользователя

Нажмите **«Начать свой путь»** и заполните имя, email, уровень английского и учебную цель. После регистрации пользователь проходит onboarding и получает вариант A или B для A/B-теста.

### 3. Открыть AI-чат

В чате можно:

- отправить сообщение AI-ассистенту;
- получить обратную связь;
- посмотреть latency ответа и его стоимость;
- запустить и завершить практическое задание;
- поставить thumbs up/down;
- активировать тариф Pro.

Каждое действие записывается в таблицу `events`.

### 4. Проверить аналитику

#### Обзор

Показывает количество пользователей, activation rate, учебные сессии, paid conversion, North Star Metric, сигналы продукта, цели пользователей, сравнение Free и Pro и гипотезу недели.

#### Воронка & retention

Показывает путь:

```text
Регистрация → Onboarding → Первое сообщение → Завершённое задание → Оплата
```

Также доступны D1, D7 и D30 retention и список основных drop-off points.

#### AI quality

Показывает среднюю latency, task success rate, стоимость одного ответа, общую стоимость AI, thumbs quality, стоимость активного пользователя и model scorecard.

#### Эксперимент

Показывает варианты A/B-теста onboarding, activation rate, lift, z-score, p-value и решение о rollout.

---

## Продуктовая модель

### North Star Metric

```text
Количество успешно завершённых учебных сессий в неделю
```

Эта метрика отражает реальную ценность обучения, связана с регулярностью использования и может быть сопоставлена с retention и оплатой.

### Activation event

Пользователь считается активированным после события:

```text
exercise_completed
```

Это сильнее, чем регистрация или первое сообщение: пользователь уже получил первый законченный учебный результат.

### Основная воронка

```text
user_signed_up
→ onboarding_completed
→ message_sent
→ exercise_completed
→ subscription_started
```

---

## События и AI telemetry

Все продуктовые действия сохраняются в таблицу `events`.

| Событие | Когда отправляется |
|---|---|
| `user_signed_up` | Пользователь зарегистрировался |
| `onboarding_completed` | Пользователь завершил onboarding |
| `goal_selected` | Пользователь выбрал цель |
| `chat_started` | Началась AI-сессия |
| `message_sent` | Пользователь отправил сообщение |
| `ai_response_received` | Получен ответ AI |
| `exercise_started` | Пользователь начал упражнение |
| `exercise_completed` | Пользователь завершил упражнение |
| `answer_rated` | Пользователь оценил AI-ответ |
| `subscription_started` | Активирован тариф |
| `subscription_cancelled` | Тариф отменён |

Для `ai_response_received` дополнительно сохраняются:

```json
{
  "session_id": "session-id",
  "model_name": "local-demo-model",
  "response_latency_ms": 640,
  "token_cost": 0.0031,
  "task_success": true,
  "retry_count": 0
}
```

Так можно связать качество AI с поведением пользователя, а не анализировать модель отдельно от продукта.

---

## Архитектура

Проект сделан автономным и не требует Node.js, Docker, PostgreSQL или внешнего API-ключа.

```text
Browser
  ↓ HTTP
Python standard library server
  ↓
SQLite database
  ↓
Product events + AI telemetry
  ↓
Dashboard calculations
```

### Backend

`app.py` содержит HTTP-сервер, REST-подобные endpoints, инициализацию SQLite, seed-генерацию demo-данных, event tracking, локальный mock AI, расчёт dashboard metrics и экспорт CSV.

### Frontend

Папка `static/` содержит `index.html`, `styles.css`, `overrides.css`, `compare.css` и `app.js`.

### Database

`schema.sql` создаёт таблицы `users`, `onboarding`, `sessions`, `messages`, `exercises`, `ratings`, `subscriptions` и `events`. Файл `product_analytics.db` создаётся автоматически при первом запуске и добавляется в `.gitignore`.

---

## API endpoints

### Служебные endpoints

```http
GET /api/health
GET /api/dashboard
GET /api/events.csv
GET /api/user/{user_id}
```

### Регистрация и onboarding

```http
POST /api/auth/signup
POST /api/onboarding
```

Пример регистрации:

```json
{
  "name": "Анна",
  "email": "anna@example.com",
  "level": "B1"
}
```

Пример onboarding:

```json
{
  "user_id": "user-id",
  "goal": "Подготовка к интервью",
  "level": "B1"
}
```

### AI-сессия и упражнения

```http
POST /api/session/start
POST /api/chat
POST /api/exercises
POST /api/exercises/complete
```

Пример сообщения:

```json
{
  "user_id": "user-id",
  "session_id": "session-id",
  "message": "Help me prepare for an interview"
}
```

### Feedback и подписка

```http
POST /api/rate
POST /api/subscription
POST /api/subscription/cancel
```

Для `/api/rate`:

```json
{
  "user_id": "user-id",
  "session_id": "session-id",
  "rating": 1
}
```

Значение `1` означает thumbs up, `0` — thumbs down.

---

## SQL и dbt

`analytics_queries.sql` содержит запросы для North Star Metric, activation funnel, AI quality by model, D1/D7/D30 retention и сравнения вариантов A/B-теста.

В проекте есть dbt-слой:

```text
dbt_project.yml
models/
├── staging/
│   └── stg_events.sql
└── marts/
    └── fct_product_metrics.sql
```

`stg_events.sql` приводит сырые события к аналитической структуре.

`fct_product_metrics.sql` строит витрину по датам и событиям с количеством событий, уникальными пользователями, средней latency, средней стоимостью и task success rate.

Текущая demo-версия использует SQLite для запуска без инфраструктуры. Для production-окружения слой можно перенести в PostgreSQL или ClickHouse без изменения продуктовой логики событий.

---

## A/B-тест onboarding

### Гипотеза

Если показать пользователю первое учебное задание прямо внутри onboarding, то больше пользователей завершат первую практику и вернутся к продукту.

### Варианты

| Вариант | Описание |
|---|---|
| A | Текущий onboarding без задания |
| B | Onboarding с первым мини-заданием |

### Primary metric

```text
Activation rate = пользователи с exercise_completed / все пользователи варианта
```

### Статистический тест

Используется двухвыборочный z-test для разницы конверсий:

```text
z = (pB − pA) / √(p̄(1−p̄)(1/nA+1/nB))
```

Уровень значимости: `α = 0.05`.

Если `p-value < 0.05` и нет отрицательного guardrail-сигнала по стоимости и качеству AI, вариант B можно раскатывать. При недостаточной выборке эксперимент продолжается.

---

## Что можно рассказать на собеседовании

Пример формулировки проекта в резюме:

> Разработал продуктовую аналитику AI-репетитора английского языка: event schema, activation funnel, D1/D7/D30 retention, AI quality metrics, unit economics и A/B-тест onboarding с расчётом статистической значимости.

Пример продуктового вывода:

> Анализ показал, что главным моментом активации является завершение первого задания, а не отправка первого сообщения. Поэтому рекомендую встроить короткое упражнение в onboarding и протестировать вариант B. Решение принимается по activation rate, retention D7, AI task success и стоимости первой сессии.

---

## Типичные проблемы

### Браузер не открывает страницу

Убедитесь, что в терминале запущен `python app.py`, а адрес начинается с `http://localhost`, не с `file://`.

### Команда Python не найдена

Проверьте альтернативную команду:

```powershell
py --version
py app.py
```

### Нужно сбросить данные

Остановите сервер и удалите файл `product_analytics.db`. При следующем запуске база создастся заново.

### Нужно посмотреть raw events

Откройте в браузере:

```text
http://localhost:8000/api/events.csv
```

Или нажмите **«Экспорт CSV»** в левом меню приложения.

---

## Как опубликовать проект на GitHub

1. Создайте новый публичный репозиторий на [github.com](https://github.com).
2. Загрузите в него все файлы проекта.
3. Убедитесь, что в репозиторий не попал файл `product_analytics.db`.
4. Скопируйте ссылку на ZIP-архив:

   ```text
   https://github.com/USERNAME/REPOSITORY/archive/refs/heads/main.zip
   ```

5. В начале этого README замените шаблонные ссылки на реальные.

Пользователь сможет скачать ZIP, распаковать его, установить Python и запустить проект командой:

```powershell
python app.py
```

GitHub хранит исходный код и ZIP-архив, но сам по себе не запускает Python backend. Для публичного demo используйте хостинг, поддерживающий Python-сервер.

## Структура проекта

```text
pet_projects/
├── app.py
├── schema.sql
├── analytics_queries.sql
├── dbt_project.yml
├── README.md
├── run.bat
├── run.ps1
├── .gitignore
├── models/
│   ├── staging/
│   │   └── stg_events.sql
│   └── marts/
│       └── fct_product_metrics.sql
└── static/
    ├── index.html
    ├── styles.css
    ├── overrides.css
    ├── compare.css
    └── app.js
```

---

## Ограничения demo-версии

AI-ответы работают в автономном mock-режиме через функцию `ai_reply()`. Это позволяет запускать проект без ключей API и сетевых зависимостей.

При подключении реальной модели необходимо сохранить ту же telemetry-схему:

- название модели;
- latency;
- стоимость токенов;
- task success;
- retries;
- пользовательская оценка.

После этого аналитические запросы и dashboard смогут работать без изменения продуктовой модели.
