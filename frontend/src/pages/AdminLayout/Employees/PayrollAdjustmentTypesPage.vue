<template>
    <div class="admin-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Виды выплат</h1>
                <p class="admin-page__subtitle">Справочник типов начислений и удержаний.</p>
            </div>
            <div class="admin-page__header-actions">
                <div class="admin-page__toolbar">
                    <Input
                        v-model="search"
                        class="admin-page__search"
                        placeholder="Поиск по названию"
                    />
                    <Button type="button" color="secondary" size="sm" :loading="loading" @click="loadPayrollAdjustmentTypes">
                        Обновить
                    </Button>
                    <Button type="button" color="primary" size="sm" @click="openCreateModal">
                        Добавить тип
                    </Button>
                </div>
            </div>
        </header>

        <section class="admin-page__section">
            <Table v-if="filteredPayrollAdjustmentTypes.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Тип</th>
                        <th>В ведомости</th>
                        <th>Авансовый</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="type in filteredPayrollAdjustmentTypes" :key="type.id">
                        <td>
                            <button
                                type="button"
                                class="admin-page__row-link"
                                @click="openEditModal(type)"
                            >
                                {{ type.name }}
                            </button>
                        </td>
                        <td>
                            {{ payrollAdjustmentTypeKindLabels[type.kind] || '—' }}
                        </td>
                        <td>
                            <span class="payroll-types__flag" :class="{ 'payroll-types__flag--on': type.show_in_report }">
                                {{ type.show_in_report ? 'Да' : 'Нет' }}
                            </span>
                        </td>
                        <td>
                            <span class="payroll-types__flag" :class="{ 'payroll-types__flag--on': type.is_advance }">
                                {{ type.is_advance ? 'Да' : 'Нет' }}
                            </span>
                        </td>
                        <td class="admin-page__actions">
                            <button
                                type="button"
                                class="admin-page__icon-button"
                                title="Редактировать"
                                @click="openEditModal(type)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                            <button
                                type="button"
                                class="admin-page__icon-button admin-page__icon-button--danger"
                                :disabled="deletingPayrollAdjustmentTypeId === type.id"
                                title="Удалить"
                                @click="handleDeletePayrollAdjustmentType(type)"
                            >
                                <BaseIcon name="Trash" />
                            </button>
                        </td>
                    </tr>
                </tbody>
            </Table>

            <div v-else class="admin-page__empty">
                <p v-if="loading">Загрузка типов начислений...</p>
                <p v-else>Типы начислений еще не созданы.</p>
            </div>
        </section>

        <Modal v-if="isModalOpen" @close="closeModal">
            <template #header>
                <div>
                    <h3 class="payroll-types__modal-title">
                        {{ isEditing ? 'Редактировать тип' : 'Новый тип' }}
                    </h3>
                    <p class="payroll-types__modal-subtitle">
                        Укажите название, тип операции и правила отображения в ведомости.
                    </p>
                </div>
            </template>

            <form class="payroll-types__form" @submit.prevent="handleSave">
                <Input
                    v-model="form.name"
                    label="Название"
                    placeholder='Например, "Премия"'
                    required
                />
                <Select
                    v-model="form.kind"
                    label="Тип операции"
                    :options="payrollAdjustmentTypeKindOptions"
                    required
                />
                <Checkbox
                    v-model="form.showInReport"
                    label="Отображать в ведомости отдельным столбцом"
                />
                <Checkbox
                    v-model="form.isAdvance"
                    label="Является авансовым удержанием"
                    :disabled="form.kind !== 'deduction'"
                />
            </form>

            <template #footer>
                <Button type="button" color="primary" :loading="saving" @click="handleSave">
                    Сохранить
                </Button>
                <Button type="button" color="ghost" :disabled="saving" @click="closeModal">
                    Отмена
                </Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
    createPayrollAdjustmentType,
    deletePayrollAdjustmentType,
    fetchPayrollAdjustmentTypes,
    updatePayrollAdjustmentType,
} from '@/api';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';

const toast = useToast();

const loading = ref(false);
const saving = ref(false);
const deletingPayrollAdjustmentTypeId = ref(null);

const payrollAdjustmentTypes = ref([]);
const search = ref('');

const payrollAdjustmentTypeKindOptions = [
    { value: 'accrual', label: 'Начисление' },
    { value: 'deduction', label: 'Удержание' },
];
const payrollAdjustmentTypeKindLabels = {
    accrual: 'Начисление',
    deduction: 'Удержание',
};

const isModalOpen = ref(false);
const editingPayrollAdjustmentTypeId = ref(null);
const isEditing = computed(() => Boolean(editingPayrollAdjustmentTypeId.value));

const form = reactive({
    name: '',
    kind: payrollAdjustmentTypeKindOptions[0].value,
    showInReport: false,
    isAdvance: false,
});

const filteredPayrollAdjustmentTypes = computed(() => {
    const list = Array.isArray(payrollAdjustmentTypes.value) ? payrollAdjustmentTypes.value : [];
    const query = (search.value || '').trim().toLocaleLowerCase('ru-RU');
    if (!query) {
        return list;
    }
    return list.filter((type) =>
        String(type?.name ?? '').toLocaleLowerCase('ru-RU').includes(query),
    );
});

