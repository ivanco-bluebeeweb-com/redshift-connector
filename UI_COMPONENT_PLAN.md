# Amazon Redshift Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`.
Основано на `IDEAL_ONBOARDING.md` этого приложения.

## 0. Разница с идеалом
Идеал предлагает live-статус execute_sql через polling — сегодняшние
примитивы не поддерживают inline long-poll. Компромисс: `execute_sql`
возвращает statement_id сразу, а `get_statement_result`/`get_statement_status`
— отдельные кнопки в форме "Обновить статус" рядом со списком запросов.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(align="start") + account/region label + `ui.Divider` + navigation `ui.ListItem`(Clusters/Serverless/Databases/Query Editor) + `ui.Button`("App settings") | Без карточек по стандарту, один "App settings" внизу. |
| Connect form (sidebar, до подключения) | `ui.Form`(action="connect_redshift") с `ui.Stack`(align="stretch") внутри children, `_field()`-обёрнутые `ui.Input`(label="Access Key ID"), `ui.Password`(label="Secret Access Key"), `ui.Select`(label="Регион") | Контейнер растянут на всю ширину, лейблы + контекстные плейсхолдеры (учли DUI-баг full_width на Form — оборачиваем в Stack). |
| Clusters (center, `center_overlay=True`) | `ui.DataTable`(cluster_identifier, node_type, status Badge, publicly_accessible Badge) + row action `ui.Button`("Подробнее") | DataTable — стандартный список объектов. |
| Serverless (center) | `ui.DataTable`(workgroup_name, namespace_name, status Badge, base_capacity) | Отдельная вкладка т.к. Serverless — другая модель ресурсов. |
| Databases (center) | `ui.DataTable`(database_name) + `ui.Button`("Открыть Query Editor") | Простой список — Data API отдаёт только имена. |
| Query Editor (center) | `ui.Form`(action="execute_sql") с полями target (cluster/workgroup Select) + database (Input) + sql (Input, placeholder="SELECT * FROM public.table LIMIT 100") + `ui.DataTable` под формой с результатом последнего statement | Форма и результат в одном экране — типичный SQL runner UX. |
| App settings (center, отдельная панель) | `ui.Text`(инструкция по IAM policy) + список подключений с `ui.Button`("Отключить", variant="destructive") | Все walkthrough-инструкции только здесь, не дублируются в сайдбаре. |

## 2. Форма подключения — стандарт
- `ui.Form(action="connect_redshift", submit_label="Подключить", children=[ui.Stack(direction="v", gap=3, align="stretch", children=[...])])` — full_width НЕ передаём в Form (не валидный kwarg, багфикс из BigQuery Connector).
- Каждое поле обёрнуто `_field(label, node)` — видимый `ui.Text`(variant="caption") + сам инпут.
- Плейсхолдеры контекстные: "AKIAIOSFODNN7EXAMPLE", "оставьте пустым для постоянных ключей" (session_token), "us-east-1".

## 3. Инварианты (закреплено по прошлой правке)
- Инпуты всегда с лейблами, плейсхолдер контекстно подходящий.
- Форма растянута на всю ширину сайдбара, содержимое растянуто внутри неё.
- Инструкции не дублируются между сайдбаром и модалкой/App settings.
