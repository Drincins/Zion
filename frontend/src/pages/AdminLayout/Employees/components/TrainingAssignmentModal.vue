<template>
    <Modal v-if="isOpen" @close="emit('close')">
        <template #header>
            <div class="training-assignment-modal__header">
                <h3 class="training-assignment-modal__title">Назначение тренинга</h3>
            </div>
        </template>
        <template #default>
            <div v-if="trainingTypesLoading" class="training-assignment-modal__loading">
                Загрузка типов тренингов...
            </div>
            <form
                v-else
                class="training-assignment-modal__form"
                @submit.prevent="handleValidatedSubmit"
            >
                <div class="training-assignment-modal__field">
                    <Select
                        v-model="eventTypeIdModel"
                        label="Тип тренинга"
                        :options="trainingTypeOptions"
                        :disabled="!trainingTypeOptions.length"
                        placeholder="Выберите тип"
                    />
                    <p v-if="getFieldError('eventTypeId')" class="training-assignment-modal__error">
                        {{ getFieldError('eventTypeId') }}
                    </p>
                </div>
                <div class="training-assignment-modal__field">
                    <DateInput v-model="dateModel" label="Дата" />
                    <p v-if="getFieldError('date')" class="training-assignment-modal__error">
                        {{ getFieldError('date') }}
                    </p>
                </div>
                <div class="training-assignment-modal__field">
                    <Input v-model="commentModel" label="Комментарий" />
                    <p v-if="getFieldError('comment')" class="training-assignment-modal__error">
                        {{ getFieldError('comment') }}
                    </p>
                </div>
                <p
                    v-if="!trainingTypeOptions.length"
                    class="training-assignment-modal__hint"
                >
                    Нет доступных типов тренингов. Добавьте тип в разделе «Тренинги».
                </p>
            </form>
        </template>
        <template #footer>
            <Button color="ghost" :disabled="creatingTrainingRecord" @click="emit('close')">
                Отмена
            </Button>
            <Button
                color="primary"
                :loading="creatingTrainingRecord"
                :disabled="!trainingTypeOptions.length"
                @click="handleValidatedSubmit"
            >
                Назначить
            </Button>
        </template>
    </Modal>
</template>

<script setup>
import { toRefs } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useEmployeeModalValidation } from './useEmployeeModalValidation';

const props = defineProps({
    isOpen: { type: Boolean, default: false },
    trainingForm: { type: Object, required: true },
    trainingTypeOptions: { type: Array, default: () => [] },
    trainingTypesLoading: { type: Boolean, default: false },
    creatingTrainingRecord: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'assign-training']);

const {
    isOpen,
    trainingForm,
    trainingTypeOptions,
    trainingTypesLoading,
    creatingTrainingRecord,
} = toRefs(props);

const trainingValidationSchema = {
    eventTypeId: 'required',
    date: 'required',
    comment: 'max:500',
};

const { bindField, getFieldError, handleValidatedSubmit } = useEmployeeModalValidation({
    isOpen,
    sourceModel: trainingForm,
    validationSchema: trainingValidationSchema,
    onSubmit: (values) => emit('assign-training', values),
});

const eventTypeIdModel = bindField('eventTypeId');
const dateModel = bindField('date');
const commentModel = bindField('comment');
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-training-assignment-modal' as *;
</style>
