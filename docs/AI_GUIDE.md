# AI Guide

## Purpose
This document gives a compact, practical map of the repo so an assistant can navigate the codebase quickly and make safe changes.

## Stack
- Backend: FastAPI + SQLAlchemy + Alembic (Python 3.12 via Docker).
- Database: PostgreSQL 16 (Docker Compose service `db`).
- Frontend: Vue 3 + Vite + Pinia + Axios + SCSS.
- Storage: S3-compatible object storage with presigned URLs.
- OCR: Tesseract + pdf2image + Pillow.
- LLM: OpenAI-compatible API (text and vision) for invoice parsing.
- Fingerprint: ZKFinger SDK plus local tools in `tools/`.

## Run (local)
1. `docker-compose up --build` (backend + db; frontend static is served by backend if built).
2. Dev frontend: `cd frontend`, then `npm ci` and `npm run dev`.
3. Optional: `docker compose --profile dev up --build` (runs the frontend container on port 5173).

## Entry Points
- Backend app: `app/main.py` (FastAPI app and router registration).
- Backend container: `backend/entrypoint.sh` (runs `alembic upgrade head` before app start).
- Frontend app: `frontend/src/main.js`.
- Frontend routes: `frontend/src/router/index.js`.
- Frontend API client: `frontend/src/api.js`.

## Repo Map
- `app/` FastAPI app entry and config.
- `backend/` domain logic, routers, schemas, services, tasks.
- `frontend/` Vue app.
- `alembic/` DB migrations.
- `docs/` documentation.
- `tools/` scripts and fingerprint tooling.
- `ZKFingerSDK_Windows_Standard/` vendor SDK.

## Backend Structure
- Routers: `backend/routers/*.py` with `/api` endpoints, registered in `app/main.py`.
- Schemas: `backend/schemas/*.py` (Pydantic DTOs).
- Models: `backend/bd/models/*.py` aggregated in `backend/bd/models/__init__.py`.
- DB: `backend/bd/database.py` (engine, session, `get_db`).
- Auth: `backend/utils.py` (JWT, password hashing, `get_current_user`).
- Permissions: `backend/services/permissions.py` and `backend/routers/access_control.py`.
- Background tasks: `backend/tasks/*` (started in `app/main.py`).
- S3: `backend/services/s3.py`.
- OCR: `backend/services/ocr.py`.
- LLM: `backend/services/llm.py`.
- Accounting: `backend/routers/accounting.py`, `backend/schemas/accounting.py`, `backend/bd/models/accounting.py`.
- Payroll: `backend/routers/payroll.py`, `backend/services/payroll_*`.
- KPI: `backend/routers/kpi.py`, `backend/bd/models/kpi.py`.
- Inventory: `backend/routers/inventory.py`, `backend/bd/models/inventory.py`.
- Staff and HR: `backend/routers/staff_*`, `backend/routers/employees_card.py`, `backend/bd/models/hr.py`.
- iiko integration: `app/config.py`, `backend/bd/iiko_olap.py`, `backend/routers/iiko_*`.

## Security Rules for New APIs
- All new business endpoints under `/api/*` must be protected by centralized auth in `app/main.py` and `backend/utils.py`. Do not create public data endpoints by default.
- Browser sessions must use the current cookie-based flow with `HttpOnly` auth cookies plus server-side session validation via `AuthSession`. Do not build new browser APIs around permanent bearer tokens in storage.
- Logout must revoke the server-side session, not only clear a cookie or remove client state.
- If a surface is isolated from the main admin app (for example checklist portal), use a separate auth scope and a separate cookie/session flow instead of reusing the main session blindly.
- New router code should rely on shared auth helpers (`get_current_user`, centralized token resolution, permission checks). Do not duplicate ad-hoc token parsing inside routers unless there is a strict integration reason.
- Public endpoints are allowed only for explicit health/login flows and must be intentionally whitelisted with a clear reason. If an endpoint returns business data, it must require auth.
- Machine-to-machine integrations must use a dedicated token or integration secret, fail closed when the secret is missing, and must not silently fall back to insecure defaults.
- Do not store browser auth tokens in `localStorage`. Frontend auth state may keep non-sensitive UI data, but access to protected APIs must rely on secure session handling.
- When adding a new API, always sanity-check: who can call it, how the session is validated, how logout/revocation behaves, and whether the endpoint leaks data without authentication.

## Frontend Structure
- Layouts: `frontend/src/layouts/` (AdminLayout and nested layouts).
- Pages: `frontend/src/pages/` and `frontend/src/pages/AdminLayout/*`.
- UI components: `frontend/src/components/UI-components`.
- Styles: `frontend/src/assets/styles` (SCSS; `vars.scss` for variables).
- State: `frontend/src/stores/user.js` (Pinia store).
- API client: `frontend/src/api.js` (Axios + caching).

