<template>
    <div class="admin-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Обучения</h1>
                <p class="admin-page__subtitle">Типы тренингов</p>
            </div>
            <div v-if="canManageTrainings" class="admin-page__header-actions">
                <Button
                    v-if="!showCreateTrainingTypeForm"
                    type="button"
                    size="sm"
                    @click="showCreateTrainingTypeForm = true"
                >
                    Добавить тип
                </Button>
            </div>
        </header>

        <FiltersPanel
            v-if="showCreateTrainingTypeForm && canManageTrainings"
            :collapsible="false"
            title="Новый тип тренинга"
        >
            <div class="admin-training__form">
                <Input
                    v-model="newTrainingTypeName"
                    label="Название"
                    placeholder='Например, "Вводный инструктаж"'
                    @keyup.enter="handleCreateTrainingType"
                />
                <div class="admin-training__form-actions">
                    <Button
                        type="button"
                        size="sm"
                        :loading="creatingTrainingType"
                        @click="handleCreateTrainingType"
                    >
                        Сохранить
                    </Button>
                    <Button
                        type="button"
                        color="ghost"
                        size="sm"
                        :disabled="creatingTrainingType"
                        @click="cancelCreateTrainingType"
                    >
                        Отмена
                    </Button>
                </div>
            </div>
        </FiltersPanel>

        <section class="admin-page__section">
            <Table v-if="trainingEventTypes.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th v-if="canManageTrainings" class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="type in trainingEventTypes"
                        :key="type.id"
                        :class="{ 'admin-training__row--editing': editingTrainingType.id === type.id }"
                        @click="canManageTrainings && editingTrainingType.id !== type.id && startEditTrainingType(type)"
                    >
                        <td>
                            <template v-if="editingTrainingType.id === type.id">
                                <Input
                                    v-model="editingTrainingType.name"
                                    label=""
                                    @keyup.enter.stop="handleUpdateTrainingType"
                                />
                            </template>
                            <template v-else>
                                {{ type.name }}
                            </template>
                        </td>
                        <td v-if="canManageTrainings" class="admin-page__actions">
                            <template v-if="editingTrainingType.id === type.id">
                                <Button
                                    color="primary"
                                    size="sm"
                                    :loading="updatingTrainingType"
                                    @click.stop="handleUpdateTrainingType"
                                >
                                    Сохранить
                                </Button>
                                <Button
                                    color="ghost"
                                    size="sm"
                                    :disabled="updatingTrainingType"
                                    @click.stop="cancelEditTrainingType"
                                >
                                    Отмена
                                </Button>
                            </template>
                            <template v-else>
                                <button
                                    type="button"
                                    class="admin-page__icon-button admin-page__icon-button--danger"
                                    :disabled="deletingTrainingTypeId === type.id"
                                    title="Удалить тип"
                                    @click.stop="handleDeleteTrainingType(type.id)"
                                >
                                    <BaseIcon name="Trash" />
                                </button>
                            </template>
                        </td>
                    </tr>
                </tbody>
            </Table>

            <div v-else class="admin-page__empty">
                <p v-if="trainingTypesLoading">Загрузка списка...</p>
                <p v-else>Типы тренингов еще не добавлены.</p>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    createTrainingEventType,
    deleteTrainingEventType,
    fetchTrainingEventTypes,
    updateTrainingEventType,
} from '@/api';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Table from '@/components/UI-components/Table.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import FiltersPanel from '@/components/UI-components/FiltersPanel.vue';
import { useUserStore } from '@/stores/user';
import { TRAININGS_MANAGE_PERMISSIONS } from '@/accessPolicy';

const toast = useToast();
const userStore = useUserStore();
const canManageTrainings = computed(() =>
    userStore.hasAnyPermission(...TRAININGS_MANAGE_PERMISSIONS),
);

