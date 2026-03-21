# Access Control Back-End Guide

This document describes the new access-control primitives and the HTTP endpoints that power the UI for managing permissions, roles, and the hierarchy of employee positions.

## Database Migration

1. Generate and apply the new Alembic revision:
   ```bash
   alembic upgrade head
   ```
   The migration creates the `permissions` and `role_permissions` tables and adds `parent_id` / `hierarchy_level` columns to `employee_positions`.
2. Existing roles named `admin` or `administrator` automatically receive the `system.admin` permission during the migration. Assign permissions to other roles through the API described below.

## Concepts & Defaults

- **Permissions (`permissions.code`)** – canonical, machine-readable strings (lowercase, dot separated) that unlock actions in the system. Pre-seeded code: `system.admin`.
- **Roles** – bundles of permissions. Users inherit permissions exclusively through their role.
- **Positions** – HR entities linked to roles; now include a parent pointer and numeric hierarchy level (`0` = top).
- `system.admin` or `staff.manage_all` permissions grant global access everywhere. Legacy role-name checks (`admin`, `administrator`, `админ`, `администратор`) still work as a fallback.

### Suggested Permission Codes

| Code | Purpose |
| ---- | ------- |
| `system.admin` | Full administrative access. |
| `staff.manage_all` | Manage any employee regardless of position/restaurant. |
| `staff.manage_subordinates` | Manage employees below the viewer in the hierarchy. |
| `staff.view_sensitive` | Access sensitive employee data (e.g. payroll). |
| `roles.manage` | Maintain permissions and roles catalogue. |
| `positions.manage` | Edit the position tree / hierarchy. |

Add new codes via the API (`POST /api/access/permissions`) before assigning them to roles.

## REST API Endpoints

All routes require an authenticated user; authorization depends on permissions as noted. `system.admin` automatically satisfies every requirement.

### Permissions Catalogue

| Method & Path | Body | Permissions | Description |
| ------------- | ---- | ----------- | ----------- |
| `GET /api/access/permissions` | – | `system.admin` or `roles.manage` | List all permissions. |
| `POST /api/access/permissions` | `{code, name, description?}` | `system.admin` or `roles.manage` | Create a new permission (codes stored lowercase). |
| `PATCH /api/access/permissions/{permission_id}` | `{name?, description?}` | `system.admin` or `roles.manage` | Update metadata. |
| `DELETE /api/access/permissions/{permission_id}` | – | `system.admin` or `roles.manage` | Delete a permission (only if unused). |

### Roles & Permission Assignment

| Method & Path | Body | Permissions | Notes |
| ------------- | ---- | ----------- | ----- |
| `GET /api/access/roles` | – | `system.admin` or `roles.manage` | Returns role id, name, permission codes, and permission objects. |
| `POST /api/access/roles` | `{name, permission_codes[]}` | `system.admin` or `roles.manage` | Create role and assign permissions. |
| `PATCH /api/access/roles/{role_id}` | `{name?, permission_codes?}` | `system.admin` or `roles.manage` | Rename and/or replace permission set. |
| `DELETE /api/access/roles/{role_id}` | – | `system.admin` or `roles.manage` | Allowed only if no users reference the role. |

### Position Hierarchy

| Method & Path | Body | Permissions | Description |
| ------------- | ---- | ----------- | ----------- |
| `GET /api/access/positions` | – | `system.admin` or `positions.manage` | List positions with parent/level metadata and role info. |
| `POST /api/access/positions` | `{name, role_id, parent_id?, hierarchy_level?}` | `system.admin` or `positions.manage` | Create a position (level auto-calculated when omitted). |
| `PATCH /api/access/positions/{position_id}` | `{name?, role_id?, parent_id?, hierarchy_level?}` | `system.admin` or `positions.manage` | Update metadata; handles re-parenting with cycle checks. |
| `DELETE /api/access/positions/{position_id}` | – | `system.admin` or `positions.manage` | Only if no children/users linked. |

## Front-End Integration Tips

- Fetch all permissions once and build a grouped matrix for assignment UI.
- When rendering position trees, sort by `hierarchy_level` then `name`.
- Use `permission_codes` from role responses for quick set membership in the UI; full permission objects carry the descriptions for tooltip/help text.
- After saving changes, refresh local caches by reloading `GET /api/access/roles` or `GET /api/access/positions`.