## Environment Variables (names only)
- App and auth: `DEFAULT_USERNAME`, `DEFAULT_PASSWORD`, `SECRET_KEY`, `APP_TZ`, `PORT`.
- Database: `DATABASE_URL`, `DATABASE_PUBLIC_URL`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.
- Secret manager: `SECRET_MANAGER_PROVIDER`, `SECRET_MANAGER_SECRET_ID`, `SECRET_MANAGER_AWS_REGION`, `AWS_REGION`, `AWS_DEFAULT_REGION`.
- iiko config: `IIKO_LOGIN`, `IIKO_PASSWORD`, `IIKO_RESTAURANTS_JSON`, `IIKO_TRANSLATIONS_JSON`, `IIKO_DATA_DIR`, `IIKO_MENU_DIR`.
- S3: `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_CHECKLIST_BUCKET`, `S3_REGION`, `S3_PRESIGNED_EXPIRES`, `ACCOUNTING_S3_PREFIX`.
- LLM: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_VISION_MODEL`, `OPENAI_BASE_URL`, `OPENAI_PROXY_URL`.
- Frontend: `VITE_SERVER_URL`, `VITE_FINGER_AGENT_URL`.

## Feature Flows

### Accounting Invoices
Primary flow:
```
InvoicesPage.vue
-> api.js: createAccountingInvoice (multipart)
-> backend/routers/accounting.py: POST /api/accounting/invoices
-> backend/services/s3.py: upload_bytes
-> DB: AccountingInvoice + AccountingInvoiceEvent + AccountingInvoiceChange
-> api.js: fetchAccountingInvoices / updateAccountingInvoice / updateAccountingInvoiceStatus
```

OCR/LLM assist flow (optional prefill):
```
InvoicesPage.vue
-> api.js: analyzeAccountingInvoice / analyzeAccountingInvoiceLLM
-> backend/routers/accounting.py: /invoices/ocr or /invoices/ocr-llm
-> backend/services/ocr.py (+ backend/services/llm.py for LLM path)
-> UI fills amount/payee/purpose/date fields
```

Attachments flow:
```
InvoicesPage.vue
-> api.js: uploadAccountingInvoiceFile / uploadAccountingPaymentOrder / uploadAccountingClosingDocument
-> backend/routers/accounting.py: /invoice-file /payment-order /closing-documents
-> S3 upload + event logging
```

Notes:
- Status list: `backend/schemas/accounting.py` (strings are in Russian).
- Closing documents can auto-close the invoice when status requires closing docs.

### Payroll
Adjustments + export flow:
```
EmployeesPage.vue / PayrollAdjustmentTypesPage.vue
-> api.js: fetchPayrollAdjustmentTypes / fetchPayrollAdjustments / create|update|deletePayrollAdjustment
-> backend/routers/payroll.py
-> DB: PayrollAdjustment (+ types)
-> api.js: exportPayrollRegister -> GET /api/payroll/export (XLSX)
```

Advances flow:
```
PayrollAdvancePage.vue
-> api.js: fetchAdvanceStatements / createAdvanceStatement / refreshAdvanceStatement
-> backend/routers/payroll_advances.py
-> backend/services/payroll_advances.py (calculations)
-> api.js: changeAdvanceStatus / postAdvanceStatement / downloadAdvanceStatement
```

Notes:
- Advance statuses: draft -> review -> confirmed -> ready -> posted (see `backend/routers/payroll_advances.py`).
- Export builders live in `backend/services/payroll_export.py`.

### KPI
Metrics + rules flow:
```
KpiMetricsPage.vue / KpiRulesPage.vue
-> api.js: fetchKpiMetrics / createKpiMetric / updateKpiMetric / fetchKpiRules
-> backend/routers/kpi.py (requires SuperAdmin)
-> DB: KpiMetric / KpiRule
```

Plan/fact flow:
```
KpiPlanFactPage.vue
-> api.js: fetchKpiPlanFacts / upsertKpiPlanFact / fetchKpiPlanFactsBulk
-> backend/routers/kpi.py
-> DB: KpiPlanFact
```

Results + payouts flow:
```
KpiResultsPage.vue / KpiPayoutsPage.vue
-> api.js: fetchKpiResults / createKpiPayoutPreview / updateKpiPayoutItem
-> backend/routers/kpi.py: /kpi/payouts/preview -> draft batch
-> POST /kpi/payouts/{id}/post -> writes PayrollAdjustment rows
```

Notes:
- KPI access is restricted to SuperAdmin (see `backend/routers/kpi.py` and route meta).
- Payout posting creates payroll adjustments using bonus/penalty adjustment types.

## UI → API → Service → Model Maps

### Accounting
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `InvoicesPage.vue` | `fetchAccountingInvoices(params)` | `GET /api/accounting/invoices` | DB query in router | `AccountingInvoice` |
| `InvoicesPage.vue` | `createAccountingInvoice(formData)` | `POST /api/accounting/invoices` | `s3.upload_bytes` | `AccountingInvoice`, `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `updateAccountingInvoice(id, payload)` | `PUT /api/accounting/invoices/{id}` | change logging in router | `AccountingInvoice`, `AccountingInvoiceChange`, `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `updateAccountingInvoiceStatus(id, payload)` | `PUT /api/accounting/invoices/{id}/status` | status change logging | `AccountingInvoice`, `AccountingInvoiceChange`, `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `deleteAccountingInvoice(id)` | `DELETE /api/accounting/invoices/{id}` | event logging | `AccountingInvoice`, `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `fetchAccountingInvoiceChanges(id)` | `GET /api/accounting/invoices/{id}/changes` | DB query in router | `AccountingInvoiceChange` |
| `InvoicesPage.vue` | `fetchAccountingInvoiceEvents(id)` | `GET /api/accounting/invoices/{id}/events` | DB query in router | `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `uploadAccountingInvoiceFile(id, file)` | `POST /api/accounting/invoices/{id}/invoice-file` | `s3.upload_bytes` | `AccountingInvoice`, `AccountingInvoiceChange`, `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `uploadAccountingPaymentOrder(id, file)` | `POST /api/accounting/invoices/{id}/payment-order` | `s3.upload_bytes` | `AccountingInvoice`, `AccountingInvoiceChange`, `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `uploadAccountingClosingDocument(id, file)` | `POST /api/accounting/invoices/{id}/closing-documents` | `s3.upload_bytes` | `AccountingInvoiceClosingDocument`, `AccountingInvoiceEvent` |
| `InvoicesPage.vue` | `analyzeAccountingInvoice(file)` | `POST /api/accounting/invoices/ocr` | `services/ocr.py` | none (analysis only) |
| `InvoicesPage.vue` | `analyzeAccountingInvoiceLLM(file)` | `POST /api/accounting/invoices/ocr-llm` | `services/ocr.py` + `services/llm.py` | none (analysis only) |

