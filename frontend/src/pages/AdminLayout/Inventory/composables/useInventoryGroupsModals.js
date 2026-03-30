import { computed, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';

import {
    INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS,
} from '@/accessPolicy';
import { useClickOutside } from '@/composables/useClickOutside';
import { useUserStore } from '@/stores/user';
import {
    createInventoryCategory,
    createInventoryGroup,
    createInventoryType,
    deleteInventoryCategory,
    deleteInventoryGroup,
    deleteInventoryType,
    updateInventoryCategory,
    updateInventoryGroup,
    updateInventoryType,
} from '@/api';

export function useInventoryGroupsModals({
    categoryMap,
    firstFloorOptions,
    groupMap,
    hasCatalogNodes,
    loadTree,
    secondFloorOptions,
    sortedGroups,
}) {
    const toast = useToast();
    const userStore = useUserStore();

    const saving = ref(false);

    const isCreateModalOpen = ref(false);
    const isCreateParentOpen = ref(false);
    const createParentRef = ref(null);
    const createExpandedGroupIds = ref(new Set());
    const createExpandedCategoryIds = ref(new Set());

    const createForm = reactive({
        name: '',
        parentNode: 'root',
    });

    const isEditModalOpen = ref(false);
    const editForm = reactive({
        id: null,
        level: '',
        name: '',
        parentGroupId: '',
        parentCategoryId: '',
    });

    const canCreateNomenclature = computed(() =>
        userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS),
    );
    const canEditNomenclature = computed(() =>
        userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS),
    );
    const canDeleteNomenclature = computed(() =>
        userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_DELETE_PERMISSIONS),
    );

    const createParentLabel = computed(() => {
        if (!hasCatalogNodes.value) {
            return 'База пуста — будет создана новая группа';
        }
        const parsed = parseCreateParentNode(createForm.parentNode);
        if (!parsed || parsed.level === 'root') {
            return '... (новая группа)';
        }
        if (parsed.level === 'g') {
            const group = groupMap.value.get(parsed.id);
            return group ? `${group.name} (новая категория)` : '... (новая группа)';
        }
        if (parsed.level === 'c') {
            const category = categoryMap.value.get(parsed.id);
            if (!category) {
                return '... (новая группа)';
            }
            const groupName = groupMap.value.get(category.group_id)?.name || `ID ${category.group_id}`;
            return `${groupName} > ${category.name} (новый вид)`;
        }
        return '... (новая группа)';
    });

    const createParentHint = computed(() => {
        if (!hasCatalogNodes.value) {
            return 'Структура пуста. Первый раздел будет создан на уровне группы.';
        }
        const parsed = parseCreateParentNode(createForm.parentNode);
        if (!parsed || parsed.level === 'root') {
            return 'Будет создана новая группа (1-й этаж).';
        }
        if (parsed.level === 'g') {
            return 'Будет создана новая категория внутри выбранной группы.';
        }
        return 'Будет создан новый вид внутри выбранной категории.';
    });

    const createSubmitLabel = computed(() => {
        if (!hasCatalogNodes.value) {
            return 'Создать группу';
        }
        const parsed = parseCreateParentNode(createForm.parentNode);
        if (!parsed || parsed.level === 'root') {
            return 'Создать группу';
        }
        if (parsed.level === 'g') {
            return 'Создать категорию';
        }
        return 'Создать вид';
    });

    function parseCreateParentNode(value) {
        if (!value || value === 'root') {
            return { level: 'root' };
        }
        const [level, idRaw] = String(value).split(':');
        if (!['g', 'c'].includes(level)) {
            return null;
        }
        const id = Number(idRaw);
        if (!Number.isFinite(id)) {
            return null;
        }
        return { level, id };
    }

    function resetCreateForm() {
        createForm.name = '';
        createForm.parentNode = 'root';
    }

    function seedCreateTreeExpansion() {
        createExpandedGroupIds.value = new Set(sortedGroups.value.map((group) => group.id));
        createExpandedCategoryIds.value = new Set();
    }

    function isCreateGroupExpanded(groupId) {
        return createExpandedGroupIds.value.has(groupId);
    }

    function isCreateCategoryExpanded(categoryId) {
        return createExpandedCategoryIds.value.has(categoryId);
    }

    function toggleCreateGroup(groupId) {
        const next = new Set(createExpandedGroupIds.value);
        if (next.has(groupId)) {
            next.delete(groupId);
        } else {
            next.add(groupId);
        }
        createExpandedGroupIds.value = next;
    }

    function toggleCreateCategory(categoryId) {
        const next = new Set(createExpandedCategoryIds.value);
        if (next.has(categoryId)) {
            next.delete(categoryId);
        } else {
            next.add(categoryId);
        }
        createExpandedCategoryIds.value = next;
    }

    function openCreateModal() {
        if (!canCreateNomenclature.value) {
            toast.error('Недостаточно прав для создания номенклатуры');
            return;
        }
        resetCreateForm();
        seedCreateTreeExpansion();
        isCreateParentOpen.value = false;
        isCreateModalOpen.value = true;
    }

    function closeCreateModal() {
        isCreateModalOpen.value = false;
        isCreateParentOpen.value = false;
        resetCreateForm();
    }

    function selectCreateParent(value) {
        createForm.parentNode = value;
        isCreateParentOpen.value = false;
    }

    function resetEditForm() {
        editForm.id = null;
        editForm.level = '';
        editForm.name = '';
        editForm.parentGroupId = '';
        editForm.parentCategoryId = '';
    }

    async function handleCreateNode() {
        if (!canCreateNomenclature.value) {
            toast.error('Недостаточно прав для создания номенклатуры');
            return;
        }
        const name = createForm.name.trim();
        if (!name) {
            toast.error('Введите название');
            return;
        }

        saving.value = true;
        try {
            if (!hasCatalogNodes.value) {
                await createInventoryGroup({ name });
            } else {
                const parent = parseCreateParentNode(createForm.parentNode);
                if (!parent || parent.level === 'root') {
                    await createInventoryGroup({ name });
                } else if (parent.level === 'g') {
                    const group = groupMap.value.get(parent.id);
                    if (!group) {
                        toast.error('Выберите папку для новой категории');
                        return;
                    }
                    await createInventoryCategory({ name, group_id: group.id });
                } else {
                    const category = categoryMap.value.get(parent.id);
                    if (!category) {
                        toast.error('Выберите папку для нового вида');
                        return;
                    }
                    await createInventoryType({
                        name,
                        group_id: category.group_id,
                        category_id: category.id,
                    });
                }
            }
            toast.success('Раздел создан');
            closeCreateModal();
            await loadTree();
        } catch (error) {
            toast.error('Не удалось создать раздел');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    function openEditModal(level, entity) {
        if (!canEditNomenclature.value) {
            toast.error('Недостаточно прав для редактирования номенклатуры');
            return;
        }
        editForm.id = entity.id;
        editForm.level = level;
        editForm.name = entity.name || '';
        editForm.parentGroupId = level !== 'group' ? String(entity.group_id || '') : '';
        editForm.parentCategoryId = level === 'type' ? String(entity.category_id || '') : '';
        isEditModalOpen.value = true;
    }

    function closeEditModal() {
        isEditModalOpen.value = false;
        resetEditForm();
    }

    async function submitEdit() {
        if (!canEditNomenclature.value) {
            toast.error('Недостаточно прав для редактирования номенклатуры');
            return;
        }
        if (!editForm.id) {
            return;
        }
        const name = editForm.name.trim();
        if (!name) {
            toast.error('Введите название');
            return;
        }

        saving.value = true;
        try {
            if (editForm.level === 'group') {
                await updateInventoryGroup(editForm.id, { name });
            } else if (editForm.level === 'category') {
                const groupId = Number(editForm.parentGroupId);
                if (!groupId) {
                    toast.error('Выберите родителя 1-го этажа');
                    return;
                }
                await updateInventoryCategory(editForm.id, { name, group_id: groupId });
            } else if (editForm.level === 'type') {
                const categoryId = Number(editForm.parentCategoryId);
                const category = categoryMap.value.get(categoryId);
                if (!category) {
                    toast.error('Выберите родителя 2-го этажа');
                    return;
                }
                await updateInventoryType(editForm.id, {
                    name,
                    group_id: category.group_id,
                    category_id: category.id,
                });
            }
            toast.success('Изменения сохранены');
            closeEditModal();
            await loadTree();
        } catch (error) {
            toast.error('Не удалось сохранить изменения');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    async function deleteNode(level, id) {
        if (!canDeleteNomenclature.value) {
            toast.error('Недостаточно прав для удаления номенклатуры');
            return;
        }
        if (!window.confirm('Удалить раздел?')) {
            return;
        }
        saving.value = true;
        try {
            if (level === 'group') {
                await deleteInventoryGroup(id);
            } else if (level === 'category') {
                await deleteInventoryCategory(id);
            } else {
                await deleteInventoryType(id);
            }
            toast.success('Раздел удален');
            await loadTree();
        } catch (error) {
            toast.error('Не удалось удалить раздел');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    useClickOutside(
        [
            {
                element: createParentRef,
                when: () => isCreateParentOpen.value,
                onOutside: () => {
                    isCreateParentOpen.value = false;
                },
            },
        ],
        { eventName: 'click' },
    );

    return {
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
        firstFloorOptions,
        handleCreateNode,
        isCreateCategoryExpanded,
        isCreateGroupExpanded,
        isCreateModalOpen,
        isCreateParentOpen,
        isEditModalOpen,
        openCreateModal,
        openEditModal,
        saving,
        secondFloorOptions,
        selectCreateParent,
        submitEdit,
        toggleCreateCategory,
        toggleCreateGroup,
    };
}
