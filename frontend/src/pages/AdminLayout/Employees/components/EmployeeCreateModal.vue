<template>
    <Modal v-if="isOpen" class="employees-create-modal" @close="emit('close')">
        <template #header>Создание сотрудника</template>
        <template #default>
            <form class="employees-create-modal__form" @submit.prevent="handleCreateSubmit">
                <section class="employees-create-modal__section">
                    <div class="employees-create-modal__section-header">
                        <h3>Основная информация</h3>
                        <p>Укажите личные данные, по которым мы сможем идентифицировать сотрудника.</p>
                    </div>
                    <div class="employees-create-modal__grid employees-create-modal__grid--two-columns">
                        <div class="employees-create-modal__field">
                            <Input
                                v-model="newEmployee.lastName"
                                label="Фамилия"
                                required
                                :class="{ 'employees-create-modal__field-invalid': isCreateFieldInvalid('lastName') }"
                            />
                            <p v-if="getCreateFieldError('lastName')" class="employees-create-modal__field-error">
                                {{ getCreateFieldError('lastName') }}
                            </p>
                        </div>
                        <div class="employees-create-modal__field">
                            <Input
                                v-model="newEmployee.firstName"
                                label="Имя"
                                required
                                :class="{ 'employees-create-modal__field-invalid': isCreateFieldInvalid('firstName') }"
                            />
                            <p v-if="getCreateFieldError('firstName')" class="employees-create-modal__field-error">
                                {{ getCreateFieldError('firstName') }}
                            </p>
                        </div>
                        <Input v-model="newEmployee.middleName" label="Отчество" />
                        <div class="employees-create-modal__field">
                            <DateInput
                                v-model="newEmployee.birthDate"
                                label="Дата рождения"
                                required
                                :class="{ 'employees-create-modal__field-invalid': isCreateFieldInvalid('birthDate') }"
                            />
                            <p v-if="getCreateFieldError('birthDate')" class="employees-create-modal__field-error">
                                {{ getCreateFieldError('birthDate') }}
                            </p>
                        </div>
                        <Select
                            v-model="newEmployee.gender"
                            label="Пол"
                            :options="genderOptions"
                            placeholder="Выберите пол"
                        />
                        <div class="employees-create-modal__field">
                            <Input
                                v-model="newEmployee.phoneInput"
                                label="Телефон (+7XXXXXXXXXX)"
                                inputmode="tel"
                                maxlength="17"
                                :class="{ 'employees-create-modal__field-invalid': isCreateFieldInvalid('phoneInput') }"
                            />
                            <p v-if="getCreateFieldError('phoneInput')" class="employees-create-modal__field-error">
                                {{ getCreateFieldError('phoneInput') }}
                            </p>
                        </div>
                        <div class="employees-create-modal__field">
                            <Input
                                v-model="newEmployee.email"
                                label="Электронная почта"
                                type="email"
                                inputmode="email"
                                :class="{ 'employees-create-modal__field-invalid': isCreateFieldInvalid('email') }"
                            />
                            <p v-if="getCreateFieldError('email')" class="employees-create-modal__field-error">
                                {{ getCreateFieldError('email') }}
                            </p>
                        </div>
                    </div>
                </section>

                <section class="employees-create-modal__section">
                    <div class="employees-create-modal__section-header">
                        <h3>Рабочие параметры</h3>
                        <p>Заполните данные о должности, ставке и местах работы сотрудника.</p>
                    </div>
                    <div class="employees-create-modal__grid employees-create-modal__grid--two-columns">
                        <Select
                            v-model="newEmployee.positionId"
                            label="Должность"
                            :options="positionOptions"
                            placeholder="Выберите должность"
                        />
                        <Input
                            v-if="!newEmployee.useIndividualRate"
                            v-model="newEmployee.rate" :disabled="!canEditRates"
                            label="Ставка"
                            type="number"
                            step="0.01"
                        />
                        <Input
                            v-if="newEmployee.useIndividualRate"
                            v-model="newEmployee.individualRate" :disabled="!canEditRates"
                            label="Индивидуальная ставка"
                            type="number"
                            step="0.01"
                        />
                        <Checkbox
                            v-model="newEmployee.useIndividualRate"
                            :disabled="!canEditRates"
                            label="Индивидуальная ставка"
                        />
                        <DateInput
                            v-model="newEmployee.hireDate"
                            label="Дата найма (если дата найма отличается от сегодняшней)"
                        />
                        <Checkbox v-model="newEmployee.isCisEmployee" label="Сотрудник СНГ" />
                        <Checkbox v-model="newEmployee.isFormalized" label="Оформлен оф." />
                        <div
                            class="employees-create-modal__field"
                            :class="{ 'employees-create-modal__field-invalid': isCreateFieldInvalid('workplaceRestaurantId') }"
                        >
                            <Select
                                v-model="newEmployee.workplaceRestaurantId"
                                label="Место работы"
                                :options="workplaceRestaurantOptions"
                                placeholder="Не выбрано"
                            />
                            <p v-if="getCreateFieldError('workplaceRestaurantId')" class="employees-create-modal__field-error">
                                {{ getCreateFieldError('workplaceRestaurantId') }}
                            </p>
                        </div>
                        <div ref="restaurantSelectRef" class="employees-create-modal__multiselect">
                            <label class="input-label">Рестораны</label>
                            <div
                                v-if="isSuperAdmin"
                                class="employees-page__checkbox-inline employees-page__checkbox-inline--separate"
                            >
                                <Checkbox
                                    v-model="newEmployee.hasFullRestaurantAccess"
                                    label="Доступ ко всем ресторанам"
                                />
                            </div>
                            <button
                                type="button"
                                class="input-field input-field--select employees-create-modal__multiselect-trigger"
                                :class="{ 'is-disabled': newEmployee.hasFullRestaurantAccess }"
                                :disabled="newEmployee.hasFullRestaurantAccess"
                                :aria-expanded="isRestaurantSelectOpen.toString()"
                                aria-haspopup="listbox"
                                @click="toggleRestaurantSelect"
                                @keydown="handleRestaurantSelectKeydown"
                            >
                                <span
                                    :class="[
                                        'employees-create-modal__multiselect-value',
                                        { 'is-placeholder': !hasRestaurantSelection },
                                    ]"
                                >
                                    {{ restaurantSelectLabel }}
                                </span>
                                <span
                                    :class="[
                                        'employees-create-modal__multiselect-icon',
                                        { 'is-open': isRestaurantSelectOpen },
                                    ]"
                                >
                                    ▾
                                </span>
                            </button>
                            <div
                                v-if="isRestaurantSelectOpen && !newEmployee.hasFullRestaurantAccess"
                                class="employees-create-modal__multiselect-list"
                                role="listbox"
                            >
                                <div class="employees-create-modal__multiselect-options">
                                    <Checkbox
                                        v-for="restaurant in restaurants"
                                        :key="restaurant.id"
                                        :model-value="newEmployee.restaurantIds.includes(restaurant.id)"
                                        :label="restaurant.name"
                                        @update:model-value="(checked) => emit('toggle-restaurant', restaurant.id, checked)"
                                    />
                                    <p v-if="!restaurants.length" class="employees-create-modal__multiselect-empty">
                                        Нет доступных ресторанов
                                    </p>
                                </div>
                            </div>
                        </div>
                        <Input v-if="isSuperAdmin" v-model="newEmployee.iikoCode" label="Код iiko" />
                        <Input v-if="isSuperAdmin" v-model="newEmployee.staffCode" label="Табельный номер" />
                    </div>
                    <div class="employees-create-modal__grid employees-create-modal__grid--two-columns">
                        <Checkbox v-if="canSyncToIiko" v-model="newEmployee.addToIiko" label="Добавить в iiko" />
                        <Checkbox
                            v-if="canViewCredentials"
                            v-model="newEmployee.createInAdmin"
                            label="Создать в админке"
                        />
                    </div>
                </section>

                <section v-if="canViewCredentials && newEmployee.createInAdmin" class="employees-create-modal__section">
                    <div class="employees-create-modal__section-header">
                        <h3>Доступ к системе</h3>
                        <p>Создайте учетные данные, если сотруднику нужен вход в систему.</p>
                    </div>
                    <div class="employees-create-modal__grid employees-create-modal__grid--two-columns">
                        <Input v-model="newEmployee.username" label="Логин" :required="false" />
                        <Input
                            v-model="newEmployee.password"
                            label="Пароль"
                            type="password"
                            :required="false"
                        />
                    </div>
                </section>
            </form>
        </template>
        <template #footer>
            <Button color="ghost" @click="emit('close')">Отмена</Button>
            <Button color="primary" :loading="isCreating" @click="handleCreateSubmit">
                Создать
            </Button>
        </template>
    </Modal>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, toRefs, watch } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { PHONE_FORMAT_ERROR, validatePhoneInput } from '@/utils/phone';