### Payroll
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `EmployeesPage.vue` | `fetchPayrollAdjustmentTypes()` | `GET /api/payroll/adjustment-types` | DB query in router | `PayrollAdjustmentType` |
| `PayrollAdjustmentTypesPage.vue` | `createPayrollAdjustmentType(payload)` | `POST /api/payroll/adjustment-types` | DB write in router | `PayrollAdjustmentType` |
| `PayrollAdjustmentTypesPage.vue` | `updatePayrollAdjustmentType(id, payload)` | `PUT /api/payroll/adjustment-types/{id}` | DB write in router | `PayrollAdjustmentType` |
| `PayrollAdjustmentTypesPage.vue` | `deletePayrollAdjustmentType(id)` | `DELETE /api/payroll/adjustment-types/{id}` | DB write in router | `PayrollAdjustmentType` |
| `EmployeesPage.vue` | `fetchPayrollAdjustments(params)` | `GET /api/payroll/adjustments` | DB query in router | `PayrollAdjustment` |
| `EmployeesPage.vue` | `createPayrollAdjustment(payload)` | `POST /api/payroll/adjustments` | DB write in router | `PayrollAdjustment` |
| `EmployeesPage.vue` | `updatePayrollAdjustment(id, payload)` | `PUT /api/payroll/adjustments/{id}` | DB write in router | `PayrollAdjustment` |
| `EmployeesPage.vue` | `deletePayrollAdjustment(id)` | `DELETE /api/payroll/adjustments/{id}` | DB write in router | `PayrollAdjustment` |
| `EmployeesPage.vue` | `createPayrollAdjustmentsBulk(payload)` | `POST /api/payroll/adjustments/bulk` | DB write in router | `PayrollAdjustment` |
| `EmployeesPage.vue` | `exportPayrollRegister(params)` | `GET /api/payroll/export` | `services/payroll_export.py` | `PayrollAdjustment`, `PayrollSalaryResult`, `Attendance` |
| `PayrollAdvancePage.vue` | `fetchAdvanceStatements()` | `GET /api/payroll/advances` | DB query in router | `PayrollAdvanceStatement` |
| `PayrollAdvancePage.vue` | `fetchAdvanceStatement(id)` | `GET /api/payroll/advances/{id}` | DB query in router | `PayrollAdvanceStatement`, `PayrollAdvanceItem` |
| `PayrollAdvancePage.vue` | `createAdvanceStatement(payload)` | `POST /api/payroll/advances` | `services/payroll_advances.py` | `PayrollAdvanceStatement`, `PayrollAdvanceItem` |
| `PayrollAdvancePage.vue` | `refreshAdvanceStatement(id)` | `POST /api/payroll/advances/{id}/refresh` | `services/payroll_advances.py` | `PayrollAdvanceStatement`, `PayrollAdvanceItem` |
| `PayrollAdvancePage.vue` | `updateAdvanceItem(statementId, itemId, payload)` | `PATCH /api/payroll/advances/{id}/items/{itemId}` | DB write in router | `PayrollAdvanceItem` |
| `PayrollAdvancePage.vue` | `changeAdvanceStatus(statementId, payload)` | `POST /api/payroll/advances/{id}/status` | status checks in router | `PayrollAdvanceStatement` |
| `PayrollAdvancePage.vue` | `postAdvanceStatement(statementId, payload)` | `POST /api/payroll/advances/{id}/post` | router + services | `PayrollAdvanceStatement`, `PayrollAdjustment` |
| `PayrollAdvancePage.vue` | `downloadAdvanceStatement(statementId)` | `GET /api/payroll/advances/{id}/download` | XLSX build in router | `PayrollAdvanceStatement` |
| `PayrollAdvancePage.vue` | `downloadAdvanceConsolidated(statementIds)` | `POST /api/payroll/advances/consolidated/download` | `services/payroll_export.py` | `PayrollAdvanceStatement` |
| `PayrollAdvancePage.vue` | `fetchAdvanceConsolidatedStatements()` | `GET /api/payroll/advances/consolidated` | DB query in router | `PayrollAdvanceConsolidatedStatement` |
| `PayrollAdvancePage.vue` | `createAdvanceConsolidatedStatement(payload)` | `POST /api/payroll/advances/consolidated` | DB write in router | `PayrollAdvanceConsolidatedStatement` |
| `PayrollAdvancePage.vue` | `downloadAdvanceConsolidatedById(id)` | `GET /api/payroll/advances/consolidated/{id}/download` | `services/payroll_export.py` | `PayrollAdvanceConsolidatedStatement` |
| `PayrollAdvancePage.vue` | `deleteAdvanceConsolidatedStatement(id)` | `DELETE /api/payroll/advances/consolidated/{id}` | DB write in router | `PayrollAdvanceConsolidatedStatement` |
| `PayrollAdvancePage.vue` | `deleteAdvanceStatement(id)` | `DELETE /api/payroll/advances/{id}` | DB write in router | `PayrollAdvanceStatement` |