const trainingEventTypes = ref([]);
const trainingTypesLoading = ref(false);
const showCreateTrainingTypeForm = ref(false);
const newTrainingTypeName = ref('');
const creatingTrainingType = ref(false);
const editingTrainingType = reactive({ id: null, name: '' });
const updatingTrainingType = ref(false);
const deletingTrainingTypeId = ref(null);

async function loadTrainingEventTypes() {
    trainingTypesLoading.value = true;
    try {
        const data = await fetchTrainingEventTypes();
        if (Array.isArray(data?.items)) {
            trainingEventTypes.value = data.items;
        } else if (Array.isArray(data)) {
            trainingEventTypes.value = data;
        } else {
            trainingEventTypes.value = [];
        }
        showCreateTrainingTypeForm.value = canManageTrainings.value && !trainingEventTypes.value.length;
    } catch (error) {
        toast.error('Не удалось загрузить типы тренингов');
        console.error(error);
    } finally {
        trainingTypesLoading.value = false;
    }
}

async function handleCreateTrainingType() {
    if (!canManageTrainings.value) {
        return;
    }
    const name = newTrainingTypeName.value.trim();
    if (!name) {
        toast.error('Введите название типа тренинга');
        return;
    }

    creatingTrainingType.value = true;
    try {
        const created = await createTrainingEventType({ name });
        if (!created?.id) {
            throw new Error('Некорректный ответ сервера');
        }
        trainingEventTypes.value = [...trainingEventTypes.value, created].sort((a, b) =>
            a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }),
        );
        newTrainingTypeName.value = '';
        showCreateTrainingTypeForm.value = false;
        toast.success('Тип тренинга создан');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось создать тип тренинга');
        console.error(error);
    } finally {
        creatingTrainingType.value = false;
    }
}

function cancelCreateTrainingType() {
    newTrainingTypeName.value = '';
    showCreateTrainingTypeForm.value = false;
}

function startEditTrainingType(type) {
    if (!canManageTrainings.value) {
        return;
    }
    editingTrainingType.id = type.id;
    editingTrainingType.name = type.name;
}

function cancelEditTrainingType() {
    editingTrainingType.id = null;
    editingTrainingType.name = '';
    updatingTrainingType.value = false;
}

async function handleUpdateTrainingType() {
    if (!canManageTrainings.value) {
        return;
    }
    if (!editingTrainingType.id) {
        return;
    }
    const name = editingTrainingType.name.trim();
    if (!name) {
        toast.error('Введите название типа тренинга');
        return;
    }

    updatingTrainingType.value = true;
    try {
        const updated = await updateTrainingEventType(editingTrainingType.id, { name });
        const updatedList = trainingEventTypes.value.map((type) =>
            type.id === editingTrainingType.id ? { ...type, name: updated.name ?? name } : type,
        );
        trainingEventTypes.value = updatedList.sort((a, b) =>
            a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }),
        );
        toast.success('Тип тренинга обновлен');
        cancelEditTrainingType();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось обновить тип тренинга');
        console.error(error);
    } finally {
        updatingTrainingType.value = false;
    }
}

async function handleDeleteTrainingType(typeId) {
    if (!canManageTrainings.value) {
        return;
    }
    if (!window.confirm('Удалить тип тренинга?')) {
        return;
    }
    deletingTrainingTypeId.value = typeId;
    try {
        await deleteTrainingEventType(typeId);
        trainingEventTypes.value = trainingEventTypes.value
            .filter((type) => type.id !== typeId)
            .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }));
        if (editingTrainingType.id === typeId) {
            cancelEditTrainingType();
        }
        showCreateTrainingTypeForm.value = canManageTrainings.value && trainingEventTypes.value.length === 0;
        toast.success('Тип тренинга удален');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить тип тренинга');
        console.error(error);
    } finally {
        deletingTrainingTypeId.value = null;
    }
}

onMounted(async () => {
    await loadTrainingEventTypes();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-training-management' as *;
</style>
