-- North Star Metric: completed learning sessions per user per week
SELECT date(s.completed_at, 'weekday 0', '-6 days') AS week_start,
       COUNT(*) AS completed_sessions,
       COUNT(DISTINCT s.user_id) AS active_learners,
       ROUND(1.0 * COUNT(*) / NULLIF(COUNT(DISTINCT s.user_id), 0), 2) AS sessions_per_active_user
FROM sessions s
WHERE s.completed_at IS NOT NULL
GROUP BY 1
ORDER BY 1;

-- Funnel: registration -> onboarding -> first message -> first completed exercise -> paid
WITH steps AS (
  SELECT COUNT(*) AS registrations,
         (SELECT COUNT(*) FROM onboarding) AS onboarding,
         (SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='message_sent') AS first_message,
         (SELECT COUNT(DISTINCT user_id) FROM events WHERE event_name='exercise_completed') AS completed_exercise,
         (SELECT COUNT(DISTINCT user_id) FROM subscriptions WHERE status='active') AS paid
  FROM users
)
SELECT * FROM steps;

-- AI quality by model: explicit success + user feedback + retries + latency + cost
SELECT m.model_name,
       COUNT(*) AS responses,
       ROUND(AVG(m.response_latency_ms)) AS avg_latency_ms,
       ROUND(AVG(m.token_cost), 4) AS avg_cost,
       ROUND(AVG(m.task_success) * 100, 1) AS task_success_rate,
       ROUND(AVG(m.retry_count), 2) AS avg_retries
FROM messages m
WHERE m.role='assistant'
GROUP BY m.model_name;

-- D1/D7/D30 retention by signup cohort
WITH first_activity AS (
  SELECT user_id, MIN(date(occurred_at)) AS first_day
  FROM events GROUP BY user_id
), cohort AS (
  SELECT u.id AS user_id, date(u.created_at) AS cohort_day,
         CAST(julianday(f.first_day) - julianday(date(u.created_at)) AS INTEGER) AS activation_gap
  FROM users u LEFT JOIN first_activity f ON f.user_id=u.id
)
SELECT cohort_day,
       COUNT(*) AS cohort_users,
       SUM(CASE WHEN activation_gap <= 1 THEN 1 ELSE 0 END) AS d1_users,
       SUM(CASE WHEN activation_gap <= 7 THEN 1 ELSE 0 END) AS d7_users,
       SUM(CASE WHEN activation_gap <= 30 THEN 1 ELSE 0 END) AS d30_users
FROM cohort
GROUP BY cohort_day
ORDER BY cohort_day;

-- A/B test activation: Variant B vs A, two-proportion z-test performed in Python app.
SELECT variant,
       COUNT(*) AS users,
       SUM(CASE WHEN EXISTS (
         SELECT 1 FROM events e WHERE e.user_id=users.id AND e.event_name='exercise_completed'
       ) THEN 1 ELSE 0 END) AS activated_users,
       ROUND(100.0 * SUM(CASE WHEN EXISTS (
         SELECT 1 FROM events e WHERE e.user_id=users.id AND e.event_name='exercise_completed'
       ) THEN 1 ELSE 0 END) / COUNT(*), 1) AS activation_rate
FROM users
GROUP BY variant;