### KPI
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `KpiMetricsPage.vue` | `fetchKpiMetrics(params)` | `GET /api/kpi/metrics` | DB query in router | `KpiMetric` |
| `KpiMetricsPage.vue` | `createKpiMetric(payload)` | `POST /api/kpi/metrics` | DB write in router | `KpiMetric` |
| `KpiMetricsPage.vue` | `updateKpiMetric(id, payload)` | `PATCH /api/kpi/metrics/{id}` | DB write in router | `KpiMetric` |
| `KpiMetricsPage.vue` | `deleteKpiMetric(id)` | `DELETE /api/kpi/metrics/{id}` | DB write in router | `KpiMetric` |
| `KpiRulesPage.vue` | `fetchKpiRules(params)` | `GET /api/kpi/rules` | DB query in router | `KpiRule` |
| `KpiRulesPage.vue` | `createKpiRule(payload)` | `POST /api/kpi/rules` | DB write in router | `KpiRule` |
| `KpiRulesPage.vue` | `updateKpiRule(id, payload)` | `PATCH /api/kpi/rules/{id}` | DB write in router | `KpiRule` |
| `KpiRulesPage.vue` | `deleteKpiRule(id)` | `DELETE /api/kpi/rules/{id}` | DB write in router | `KpiRule` |
| `KpiResultsPage.vue` | `fetchKpiResults(params)` | `GET /api/kpi/results` | DB query in router | `KpiResult` |
| `KpiResultsPage.vue` | `createKpiResult(payload)` | `POST /api/kpi/results` | DB write in router | `KpiResult` |
| `KpiResultsPage.vue` | `updateKpiResult(id, payload)` | `PATCH /api/kpi/results/{id}` | DB write in router | `KpiResult` |
| `KpiResultsPage.vue` | `deleteKpiResult(id)` | `DELETE /api/kpi/results/{id}` | DB write in router | `KpiResult` |
| `KpiPlanFactPage.vue` | `fetchKpiPlanFacts(params)` | `GET /api/kpi/plan-fact` | DB query in router | `KpiPlanFact` |
| `KpiPlanFactPage.vue` | `fetchKpiPlanFactsBulk(params)` | `GET /api/kpi/plan-fact/bulk` | DB query in router | `KpiPlanFact` |
| `KpiPlanFactPage.vue` | `upsertKpiPlanFact(payload)` | `PUT /api/kpi/plan-fact` | DB write in router | `KpiPlanFact` |
| `KpiPayoutsPage.vue` | `fetchKpiPayoutBatches(params)` | `GET /api/kpi/payouts` | DB query in router | `KpiPayoutBatch` |
| `KpiPayoutsPage.vue` | `fetchKpiPayoutBatch(id)` | `GET /api/kpi/payouts/{id}` | DB query in router | `KpiPayoutBatch`, `KpiPayoutItem` |
| `KpiPayoutsPage.vue` | `deleteKpiPayoutBatch(id)` | `DELETE /api/kpi/payouts/{id}` | DB write in router | `KpiPayoutBatch` |
| `KpiPayoutsPage.vue` | `createKpiPayoutPreview(payload)` | `POST /api/kpi/payouts/preview` | calculations in router | `KpiPayoutBatch`, `KpiPayoutItem` |
| `KpiPayoutsPage.vue` | `createKpiPayoutPreviewByMetric(payload)` | `POST /api/kpi/payouts/preview-metric` | calculations in router | `KpiPayoutBatch`, `KpiPayoutItem` |
| `KpiPayoutsPage.vue` | `updateKpiPayoutItem(batchId, itemId, payload)` | `PATCH /api/kpi/payouts/{batchId}/items/{itemId}` | DB write in router | `KpiPayoutItem` |
| `KpiPayoutsPage.vue` | `deleteKpiPayoutItem(batchId, itemId)` | `DELETE /api/kpi/payouts/{batchId}/items/{itemId}` | DB write in router | `KpiPayoutItem` |
| `KpiPayoutsPage.vue` | `postKpiPayoutBatch(batchId, payload)` | `POST /api/kpi/payouts/{batchId}/post` | creates payroll adjustments | `KpiPayoutBatch`, `KpiPayoutItem`, `PayrollAdjustment` |

