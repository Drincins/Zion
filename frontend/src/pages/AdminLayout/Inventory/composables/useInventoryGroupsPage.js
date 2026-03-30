import { computed, onMounted, ref } from 'vue';
import { useToast } from 'vue-toastification';

import { useInventoryGroupsModals } from './useInventoryGroupsModals';
import { fetchInventoryCategories, fetchInventoryGroups, fetchInventoryTypes } from '@/api';

export function useInventoryGroupsPage() {
    const toast = useToast();

    const groups = ref([]);
    const categories = ref([]);
    const types = ref([]);
    const loading = ref(false);

    const isTreeExpanded = ref(false);
    const expandedGroupIds = ref(new Set());
    const expandedCategoryIds = ref(new Set());

    const sortedGroups = computed(() =>
        [...groups.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
    );
    const sortedCategories = computed(() =>
        [...categories.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
    );
    const sortedTypes = computed(() =>
        [...types.value].sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' })),
    );

    const groupMap = computed(() => {
        const map = new Map();
        groups.value.forEach((group) => map.set(group.id, group));
        return map;
    });

    const categoryMap = computed(() => {
        const map = new Map();
        categories.value.forEach((category) => map.set(category.id, category));
        return map;
    });

    const firstFloorOptions = computed(() =>
        sortedGroups.value.map((group) => ({ value: String(group.id), label: group.name })),
    );

    const secondFloorOptions = computed(() =>
        sortedCategories.value.map((category) => {
            const groupName = groupMap.value.get(category.group_id)?.name || `ID ${category.group_id}`;
            return { value: String(category.id), label: `${groupName} > ${category.name}` };
        }),
    );

    const categoriesByGroup = computed(() => {
        const map = new Map();
        for (const category of sortedCategories.value) {
            const bucket = map.get(category.group_id) || [];
            bucket.push(category);
            map.set(category.group_id, bucket);
        }
        return map;
    });

    const typesByCategory = computed(() => {
        const map = new Map();
        for (const type of sortedTypes.value) {
            const bucket = map.get(type.category_id) || [];
            bucket.push(type);
            map.set(type.category_id, bucket);
        }
        return map;
    });

    const hasCatalogNodes = computed(
        () => groups.value.length > 0 || categories.value.length > 0 || types.value.length > 0,
    );

    function isGroupExpanded(groupId) {
        return expandedGroupIds.value.has(groupId);
    }

    function isCategoryExpanded(categoryId) {
        return expandedCategoryIds.value.has(categoryId);
    }

    function toggleGroup(groupId) {
        const next = new Set(expandedGroupIds.value);
        if (next.has(groupId)) {
            next.delete(groupId);
        } else {
            next.add(groupId);
        }
        expandedGroupIds.value = next;
    }

    function toggleCategory(categoryId) {
        const next = new Set(expandedCategoryIds.value);
        if (next.has(categoryId)) {
            next.delete(categoryId);
        } else {
            next.add(categoryId);
        }
        expandedCategoryIds.value = next;
    }

    async function loadTree() {
        loading.value = true;
        try {
            const [groupsData, categoriesData, typesData] = await Promise.all([
                fetchInventoryGroups(),
                fetchInventoryCategories(),
                fetchInventoryTypes(),
            ]);
            groups.value = Array.isArray(groupsData) ? groupsData : [];
            categories.value = Array.isArray(categoriesData) ? categoriesData : [];
            types.value = Array.isArray(typesData) ? typesData : [];
            expandedGroupIds.value = new Set();
            expandedCategoryIds.value = new Set();
        } catch (error) {
            toast.error('Не удалось загрузить структуру товаров');
            console.error(error);
        } finally {
            loading.value = false;
        }
    }
    const {
        canCreateNomenclature,
        canDeleteNomenclature,
        canEditNomenclature,
        closeCreateModal,
        closeEditModal,
        createForm,
        createParentHint,
        createParentLabel,
        createParentRef,
        createSubmitLabel,
        deleteNode,
        editForm,
        handleCreateNode,
        isCreateCategoryExpanded,
        isCreateGroupExpanded,
        isCreateModalOpen,
        isCreateParentOpen,
        isEditModalOpen,
        openCreateModal,
        openEditModal,
        saving,
        selectCreateParent,
        submitEdit,
        toggleCreateCategory,
        toggleCreateGroup,
    } = useInventoryGroupsModals({
        categoriesByGroup,
        categoryMap,
        firstFloorOptions,
        groupMap,
        hasCatalogNodes,
        loadTree,
        secondFloorOptions,
        sortedGroups,
        typesByCategory,
    });

    onMounted(() => {
        loadTree();
    });

    return {
        sortedGroups,
        categoriesByGroup,
        typesByCategory,
        firstFloorOptions,
        secondFloorOptions,
        loading,
        saving,
        isTreeExpanded,
        isCreateModalOpen,
        isCreateParentOpen,
        createParentRef,
        createForm,
        isEditModalOpen,
        editForm,
        createParentLabel,
        createParentHint,
        createSubmitLabel,
        canCreateNomenclature,
        canEditNomenclature,
        canDeleteNomenclature,
        isGroupExpanded,
        isCategoryExpanded,
        toggleGroup,
        toggleCategory,
        isCreateGroupExpanded,
        isCreateCategoryExpanded,
        toggleCreateGroup,
        toggleCreateCategory,
        openCreateModal,
        closeCreateModal,
        selectCreateParent,
        loadTree,
        handleCreateNode,
        openEditModal,
        closeEditModal,
        submitEdit,
        deleteNode,
    };
}
