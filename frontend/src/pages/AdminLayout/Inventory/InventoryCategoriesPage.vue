<template>
    <section class="inventory-page__section">
        <div class="inventory-page__section-header">
            <h2>Категории</h2>
            <Button color="ghost" size="sm" :loading="loadingCategories" @click="loadCategories">
                Обновить
            </Button>
        </div>
        <form class="inventory-page__form inventory-page__form--grid" @submit.prevent="handleCreateCategory">
            <Input v-model="newCategory.name" label="Название категории" placeholder="Например, Листовые" />
            <Select
                v-model="newCategory.groupId"
                label="Группа"
                :options="groupOptions"
                placeholder="Выберите группу"
            />
            <div class="inventory-page__form-actions">
                <Button type="submit" color="primary" size="sm" :loading="saving">Добавить</Button>
                <Button type="button" color="ghost" size="sm" @click="resetCategoryForm">Очистить</Button>
            </div>
        </form>
        <div v-if="loadingCategories" class="inventory-page__loading">Загрузка категорий...</div>
        <div v-else>
            <Table v-if="categories.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Группа</th>
                        <th class="inventory-page__actions-column">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="category in categories" :key="category.id">
                        <td>
                            <template v-if="editingCategory.id === category.id">
                                <Input v-model="editingCategory.name" label="" />
                            </template>
                            <template v-else>
                                {{ category.name }}
                            </template>
                        </td>
                        <td>
                            <template v-if="editingCategory.id === category.id">
                                <Select v-model="editingCategory.groupId" label="Группа" :options="groupOptions" />
                            </template>
                            <template v-else>
                                {{ getGroupName(category.group_id) }}
                            </template>
                        </td>
                        <td class="inventory-page__actions-column">
                            <template v-if="editingCategory.id === category.id">
                                <Button color="primary" size="sm" :loading="saving" @click="handleUpdateCategory">
                                    Сохранить
                                </Button>
                                <Button color="ghost" size="sm" :disabled="saving" @click="cancelEditCategory">
                                    Отмена
                                </Button>
                            </template>
                            <template v-else>
                                <Button color="ghost" size="sm" @click="startEditCategory(category)">
                                    Изменить
                                </Button>
                                <Button
                                    color="danger"
                                    size="sm"
                                    :loading="saving"
                                    @click="handleDeleteCategory(category.id)"
                                >
                                    Удалить
                                </Button>
                            </template>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <p v-else class="inventory-page__empty">Категории еще не созданы.</p>
        </div>
    </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import {
    createInventoryCategory,
    deleteInventoryCategory,
    fetchInventoryCategories,
    fetchInventoryGroups,
    updateInventoryCategory,
} from '@/api';

const toast = useToast();

const categories = ref([]);
const groups = ref([]);
const loadingCategories = ref(false);
const saving = ref(false);

const newCategory = reactive({ name: '', groupId: null });
const editingCategory = reactive({ id: null, name: '', groupId: null });

const groupOptions = computed(() =>
    groups.value
        .map((group) => ({ value: String(group.id), label: group.name }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
);

const groupMap = computed(() => {
    const map = new Map();
    for (const group of groups.value) {
        map.set(group.id, group.name);
    }
    return map;
});

function getGroupName(id) {
    return groupMap.value.get(id) || `ID ${id}`;
}

async function loadGroups() {
    try {
        const data = await fetchInventoryGroups();
        groups.value = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error('Не удалось загрузить группы');
        console.error(error);
    }
}

async function loadCategories() {
    loadingCategories.value = true;
    try {
        const data = await fetchInventoryCategories();
        categories.value = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error('Не удалось загрузить категории');
        console.error(error);
    } finally {
        loadingCategories.value = false;
    }
}

function resetCategoryForm() {
    newCategory.name = '';
    newCategory.groupId = null;
}

function startEditCategory(category) {
    editingCategory.id = category.id;
    editingCategory.name = category.name;
    editingCategory.groupId = category.group_id ? String(category.group_id) : null;
}

function cancelEditCategory() {
    editingCategory.id = null;
    editingCategory.name = '';
    editingCategory.groupId = null;
}

async function handleCreateCategory() {
    const name = newCategory.name.trim();
    const groupId = newCategory.groupId ? Number(newCategory.groupId) : null;
    if (!name || !groupId) {
        toast.error('Введите название и выберите группу');
        return;
    }
    saving.value = true;
    try {
        await createInventoryCategory({ name, group_id: groupId });
        toast.success('Категория создана');
        resetCategoryForm();
        await loadCategories();
    } catch (error) {
        toast.error('Не удалось создать категорию');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleUpdateCategory() {
    if (!editingCategory.id) {
        return;
    }
    const name = editingCategory.name.trim();
    const groupId = editingCategory.groupId ? Number(editingCategory.groupId) : null;
    if (!name || !groupId) {
        toast.error('Введите название и выберите группу');
        return;
    }
    saving.value = true;
    try {
        await updateInventoryCategory(editingCategory.id, { name, group_id: groupId });
        toast.success('Категория обновлена');
        cancelEditCategory();
        await loadCategories();
    } catch (error) {
        toast.error('Не удалось обновить категорию');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleDeleteCategory(categoryId) {
    if (!window.confirm('Удалить категорию? Товары и движения могут потребовать обновления.')) {
        return;
    }
    saving.value = true;
    try {
        await deleteInventoryCategory(categoryId);
        toast.success('Категория удалена');
        await loadCategories();
    } catch (error) {
        toast.error('Не удалось удалить категорию');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

onMounted(async () => {
    await Promise.all([loadGroups(), loadCategories()]);
});
</script>