<template>
    <Modal @close="closeItemDetail">
        <template #header>Карточка товара</template>
        <template #default>
            <div class="inventory-items__detail-card">
                <div class="inventory-items__detail-info">
                    <h3 class="inventory-items__detail-title">{{ detailItemEntry.item.name }}</h3>
                    <p class="inventory-items__detail-note">
                        {{ detailItemEntry.item.note || 'Описание не заполнено' }}
                    </p>
                    <div class="inventory-items__detail-grid">
                        <div>
                            <span class="inventory-items__detail-label">Код</span>
                            <span class="inventory-items__detail-value">{{ detailItemEntry.item.code }}</span>
                        </div>
                        <div>
                            <span class="inventory-items__detail-label">Стоимость в подразделении</span>
                            <span class="inventory-items__detail-value">
                                {{ formatMoney(detailItemEntry.locationAvgCost ?? detailItemEntry.item.cost) }}
                            </span>
                        </div>
                        <div>
                            <span class="inventory-items__detail-label">Раздел каталога</span>
                            <span class="inventory-items__detail-value">{{ getCatalogPath(detailItemEntry.item) }}</span>
                        </div>
                        <div>
                            <span class="inventory-items__detail-label">Количество в подразделении</span>
                            <span class="inventory-items__detail-value">{{ detailItemEntry.quantity }} шт.</span>
                        </div>
                        <div>
                            <span class="inventory-items__detail-label">Производитель</span>
                            <span class="inventory-items__detail-value">
                                {{ detailItemEntry.item.manufacturer || '—' }}
                            </span>
                        </div>
                        <div>
                            <span class="inventory-items__detail-label">Условия хранения</span>
                            <span class="inventory-items__detail-value">
                                {{ detailItemEntry.item.storage_conditions || '—' }}
                            </span>
                        </div>
                    </div>
                </div>
                <div class="inventory-items__detail-photo">
                    <img
                        v-if="detailItemEntry.item.photo_url"
                        :src="detailItemEntry.item.photo_url"
                        :alt="detailItemEntry.item.name || 'Фото товара'"
                    />
                    <div v-else class="inventory-items__detail-photo-empty">Нет фото</div>
                </div>
            </div>
            <div class="inventory-items__detail-actions">
                <Input
                    :model-value="quantityForm.value"
                    label="Изменить количество в подразделении"
                    type="number"
                    min="0"
                    :readonly="!canCreateMovement"
                    @update:model-value="updateQuantityFormField('value', $event)"
                />
                <Button
                    v-if="canCreateMovement"
                    color="primary"
                    size="sm"
                    :loading="saving"
                    @click="handleUpdateQuantityFromDetail"
                >
                    Сохранить количество
                </Button>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';

const emit = defineEmits(['update:quantityForm']);

const props = defineProps({
    canCreateMovement: { type: Boolean, required: true },
    closeItemDetail: { type: Function, required: true },
    detailItemEntry: { type: Object, required: true },
    formatMoney: { type: Function, required: true },
    getCatalogPath: { type: Function, required: true },
    handleUpdateQuantityFromDetail: { type: Function, required: true },
    quantityForm: { type: Object, required: true },
    saving: { type: Boolean, required: true },
});

function updateQuantityFormField(field, value) {
    emit('update:quantityForm', {
        ...props.quantityForm,
        [field]: value
    });
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>