### Inventory
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `InventoryGroupsPage.vue` | `fetchInventoryGroups()` | `GET /api/inventory/groups` | DB query in router | `InvGroup` |
| `InventoryGroupsPage.vue` | `createInventoryGroup(payload)` | `POST /api/inventory/groups` | DB write in router | `InvGroup` |
| `InventoryGroupsPage.vue` | `updateInventoryGroup(id, payload)` | `PUT /api/inventory/groups/{id}` | DB write in router | `InvGroup` |
| `InventoryGroupsPage.vue` | `deleteInventoryGroup(id)` | `DELETE /api/inventory/groups/{id}` | DB write in router | `InvGroup` |
| `InventoryCategoriesPage.vue` | `fetchInventoryCategories(params)` | `GET /api/inventory/categories` | DB query in router | `InvCategory` |
| `InventoryCategoriesPage.vue` | `createInventoryCategory(payload)` | `POST /api/inventory/categories` | DB write in router | `InvCategory` |
| `InventoryCategoriesPage.vue` | `updateInventoryCategory(id, payload)` | `PUT /api/inventory/categories/{id}` | DB write in router | `InvCategory` |
| `InventoryCategoriesPage.vue` | `deleteInventoryCategory(id)` | `DELETE /api/inventory/categories/{id}` | DB write in router | `InvCategory` |
| `InventoryItemsPage.vue` | `fetchInventoryItems(params)` | `GET /api/inventory/items` | DB query in router | `InvItem` |
| `InventoryItemsPage.vue` | `createInventoryItem(payload)` | `POST /api/inventory/items` | DB write in router | `InvItem` |
| `InventoryItemsPage.vue` | `updateInventoryItem(id, payload)` | `PUT /api/inventory/items/{id}` | change logging in router | `InvItem`, `InvItemChange` |
| `InventoryItemsPage.vue` | `deleteInventoryItem(id)` | `DELETE /api/inventory/items/{id}` | DB write in router | `InvItem` |
| `InventoryItemsPage.vue` | `uploadInventoryItemPhoto(file)` | `POST /api/inventory/items/photo` | `s3.upload_bytes` | `InvItem` (photo key) |
| `InventoryItemsPage.vue` | `fetchInventoryItemChanges(id)` | `GET /api/inventory/items/{id}/changes` | DB query in router | `InvItemChange` |
| `InventoryRecordsPage.vue` | `fetchInventoryRecords(params)` | `GET /api/inventory/records` | DB query in router | `InvItemRecord` |
| `InventoryRecordsPage.vue` | `createInventoryRecord(payload)` | `POST /api/inventory/records` | stock update in router | `InvItemRecord`, `InvItemStock` |
| `InventoryRecordsPage.vue` | `updateInventoryRecord(id, payload)` | `PUT /api/inventory/records/{id}` | stock update in router | `InvItemRecord`, `InvItemStock` |
| `InventoryRecordsPage.vue` | `deleteInventoryRecord(id)` | `DELETE /api/inventory/records/{id}` | stock update in router | `InvItemRecord`, `InvItemStock` |
| `InventoryBalancePage.vue` | `fetchInventoryBalance(params)` | `GET /api/inventory/balance` | DB query in router | `InvItemStock` |

