<template>
    <div class="admin-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Подразделения</h1>
                <p class="admin-page__subtitle">Подразделения ресторанов и настройки мульти-смен.</p>
            </div>
            <div class="admin-page__header-actions">
                <div class="admin-page__toolbar">
                    <Input
                        v-model="search"
                        class="admin-page__search"
                        placeholder="Поиск по подразделению"
                    />
                    <Button
                        type="button"
                        color="secondary"
                        size="sm"
                        :loading="loading"
                        @click="loadRestaurantSubdivisions"
                    >
                        Обновить
                    </Button>
                    <Button
                        v-if="canManagePositions"
                        type="button"
                        color="primary"
                        size="sm"
                        @click="openCreateModal"
                    >
                        Добавить подразделение
                    </Button>
                </div>
            </div>
        </header>

        <section v-if="canManagePositions" class="admin-page__section">
            <Table v-if="filteredSubdivisions.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Мульти</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="sub in filteredSubdivisions" :key="sub.id">
                        <td>
                            <button type="button" class="admin-page__row-link" @click="openEditModal(sub)">
                                {{ sub.name }}
                            </button>
                        </td>
                        <td>
                            {{ sub.is_multi ? 'Да' : 'Нет' }}
                        </td>
                        <td class="admin-page__actions">
                            <button
                                type="button"
                                class="admin-page__icon-button"
                                title="Редактировать"
                                @click="openEditModal(sub)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                            <button
                                type="button"
                                class="admin-page__icon-button admin-page__icon-button--danger"
                                :disabled="deletingSubdivisionId === sub.id"
                                title="Удалить"
                                @click="handleDeleteSubdivision(sub)"
                            >
                                <BaseIcon name="Trash" />
                            </button>
                        </td>
                    </tr>
                </tbody>
            </Table>

            <div v-else class="admin-page__empty">
                <p v-if="loading">Загрузка подразделений...</p>
                <p v-else>Подразделений пока нет.</p>
            </div>
        </section>

        <div v-else class="admin-page__empty">
            <p>Доступ ограничен.</p>
        </div>

        <Modal v-if="isModalOpen" @close="closeModal">
            <template #header>
                <div>
                    <h3 class="subdivisions__modal-title">
                        {{ isEditing ? 'Редактировать подразделение' : 'Новое подразделение' }}
                    </h3>
                    <p class="subdivisions__modal-subtitle">
                        Мульти позволяет сотрудникам выбирать должность при начале смены.
                    </p>
                </div>
            </template>

            <form class="subdivisions__form" @submit.prevent="handleSaveSubdivision">
                <Input v-model="form.name" label="Название" placeholder="Кухня, Бар, Зал" />
                <Checkbox
                    v-model="form.isMulti"
                    label="Мульти (можно выбирать должность при начале смены)"
                />
            </form>

            <template #footer>
                <Button color="primary" :loading="saving" @click="handleSaveSubdivision">
                    Сохранить
                </Button>
                <Button color="ghost" :disabled="saving" @click="closeModal">
                    Отмена
                </Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import {
    createRestaurantSubdivision,
    deleteRestaurantSubdivision,
    fetchRestaurantSubdivisions,
    updateRestaurantSubdivision,
} from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Input from '@/components/UI-components/Input.vue';
import Button from '@/components/UI-components/Button.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Table from '@/components/UI-components/Table.vue';
import Modal from '@/components/UI-components/Modal.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { extractApiErrorMessage } from '@/utils/apiErrors';

const userStore = useUserStore();
const toast = useToast();

const canManagePositions = computed(() =>
    userStore.hasAnyPermission('positions.manage', 'system.admin'),
);

const restaurantSubdivisions = ref([]);
const loading = ref(false);
const saving = ref(false);
const deletingSubdivisionId = ref(null);
const search = ref('');

const isModalOpen = ref(false);
const editingSubdivisionId = ref(null);
const isEditing = computed(() => Boolean(editingSubdivisionId.value));

const form = reactive({
    name: '',
    isMulti: false,
});

const filteredSubdivisions = computed(() => {
    const list = Array.isArray(restaurantSubdivisions.value) ? restaurantSubdivisions.value : [];
    const query = (search.value || '').trim().toLocaleLowerCase('ru-RU');
    if (!query) {
        return list;
    }
    return list.filter((item) => String(item?.name ?? '').toLocaleLowerCase('ru-RU').includes(query));
});

