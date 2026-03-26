import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';

import {
    createInventoryCategory,
    deleteInventoryCategory,
    fetchInventoryCategories,
    fetchInventoryGroups,
    updateInventoryCategory,
} from '@/api';

export function useInventoryCategoriesPage() {
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

    return {
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
    };
}