### Access Control
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `AccessPermissionsPage.vue` | `fetchAccessPermissions()` | `GET /api/access/permissions` | DB query in router | `Permission` |
| `AccessPermissionsPage.vue` | `fetchAccessRoles()` | `GET /api/access/roles` | DB query in router | `Role`, `RolePermission` |
| `AccessPermissionsPage.vue` | `fetchRolePermissions(roleId)` | `GET /api/access/roles/{id}/permissions` | DB query in router | `RolePermission` |
| `AccessPermissionsPage.vue` | `fetchRolePermissionsMap(ids)` | `GET /api/access/roles/permissions-map` | DB query in router | `RolePermission` |
| `AccessPermissionsPage.vue` | `updateRolePermissions(id, codes)` | `PUT /api/access/roles/{id}/permissions` | DB write in router | `RolePermission` |
| `AccessPermissionsPage.vue` | `fetchAccessPositions()` | `GET /api/access/positions` | DB query in router | `Position` |
| `AccessPermissionsPage.vue` | `fetchPositionPermissions(id)` | `GET /api/access/positions/{id}/permissions` | DB query in router | `PositionPermission` |
| `AccessPermissionsPage.vue` | `fetchPositionPermissionsMap(ids)` | `GET /api/access/positions/permissions-map` | DB query in router | `PositionPermission` |
| `AccessPermissionsPage.vue` | `addPositionPermission(id, code)` | `POST /api/access/positions/{id}/permissions` | DB write in router | `PositionPermission` |
| `AccessPermissionsPage.vue` | `removePositionPermission(id, code)` | `DELETE /api/access/positions/{id}/permissions/{code}` | DB write in router | `PositionPermission` |
| `AccessPermissionsPage.vue` | `addUserPermission(id, code)` | `POST /api/access/users/{id}/permissions` | DB write in router | `UserPermission` |
| `AccessPermissionsPage.vue` | `removeUserPermission(id, code)` | `DELETE /api/access/users/{id}/permissions/{code}` | DB write in router | `UserPermission` |
| `PositionsPage.vue` | `createAccessPosition(payload)` | `POST /api/access/positions` | DB write in router | `Position` |
| `PositionsPage.vue` | `updateAccessPosition(id, payload)` | `PATCH /api/access/positions/{id}` | DB write in router | `Position` |
| `PositionsPage.vue` | `deleteAccessPosition(id)` | `DELETE /api/access/positions/{id}` | DB write in router | `Position` |
| `PositionsPage.vue` | `fetchPaymentFormats()` | `GET /api/access/payment-formats` | DB query in router | `PaymentFormat` |
| `PositionsPage.vue`, `DepartmentsPage.vue` | `fetchRestaurantSubdivisions()` | `GET /api/access/restaurant-subdivisions` | DB query in router | `RestaurantSubdivision` |
| `DepartmentsPage.vue` | `createRestaurantSubdivision(payload)` | `POST /api/access/restaurant-subdivisions` | DB write in router | `RestaurantSubdivision` |
| `DepartmentsPage.vue` | `updateRestaurantSubdivision(id, payload)` | `PATCH /api/access/restaurant-subdivisions/{id}` | DB write in router | `RestaurantSubdivision` |
| `DepartmentsPage.vue` | `deleteRestaurantSubdivision(id)` | `DELETE /api/access/restaurant-subdivisions/{id}` | DB write in router | `RestaurantSubdivision` |

