<template>
    <div class="employees-page__modal-section">
        <div class="employees-page__trainings-toolbar">
            <Button
                v-if="canManageTrainings"
                color="primary"
                :loading="creatingTrainingRecord"
                :disabled="trainingTypesLoading || !trainingTypeOptions.length"
                @click="emit('open-training-assignment')"
            >
                Назначить тренинг
            </Button>
        </div>
        <p
            v-if="trainingTypesLoading"
            class="employees-page__trainings-hint"
        >
            Загрузка типов тренингов...
        </p>
        <p
            v-else-if="!trainingTypeOptions.length"
            class="employees-page__trainings-hint"
        >
            Нет доступных типов тренингов. Добавьте тип в разделе «Тренинги».
        </p>

        <div v-if="trainingsLoading" class="employees-page__modal-loading">Загрузка тренингов...</div>
        <div v-else>
            <Table v-if="employeeTrainings.length">
                <thead>
                    <tr>
                        <th>Дата</th>
                        <th>Тренинг</th>
                        <th>Комментарий</th>
                        <th class="employees-page__trainings-actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr
                        v-for="training in employeeTrainings"
                        :key="training.id"
                        :class="[
                            'employees-page__trainings-row',
                            {
                                'employees-page__trainings-row--editing':
                                    editingTrainingRecord.id === training.id
                            }
                        ]"
                        @click="
                            editingTrainingRecord.id !== training.id &&
                                emit('start-edit-training', training)
                        "
                    >
                        <td>
                            <template v-if="editingTrainingRecord.id === training.id">
                                <DateInput
                                    :model-value="editingTrainingRecord.date"
                                    label=""
                                    @update:model-value="updateEditingTrainingField('date', $event)"
                                />
                            </template>
                            <template v-else>
                                {{ formatDate(training.date) }}
                            </template>
                        </td>
                        <td>
                            <template v-if="editingTrainingRecord.id === training.id">
                                <Select
                                    :model-value="editingTrainingRecord.eventTypeId"
                                    :options="trainingTypeOptions"
                                    @update:model-value="updateEditingTrainingField('eventTypeId', $event)"
                                />
                            </template>
                            <template v-else>
                                {{ training.event_type?.name || '—' }}
                            </template>
                        </td>
                        <td class="employees-page__trainings-comment">
                            <template v-if="editingTrainingRecord.id === training.id">
                                <Input
                                    :model-value="editingTrainingRecord.comment"
                                    label=""
                                    @update:model-value="updateEditingTrainingField('comment', $event)"
                                />
                            </template>
                            <template v-else>
                                {{ training.comment || '—' }}
                            </template>
                        </td>
                        <td class="employees-page__trainings-actions">
                            <template v-if="editingTrainingRecord.id === training.id">
                                <Button
                                    color="primary"
                                    size="sm"
                                    :loading="updatingTrainingRecord"
                                    @click.stop="emit('update-training')"
                                >
                                    Сохранить
                                </Button>
                                <Button
                                    color="ghost"
                                    size="sm"
                                    :disabled="updatingTrainingRecord"
                                    @click.stop="emit('cancel-edit-training')"
                                >
                                    Отмена
                                </Button>
                            </template>
                            <template v-else>
                                <button
                                    v-if="canManageTrainings"
                                    type="button"
                                    class="employees-page__icon-button employees-page__icon-button--edit"
                                    title="Редактировать"
                                    @click.stop="emit('start-edit-training', training)"
                                >
                                    <BaseIcon name="Edit" />
                                </button>
                                <button
                                    v-if="canManageTrainings"
                                    type="button"
                                    class="employees-page__icon-button"
                                    :disabled="deletingTrainingRecordId === training.id"
                                    title="Удалить тренинг"
                                    @click.stop="emit('delete-training', training.id)"
                                >
                                    <BaseIcon name="Trash" />
                                </button>
                            </template>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <p v-if="employeeTrainings.length" class="employees-page__trainings-table-hint">
                Нажмите на строку, чтобы отредактировать тренинг.
            </p>
            <p v-else class="employees-page__empty">Тренинги ещё не назначены.</p>
        </div>
    </div>
</template>

<script setup>
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';

defineProps({
    canManageTrainings: { type: Boolean, default: false },
    creatingTrainingRecord: { type: Boolean, default: false },
    trainingTypesLoading: { type: Boolean, default: false },
    trainingTypeOptions: { type: Array, default: () => [] },
    trainingsLoading: { type: Boolean, default: false },
    employeeTrainings: { type: Array, default: () => [] },
    editingTrainingRecord: { type: Object, default: () => ({}) },
    updatingTrainingRecord: { type: Boolean, default: false },
    deletingTrainingRecordId: { type: [Number, String], default: null },
    formatDate: { type: Function, required: true }
});

const emit = defineEmits([
    'open-training-assignment',
    'start-edit-training',
    'cancel-edit-training',
    'update-training',
    'update-edit-training-field',
    'delete-training'
]);

function updateEditingTrainingField(field, value) {
    emit('update-edit-training-field', { field, value });
}
</script>

<style scoped lang="scss">
.employees-page__modal-loading {
    text-align: center;
    padding: 24px 0;
    color: var(--color-text-soft);
}

.employees-page__empty {
    text-align: center;
    color: var(--color-text-soft);
    padding: 24px 0;
}

.employees-page__trainings-comment {
    max-width: 320px;
    white-space: pre-wrap;
    word-break: break-word;
}

.employees-page__trainings-row {
    cursor: pointer;
    transition: background-color $duration;
}

.employees-page__trainings-row--editing {
    background-color: var(--color-surface);
}

.employees-page__trainings-row--editing:hover {
    background-color: var(--color-surface);
}

.employees-page__trainings-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 12px;
}

.employees-page__trainings-actions {
    width: 220px;
    text-align: right;
    white-space: nowrap;
}

.employees-page__trainings-hint {
    margin-top: -8px;
    margin-bottom: 12px;
    font-size: 14px;
    color: var(--color-text-soft);
}

.employees-page__trainings-table-hint {
    margin-top: 8px;
    font-size: 14px;
    color: var(--color-text-soft);
}

.employees-page__icon-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    border-radius: 8px;
    background: transparent;
    cursor: pointer;
    color: var(--color-danger);
    transition: background-color $duration, color $duration;
}

.employees-page__icon-button:disabled {
    opacity: 0.6;
    cursor: default;
}

.employees-page__icon-button:not(:disabled):hover {
    opacity: 0.6;
}

.employees-page__icon-button--edit {
    color: var(--color-text);
}

.employees-page__icon-button--edit:not(:disabled):hover {
    color: var(--color-primary);
}
</style>
