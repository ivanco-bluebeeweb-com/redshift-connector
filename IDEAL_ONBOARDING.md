# Amazon Redshift Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: data
engineer, администрирующий собственный AWS-аккаунт с Redshift (provisioned
cluster и/или Redshift Serverless).

## 1. Credential type
AWS Access Key ID + Secret Access Key (тот же BYOK-паттерн, что AWS
Connector) — все запросы подписываются AWS SigV4 напрямую (переиспользуем
`aws_sigv4.py` из AWS Connector, т.к. в рантайме нет boto3). Через них
работает Redshift Data API — не нужен ни JDBC-драйвер, ни отдельные
креды на сам кластер (Data API сам достаёт секрет из Secrets Manager или
использует temporary credentials).

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` со ссылкой "IAM > Users > Security
   credentials > Create access key" и явным напоминанием: политике нужен
   `redshift-data:*` + `redshift:GetClusterCredentials` (или
   `redshift-serverless:GetCredentials`) — частая ошибка: ключ создан, но
   без прав на Data API, первый запрос падает с AccessDenied.
2. **Форма** — access_key_id, secret_access_key (Password), region (Select
   с частыми регионами AWS), опционально session_token для временных
   креды (SSO/AssumeRole).
3. **После успеха** — сразу `audit_redshift`: кластеры без automated
   snapshot, workgroups без enhanced VPC routing, наличие publicly
   accessible кластеров (частая находка для security-обзора) — сразу
   полезно, не пустой экран.
4. **Clusters-first UX** — центр экрана сразу показывает список
   provisioned-кластеров и serverless workgroups вместе (namespace/
   workgroup), т.к. многие аккаунты используют оба режима одновременно.
5. **Ошибка "AccessDenied для Data API"** — конкретное сообщение: "У
   этого IAM-пользователя нет прав на Redshift Data API — добавьте
   политику AmazonRedshiftDataFullAccess (или уже кастомную с
   redshift-data:*) и повторите", а не общее "не удалось подключиться".
6. **Ошибка "cluster/workgroup not found for Data API"** — Data API
   требует явно указать либо cluster_identifier + db_user/secret_arn,
   либо workgroup_name (для Serverless) — если запрос выполняется без
   выбранного целевого кластера/workgroup, форма должна прямо попросить
   выбрать его, а не падать с невнятной 400.
7. **Query-first workflow** — рядом со списком баз данных кнопка
   "Выполнить запрос" ведёт к простому SQL-редактору; `execute_sql`
   выполняется асинхронно через Data API (execute-statement возвращает
   statement_id, дальше poll через describe-statement) — UI должен
   явно показывать "Выполняется..." вместо зависания.
8. **Не путать регион аккаунта с регионом кластера** — Redshift Data API
   region-scoped: если кластер в другом регионе, чем указан при
   подключении, ошибка "cluster not found" — сообщение должно подсказывать
   проверить регион.

## 3. Что публикуется
Provisioned-кластеры (список/детали/snapshot management), Redshift
Serverless (namespaces/workgroups), Databases (list via Data API),
Data API (execute_sql/describe/cancel/list statements), audit.