const props = defineProps({
    isOpen: { type: Boolean, default: false },
    newEmployee: { type: Object, required: true },
    genderOptions: { type: Array, default: () => [] },
    positionOptions: { type: Array, default: () => [] },
    workplaceRestaurantOptions: { type: Array, default: () => [] },
    restaurants: { type: Array, default: () => [] },
    isCreating: { type: Boolean, default: false },
    canEditRates: { type: Boolean, default: false },
    isSuperAdmin: { type: Boolean, default: false },
    canViewCredentials: { type: Boolean, default: false },
    canSyncToIiko: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'create', 'toggle-restaurant']);

const {
    isOpen,
    newEmployee,
    genderOptions,
    positionOptions,
    workplaceRestaurantOptions,
    restaurants,
    isCreating,
    canEditRates,
    isSuperAdmin,
    canViewCredentials,
    canSyncToIiko,
} = toRefs(props);

const isRestaurantSelectOpen = ref(false);
const restaurantSelectRef = ref(null);
const isCreateValidationVisible = ref(false);

const selectedRestaurants = computed(() => {
    const ids = Array.isArray(newEmployee.value?.restaurantIds)
        ? new Set(newEmployee.value.restaurantIds.map((id) => Number(id)))
        : new Set();
    return Array.isArray(restaurants.value)
        ? restaurants.value.filter((restaurant) => ids.has(Number(restaurant.id)))
        : [];
});

