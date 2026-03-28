<template>
    <div class="user-info">
        <template v-if="showProfile">
            <template v-if="profile">
                <section class="user-info__card">
                    <h3 class="h3 user-info__card-title">Личные данные пользователя</h3>
                    <div class="user-info__profile-grid">
                        <section class="user-info__profile-section">
                            <h4 class="user-info__profile-title">Основное</h4>
                            <div class="user-info__profile-photo">
                                <img
                                    v-if="profile.photoUrl"
                                    class="user-info__profile-photo-img"
                                    :src="profile.photoUrl"
                                    :alt="`Фото: ${profile.fullName}`"
                                />
                                <div v-else class="user-info__profile-photo-fallback">
                                    {{ profile.photoFallback }}
                                </div>
                            </div>
                            <dl class="user-info__profile-list">
                                <div class="user-info__profile-item">
                                    <dt>ФИО</dt>
                                    <dd>{{ profile.fullName }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Пол</dt>
                                    <dd>{{ formatGender(profile.gender) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Телефон</dt>
                                    <dd>{{ displayValue(profile.phoneNumber) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Электронная почта</dt>
                                    <dd>{{ displayValue(profile.email) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Дата рождения</dt>
                                    <dd>{{ formatDate(profile.birthDate) }}</dd>
                                </div>
                            </dl>
                        </section>

                        <section class="user-info__profile-section">
                            <h4 class="user-info__profile-title">Работа</h4>
                            <dl class="user-info__profile-list">
                                <div class="user-info__profile-item">
                                    <dt>Компания</dt>
                                    <dd>{{ displayValue(profile.companyName) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Должность</dt>
                                    <dd>{{ displayValue(profile.positionName) }}</dd>
                                </div>
                                <div v-if="canViewSensitiveStaffFields" class="user-info__profile-item">
                                    <dt>Роль</dt>
                                    <dd>{{ displayValue(profile.roleName) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Дата найма</dt>
                                    <dd>{{ formatDate(profile.hireDate) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Место работы</dt>
                                    <dd>{{ displayValue(profile.workplaceRestaurantName) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Подразделение</dt>
                                    <dd>{{ displayValue(profile.restaurantSubdivisionName) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Рестораны</dt>
                                    <dd>{{ profile.restaurantsText }}</dd>
                                </div>
                            </dl>
                        </section>

                        <section class="user-info__profile-section">
                            <h4 class="user-info__profile-title">Финансы</h4>
                            <dl class="user-info__profile-list">
                                <div class="user-info__profile-item">
                                    <dt>Текущая ставка</dt>
                                    <dd>{{ profile.rateHidden ? '$$$' : formatAmount(profile.rate) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Индивидуальная ставка</dt>
                                    <dd>{{ profile.rateHidden ? '$$$' : formatAmount(profile.individualRate) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Ставка должности</dt>
                                    <dd>{{ profile.rateHidden ? '$$$' : formatAmount(profile.positionRate) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Формат оплаты</dt>
                                    <dd>{{ displayValue(profile.paymentFormatName) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Режим расчета</dt>
                                    <dd>{{ formatCalculationMode(profile.paymentCalculationMode) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Часов в смене</dt>
                                    <dd>{{ formatNumber(profile.hoursPerShift) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Норма смен в месяц</dt>
                                    <dd>{{ formatNumber(profile.monthlyShiftNorm) }}</dd>
                                </div>
                            </dl>
                        </section>

                        <section class="user-info__profile-section">
                            <h4 class="user-info__profile-title">Учетные данные</h4>
                            <dl class="user-info__profile-list">
                                <div class="user-info__profile-item">
                                    <dt>Логин</dt>
                                    <dd>{{ displayValue(profile.username) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Табельный номер</dt>
                                    <dd>{{ displayValue(profile.staffCode) }}</dd>
                                </div>
                                <div v-if="canViewSensitiveStaffFields" class="user-info__profile-item">
                                    <dt>Код iiko</dt>
                                    <dd>{{ displayValue(profile.iikoCode) }}</dd>
                                </div>
                                <div v-if="canViewSensitiveStaffFields" class="user-info__profile-item">
                                    <dt>Код сотрудника (Айко)</dt>
                                    <dd>{{ displayValue(profile.iikoId) }}</dd>
                                </div>
                                <div v-if="canViewSensitiveStaffFields" class="user-info__profile-item">
                                    <dt>Согласие на передачу конфиденциальных данных</dt>
                                    <dd>{{ formatBoolean(profile.confidentialDataConsent) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Отпечаток пальца</dt>
                                    <dd>{{ formatBoolean(profile.hasFingerprint) }}</dd>
                                </div>
                                <div class="user-info__profile-item">
                                    <dt>Статус</dt>
                                    <dd>{{ profile.isFired ? 'Уволен' : 'Активен' }}</dd>
                                </div>
                            </dl>
                        </section>
                    </div>
                </section>

                <div class="user-info__actions-row">
                    <section class="user-info__card">
                        <h4 class="user-info__profile-title">Финансы: начисления и удержания</h4>
                        <p class="user-info__inline-note">Период: {{ financeMonthLabel }}</p>
                        <p v-if="payrollLoading" class="user-info__inline-note">Загружаем начисления...</p>
                        <p v-else-if="payrollError" class="user-info__inline-note user-info__inline-note--warning">
                            {{ payrollError }}
                        </p>
                        <dl v-else class="user-info__profile-list">
                            <div class="user-info__profile-item">
                                <dt>Операций в периоде</dt>
                                <dd>{{ financeSummary.entriesCount }}</dd>
                            </div>
                            <div v-for="item in financeSummary.rows" :key="item.key" class="user-info__profile-item">
                                <dt>{{ item.label }}</dt>
                                <dd>{{ formatMoneyWithMask(item.amount, profile.rateHidden) }}</dd>
                            </div>
                        </dl>
                    </section>

                    <section class="user-info__card">
                        <h4 class="user-info__profile-title">Сменить пароль</h4>
                        <form class="user-info__password-form" @submit.prevent="handlePasswordChange">
                            <Input
                                v-model="passwordForm.nextPassword"
                                label="Новый пароль"
                                type="password"
                                autocomplete="new-password"
                            />
                            <Input
                                v-model="passwordForm.confirmPassword"
                                label="Повторите пароль"
                                type="password"
                                autocomplete="new-password"
                            />
                            <Button
                                type="submit"
                                color="primary"
                                :loading="passwordSaving"
                                :disabled="!canSubmitPasswordChange"
                            >
                                Сменить пароль
                            </Button>
                        </form>
                        <p class="user-info__inline-note">
                            Изменение применяется только к вашей учетной записи.
                        </p>
                    </section>

                    <section v-if="canCustomizeInterfaceTheme" class="user-info__card user-info__theme-card">
                        <h3 class="user-info__profile-title">Тема интерфейса</h3>
                        <p class="user-info__theme-note">
                            Настройка сохраняется в вашем аккаунте и не влияет на других сотрудников.
                        </p>
                        <Select
                            :model-value="themeStore.interfaceTheme"
                            label="Текущая тема интерфейса"
                            :options="interfaceThemeOptions"
                            :disabled="themeStore.isSaving"
                            placeholder="Выберите тему"
                            @update:model-value="handleInterfaceThemeChange"
                        />
                        <p class="user-info__theme-hint">
                            Для пользователей без админки всегда используется классическая тема.
                        </p>
                    </section>
                </div>
            </template>
            <section v-else class="user-info__card">
                <h3 class="h3 user-info__card-title">Личные данные пользователя</h3>
                <p class="user-info__empty">Загрузка...</p>
            </section>
        </template>

    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import {
    fetchEmployeeCard,
    fetchPayrollAdjustments,
    updateUser,
    fetchUser,
    updateStaffEmployee,
} from '@/api';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import { useThemeStore } from '@/stores/theme';
import { useUserStore } from '@/stores/user';
import { isSystemLevelRole } from '@/utils/roles';

const props = defineProps({
    section: {
        type: String,
        default: 'all',
    },
});

const userStore = useUserStore();
const themeStore = useThemeStore();
const toast = useToast();

const showProfile = computed(() => props.section === 'all' || props.section === 'profile');
const canCustomizeInterfaceTheme = computed(() => themeStore.canCustomizeInterfaceTheme);
const interfaceThemeOptions = computed(() => themeStore.interfaceThemeOptions);

const canViewSensitiveStaffFields = computed(() => {
    return userStore.hasPermission('system.admin') || isSystemLevelRole(userStore.roleName);
});

const user = ref(null);
const employeeCard = ref(null);
const payrollAdjustments = ref([]);
const payrollLoading = ref(false);
const payrollError = ref('');
const passwordSaving = ref(false);
const passwordForm = reactive({
    nextPassword: '',
    confirmPassword: '',
});

const genderLabels = {
    male: 'Мужской',
    female: 'Женский',
};

const calculationModeLabels = {
    hourly: 'Почасовой',
    fixed: 'Фиксированный',
    shift_norm: 'По норме смен',
};

const financeCategoryOrder = ['advance', 'salary', 'bonus', 'penalty', 'deduction', 'accrual'];

const financeCategoryLabels = {
    advance: 'Аванс',
    salary: 'Зарплата',
    bonus: 'Премии',
    penalty: 'Штрафы',
    deduction: 'Прочие удержания',
    accrual: 'Прочие начисления',
};

const profile = computed(() => {
    const base = user.value || null;
    const card = employeeCard.value || null;
    if (!base && !card) {
        return null;
    }

    const restaurants = Array.isArray(base?.restaurants) ? base.restaurants : [];
    const restaurantNames = restaurants
        .map((restaurant) => restaurant?.name)
        .filter((name) => typeof name === 'string' && name.trim().length);

    const workplaceRestaurantIdRaw = card?.workplace_restaurant_id ?? base?.workplace_restaurant_id;
    const workplaceRestaurantId = Number(workplaceRestaurantIdRaw);
    let workplaceRestaurantName = null;
    if (Number.isFinite(workplaceRestaurantId) && workplaceRestaurantId > 0) {
        workplaceRestaurantName = restaurants.find((restaurant) => Number(restaurant?.id) === workplaceRestaurantId)?.name
            || `Ресторан #${workplaceRestaurantId}`;
    }

    const fullNameParts = [card?.last_name ?? base?.last_name, card?.first_name ?? base?.first_name, card?.middle_name]
        .map((part) => (typeof part === 'string' ? part.trim() : ''))
        .filter(Boolean);
    const fullName = fullNameParts.join(' ') || (card?.username ?? base?.username ?? '');

    const photoFallback = fullNameParts
        .slice(0, 2)
        .map((part) => part.charAt(0).toUpperCase())
        .join('') || 'U';

    return {
        fullName,
        photoUrl: card?.photo_url ?? null,
        photoFallback,
        gender: card?.gender ?? base?.gender ?? null,
        phoneNumber: card?.phone_number ?? null,
        email: card?.email ?? base?.email ?? null,
        birthDate: card?.birth_date ?? null,
        companyName: card?.company_name ?? base?.company?.name ?? null,
        roleName: card?.role_name ?? base?.role?.name ?? null,
        positionName: card?.position_name ?? base?.position?.name ?? null,
        rate: card?.rate ?? null,
        individualRate: card?.individual_rate ?? base?.individual_rate ?? null,
        positionRate: base?.position?.rate ?? null,
        rateHidden: Boolean(card?.rate_hidden),
        hireDate: card?.hire_date ?? null,
        isFired: Boolean(card?.fired ?? base?.fired),
        username: card?.username ?? base?.username ?? null,
        staffCode: card?.staff_code ?? null,
        iikoCode: card?.iiko_code ?? base?.iiko_code ?? null,
        iikoId: card?.iiko_id ?? null,
        confidentialDataConsent: Boolean(card?.confidential_data_consent),
        hasFingerprint: Boolean(card?.has_fingerprint),
        workplaceRestaurantName,
        restaurantSubdivisionName: userStore.restaurantSubdivisionName || null,
        restaurantsText: restaurantNames.length ? restaurantNames.join(', ') : '—',
        paymentFormatName: base?.position?.payment_format?.name ?? null,
        paymentCalculationMode: base?.position?.payment_format?.calculation_mode ?? null,
        hoursPerShift: base?.position?.hours_per_shift ?? null,
        monthlyShiftNorm: base?.position?.monthly_shift_norm ?? null,
    };
});

const financeMonthLabel = computed(() => {
    return new Intl.DateTimeFormat('ru-RU', {
        month: 'long',
        year: 'numeric',
    }).format(new Date());
});

const monthlyPayrollAdjustments = computed(() => {
    return (Array.isArray(payrollAdjustments.value) ? payrollAdjustments.value : []).filter((adjustment) =>
        isCurrentMonth(adjustment?.date),
    );
});

const financeSummary = computed(() => {
    const totals = financeCategoryOrder.reduce((accumulator, key) => {
        accumulator[key] = 0;
        return accumulator;
    }, {});

    monthlyPayrollAdjustments.value.forEach((adjustment) => {
        const amount = Number(adjustment?.amount);
        if (!Number.isFinite(amount)) {
            return;
        }
        const key = resolveFinanceSummaryKey(adjustment);
        totals[key] += Math.abs(amount);
    });

    return {
        entriesCount: monthlyPayrollAdjustments.value.length,
        rows: financeCategoryOrder.map((key) => ({
            key,
            label: financeCategoryLabels[key],
            amount: totals[key] || 0,
        })),
    };
});

const canSubmitPasswordChange = computed(() => {
    if (!userStore.id || passwordSaving.value) {
        return false;
    }
    const nextPassword = String(passwordForm.nextPassword || '');
    const confirmPassword = String(passwordForm.confirmPassword || '');
    return nextPassword.length >= 4 && nextPassword === confirmPassword;
});

const formatGender = (value) => genderLabels[value] ?? '—';

const formatDate = (value) => {
    if (!value) {
        return '—';
    }
    const parsed = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return '—';
    }
    return parsed.toLocaleDateString('ru-RU');
};

const formatAmount = (value) => {
    if (value === null || value === undefined || value === '') {
        return '—';
    }
    const normalized = Number(value);
    if (!Number.isFinite(normalized)) {
        return '—';
    }
    return normalized.toLocaleString('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
};

const formatNumber = (value) => {
    if (value === null || value === undefined || value === '') {
        return '—';
    }
    const normalized = Number(value);
    if (!Number.isFinite(normalized)) {
        return '—';
    }
    return normalized.toLocaleString('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    });
};

const formatCalculationMode = (value) => {
    if (!value) {
        return '—';
    }
    return calculationModeLabels[value] || value;
};

const formatMoneyWithMask = (value, masked = false) => {
    if (masked) {
        return '$$$';
    }
    return formatAmount(value);
};

const formatBoolean = (value) => (value ? 'Да' : 'Нет');

const displayValue = (value) => {
    if (value === null || value === undefined) {
        return '—';
    }
    const text = String(value).trim();
    return text || '—';
};

async function loadUser(userId) {
    const [userResult, cardResult] = await Promise.allSettled([
        fetchUser(userId),
        fetchEmployeeCard(userId),
    ]);

    if (userResult.status === 'fulfilled') {
        user.value = userResult.value;
    }

    if (cardResult.status === 'fulfilled') {
        employeeCard.value = cardResult.value;
    }

    if (userResult.status === 'rejected' && cardResult.status === 'rejected') {
        toast.error('Не удалось загрузить данные пользователя');
    }
}

async function loadPayrollData(userId) {
    payrollLoading.value = true;
    payrollError.value = '';
    try {
        const data = await fetchPayrollAdjustments({ user_id: userId });
        payrollAdjustments.value = Array.isArray(data?.items) ? data.items : [];
    } catch (error) {
        payrollAdjustments.value = [];
        if (error?.response?.status === 403) {
            payrollError.value = 'Нет доступа к финансовой аналитике.';
            return;
        }
        payrollError.value = error?.response?.data?.detail || 'Не удалось загрузить финансовые данные.';
    } finally {
        payrollLoading.value = false;
    }
}

async function handleInterfaceThemeChange(nextTheme) {
    if (!nextTheme || nextTheme === themeStore.interfaceTheme) {
        return;
    }
    const result = await themeStore.saveInterfaceTheme(nextTheme);
    if (!result.ok) {
        toast.error('Не удалось сохранить тему');
    }
}

async function handlePasswordChange() {
    if (!canSubmitPasswordChange.value || !userStore.id) {
        if (String(passwordForm.nextPassword || '').length < 6) {
            toast.error('Пароль должен содержать минимум 6 символов');
            return;
        }
        if (passwordForm.nextPassword !== passwordForm.confirmPassword) {
            toast.error('Пароли не совпадают');
            return;
        }
        return;
    }

    passwordSaving.value = true;
    try {
        try {
            await updateStaffEmployee(userStore.id, { password: passwordForm.nextPassword });
        } catch (error) {
            const status = Number(error?.response?.status || 0);
            if (status === 400 || status === 405 || status === 422) {
                await updateUser(userStore.id, { password: passwordForm.nextPassword });
            } else {
                throw error;
            }
        }
        passwordForm.nextPassword = '';
        passwordForm.confirmPassword = '';
        toast.success('Пароль успешно обновлен');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сменить пароль');
    } finally {
        passwordSaving.value = false;
    }
}

onMounted(async () => {
    const tasks = [];
    if (showProfile.value && userStore.id) {
        tasks.push(loadUser(userStore.id));
        tasks.push(loadPayrollData(userStore.id));
    }
    if (userStore.isAuthenticated && !themeStore.isLoaded) {
        tasks.push(themeStore.bootstrapTheme());
    }
    if (tasks.length) {
        await Promise.allSettled(tasks);
    }
});

function isCurrentMonth(value) {
    if (!value) {
        return false;
    }
    const parsed = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return false;
    }
    const now = new Date();
    return parsed.getFullYear() === now.getFullYear() && parsed.getMonth() === now.getMonth();
}

function containsAnyKeyword(value, keywords) {
    return keywords.some((keyword) => value.includes(keyword));
}

function resolveFinanceSummaryKey(adjustment) {
    const type = adjustment?.adjustment_type ?? null;
    const kind = String(type?.kind || '').trim().toLowerCase();
    const typeName = String(type?.name || '').trim().toLowerCase();
    const comment = String(adjustment?.comment || '').trim().toLowerCase();
    const combined = `${typeName} ${comment}`;

    if (Boolean(type?.is_advance) || containsAnyKeyword(combined, ['аванс', 'advance'])) {
        return 'advance';
    }
    if (containsAnyKeyword(combined, ['зарплат', 'salary'])) {
        return 'salary';
    }
    if (containsAnyKeyword(combined, ['прем', 'bonus'])) {
        return 'bonus';
    }
    if (containsAnyKeyword(combined, ['штраф', 'penalty', 'пеня'])) {
        return 'penalty';
    }
    if (kind === 'deduction') {
        return 'deduction';
    }
    return 'accrual';
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/user-info.scss' as *;
</style>
