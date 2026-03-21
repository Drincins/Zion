<template>
    <div class="employees-page__modal-section">
        <div
            v-if="(canManageEmployees || canSyncEmployeeToIiko) && !cardLoading"
            class="employees-page__info-toolbar"
        >
            <Button
                v-if="canSyncEmployeeToIiko && !(employeeCard?.fired ?? activeEmployee?.fired)"
                color="secondary"
                size="sm"
                class="employees-page__toolbar-icon-button employees-page__toolbar-iiko-button"
                :loading="syncingEmployeeToIiko"
                :title="(employeeCard?.iiko_id || activeEmployee?.iiko_id) ? 'Обновить в iiko' : 'Создать в iiko'"
                :aria-label="(employeeCard?.iiko_id || activeEmployee?.iiko_id) ? 'Обновить сотрудника в iiko' : 'Создать сотрудника в iiko'"
                @click="emit('sync-employee-to-iiko')"
            >
                <span class="employees-page__toolbar-iiko-label">iiko</span>
            </Button>
            <Button
                color="primary"
                size="sm"
                class="employees-page__toolbar-icon-button"
                :title="isEditMode ? 'Закрыть редактирование' : 'Редактировать'"
                :aria-label="isEditMode ? 'Закрыть редактирование' : 'Редактировать сотрудника'"
                @click="emit('toggle-edit-mode')"
            >
                <BaseIcon name="Edit" class="employees-page__toolbar-action-icon" />
            </Button>
            <Button
                v-if="canRestoreEmployees && (employeeCard?.fired ?? activeEmployee?.fired)"
                color="success"
                size="sm"
                class="employees-page__toolbar-icon-button"
                :loading="restoringEmployee"
                title="Восстановить сотрудника"
                aria-label="Восстановить сотрудника"
                @click="emit('restore-employee')"
            >
                <BaseIcon name="Arrow" class="employees-page__toolbar-action-icon" />
            </Button>
            <Button
                v-if="canManageEmployees && !(employeeCard?.fired ?? activeEmployee?.fired)"
                color="danger"
                size="sm"
                class="employees-page__toolbar-icon-button"
                :loading="deletingEmployee"
                title="Удалить сотрудника"
                aria-label="Удалить сотрудника"
                @click="emit('delete-employee')"
            >
                <BaseIcon name="Trash" class="employees-page__toolbar-action-icon" />
            </Button>
        </div>
        <div v-if="cardLoading" class="employees-page__modal-loading">
            Загрузка данных...
        </div>
        <div v-else class="employees-page__details">
            <section class="employees-page__info-card">
                <h4 class="employees-page__info-card-title">Основное</h4>
                <dl class="employees-page__info-list">
                    <div class="employees-page__info-item">
                        <dt>ФИО</dt>
                        <dd>{{ formatFullName(employeeCard) }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Пол</dt>
                        <dd>{{ formatGender(employeeCard?.gender) }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Телефон</dt>
                        <dd>{{ employeeCard?.phone_number || '-' }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Электронная почта</dt>
                        <dd>{{ employeeCard?.email || '-' }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Дата рождения</dt>
                        <dd>{{ formatDate(employeeCard?.birth_date) }}</dd>
                    </div>
                </dl>
            </section>
            <section class="employees-page__info-card">
                <h4 class="employees-page__info-card-title">Работа</h4>
                <dl class="employees-page__info-list">
                    <div class="employees-page__info-item">
                        <dt>Компания</dt>
                        <dd>{{ employeeCard?.company_name || '—' }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Должность</dt>
                        <dd>{{ employeeCard?.position_name || '—' }}</dd>
                    </div>
                    <div v-if="canViewSensitiveStaffFields" class="employees-page__info-item">
                        <dt>Роль</dt>
                        <dd>{{ employeeCard?.role_name || '—' }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Ставка</dt>
                        <dd v-if="employeeCard?.rate_hidden">$$$</dd>
                        <dd v-else>{{ formatAmount(employeeCard?.rate) }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Дата найма</dt>
                        <dd>{{ formatDate(employeeCard?.hire_date) }}</dd>
                    </div>
                    <div v-if="employeeCard?.fired" class="employees-page__info-item">
                        <dt>Дата увольнения</dt>
                        <dd>{{ formatDate(employeeCard?.fire_date) }}</dd>
                    </div>
                </dl>
            </section>
            <section class="employees-page__info-card">
                <h4 class="employees-page__info-card-title">Учётные данные</h4>
                <dl class="employees-page__info-list">
                    <div v-if="!isTimeControlRole" class="employees-page__info-item">
                        <dt>Логин</dt>
                        <dd>{{ employeeCard?.username || '—' }}</dd>
                    </div>
                    <div class="employees-page__info-item">
                        <dt>Табельный номер</dt>
                        <dd>{{ employeeCard?.staff_code || '—' }}</dd>
                    </div>
                    <div v-if="canViewSensitiveStaffFields" class="employees-page__info-item">
                        <dt>Код iiko</dt>
                        <dd>{{ employeeCard?.iiko_code || '—' }}</dd>
                    </div>
                    <div v-if="canViewSensitiveStaffFields" class="employees-page__info-item">
                        <dt>Код сотрудника (Айки)</dt>
                        <dd>{{ employeeCard?.iiko_id || activeEmployee?.iiko_id || '—' }}</dd>
                    </div>
                    <div v-if="canViewSensitiveStaffFields" class="employees-page__info-item">
                        <dt>Согласие на передачу конфиденциальных данных</dt>
                        <dd>{{ employeeCard?.confidential_data_consent ? 'Да' : 'Нет' }}</dd>
                    </div>
                    <div v-if="canViewSensitiveStaffFields" class="employees-page__info-item">
                        <dt>Статус</dt>
                        <dd>{{ employeeCard?.fired ? 'Уволен' : 'Активен' }}</dd>
                    </div>
                </dl>
            </section>
        </div>
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';

defineProps({
    canManageEmployees: { type: Boolean, default: false },
    cardLoading: { type: Boolean, default: false },
    isEditMode: { type: Boolean, default: false },
    canRestoreEmployees: { type: Boolean, default: false },
    restoringEmployee: { type: Boolean, default: false },
    deletingEmployee: { type: Boolean, default: false },
    employeeCard: { type: Object, default: null },
    activeEmployee: { type: Object, default: null },
    canViewSensitiveStaffFields: { type: Boolean, default: false },
    canSyncEmployeeToIiko: { type: Boolean, default: false },
    syncingEmployeeToIiko: { type: Boolean, default: false },
    isTimeControlRole: { type: Boolean, default: false },
    formatFullName: { type: Function, required: true },
    formatGender: { type: Function, required: true },
    formatAmount: { type: Function, required: true },
    formatDate: { type: Function, required: true }
});

const emit = defineEmits(['toggle-edit-mode', 'restore-employee', 'delete-employee', 'sync-employee-to-iiko']);
</script>

<style scoped lang="scss">
.employees-page__modal-loading {
    text-align: center;
    padding: 24px 0;
    color: var(--color-text-soft);
}

.employees-page__info-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: flex-end;
}

.employees-page__toolbar-icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    min-width: 36px;
    padding: 0;
    border-radius: 10px;
}

.employees-page__toolbar-action-icon {
    width: 18px;
    height: 18px;
    display: block;
}

.employees-page__toolbar-iiko-button {
    width: 36px;
    min-width: 36px;
    padding: 0;
    border: none;
    background: #ff2f39;
    color: #ffffff;
    line-height: 1;
}

.employees-page__toolbar-iiko-button:hover:not(:disabled) {
    opacity: 1;
    filter: brightness(1.08);
}

.employees-page__toolbar-iiko-label {
    display: inline-block;
    font-family: Arial Black, Arial, sans-serif;
    font-size: 11px;
    line-height: 1;
    font-weight: 900;
    letter-spacing: -0.25px;
    text-transform: lowercase;
    color: #ffffff;
}

.employees-page__details {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.employees-page__info-card {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 20px;
    background: var(--color-surface);
    border-radius: 16px;
    border: 1px solid var(--color-border);
    color: var(--color-text);
}

.employees-page__info-card-title {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--color-primary);
}

.employees-page__info-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 0;
}

.employees-page__info-item dt {
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--color-text);
}

.employees-page__info-item dd {
    margin: 0;
    color: var(--color-text-soft);
}

@media (max-width: 1024px) {
    .employees-page__details {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 720px) {
    .employees-page__details {
        grid-template-columns: 1fr;
    }
}
</style>