function sortSubdivisions(items) {
    return [...(items || [])].sort((a, b) =>
        String(a?.name || '').localeCompare(String(b?.name || ''), 'ru', { sensitivity: 'base' }),
    );
}

function normalizeSubdivision(item) {
    if (!item || typeof item !== 'object') {
        return null;
    }
    const id = Number(item.id);
    if (!Number.isFinite(id) || id <= 0) {
        return null;
    }
    return {
        ...item,
        id,
        name: String(item.name || '').trim(),
        is_multi: Boolean(item.is_multi),
    };
}

function upsertSubdivision(item) {
    const normalized = normalizeSubdivision(item);
    if (!normalized) {
        return false;
    }
    const current = Array.isArray(restaurantSubdivisions.value) ? restaurantSubdivisions.value : [];
    const existingIndex = current.findIndex((row) => Number(row?.id) === normalized.id);
    if (existingIndex === -1) {
        restaurantSubdivisions.value = sortSubdivisions([...current, normalized]);
        return true;
    }
    const next = [...current];
    next[existingIndex] = {
        ...next[existingIndex],
        ...normalized,
    };
    restaurantSubdivisions.value = sortSubdivisions(next);
    return true;
}

function resetForm() {
    form.name = '';
    form.isMulti = false;
}

async function loadRestaurantSubdivisions() {
    if (!canManagePositions.value) {
        restaurantSubdivisions.value = [];
        return;
    }
    loading.value = true;
    try {
        const data = await fetchRestaurantSubdivisions();
        restaurantSubdivisions.value = sortSubdivisions(Array.isArray(data) ? data : []);
    } catch (error) {
        if (error?.response?.status === 403) {
            restaurantSubdivisions.value = [];
        } else {
            toast.error('Не удалось загрузить подразделения ресторана');
            console.error(error);
        }
    } finally {
        loading.value = false;
    }
}

function openCreateModal() {
    resetForm();
    editingSubdivisionId.value = null;
    isModalOpen.value = true;
}

function openEditModal(subdivision) {
    if (!subdivision) return;
    editingSubdivisionId.value = subdivision.id;
    form.name = subdivision.name || '';
    form.isMulti = Boolean(subdivision.is_multi);
    isModalOpen.value = true;
}

function closeModal() {
    isModalOpen.value = false;
    saving.value = false;
    editingSubdivisionId.value = null;
    resetForm();
}

async function handleSaveSubdivision() {
    const name = form.name.trim();
    if (!name) {
        toast.error('Укажите название подразделения');
        return;
    }
    saving.value = true;
    const payload = { name, is_multi: Boolean(form.isMulti) };
    try {
        let savedSubdivision = null;
        if (editingSubdivisionId.value) {
            savedSubdivision = await updateRestaurantSubdivision(editingSubdivisionId.value, payload);
            toast.success('Подразделение обновлено');
        } else {
            savedSubdivision = await createRestaurantSubdivision(payload);
            toast.success('Подразделение создано');
        }
        if (!upsertSubdivision(savedSubdivision)) {
            await loadRestaurantSubdivisions();
        }
        closeModal();
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось сохранить подразделение'));
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleDeleteSubdivision(subdivision) {
    if (!subdivision?.id) {
        return;
    }
    if (!confirm(`Удалить подразделение "${subdivision.name}"?`)) {
        return;
    }
    deletingSubdivisionId.value = subdivision.id;
    try {
        await deleteRestaurantSubdivision(subdivision.id);
        toast.success('Подразделение удалено');
        restaurantSubdivisions.value = sortSubdivisions(
            restaurantSubdivisions.value.filter((item) => Number(item?.id) !== Number(subdivision.id)),
        );
    } catch (error) {
        toast.error(extractApiErrorMessage(error, 'Не удалось удалить подразделение'));
        console.error(error);
    } finally {
        deletingSubdivisionId.value = null;
    }
}

onMounted(() => {
    if (canManagePositions.value) {
        loadRestaurantSubdivisions();
    }
});

watch(
    () => canManagePositions.value,
    (canManage) => {
        if (!canManage) {
            restaurantSubdivisions.value = [];
            closeModal();
            return;
        }
        loadRestaurantSubdivisions();
    },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/staff-departments' as *;
</style>
