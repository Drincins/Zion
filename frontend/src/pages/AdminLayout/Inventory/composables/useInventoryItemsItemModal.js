import { computed } from 'vue';
import { useToast } from 'vue-toastification';

import { allocateInventoryItem, createInventoryItem, updateInventoryItem, uploadInventoryItemPhoto } from '@/api';

export function useInventoryItemsItemModal({
    canCreateMovement,
    canCreateNomenclature,
    canEditNomenclature,
    catalogItems,
    departmentOptions,
    hasLoadedByFilters,
    isCatalogModalOpen,
    isEditMode,
    isItemModalOpen,
    itemForm,
    loadCatalogItemsForModal,
    loadItemsByFilters,
    parseCatalogNodeValue,
    parseNumber,
    photoInputRef,
    saving,
    seedCatalogExpandedTrees,
    typeMap,
    uploadingPhoto,
    userStore,
}) {
    const toast = useToast();

    const selectedCatalogItem = computed(() =>
        catalogItems.value.find((entry) => Number(entry.id) === Number(itemForm.selectedCatalogItemId)) || null,
    );

    const isCatalogSourceMode = computed(() => !isEditMode.value && itemForm.useCatalogItem);

    const canOpenCreateModal = computed(() => canCreateNomenclature.value || canCreateMovement.value);
    const canToggleCreateSourceMode = computed(() =>
        !isEditMode.value && canCreateNomenclature.value && canCreateMovement.value,
    );
    const canSubmitItemModal = computed(() => {
        if (isEditMode.value) {
            return canEditNomenclature.value;
        }
        return isCatalogSourceMode.value ? canCreateMovement.value : canCreateNomenclature.value;
    });
    const canEditModalPhoto = computed(() => {
        if (isEditMode.value) {
            return canEditNomenclature.value;
        }
        return !isCatalogSourceMode.value && canCreateNomenclature.value;
    });

    const catalogItemsForPicker = computed(() => {
        const search = itemForm.catalogSearch.trim().toLowerCase();
        const source = [...catalogItems.value].sort((a, b) =>
            String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }),
        );
        if (!search) {
            return source.slice(0, 200);
        }
        return source
            .filter((item) => {
                const stack = [item.code, item.name, item.note]
                    .filter(Boolean)
                    .join(' ')
                    .toLowerCase();
                return stack.includes(search);
            })
            .slice(0, 200);
    });

    const catalogBaseCost = computed(() => {
        if (!selectedCatalogItem.value) {
            return NaN;
        }
        return parseNumber(
            selectedCatalogItem.value.default_cost ?? selectedCatalogItem.value.cost,
        );
    });

    const isCatalogCostOverride = computed(() => {
        if (!isCatalogSourceMode.value || !selectedCatalogItem.value) {
            return false;
        }
        const currentCost = parseNumber(itemForm.cost);
        const baseCost = catalogBaseCost.value;
        if (Number.isNaN(currentCost) || Number.isNaN(baseCost)) {
            return false;
        }
        return Math.abs(currentCost - baseCost) > 0.0001;
    });

    function resetItemForm() {
        itemForm.id = null;
        itemForm.code = '';
        itemForm.name = '';
        itemForm.catalogNodeId = '';
        itemForm.cost = '';
        itemForm.note = '';
        itemForm.manufacturer = '';
        itemForm.storageConditions = '';
        itemForm.photoUrl = '';
        itemForm.photoPreviewUrl = '';
        itemForm.useInstanceCodes = true;
        itemForm.useCatalogItem = false;
        itemForm.selectedCatalogItemId = null;
        itemForm.catalogSearch = '';
        itemForm.targetOptionId = '';
        itemForm.targetQuantity = '1';
    }

    function getDefaultCreateDepartmentOptionId() {
        const options = departmentOptions.value.filter(
            (option) => option.type === 'warehouse' || option.type === 'restaurant' || option.type === 'subdivision',
        );
        if (!options.length) {
            return '';
        }

        const preferredSubdivisionId = Number(userStore.restaurantSubdivisionId);
        if (Number.isFinite(preferredSubdivisionId) && preferredSubdivisionId > 0) {
            const subdivisionOption = options.find(
                (option) => option.type === 'subdivision' && Number(option.subdivision_id) === preferredSubdivisionId,
            );
            if (subdivisionOption) {
                return subdivisionOption.id;
            }
        }

        const preferredRestaurantId = Number(userStore.workplaceRestaurantId);
        if (Number.isFinite(preferredRestaurantId) && preferredRestaurantId > 0) {
            const restaurantOption = options.find(
                (option) => option.type === 'restaurant' && Number(option.restaurant_id) === preferredRestaurantId,
            );
            if (restaurantOption) {
                return restaurantOption.id;
            }
        }

        if (options.length === 1) {
            return options[0].id;
        }
        return '';
    }

    function selectCatalogItem(item) {
        if (!item || !item.id) {
            return;
        }
        itemForm.useCatalogItem = true;
        itemForm.selectedCatalogItemId = Number(item.id);
        itemForm.name = item.name || '';
        itemForm.note = item.note || '';
        itemForm.manufacturer = item.manufacturer || '';
        itemForm.storageConditions = item.storage_conditions || '';
        itemForm.catalogNodeId = item.kind_id ? `t:${item.kind_id}` : '';
        itemForm.photoUrl = item.photo_key || item.photo_url || '';
        itemForm.photoPreviewUrl = item.photo_url || item.photo_key || '';
        itemForm.cost = String(item.default_cost ?? item.cost ?? '');
        itemForm.useInstanceCodes = item.use_instance_codes !== false;
        if (!itemForm.targetOptionId) {
            itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
        }
    }

    function toggleCatalogSourceMode() {
        if (isEditMode.value || !canToggleCreateSourceMode.value) {
            return;
        }
        itemForm.useCatalogItem = !itemForm.useCatalogItem;
        itemForm.selectedCatalogItemId = null;
        itemForm.catalogSearch = '';
        if (itemForm.useCatalogItem) {
            itemForm.name = '';
            itemForm.note = '';
            itemForm.manufacturer = '';
            itemForm.storageConditions = '';
            itemForm.catalogNodeId = '';
            itemForm.cost = '';
            itemForm.photoUrl = '';
            itemForm.photoPreviewUrl = '';
            itemForm.useInstanceCodes = true;
            itemForm.targetQuantity = '1';
            if (!itemForm.targetOptionId) {
                itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
            }
            void loadCatalogItemsForModal();
        } else {
            itemForm.name = '';
            itemForm.note = '';
            itemForm.manufacturer = '';
            itemForm.storageConditions = '';
            itemForm.catalogNodeId = '';
            itemForm.cost = '';
            itemForm.photoUrl = '';
            itemForm.photoPreviewUrl = '';
            itemForm.useInstanceCodes = true;
            itemForm.targetOptionId = '';
            itemForm.targetQuantity = '1';
        }
    }

    function openPhotoPicker() {
        if (!photoInputRef.value || uploadingPhoto.value || !canEditModalPhoto.value) {
            return;
        }
        photoInputRef.value.click();
    }

    function openCreateModal() {
        if (!canOpenCreateModal.value) {
            toast.error('Недостаточно прав для работы с номенклатурой склада');
            return;
        }
        resetItemForm();
        itemForm.useCatalogItem = canCreateMovement.value;
        itemForm.targetOptionId = getDefaultCreateDepartmentOptionId();
        isEditMode.value = false;
        isItemModalOpen.value = true;
        seedCatalogExpandedTrees();
        if (itemForm.useCatalogItem) {
            void loadCatalogItemsForModal();
        }
    }

    function openEditModal(item) {
        if (!canEditNomenclature.value) {
            toast.error('Недостаточно прав для редактирования товара');
            return;
        }
        itemForm.id = item.id;
        itemForm.code = item.code || '';
        itemForm.name = item.name || '';
        itemForm.catalogNodeId = item.kind_id ? `t:${item.kind_id}` : '';
        itemForm.cost = item.cost !== null && item.cost !== undefined ? String(item.cost) : '';
        itemForm.note = item.note || '';
        itemForm.manufacturer = item.manufacturer || '';
        itemForm.storageConditions = item.storage_conditions || '';
        itemForm.photoUrl = item.photo_key || item.photo_url || '';
        itemForm.photoPreviewUrl = item.photo_url || item.photo_key || '';
        itemForm.useInstanceCodes = item.use_instance_codes !== false;
        itemForm.useCatalogItem = false;
        itemForm.selectedCatalogItemId = null;
        itemForm.catalogSearch = '';
        itemForm.targetOptionId = '';
        itemForm.targetQuantity = '1';
        isEditMode.value = true;
        isItemModalOpen.value = true;
        seedCatalogExpandedTrees();
    }

    function closeItemModal() {
        isItemModalOpen.value = false;
        isCatalogModalOpen.value = false;
        isEditMode.value = false;
        resetItemForm();
    }

    async function handleUploadItemPhoto(event) {
        const file = event?.target?.files?.[0];
        if (!file || !canEditModalPhoto.value) {
            return;
        }
        uploadingPhoto.value = true;
        try {
            const response = await uploadInventoryItemPhoto(file);
            itemForm.photoUrl = response?.attachment_key || response?.attachment_url || '';
            itemForm.photoPreviewUrl = response?.attachment_url || response?.attachment_key || '';
            toast.success('Фото загружено');
        } catch (error) {
            toast.error('Не удалось загрузить фото');
            console.error(error);
        } finally {
            uploadingPhoto.value = false;
            if (event?.target) {
                event.target.value = '';
            }
        }
    }

    async function submitItem() {
        if (!canSubmitItemModal.value) {
            toast.error('Недостаточно прав для сохранения изменений');
            return;
        }
        const cost = parseNumber(itemForm.cost);
        if (Number.isNaN(cost)) {
            toast.error('Стоимость должна быть числом');
            return;
        }

        const targetOption = departmentOptions.value.find((option) => option.id === itemForm.targetOptionId);
        const quantity = Number.parseInt(String(itemForm.targetQuantity || '0'), 10);

        saving.value = true;
        try {
            if (isCatalogSourceMode.value) {
                if (!selectedCatalogItem.value?.id) {
                    toast.error('Выберите товар из каталога');
                    return;
                }
                if (!targetOption || !['warehouse', 'restaurant', 'subdivision'].includes(targetOption.type)) {
                    toast.error('Выберите подразделение');
                    return;
                }
                if (!Number.isFinite(quantity) || quantity <= 0) {
                    toast.error('Введите корректное количество');
                    return;
                }

                if (isCatalogCostOverride.value) {
                    const confirmed = window.confirm(
                        'Стоимость отличается от каталога. Изменение применится только к этой партии товара. Продолжить?',
                    );
                    if (!confirmed) {
                        return;
                    }
                }

                const allocatePayload = {
                    location_kind: targetOption.type,
                    quantity,
                    unit_cost: cost,
                    comment: isCatalogCostOverride.value
                        ? 'Добавление партии из каталога с изменением стоимости'
                        : 'Добавление партии из каталога',
                };
                if (targetOption.type === 'restaurant') {
                    allocatePayload.restaurant_id = Number(targetOption.restaurant_id);
                }
                if (targetOption.type === 'subdivision') {
                    allocatePayload.subdivision_id = Number(targetOption.subdivision_id);
                }

                await allocateInventoryItem(selectedCatalogItem.value.id, allocatePayload);
                toast.success('Партия добавлена в подразделение');
            } else if (isEditMode.value && itemForm.id) {
                const parsedNode = parseCatalogNodeValue(itemForm.catalogNodeId);
                if (!parsedNode || parsedNode.level !== 't') {
                    toast.error('Выберите раздел 3-го этажа');
                    return;
                }

                const type = typeMap.value.get(parsedNode.id);
                if (!type) {
                    toast.error('Раздел каталога не найден');
                    return;
                }

                const name = itemForm.name.trim();
                if (!name) {
                    toast.error('Введите название товара');
                    return;
                }

                await updateInventoryItem(itemForm.id, {
                    name,
                    group_id: type.group_id,
                    category_id: type.category_id,
                    kind_id: type.id,
                    cost,
                    note: itemForm.note || undefined,
                    manufacturer: itemForm.manufacturer || undefined,
                    storage_conditions: itemForm.storageConditions || undefined,
                    photo_url: itemForm.photoUrl || null,
                    use_instance_codes: Boolean(itemForm.useInstanceCodes),
                });
                toast.success('Товар обновлен');
            } else {
                const parsedNode = parseCatalogNodeValue(itemForm.catalogNodeId);
                if (!parsedNode || parsedNode.level !== 't') {
                    toast.error('Выберите раздел 3-го этажа');
                    return;
                }

                const type = typeMap.value.get(parsedNode.id);
                if (!type) {
                    toast.error('Раздел каталога не найден');
                    return;
                }

                const name = itemForm.name.trim();
                if (!name) {
                    toast.error('Введите название товара');
                    return;
                }

                await createInventoryItem({
                    name,
                    group_id: type.group_id,
                    category_id: type.category_id,
                    kind_id: type.id,
                    cost,
                    note: itemForm.note || undefined,
                    manufacturer: itemForm.manufacturer || undefined,
                    storage_conditions: itemForm.storageConditions || undefined,
                    photo_url: itemForm.photoUrl || null,
                    use_instance_codes: Boolean(itemForm.useInstanceCodes),
                    initial_quantity: 0,
                });
                toast.success('Товар создан');
            }

            closeItemModal();
            if (hasLoadedByFilters.value) {
                await loadItemsByFilters();
            }
            await loadCatalogItemsForModal(true);
        } catch (error) {
            toast.error('Не удалось сохранить товар');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    return {
        canEditModalPhoto,
        canOpenCreateModal,
        canSubmitItemModal,
        canToggleCreateSourceMode,
        catalogBaseCost,
        catalogItemsForPicker,
        closeItemModal,
        getDefaultCreateDepartmentOptionId,
        handleUploadItemPhoto,
        isCatalogCostOverride,
        isCatalogSourceMode,
        openCreateModal,
        openEditModal,
        openPhotoPicker,
        selectedCatalogItem,
        selectCatalogItem,
        submitItem,
        toggleCatalogSourceMode,
        resetItemForm,
    };
}