watch(
    () => form.kind,
    (kind) => {
        if (kind !== 'deduction') {
            form.isAdvance = false;
        }
    },
);

function resetForm() {
    form.name = '';
    form.kind = payrollAdjustmentTypeKindOptions[0].value;
    form.showInReport = false;
    form.isAdvance = false;
}

function sortTypes(types) {
    return [...(types || [])].sort((a, b) =>
        String(a?.name || '').localeCompare(String(b?.name || ''), 'ru', { sensitivity: 'base' }),
    );
}

function normalizePayrollAdjustmentType(type) {
    if (!type || typeof type !== 'object') {
        return null;
    }
    const id = Number(type.id);
    if (!Number.isFinite(id) || id <= 0) {
        return null;
    }
    return {
        ...type,
        id,
        name: String(type.name || '').trim(),
        kind: String(type.kind || payrollAdjustmentTypeKindOptions[0].value),
        show_in_report: Boolean(type.show_in_report),
        is_advance: Boolean(type.is_advance),
    };
}

function upsertPayrollAdjustmentType(type) {
    const normalized = normalizePayrollAdjustmentType(type);
    if (!normalized) {
        return false;
    }
    const existingIndex = payrollAdjustmentTypes.value.findIndex(
        (item) => Number(item?.id) === normalized.id,
    );
    if (existingIndex === -1) {
        payrollAdjustmentTypes.value = sortTypes([...payrollAdjustmentTypes.value, normalized]);
        return true;
    }
    const next = [...payrollAdjustmentTypes.value];
    next[existingIndex] = {
        ...next[existingIndex],
        ...normalized,
    };
    payrollAdjustmentTypes.value = sortTypes(next);
    return true;
}

async function loadPayrollAdjustmentTypes() {
    loading.value = true;
    try {
        const data = await fetchPayrollAdjustmentTypes();
        let list = [];
        if (Array.isArray(data?.items)) {
            list = data.items;
        } else if (Array.isArray(data)) {
            list = data;
        }
        payrollAdjustmentTypes.value = sortTypes(list);
    } catch (error) {
        toast.error('Не удалось загрузить типы начислений');
        console.error(error);
    } finally {
        loading.value = false;
    }
}

function openCreateModal() {
    editingPayrollAdjustmentTypeId.value = null;
    resetForm();
    isModalOpen.value = true;
}

function openEditModal(type) {
    if (!type) {
        return;
    }
    editingPayrollAdjustmentTypeId.value = Number(type.id) || null;
    form.name = type.name || '';
    form.kind = type.kind || payrollAdjustmentTypeKindOptions[0].value;
    form.showInReport = Boolean(type.show_in_report);
    form.isAdvance = Boolean(type.is_advance);
    isModalOpen.value = true;
}

function closeModal() {
    isModalOpen.value = false;
    saving.value = false;
    editingPayrollAdjustmentTypeId.value = null;
    resetForm();
}

async function handleSave() {
    const name = String(form.name || '').trim();
    if (!name) {
        toast.error('Введите название типа начисления');
        return;
    }
    const kind = form.kind;
    if (!kind) {
        toast.error('Выберите тип операции');
        return;
    }
    if (form.isAdvance && kind !== 'deduction') {
        toast.error('Авансовым может быть только удержание');
        return;
    }

    saving.value = true;
    try {
        const payload = {
            name,
            kind,
            show_in_report: Boolean(form.showInReport),
            is_advance: kind === 'deduction' ? Boolean(form.isAdvance) : false,
        };
        let savedType = null;
        if (isEditing.value) {
            savedType = await updatePayrollAdjustmentType(editingPayrollAdjustmentTypeId.value, payload);
            toast.success('Тип начисления обновлен');
        } else {
            savedType = await createPayrollAdjustmentType(payload);
            toast.success('Тип начисления создан');
        }
        if (!upsertPayrollAdjustmentType(savedType)) {
            await loadPayrollAdjustmentTypes();
        }
        closeModal();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить тип начисления');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleDeletePayrollAdjustmentType(type) {
    const typeId = Number(type?.id);
    if (!Number.isFinite(typeId) || typeId <= 0) {
        return;
    }
    if (!window.confirm(`Удалить тип "${type?.name}"?`)) {
        return;
    }

    deletingPayrollAdjustmentTypeId.value = typeId;
    try {
        await deletePayrollAdjustmentType(typeId);
        payrollAdjustmentTypes.value = sortTypes(
            payrollAdjustmentTypes.value.filter((item) => item.id !== typeId),
        );
        toast.success('Тип начисления удален');
        if (editingPayrollAdjustmentTypeId.value === typeId) {
            closeModal();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить тип начисления');
        console.error(error);
    } finally {
        deletingPayrollAdjustmentTypeId.value = null;
    }
}

onMounted(() => {
    loadPayrollAdjustmentTypes();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-payroll-adjustment-types' as *;
</style>
