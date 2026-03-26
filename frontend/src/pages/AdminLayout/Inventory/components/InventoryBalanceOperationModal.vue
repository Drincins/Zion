<template>
    <Modal class="inventory-balance__operation-modal-window" @close="closeOperationModal">
        <template #header>
            <div class="inventory-balance__operation-modal-head">
                <div>
                    <h3>Операция по товару</h3>
                    <p>{{ selectedRestaurantName }} · {{ selectedStoragePlaceLabel }}</p>
                </div>
            </div>
        </template>

        <template #default>
            <div class="inventory-balance__operation-body">
                <div class="inventory-balance__operation-type-list">
                    <button
                        v-for="option in operationTypeOptions"
                        :key="option.value"
                        type="button"
                        :class="['inventory-balance__operation-type-btn', { 'is-active': operationType === option.value }]"
                        @click="$emit('update:operationType', option.value)"
                    >
                        {{ option.label }}
                    </button>
                </div>

                <div class="inventory-balance__operation-grid">
                    <Select
                        v-model="operationForm.itemId"
                        label="Товар"
                        :options="operationItemOptions"
                        placeholder="Выберите товар"
                        searchable
                    />
                    <Input
                        v-model="operationForm.quantity"
                        label="Количество"
                        type="number"
                        min="1"
                        step="1"
                        placeholder="Например, 5"
                    />

                    <Select
                        v-if="isIncomeOperation"
                        v-model="operationForm.targetStoragePlaceId"
                        label="Куда зачислить"
                        :options="targetStoragePlaceOptions"
                        placeholder="Выберите место хранения"
                        searchable
                    />

                    <Input
                        v-if="isIncomeOperation"
                        v-model="operationForm.unitCost"
                        label="Цена за единицу"
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="По умолчанию из карточки"
                    />

                    <Select
                        v-if="isTransferOperation || isWriteoffOperation"
                        v-model="operationForm.sourceStoragePlaceId"
                        label="Откуда"
                        :options="sourceStoragePlaceOptions"
                        placeholder="Выберите место хранения"
                        searchable
                    />

                    <Select
                        v-if="isTransferOperation"
                        v-model="operationForm.targetRestaurantId"
                        label="Куда перемещаем"
                        :options="restaurantOptions"
                        placeholder="Выберите ресторан"
                        searchable
                    />

                    <Select
                        v-if="isTransferOperation"
                        v-model="operationForm.targetStoragePlaceId"
                        label="Место хранения получателя"
                        :options="targetStoragePlaceOptions"
                        placeholder="Выберите место хранения"
                        searchable
                    />

                    <Input
                        v-model="operationForm.reason"
                        label="Комментарий / основание"
                        placeholder="Например: поставка, внутренний перевод, списание"
                    />
                </div>

                <p v-if="isTransferOperation || isWriteoffOperation" class="inventory-balance__operation-hint">
                    Доступно в источнике: <strong>{{ sourceLocationQuantity }}</strong> шт.
                </p>
                <p v-else-if="isIncomeOperation && selectedOperationItem" class="inventory-balance__operation-hint">
                    Товар будет зачислен в {{ selectedRestaurantName }} · {{ operationTargetStoragePlaceLabel }}.
                </p>

                <section class="inventory-balance__operation-preview">
                    <h4>Запись операции</h4>
                    <dl>
                        <dt>Что</dt>
                        <dd>{{ operationDraftRecord.what }}</dd>
                        <dt>Сколько</dt>
                        <dd>{{ operationDraftRecord.quantity }}</dd>
                        <dt>Откуда</dt>
                        <dd>{{ operationDraftRecord.from }}</dd>
                        <dt>Куда</dt>
                        <dd>{{ operationDraftRecord.to }}</dd>
                        <dt>Как</dt>
                        <dd>{{ operationDraftRecord.method }}</dd>
                        <dt>Почему</dt>
                        <dd>{{ operationDraftRecord.reason }}</dd>
                    </dl>
                </section>
            </div>
        </template>

        <template #footer>
            <div class="inventory-balance__operation-actions">
                <Button color="ghost" size="sm" :disabled="operationSubmitting" @click="closeOperationModal">
                    Отмена
                </Button>
                <Button color="primary" size="sm" :loading="operationSubmitting" @click="submitOperation">
                    Сохранить операцию
                </Button>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

defineEmits(['update:operationType']);

defineProps({
    closeOperationModal: { type: Function, required: true },
    isIncomeOperation: { type: Boolean, required: true },
    isTransferOperation: { type: Boolean, required: true },
    isWriteoffOperation: { type: Boolean, required: true },
    operationDraftRecord: { type: Object, required: true },
    operationForm: { type: Object, required: true },
    operationItemOptions: { type: Array, required: true },
    operationSubmitting: { type: Boolean, required: true },
    operationTargetStoragePlaceLabel: { type: String, required: true },
    operationType: { type: String, required: true },
    operationTypeOptions: { type: Array, required: true },
    restaurantOptions: { type: Array, required: true },
    selectedOperationItem: { type: Object, default: null },
    selectedRestaurantName: { type: String, required: true },
    selectedStoragePlaceLabel: { type: String, required: true },
    sourceLocationQuantity: { type: Number, required: true },
    sourceStoragePlaceOptions: { type: Array, required: true },
    submitOperation: { type: Function, required: true },
    targetStoragePlaceOptions: { type: Array, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-balance' as *;
</style>
