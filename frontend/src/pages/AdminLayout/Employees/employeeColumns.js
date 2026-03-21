export const EMPLOYEE_COLUMNS = [
    { id: 'staff_code', label: 'Табельный номер', type: 'text' },
    { id: 'full_name', label: 'ФИО', type: 'fullName' },
    { id: 'phone_number', label: 'Телефон', type: 'phone' },
    { id: 'company_name', label: 'Компания', type: 'text' },
    { id: 'position_name', label: 'Должность', type: 'text' },
    { id: 'iiko_id', label: 'Код сотрудника (Айки)', type: 'text', sensitive: true },
    { id: 'gender', label: 'Пол', type: 'gender' },
    { id: 'hire_date', label: 'Дата найма', type: 'date' },
    { id: 'fire_date', label: 'Дата увольнения', type: 'date' },
    { id: 'birth_date', label: 'Дата рождения', type: 'date' },
    { id: 'is_cis_employee', label: 'Сотрудник СНГ', type: 'boolean' },
    { id: 'restaurants', label: 'Рестораны', type: 'restaurants' },
    { id: 'status', label: 'Статус', type: 'status', sensitive: true },
];

export function getEmployeeColumns(canViewSensitiveStaffFields = false) {
    if (canViewSensitiveStaffFields) {
        return EMPLOYEE_COLUMNS;
    }

    return EMPLOYEE_COLUMNS.filter((column) => !column.sensitive);
}