### Staff (Admin)
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `EmployeesPage.vue` | `fetchEmployees(params)` | `GET /api/staff/employees` | DB query in router | `User`, `Position`, `Role` |
| `EmployeesPage.vue` | `fetchEmployeeDetail(id)` | `GET /api/staff/employees/{id}` | DB query in router | `User` |
| `EmployeesPage.vue` | `updateStaffEmployee(id, payload)` | `PUT /api/staff/employees/{id}` | `employee_changes` logging | `User`, `EmployeeChangeEvent` |
| `EmployeesPage.vue` | `deleteStaffEmployee(id, ...)` | `DELETE /api/staff/employees/{id}` | optional iiko sync | `User` |
| `EmployeesPage.vue` | `restoreStaffEmployee(id)` | `POST /api/staff/employees/{id}/restore` | DB write in router | `User` |
| `EmployeesPage.vue` | `uploadEmployeePhoto(id, file)` | `POST /api/staff/employees/{id}/photo` | `s3.upload_employee_photo` | `User` |
| `EmployeesPage.vue` | `fetchEmployeeCard(id)` | `GET /api/employees/{id}/card` | DB query in router | `User`, `MedicalCheckRecord`, `CisDocumentRecord` |
| `EmployeesPage.vue` | `fetchEmployeeAttendances(id, params)` | `GET /api/employees/{id}/attendances` | DB query in router | `Attendance` |
| `EmployeesPage.vue` | `createEmployeeAttendance(id, payload)` | `POST /api/employees/{id}/attendances` | attendance recalcs | `Attendance` |
| `EmployeesPage.vue` | `updateEmployeeAttendance(id, attendanceId, payload)` | `PATCH /api/employees/{id}/attendances/{attendanceId}` | attendance recalcs | `Attendance` |
| `EmployeesPage.vue` | `deleteEmployeeAttendance(id, attendanceId)` | `DELETE /api/employees/{id}/attendances/{attendanceId}` | attendance recalcs | `Attendance` |
| `EmployeesPage.vue` | `recalculateEmployeeNightMinutes(id, payload)` | `POST /api/employees/{id}/attendances/recalculate-night` | attendance recalcs | `Attendance` |
| `EmployeesPage.vue` | `fetchTimesheetOptions()` | `GET /api/staff/employees/timesheet/options` | DB query in router | `Position` |
| `EmployeesPage.vue` | `exportTimesheetReport(params)` | `GET /api/staff/employees/timesheet/export` | `services/timesheet_export.py` | `Attendance` |
| `EmployeesPage.vue` | `exportEmployeesListXlsx(payload)` | `POST /api/staff/employees/export` | XLSX build in router | `User` |
| `EmployeesPage.vue` | `fetchUser(id)` | `GET /api/users/{id}` | DB query in router | `User` |
| `EmployeesPage.vue` | `createUser(payload)` | `POST /api/users` | DB write in router | `User` |
| `EmployeesPage.vue` | `updateUser(id, payload)` | `PUT /api/users/{id}` | `employee_changes` logging | `User`, `EmployeeChangeEvent` |
| `EmployeesPage.vue` | `fetchMedicalCheckTypes()` | `GET /api/medical-checks/types` | DB query in router | `MedicalCheckType` |
| `EmployeesPage.vue` | `createMedicalCheckRecord(payload)` | `POST /api/medical-checks/records` | DB write in router | `MedicalCheckRecord` |
| `EmployeesPage.vue` | `updateMedicalCheckRecord(id, payload)` | `PUT /api/medical-checks/records/{id}` | DB write in router | `MedicalCheckRecord` |
| `EmployeesPage.vue` | `deleteMedicalCheckRecord(id)` | `DELETE /api/medical-checks/records/{id}` | DB write in router | `MedicalCheckRecord` |
| `EmployeesPage.vue` | `fetchCisDocumentTypes()` | `GET /api/cis-documents/types` | DB query in router | `CisDocumentType` |
| `EmployeesPage.vue` | `createCisDocumentRecord(payload)` | `POST /api/cis-documents/records` | DB write in router | `CisDocumentRecord` |
| `EmployeesPage.vue` | `updateCisDocumentRecord(id, payload)` | `PUT /api/cis-documents/records/{id}` | DB write in router | `CisDocumentRecord` |
| `EmployeesPage.vue` | `deleteCisDocumentRecord(id)` | `DELETE /api/cis-documents/records/{id}` | DB write in router | `CisDocumentRecord` |
| `EmployeesPage.vue` | `uploadCisDocumentAttachment(id, file)` | `POST /api/cis-documents/users/{id}/attachment` | `s3.upload_user_attachment` | `CisDocumentRecord` |
| `ActivityLogPage.vue` | `fetchEmployeeChangeEvents(params)` | `GET /api/employee-change-events` | DB query in router | `EmployeeChangeEvent` |
| `LaborFund.vue` | `fetchLaborSummary(params)` | `GET /api/labor-summary` | DB query in router | `Attendance` |
| `Birthday.vue` | `fetchEmployees(params)` | `GET /api/staff/employees` | DB query in router | `User` |

### Staff Portal (Time Tracking)
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `LoginUser.vue` | `loginStaffByCode(code, options)` | `POST /api/staff/login` | staff portal router | `User`, `Attendance` |
| `TimeTracking.vue` | `fetchStaffPositions()` | `GET /api/staff/positions` | staff portal router | `Position` |
| `TimeTracking.vue` | `fetchStaffAttendancesMonth(params)` | `GET /api/staff/attendances/month` | staff portal router | `Attendance` |
| `TimeTracking.vue` | `openStaffAttendance(payload)` | `POST /api/staff/attendances/open` | attendance calculations | `Attendance` |
| `TimeTracking.vue` | `closeStaffAttendance(payload)` | `POST /api/staff/attendances/close` | attendance calculations | `Attendance` |
| `TimeTracking.vue` | `identifyFingerprint()` | `POST http://127.0.0.1:47123/identify` | local finger agent | none (external) |

