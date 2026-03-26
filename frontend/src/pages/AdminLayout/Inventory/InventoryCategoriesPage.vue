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
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import { useInventoryCategoriesPage } from '@/pages/AdminLayout/Inventory/composables/useInventoryCategoriesPage';

const {
    categories,
    loadingCategories,
    saving,
    newCategory,
    editingCategory,
    groupOptions,
    getGroupName,
    loadCategories,
    resetCategoryForm,
    startEditCategory,
    cancelEditCategory,
    handleCreateCategory,
    handleUpdateCategory,
    handleDeleteCategory,
} = useInventoryCategoriesPage();
</script>