const hasRestaurantSelection = computed(() =>
    Boolean(newEmployee.value?.hasFullRestaurantAccess) || selectedRestaurants.value.length > 0,
);

const restaurantSelectLabel = computed(() => {
    if (newEmployee.value?.hasFullRestaurantAccess) {
        return 'Все рестораны';
    }
    if (!selectedRestaurants.value.length) {
        return 'Выберите рестораны';
    }
    if (selectedRestaurants.value.length <= 2) {
        return selectedRestaurants.value
            .map((item) => item.name || `Ресторан #${item.id}`)
            .filter(Boolean)
            .join(', ');
    }
    return `Выбрано: ${selectedRestaurants.value.length}`;
});

const createValidationErrors = computed(() => {
    const errors = {};
    const lastName = (newEmployee.value?.lastName || '').trim();
    const firstName = (newEmployee.value?.firstName || '').trim();
    const birthDate = (newEmployee.value?.birthDate || '').trim();
    const workplaceRestaurantId = newEmployee.value?.workplaceRestaurantId;

    if (!lastName) {
        errors.lastName = 'Укажите фамилию.';
    }
    if (!firstName) {
        errors.firstName = 'Укажите имя.';
    }
    if (!birthDate) {
        errors.birthDate = 'Укажите дату рождения.';
    }
    if (
        workplaceRestaurantId === null
        || workplaceRestaurantId === undefined
        || workplaceRestaurantId === ''
    ) {
        errors.workplaceRestaurantId = 'Укажите место работы.';
    } else if (!Number.isFinite(Number(workplaceRestaurantId))) {
        errors.workplaceRestaurantId = 'Выберите корректное место работы.';
    }

    const phoneError = validatePhoneInput(newEmployee.value?.phoneInput, {
        errorMessage: `${PHONE_FORMAT_ERROR}.`
    });
    if (phoneError) {
        errors.phoneInput = phoneError;
    }

    const emailError = validateCreateEmail(newEmployee.value?.email);
    if (emailError) {
        errors.email = emailError;
    }

    return errors;
});

function validateCreateEmail(value) {
    const raw = (value ?? '').toString().trim();
    if (!raw) {
        return '';
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(raw)) {
        return 'Введите корректный email адрес.';
    }

    return '';
}

function getCreateFieldError(fieldName) {
    if (!isCreateValidationVisible.value) {
        return '';
    }
    return createValidationErrors.value[fieldName] || '';
}

function isCreateFieldInvalid(fieldName) {
    return Boolean(getCreateFieldError(fieldName));
}

function handleCreateSubmit() {
    isCreateValidationVisible.value = true;
    if (Object.keys(createValidationErrors.value).length > 0) {
        return;
    }
    emit('create');
}

function toggleRestaurantSelect() {
    if (newEmployee.value?.hasFullRestaurantAccess) {
        return;
    }
    isRestaurantSelectOpen.value = !isRestaurantSelectOpen.value;
}

function closeRestaurantSelect() {
    isRestaurantSelectOpen.value = false;
}

function handleRestaurantSelectKeydown(event) {
    if (event.key === 'Escape') {
        closeRestaurantSelect();
        return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleRestaurantSelect();
    }
}

function handleOutsideClick(event) {
    if (!isRestaurantSelectOpen.value) {
        return;
    }
    const root = restaurantSelectRef.value;
    if (!root || root.contains(event.target)) {
        return;
    }
    closeRestaurantSelect();
}

onMounted(() => {
    document.addEventListener('mousedown', handleOutsideClick);
});

onBeforeUnmount(() => {
    document.removeEventListener('mousedown', handleOutsideClick);
});

watch(
    () => isOpen.value,
    (open) => {
        if (!open) {
            closeRestaurantSelect();
            isCreateValidationVisible.value = false;
        }
    },
);

watch(
    () => newEmployee.value?.hasFullRestaurantAccess,
    (value) => {
        if (value) {
            closeRestaurantSelect();
        }
    },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-create-modal' as *;
</style>
