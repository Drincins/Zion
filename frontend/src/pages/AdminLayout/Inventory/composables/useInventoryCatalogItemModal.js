import { useToast } from 'vue-toastification';

import { createInventoryItem, updateInventoryItem, uploadInventoryItemPhoto } from '@/api';

export function useInventoryCatalogItemModal({
    canCreateNomenclature,
    canSubmitItemModal,
    isCatalogModalOpen,
    isEditMode,
    isItemModalOpen,
    itemForm,
    loadItems,
    parseNumber,
    photoInputRef,
    saving,
    seedModalPickerTree,
    typeMap,
    uploadingPhoto,
}) {
    const toast = useToast();

    function resetItemForm() {
        itemForm.id = null;
        itemForm.name = '';
        itemForm.note = '';
        itemForm.manufacturer = '';
        itemForm.storageConditions = '';
        itemForm.typeId = '';
        itemForm.cost = '';
        itemForm.photoUrl = '';
        itemForm.useInstanceCodes = true;
        itemForm.isActive = true;
        itemForm.createdAt = '';
    }

    function openCreateModal() {
        if (!canCreateNomenclature.value) {
            toast.error('Недостаточно прав для создания товара');
            return;
        }
        resetItemForm();
        isEditMode.value = false;
        isItemModalOpen.value = true;
        isCatalogModalOpen.value = false;
        seedModalPickerTree();
    }

    function setItemFormFromItem(item) {
        if (!item) {
            resetItemForm();
            return;
        }
        itemForm.id = item.id;
        itemForm.name = item.name || '';
        itemForm.note = item.note || '';
        itemForm.manufacturer = item.manufacturer || '';
        itemForm.storageConditions = item.storage_conditions || '';
        itemForm.typeId = item.kind_id ? String(item.kind_id) : '';
        itemForm.cost = item.cost !== null && item.cost !== undefined ? String(item.cost) : '';
        itemForm.photoUrl = item.photo_key || item.photo_url || '';
        itemForm.useInstanceCodes = item.use_instance_codes !== false;
        itemForm.isActive = item.is_active !== false;
        itemForm.createdAt = item.created_at || '';
    }

    function closeItemModal() {
        isItemModalOpen.value = false;
        isCatalogModalOpen.value = false;
        isEditMode.value = false;
        resetItemForm();
    }

    function openPhotoPicker() {
        if (!photoInputRef.value || uploadingPhoto.value || !canSubmitItemModal.value) {
            return;
        }
        photoInputRef.value.click();
    }

    async function handleUploadItemPhoto(event) {
        const file = event?.target?.files?.[0];
        if (!file || !canSubmitItemModal.value) {
            return;
        }
        uploadingPhoto.value = true;
        try {
            const response = await uploadInventoryItemPhoto(file);
            itemForm.photoUrl = response?.attachment_key || response?.attachment_url || '';
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
            toast.error(isEditMode.value ? 'Недостаточно прав для редактирования товара' : 'Недостаточно прав для создания товара');
            return;
        }
        const name = itemForm.name.trim();
        if (!name) {
            toast.error('Введите название товара');
            return;
        }

        const type = typeMap.value.get(Number(itemForm.typeId));
        if (!type) {
            toast.error('Выберите вид товара');
            return;
        }

        const cost = parseNumber(itemForm.cost);
        if (Number.isNaN(cost)) {
            toast.error('Стоимость должна быть числом');
            return;
        }

        saving.value = true;
        try {
            if (isEditMode.value && itemForm.id) {
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
                    is_active: Boolean(itemForm.isActive),
                });
                toast.success('Товар обновлен');
            } else {
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
                    is_active: Boolean(itemForm.isActive),
                    initial_quantity: 0,
                });
                toast.success('Товар создан');
            }

            closeItemModal();
            await loadItems();
        } catch (error) {
            toast.error('Не удалось сохранить товар');
            console.error(error);
        } finally {
            saving.value = false;
        }
    }

    return {
        closeItemModal,
        handleUploadItemPhoto,
        openCreateModal,
        openPhotoPicker,
        resetItemForm,
        setItemFormFromItem,
        submitItem,
    };
}