### Restaurants & Companies
| UI (Vue) | Frontend API | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `RestaurantsPage.vue` | `api.get('/api/companies/')` | `GET /api/companies` | DB query in router | `Company` |
| `RestaurantsPage.vue` | `api.get('/api/restaurants/')` | `GET /api/restaurants` | DB query in router | `Restaurant` |
| `RestaurantsPage.vue` | `api.post('/api/restaurants/{companyId}')` | `POST /api/restaurants/{company_id}` | DB write in router | `Restaurant` |
| `RestaurantsPage.vue` | `api.put('/api/restaurants/{id}')` | `PUT /api/restaurants/{id}` | DB write in router | `Restaurant` |
| `RestaurantsPage.vue` | `api.delete('/api/restaurants/{id}')` | `DELETE /api/restaurants/{id}` | DB write in router | `Restaurant` |
| `InvoicesPage.vue`, `EmployeesPage.vue`, `InventoryRecordsPage.vue` | `fetchRestaurants()` | `GET /api/restaurants` | DB query in router | `Restaurant` |

### Checklists
| UI (Vue) | Frontend API (`frontend/src/api.js`) | Backend route | Service | Model |
| --- | --- | --- | --- | --- |
| `ChecklistsPage.vue` | `fetchChecklists()` | `GET /api/checklists` | DB query in router | `Checklist` |
| `ChecklistsPage.vue` | `fetchChecklist(id)` | `GET /api/checklists/{id}` | DB query in router | `Checklist`, `ChecklistSection`, `ChecklistQuestion` |
| `ChecklistsPage.vue` | `createChecklist(payload)` | `POST /api/checklists` | DB write in router | `Checklist` |
| `ChecklistsPage.vue` | `updateChecklist(id, payload)` | `PATCH /api/checklists/{id}` | DB write in router | `Checklist` |
| `ChecklistsPage.vue` | `deleteChecklist(id)` | `DELETE /api/checklists/{id}` | DB write in router | `Checklist` |
| `ChecklistsPage.vue` | `createChecklistSection(id, payload)` | `POST /api/checklists/{id}/sections` | DB write in router | `ChecklistSection` |
| `ChecklistsPage.vue` | `updateChecklistSection(id, sectionId, payload)` | `PATCH /api/checklists/{id}/sections/{sectionId}` | DB write in router | `ChecklistSection` |
| `ChecklistsPage.vue` | `deleteChecklistSection(id, sectionId)` | `DELETE /api/checklists/{id}/sections/{sectionId}` | DB write in router | `ChecklistSection` |
| `ChecklistsPage.vue` | `createChecklistQuestion(id, payload)` | `POST /api/checklists/{id}/questions` | DB write in router | `ChecklistQuestion` |
| `ChecklistsPage.vue` | `updateChecklistQuestion(id, questionId, payload)` | `PATCH /api/checklists/{id}/questions/{questionId}` | DB write in router | `ChecklistQuestion` |
| `ChecklistsPage.vue` | `deleteChecklistQuestion(id, questionId)` | `DELETE /api/checklists/{id}/questions/{questionId}` | DB write in router | `ChecklistQuestion` |
| `ChecklistsPage.vue` | `fetchChecklistReportSummary(params)` | `GET /api/checklists/reports/summary` | report builder in router | `ChecklistAnswer` |
| `ChecklistsPage.vue` | `fetchChecklistReportMetrics(params)` | `GET /api/checklists/reports/metrics` | report builder in router | `ChecklistAnswer` |
| `ChecklistsPage.vue` | `fetchChecklistAttempts(params)` | `GET /api/checklists/reports/attempts` | report builder in router | `ChecklistAnswer` |
| `ChecklistsPage.vue` | `fetchChecklistAttemptDetail(id)` | `GET /api/checklists/reports/attempts/{id}` | report builder in router | `ChecklistAnswer` |
| `ChecklistsPage.vue` | `exportChecklistAttempt(id, format)` | `GET /api/checklists/reports/attempts/{id}/export` | `backend.services.checklists_export` | file output |
| `ChecklistsPage.vue` | `deleteChecklistAttempt(id)` | `DELETE /api/checklists/reports/attempts/{id}` | DB write in router | `ChecklistAnswer` |

## Fingerprint
- Fingerprint integration: `backend/routers/fingerprint_templates.py` with tooling in `tools/` and the SDK in `ZKFingerSDK_Windows_Standard/`.

## Notes for AI Changes
- New API endpoint: add schema + router + register in `app/main.py` + update `frontend/src/api.js` + add route/page if needed.
- Avoid committing secrets from `.env`.
- Some files contain non-ASCII text. If console output is garbled, open with UTF-8.
