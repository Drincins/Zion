<template>
    <div class="time-tracking">
        <template v-if="!isFired">
            <div class="time-tracking__profile">
            <div class="time-tracking__user">
                <div class="time-tracking__card">
                    <h1 class="time-tracking__title">{{ greeting }}</h1>
                    <div class="time-tracking__profile-main">
                        <div class="time-tracking__profile-photo">
                            <img v-if="employeePhotoUrl" :src="employeePhotoUrl" alt="Фото сотрудника" />
                            <span v-else class="time-tracking__profile-placeholder">{{ employeeInitials }}</span>
                        </div>
                        <div class="time-tracking__profile-meta">
                            <p v-if="employeePosition" class="time-tracking__profile-role">{{ employeePosition }}</p>
                            <span class="time-tracking__profile-role">{{ employeeRestaurantLabel }}</span>
                        </div>
                    </div>
                    <p class="time-tracking__subtitle">{{ subtitle }}</p>
                    <div v-if="showWaiterTurnoverMetric" class="time-tracking__sales-metric">
                        <p class="time-tracking__sales-metric-label">{{ waiterTurnoverTitle }}</p>
                        <p v-if="waiterTurnoverLoading" class="time-tracking__sales-metric-value">Загрузка...</p>
                        <p v-else-if="waiterTurnoverError" class="time-tracking__sales-metric-value">{{ waiterTurnoverError }}</p>
                        <!-- <p v-else class="time-tracking__sales-metric-value">{{ waiterTurnoverValue }}</p> -->
                    </div>
                    <div v-if="hasOpenShift" class="time-tracking__timer">{{ timer }}</div>
                    <div class="time-tracking__actions">
                        <div v-if="isRestaurantSelectorVisible" class="time-tracking__restaurant-select">
                            <Select
                                v-model="selectedRestaurantId"
                                placeholder="Выбери ресторан"
                                :options="restaurantOptions"
                                :disabled="hasOpenShift || isActionLoading"
                            />
                        </div>
                        <div v-if="isPositionSelectorVisible" class="time-tracking__restaurant-select">
                            <Select
                                v-model="selectedPositionId"
                                placeholder="Выбери должность"
                                :options="positionSelectOptions"
                                :disabled="hasOpenShift || isActionLoading || positionsLoading"
                            />
                        </div>
                        <Button
                            class="time-tracking__action-button"
                            :color="hasOpenShift ? 'danger' : 'primary'"
                            size="lg"
                            block
                            :disabled="actionDisabled"
                            :loading="isActionLoading"
                            @click="handleAction"
                        >
                            {{ actionButtonText }}
                        </Button>
                        <Button
                            class="time-tracking__secondary-button"
                            color="outline"
                            block
                            :disabled="isActionLoading"
                            @click="handleLogout"
                        >
                            Выйти
                        </Button>
                    </div>
                </div>
                <div class="time-tracking__history">
                    <h2 class="time-tracking__history-title">Смены в этом месяце</h2>
                    <div v-if="isHistoryLoading" class="time-tracking__history-message">Загружаем список смен…</div>
                    <div v-else-if="attendanceRows.length" class="time-tracking__history-content">
                        <div v-if="attendanceTotalsSummary.hasData" class="time-tracking__totals">
                            <div class="time-tracking__totals-item">
                                <span class="time-tracking__totals-label">Итого часов</span>
                                <span class="time-tracking__totals-value">{{ attendanceTotalsSummary.totalDuration }}</span>
                            </div>
                            <div class="time-tracking__totals-item">
                                <span class="time-tracking__totals-label">Ночные часы</span>
                                <span class="time-tracking__totals-value">{{ attendanceTotalsSummary.nightDuration }}</span>
                            </div>
                        </div>
                        <div class="time-tracking__table-wrapper">
                            <table class="time-tracking__table">
                                <thead>
                                    <tr>
                                        <th>Дата</th>
                                        <th>Приход</th>
                                        <th>Уход</th>
                                        <th>Должность</th>
                                        <th>Ресторан</th>
                                        <th>Часы</th>
                                        <th>Ночные часы</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="attendance in attendanceRows" :key="attendance.id">
                                        <td>{{ attendance.date }}</td>
                                        <td>{{ attendance.start }}</td>
                                        <td>{{ attendance.end }}</td>
                                        <td>{{ attendance.position }}</td>
                                        <td>{{ attendance.restaurant }}</td>
                                        <td>{{ attendance.duration }}</td>
                                        <td>{{ attendance.nightDuration }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <p v-else class="time-tracking__history-message">В этом месяце ещё не было смен.</p>
                </div>
            </div>
        </div>
        <div class="time-tracking__profile">
            <div class="time-tracking__documents">
                <div v-if="hasBirthdayBlock" class="time-tracking__birthdays">
                    <p v-if="birthdaysLoading" class="time-tracking__birthday-message">Ищем именинников…</p>
                    <p
                        v-else-if="birthdaysError"
                        class="time-tracking__birthday-message time-tracking__birthday-message--error"
                    >
                        {{ birthdaysError }}
                    </p>
                    <template v-else>
                        <div v-if="birthdaysToday.length" class="time-tracking__birthday-section">
                            <p class="time-tracking__birthday-heading">Сегодня день рождения</p>
                            <ul class="time-tracking__birthday-list">
                                <li v-for="person in birthdaysToday" :key="person.id" class="time-tracking__birthday-item">
                                    <div class="time-tracking__birthday-main">
                                        <span class="time-tracking__birthday-name">{{ person.name }}</span>
                                        <span class="time-tracking__birthday-meta">{{ person.position }}</span>
                                    </div>
                                    <span class="time-tracking__birthday-date">{{ person.formattedDate }}</span>
                                </li>
                            </ul>
                        </div>
                        <div v-if="birthdaysTomorrow.length" class="time-tracking__birthday-section">
                            <p class="time-tracking__birthday-heading">Завтра день рождения</p>
                            <ul class="time-tracking__birthday-list">
                                <li v-for="person in birthdaysTomorrow" :key="person.id" class="time-tracking__birthday-item">
                                    <div class="time-tracking__birthday-main">
                                        <span class="time-tracking__birthday-name">{{ person.name }}</span>
                                        <span class="time-tracking__birthday-meta">{{ person.position }}</span>
                                    </div>
                                    <span class="time-tracking__birthday-date">{{ person.formattedDate }}</span>
                                </li>
                            </ul>
                        </div>
                    </template>
                </div>
                <section class="time-tracking__document-card">
                    <header class="time-tracking__document-header">
                        <div>
                            <h3 class="time-tracking__document-title">Медкнижка</h3>
                            <p class="time-tracking__document-subtitle">Актуальные медосмотры</p>
                        </div>
                        <div class="time-tracking__document-header-actions">
                            <div v-if="medicalHasAlerts" class="time-tracking__document-counters">
                                <span
                                    v-if="medicalStatusCounts.expiring"
                                    class="time-tracking__document-chip time-tracking__document-chip--warning"
                                >
                                    Скоро истекает: {{ medicalStatusCounts.expiring }}
                                </span>
                                <span
                                    v-if="medicalStatusCounts.expired"
                                    class="time-tracking__document-chip time-tracking__document-chip--danger"
                                >
                                    Просрочено: {{ medicalStatusCounts.expired }}
                                </span>
                                <span
                                    v-if="medicalStatusCounts.unknown"
                                    class="time-tracking__document-chip time-tracking__document-chip--muted"
                                >
                                    Неизвестно: {{ medicalStatusCounts.unknown }}
                                </span>
                            </div>
                            <button
                                v-if="medicalHasAlerts"
                                type="button"
                                class="time-tracking__document-toggle"
                                :aria-expanded="medicalExpanded"
                                @click="toggleMedicalExpanded"
                            >
                                <span>{{ medicalExpanded ? 'Свернуть' : 'Показать' }}</span>
                                <span
                                    :class="[
                                        'time-tracking__document-toggle-icon',
                                        { 'time-tracking__document-toggle-icon--open': medicalExpanded },
                                    ]"
                                >
                                    ▾
                                </span>
                            </button>
                        </div>
                    </header>
                    <div v-if="employeeCardLoading" class="time-tracking__document-message">
                        Загружаем документы…
                    </div>
                    <div
                        v-else-if="employeeCardError"
                        class="time-tracking__document-message time-tracking__document-message--error"
                    >
                        {{ employeeCardError }}
                    </div>
                    <div v-else>
                        <template v-if="medicalHasAlerts">
                            <Transition
                                @enter="onCollapseEnter"
                                @after-enter="onCollapseAfterEnter"
                                @leave="onCollapseLeave"
                                @after-leave="onCollapseAfterLeave"
                            >
                                <div v-if="medicalExpanded" class="time-tracking__document-list time-tracking__document-list--collapsible">
                                    <article
                                        v-for="record in medicalAlertRecords"
                                        :key="record.id"
                                        class="time-tracking__document-item"
                                    >
                                        <div class="time-tracking__document-main">
                                            <p class="time-tracking__document-name">
                                                {{ record.medical_check_type?.name || 'Осмотр' }}
                                            </p>
                                            <p class="time-tracking__document-meta">
                                                Пройдено: {{ formatDocumentDate(record.passed_at) }}
                                                <br>
                                                След. дата: {{ formatDocumentDate(record.next_due_at) }}
                                            </p>
                                        </div>
                                        <span :class="['time-tracking__status-pill', statusClass(record.status)]">
                                            {{ statusLabel(record.status) }}
                                        </span>
                                    </article>
                                </div>
                            </Transition>
                        </template>
                        <p
                            v-else-if="medicalShowAllValid"
                            class="time-tracking__document-message time-tracking__document-message--success"
                        >
                            Всё действительно
                        </p>
                        <p v-else-if="!medicalRecords.length" class="time-tracking__document-message">
                            Записей медкнижки пока нет.
                        </p>
                    </div>
                </section>
                <section v-if="showCisDocuments" class="time-tracking__document-card">
                    <header class="time-tracking__document-header">
                        <div>
                            <h3 class="time-tracking__document-title">Документы СНГ</h3>
                            <p class="time-tracking__document-subtitle">Разрешения и подтверждения</p>
                        </div>
                        <div class="time-tracking__document-header-actions">
                            <div v-if="cisHasAlerts" class="time-tracking__document-counters">
                                <span
                                    v-if="cisStatusCounts.expiring"
                                    class="time-tracking__document-chip time-tracking__document-chip--warning"
                                >
                                    Скоро истекает: {{ cisStatusCounts.expiring }}
                                </span>
                                <span
                                    v-if="cisStatusCounts.expired"
                                    class="time-tracking__document-chip time-tracking__document-chip--danger"
                                >
                                    Просрочено: {{ cisStatusCounts.expired }}
                                </span>
                                <span
                                    v-if="cisStatusCounts.unknown"
                                    class="time-tracking__document-chip time-tracking__document-chip--muted"
                                >
                                    Неизвестно: {{ cisStatusCounts.unknown }}
                                </span>
                            </div>
                            <button
                                v-if="cisHasAlerts"
                                type="button"
                                class="time-tracking__document-toggle"
                                :aria-expanded="cisExpanded"
                                @click="toggleCisExpanded"
                            >
                                <span>{{ cisExpanded ? 'Свернуть' : 'Показать' }}</span>
                                <span
                                    :class="[
                                        'time-tracking__document-toggle-icon',
                                        { 'time-tracking__document-toggle-icon--open': cisExpanded },
                                    ]"
                                >
                                    ▾
                                </span>
                            </button>
                        </div>
                    </header>
                    <div v-if="employeeCardLoading" class="time-tracking__document-message">
                        Загружаем документы…
                    </div>
                    <div
                        v-else-if="employeeCardError"
                        class="time-tracking__document-message time-tracking__document-message--error"
                    >
                        {{ employeeCardError }}
                    </div>
                    <div v-else>
                        <template v-if="cisHasAlerts">
                            <Transition
                                @enter="onCollapseEnter"
                                @after-enter="onCollapseAfterEnter"
                                @leave="onCollapseLeave"
                                @after-leave="onCollapseAfterLeave"
                            >
                                <div v-if="cisExpanded" class="time-tracking__document-list time-tracking__document-list--collapsible">
                                    <article
                                        v-for="record in cisAlertRecords"
                                        :key="record.id"
                                        class="time-tracking__document-item"
                                    >
                                        <div class="time-tracking__document-main">
                                            <p class="time-tracking__document-name">
                                                {{ record.cis_document_type?.name || 'Документ' }}
                                                <span v-if="record.number" class="time-tracking__document-number">
                                                    № {{ record.number }}
                                                </span>
                                            </p>
                                            <p class="time-tracking__document-meta">
                                                Действует до: {{ formatDocumentDate(record.expires_at) }}
                                                <br>
                                                Выдан: {{ formatDocumentDate(record.issued_at) }}
                                            </p>
                                            <p v-if="record.issuer" class="time-tracking__document-meta">
                                                Орган: {{ record.issuer }}
                                            </p>
                                        </div>
                                        <div class="time-tracking__document-side">
                                            <span :class="['time-tracking__status-pill', statusClass(record.status)]">
                                                {{ statusLabel(record.status) }}
                                            </span>
                                            <a
                                                v-if="record.attachment_url"
                                                class="time-tracking__document-link"
                                                :href="record.attachment_url"
                                                target="_blank"
                                                rel="noopener"
                                            >
                                                Файл
                                            </a>
                                        </div>
                                    </article>
                                </div>
                            </Transition>
                        </template>
                        <p
                            v-else-if="cisShowAllValid"
                            class="time-tracking__document-message time-tracking__document-message--success"
                        >
                            Всё действительно
                        </p>
                        <p v-else-if="!cisDocuments.length" class="time-tracking__document-message">
                            Документы СНГ не найдены.
                        </p>
                    </div>
                </section>
            </div>
            </div>
        </template>
        <template v-else>
            <div class="time-tracking__blocked">
                <p class="time-tracking__blocked-text">Доступ запрещен, вы уволены</p>
            </div>
        </template>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import {
    closeStaffAttendance,
    fetchStaffAttendancesMonth,
    openStaffAttendance,
    fetchRestaurants,
    fetchEmployees,
    fetchEmployeeCard,
    fetchStaffPositions,
    fetchStaffWaiterTurnoverMetric,
} from '@/api';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import Select from '@/components/UI-components/Select.vue';

const router = useRouter();
const toast = useToast();
const userStore = useUserStore();
const isFired = computed(() => userStore.isFired);

const isLoading = ref(false);
const isActionLoading = ref(false);
const currentAttendance = ref(null);
const attendances = ref([]);
const employees = ref([]);
const employeeCard = ref(null);
const employeeCardLoading = ref(false);
const employeeCardError = ref('');
const waiterTurnover = ref(null);
const waiterTurnoverLoading = ref(false);
const waiterTurnoverError = ref('');
const timer = ref('00:00:00');
const birthdaysLoading = ref(false);
const birthdaysError = ref('');
const restaurants = ref([]);
const selectedRestaurantId = ref(null);
const positionOptions = ref([]);
const positionsLoading = ref(false);
const selectedPositionId = ref(null);
const medicalExpanded = ref(false);
const cisExpanded = ref(false);

let timerInterval = null;

const userName = computed(() => {
    return userStore.fullName || userStore.firstName || userStore.login || '';
});

const employeeDisplayName = computed(() => {
    const card = employeeCard.value;
    const parts = [card?.last_name, card?.first_name, card?.middle_name].filter(Boolean);
    if (parts.length) {
        return parts.join(' ');
    }
    return userStore.fullName || userStore.firstName || userStore.login || 'Сотрудник';
});

const employeeInitials = computed(() => {
    const name = employeeDisplayName.value || '';
    const parts = name.split(' ').filter(Boolean);
    const letters = parts.slice(0, 2).map((part) => part[0]).join('');
    return letters || '?';
});

const employeePosition = computed(() => {
    return employeeCard.value?.position_name || userStore.positionName || '';
});

const employeePhotoUrl = computed(() => employeeCard.value?.photo_url || '');

const employeeRestaurantName = computed(() => {
    const attendance = currentAttendance.value;
    if (attendance?.restaurant_name) {
        return attendance.restaurant_name;
    }
    if (attendance?.restaurant_id !== null && attendance?.restaurant_id !== undefined) {
        return `Ресторан #${attendance.restaurant_id}`;
    }

    const workplaceId = userStore.workplaceRestaurantId;
    if (workplaceId) {
        const match = restaurants.value.find((restaurant) => Number(restaurant?.id) === Number(workplaceId));
        if (match?.name) {
            return match.name;
        }
        return `Ресторан #${workplaceId}`;
    }

    if (userStore.restaurantSubdivisionName) {
        return userStore.restaurantSubdivisionName;
    }

    if (restaurants.value.length === 1 && restaurants.value[0]?.name) {
        return restaurants.value[0].name;
    }

    return '—';
});

const employeeRestaurantLabel = computed(() => {
    const name = employeeRestaurantName.value;
    if (!name || name === '—') {
        return 'Ресторан не указан';
    }
    return `Ресторан: ${name}`;
});

const medicalRecords = computed(() =>
    Array.isArray(employeeCard.value?.medical_checks) ? employeeCard.value.medical_checks : [],
);

const cisDocuments = computed(() =>
    Array.isArray(employeeCard.value?.cis_documents) ? employeeCard.value.cis_documents : [],
);

const isCisEmployee = computed(() => Boolean(employeeCard.value?.is_cis_employee));

const showCisDocuments = computed(() => isCisEmployee.value || cisDocuments.value.length > 0);

const medicalStatusCounts = computed(() => countStatuses(medicalRecords.value));
const cisStatusCounts = computed(() => countStatuses(cisDocuments.value));
const medicalAlertRecords = computed(() => filterAlertRecords(medicalRecords.value));
const cisAlertRecords = computed(() => filterAlertRecords(cisDocuments.value));
const medicalHasAlerts = computed(() => medicalAlertRecords.value.length > 0);
const cisHasAlerts = computed(() => cisAlertRecords.value.length > 0);
const medicalShowAllValid = computed(() => medicalRecords.value.length > 0 && !medicalHasAlerts.value);
const cisShowAllValid = computed(() => cisDocuments.value.length > 0 && !cisHasAlerts.value);

const greeting = computed(() => {
    const name = userName.value;
    return name ? `Привет, ${name}!` : 'Добро пожаловать!';
});

const hasOpenShift = computed(() => {
    return Boolean(currentAttendance.value) && !currentAttendance.value.close_time;
});

const subtitle = computed(() => {
    if (isLoading.value) {
        return 'Загружаем информацию о вашей смене…';
    }
    if (hasOpenShift.value) {
        return 'Ваша смена активна. Не забудьте завершить её по окончании работы.';
    }
    return 'Вы можете начать смену, когда будете готовы.';
});

const showWaiterTurnoverMetric = computed(
    () => waiterTurnoverLoading.value || Boolean(waiterTurnoverError.value) || Boolean(waiterTurnover.value?.enabled),
);

const waiterTurnoverTitle = computed(() => {
    const mode = waiterTurnover.value?.amount_mode;
    if (mode === 'discount_only') {
        return 'Мои скидки за период';
    }
    if (mode === 'sum_with_discount') {
        return 'Мой оборот со скидкой';
    }
    return 'Мой оборот без скидки';
});

const actionLabel = computed(() => (hasOpenShift.value ? 'Завершить смену' : 'Начать смену'));

const actionButtonText = computed(() => {
    if (isActionLoading.value) {
        return hasOpenShift.value ? 'Завершаем…' : 'Запускаем…';
    }
    return actionLabel.value;
});

const requiresRestaurantSelection = computed(() => restaurants.value.length > 1);

const isRestaurantSelected = computed(() => Boolean(selectedRestaurantId.value));

const actionDisabled = computed(() => {
    const requiresSelection = requiresRestaurantSelection.value;
    const selectionMissing = requiresSelection && !isRestaurantSelected.value && !hasOpenShift.value;
    const positionRequired = isMultiSubdivision.value && !hasOpenShift.value && positionSelectOptions.value.length > 0;
    const positionMissing = positionRequired && !isPositionSelected.value;
    return !userStore.token || isLoading.value || isActionLoading.value || selectionMissing || positionMissing;
});

const isHistoryLoading = computed(() => {
    return isLoading.value && attendances.value.length === 0;
});

const restaurantOptions = computed(() =>
    restaurants.value.map((restaurant) => ({
        value: String(restaurant.id),
        label: restaurant.name ?? `Ресторан #${restaurant.id}`,
    })),
);

const isRestaurantSelectorVisible = computed(() => restaurants.value.length > 1);
const isMultiSubdivision = computed(() => Boolean(userStore.restaurantSubdivisionIsMulti));
const positionSelectOptions = computed(() =>
    positionOptions.value.map((pos) => ({
        value: String(pos.id),
        label: pos.name || `Должность #${pos.id}`,
    })),
);
const isPositionSelectorVisible = computed(() => isMultiSubdivision.value && !hasOpenShift.value);
const isPositionSelected = computed(() => Boolean(selectedPositionId.value));

const attendanceRows = computed(() => {
    return [...attendances.value]
        .sort((a, b) => {
            const aDate = parseAttendanceDateTime(a.open_date, a.open_time);
            const bDate = parseAttendanceDateTime(b.open_date, b.open_time);

            const aTime = aDate ? aDate.getTime() : -Infinity;
            const bTime = bDate ? bDate.getTime() : -Infinity;

            return bTime - aTime;
        })
        .map((attendance) => ({
            id: attendance.id ?? `${attendance.open_date ?? 'open'}-${attendance.open_time ?? 'time'}`,
            date: formatDateDisplay(attendance.open_date),
            start: formatTimeDisplay(attendance.open_time),
            end: formatTimeDisplay(attendance.close_time),
            position: attendance.position_name || '—',
            restaurant: formatRestaurantName(attendance),
            duration: formatDurationHHMM(attendance.duration_minutes),
            nightDuration: formatDurationHHMM(attendance.night_minutes),
        }));
});

const attendanceTotals = computed(() => {
    const items = Array.isArray(attendances.value) ? attendances.value : [];
    const totals = items.reduce(
        (acc, attendance) => {
            const duration = Number(attendance?.duration_minutes);
            if (Number.isFinite(duration)) {
                acc.totalMinutes += duration;
            }

            const night = Number(attendance?.night_minutes);
            if (Number.isFinite(night)) {
                acc.nightMinutes += night;
            }

            return acc;
        },
        { totalMinutes: 0, nightMinutes: 0 },
    );

    return {
        hasData: items.length > 0,
        totalMinutes: totals.totalMinutes,
        nightMinutes: totals.nightMinutes,
    };
});

const attendanceTotalsSummary = computed(() => {
    const totals = attendanceTotals.value;
    if (!totals.hasData) {
        return {
            hasData: false,
            totalDuration: '-',
            nightDuration: '-',
        };
    }

    return {
        hasData: true,
        totalDuration: formatDurationHHMM(totals.totalMinutes),
        nightDuration: formatDurationHHMM(totals.nightMinutes),
    };
});

const birthdayEntries = computed(() =>
    employees.value
        .map((employee) => {
            const birthDate = parseBirthDate(employee?.birth_date);
            if (!birthDate) return null;

            return {
                id: employee.id,
                name: formatFullName(employee),
                position: employee.position_name || '—',
                birthDate,
                formattedDate: formatBirthdayDate(birthDate),
                daysUntil: daysUntilBirthday(birthDate),
            };
        })
        .filter(Boolean),
);

const birthdaysToday = computed(() => birthdayEntries.value.filter((item) => item.daysUntil === 0));

const birthdaysTomorrow = computed(() =>
    birthdayEntries.value
        .filter((item) => item.daysUntil === 1)
        .sort((a, b) => a.birthDate.getDate() - b.birthDate.getDate()),
);

const hasBirthdayBlock = computed(
    () =>
        birthdaysLoading.value ||
        Boolean(birthdaysError.value) ||
        birthdaysToday.value.length > 0 ||
        birthdaysTomorrow.value.length > 0,
);

const statusLabels = {
    ok: 'Действителен',
    expiring: 'Скоро истекает',
    expired: 'Просрочено',
    unknown: 'Неизвестно',
};

const statusClasses = {
    ok: 'time-tracking__status-pill--success',
    expiring: 'time-tracking__status-pill--warning',
    expired: 'time-tracking__status-pill--danger',
    unknown: 'time-tracking__status-pill--muted',
};

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function resetTimer() {
    stopTimer();
    timer.value = '00:00:00';
}

function parseAttendanceDateTime(dateString, timeString) {
    if (!dateString) {
        return null;
    }

    const explicitOffset = /([zZ]|[+-]\d{2}:?\d{2})$/.test(timeString || '');
    if (explicitOffset) {
        const parsed = new Date(`${dateString}T${timeString}`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    }

    const [yearStr, monthStr, dayStr] = dateString.split('-');
    const year = Number(yearStr);
    const month = Number(monthStr) - 1;
    const day = Number(dayStr);
    if (![year, month, day].every(Number.isFinite)) {
        return null;
    }

    let hours = 0;
    let minutes = 0;
    let seconds = 0;

    if (timeString && typeof timeString === 'string') {
        const match = timeString.match(/(\d{1,2}):(\d{2})(?::(\d{2}))?/);
        if (match) {
            hours = Number(match[1]);
            minutes = Number(match[2]);
            seconds = match[3] ? Number(match[3]) : 0;
        }
    }

    const parsedLocal = new Date(year, month, day, hours, minutes, seconds);
    return Number.isNaN(parsedLocal.getTime()) ? null : parsedLocal;
}

function formatDocumentDate(value) {
    if (!value) {
        return '—';
    }
    const [year, month, day] = String(value).slice(0, 10).split('-');
    if (!year || !month || !day) {
        return '—';
    }
    return `${day.padStart(2, '0')}.${month.padStart(2, '0')}.${year}`;
}

function normalizeStatus(value) {
    if (!value || typeof value !== 'string') {
        return 'unknown';
    }
    const normalized = value.trim().toLowerCase();
    return normalized && normalized in statusLabels ? normalized : 'unknown';
}

function statusLabel(value) {
    return statusLabels[normalizeStatus(value)];
}

function statusClass(value) {
    return statusClasses[normalizeStatus(value)];
}

function countStatuses(records) {
    const counts = {
        ok: 0,
        expiring: 0,
        expired: 0,
        unknown: 0,
    };
    const items = Array.isArray(records) ? records : [];
    items.forEach((record) => {
        const status = normalizeStatus(record?.status);
        counts[status] = (counts[status] ?? 0) + 1;
    });
    return counts;
}

function filterAlertRecords(records) {
    const items = Array.isArray(records) ? records : [];
    return items.filter((record) => normalizeStatus(record?.status) !== 'ok');
}

function onCollapseEnter(el) {
    el.style.overflow = 'hidden';
    el.style.height = '0';
    el.style.opacity = '0';
    el.style.transform = 'translateY(-6px)';
    requestAnimationFrame(() => {
        el.style.height = `${el.scrollHeight}px`;
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
    });
}

function onCollapseAfterEnter(el) {
    el.style.height = '';
    el.style.opacity = '';
    el.style.transform = '';
    el.style.overflow = '';
}

function onCollapseLeave(el) {
    el.style.overflow = 'hidden';
    el.style.height = `${el.scrollHeight}px`;
    el.style.opacity = '1';
    el.style.transform = 'translateY(0)';
    requestAnimationFrame(() => {
        el.style.height = '0';
        el.style.opacity = '0';
        el.style.transform = 'translateY(-6px)';
    });
}

function onCollapseAfterLeave(el) {
    el.style.height = '';
    el.style.opacity = '';
    el.style.transform = '';
    el.style.overflow = '';
}

function toggleMedicalExpanded() {
    if (!medicalHasAlerts.value) {
        return;
    }
    medicalExpanded.value = !medicalExpanded.value;
}

function toggleCisExpanded() {
    if (!cisHasAlerts.value) {
        return;
    }
    cisExpanded.value = !cisExpanded.value;
}

function updateTimer() {
    if (!hasOpenShift.value) {
        return;
    }

    const attendance = currentAttendance.value;
    const openedAt = parseAttendanceDateTime(attendance.open_date, attendance.open_time);

    if (!openedAt || Number.isNaN(openedAt.getTime())) {
        timer.value = '00:00:00';
        return;
    }

    const diffMs = Date.now() - openedAt.getTime();
    if (diffMs < 0) {
        timer.value = '00:00:00';
        return;
    }

    const hours = Math.floor(diffMs / 3600000);
    const minutes = Math.floor((diffMs % 3600000) / 60000);
    const seconds = Math.floor((diffMs % 60000) / 1000);

    const parts = [hours, minutes, seconds]
        .map((value) => String(value).padStart(2, '0'))
        .join(':');

    timer.value = parts;
}

function startTimer() {
    stopTimer();
    updateTimer();
    timerInterval = setInterval(updateTimer, 1000);
}

function setAttendance(attendance) {
    currentAttendance.value = attendance;
    updateSelectedRestaurantFromAttendance(attendance);
    updateSelectedPositionFromAttendance(attendance);
    selectDefaultRestaurant();
    selectDefaultPosition();
    if (attendance && !attendance.close_time) {
        timer.value = '00:00:00';
        startTimer();
    } else {
        resetTimer();
    }
}

function selectDefaultRestaurant() {
    if (selectedRestaurantId.value || !restaurants.value.length) {
        return;
    }

    if (restaurants.value.length === 1) {
        selectedRestaurantId.value = String(restaurants.value[0].id);
    }
}

function updateSelectedRestaurantFromAttendance(attendance) {
    if (!attendance || !attendance.restaurant_id) {
        return;
    }

    const restaurantId = Number(attendance.restaurant_id);
    if (!Number.isFinite(restaurantId)) {
        return;
    }

    selectedRestaurantId.value = String(restaurantId);

    const hasRestaurantInList = restaurants.value.some(
        (restaurant) => Number(restaurant?.id) === restaurantId,
    );

    if (!hasRestaurantInList) {
        restaurants.value = [
            { id: restaurantId, name: `Ресторан #${restaurantId}` },
            ...restaurants.value,
        ];
    }
}

function updateSelectedPositionFromAttendance(attendance) {
    if (!attendance || attendance.position_id === null || attendance.position_id === undefined) {
        return;
    }
    const pid = Number(attendance.position_id);
    if (!Number.isFinite(pid)) {
        return;
    }
    selectedPositionId.value = String(pid);
}

function selectDefaultPosition() {
    if (!isMultiSubdivision.value || hasOpenShift.value) {
        return;
    }
    if (selectedPositionId.value && positionSelectOptions.value.some((opt) => opt.value === String(selectedPositionId.value))) {
        return;
    }
    if (userStore.positionId) {
        const match = positionSelectOptions.value.find((opt) => Number(opt.value) === Number(userStore.positionId));
        if (match) {
            selectedPositionId.value = String(match.value);
            return;
        }
    }
    if (positionSelectOptions.value.length) {
        selectedPositionId.value = positionSelectOptions.value[0].value;
    }
}

function formatDateDisplay(dateString) {
    if (!dateString || typeof dateString !== 'string') {
        return '—';
    }
    const parts = dateString.split('-');
    if (parts.length !== 3) {
        return dateString;
    }
    const [year, month, day] = parts;
    if (!year || !month || !day) {
        return dateString;
    }
    return `${day.padStart(2, '0')}.${month.padStart(2, '0')}.${year}`;
}

function formatTimeDisplay(timeString) {
    if (!timeString || typeof timeString !== 'string') {
        return '—';
    }

    const match = timeString.match(/(\d{1,2}):(\d{2})/);
    if (!match) {
        return timeString;
    }

    const [, hours, minutes] = match;
    return `${hours.padStart(2, '0')}:${minutes}`;
}

function formatDurationHHMM(minutes) {
    if (typeof minutes !== 'number' || Number.isNaN(minutes)) {
        return '—';
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
}

function formatRestaurantName(attendance) {
    if (!attendance) {
        return '—';
    }
    if (attendance.restaurant_name) {
        return attendance.restaurant_name;
    }
    const restaurantId = attendance.restaurant_id;
    if (restaurantId === null || restaurantId === undefined) {
        return '—';
    }
    return `Ресторан #${restaurantId}`;
}

function formatDuration(minutes) {
    if (typeof minutes !== 'number' || Number.isNaN(minutes)) {
        return null;
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours && mins) {
        return `${hours} ч ${mins} мин`;
    }
    if (hours) {
        return `${hours} ч`;
    }
    return `${mins} мин`;
}

function parseBirthDate(value) {
    if (!value) return null;
    const [year, month, day] = value.split('-').map(Number);
    if (!year || !month || !day) return null;
    return new Date(year, month - 1, day);
}

function formatFullName(employee) {
    if (!employee) return '—';
    const parts = [employee.last_name, employee.first_name, employee.middle_name].filter(Boolean);
    return parts.length ? parts.join(' ') : employee.username;
}

function formatBirthdayDate(date) {
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long' });
}

function daysUntilBirthday(birthDate) {
    const today = new Date();
    const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const target = new Date(today.getFullYear(), birthDate.getMonth(), birthDate.getDate());
    if (target < todayStart) {
        target.setFullYear(target.getFullYear() + 1);
    }

    const diffMs = target.getTime() - todayStart.getTime();
    return Math.round(diffMs / 86400000);
}

function handleApiError(error, fallbackMessage) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    if (status === 403 && userStore.setFiredFromDetail(detail)) {
        setAttendance(null);
        attendances.value = [];
        return;
    }
    if (status === 401 || status === 403) {
        toast.error(detail || 'Сессия истекла. Авторизуйтесь снова.');
        setAttendance(null);
        attendances.value = [];
        userStore.logout();
        router.replace({ name: 'user-login' });
        return;
    }

    if (detail) {
        toast.error(detail);
        return;
    }

    if (fallbackMessage) {
        toast.error(fallbackMessage);
    }
    console.error(error);
}

async function fetchCurrentAttendance(options = {}) {
    if (!userStore.token) {
        return;
    }

    const { showLoader = true } = options;

    if (showLoader) {
        isLoading.value = true;
    }

    try {
        const data = await fetchStaffAttendancesMonth();
        const items = Array.isArray(data.items) ? data.items : [];
        attendances.value = items;
        const openAttendance = items.find((item) => !item.close_time) ?? null;
        setAttendance(openAttendance);
    } catch (error) {
        handleApiError(error, 'Не удалось загрузить данные смены');
    } finally {
        if (showLoader) {
            isLoading.value = false;
        }
    }
}

async function fetchAvailableRestaurants() {
    if (!userStore.token) {
        return;
    }

    try {
        const data = await fetchRestaurants();
        const items = Array.isArray(data) ? data : [];
        const allowedIds = Array.isArray(userStore.restaurantIds) && userStore.restaurantIds.length
            ? new Set(userStore.restaurantIds.map((id) => Number(id)).filter((id) => Number.isFinite(id)))
            : null;

        const normalized = allowedIds
            ? items.filter((restaurant) => allowedIds.has(Number(restaurant?.id)))
            : items;

        restaurants.value = normalized;
        selectDefaultRestaurant();
    } catch (error) {
        restaurants.value = [];
        handleApiError(error, 'Не удалось загрузить список ресторанов');
    }
}

async function fetchAvailablePositions() {
    if (!userStore.token || !isMultiSubdivision.value) {
        positionOptions.value = [];
        selectedPositionId.value = null;
        return;
    }
    positionsLoading.value = true;
    try {
        const data = await fetchStaffPositions();
        const items = Array.isArray(data) ? data : [];
        positionOptions.value = items;
        selectDefaultPosition();
    } catch (error) {
        positionOptions.value = [];
        handleApiError(error, 'Не удалось загрузить список должностей');
    } finally {
        positionsLoading.value = false;
    }
}

async function fetchEmployeeBirthdays() {
    if (!userStore.token) {
        return;
    }

    birthdaysLoading.value = true;
    birthdaysError.value = '';

    try {
        const { items } = await fetchEmployees({ limit: 500 });
        employees.value = items ?? [];
    } catch (error) {
        employees.value = [];
        const status = error?.response?.status;
        if (status === 403) {
            birthdaysError.value = '';
            return;
        }
        birthdaysError.value = error?.response?.data?.detail || 'Не удалось загрузить дни рождения.';
        handleApiError(error, birthdaysError.value);
    } finally {
        birthdaysLoading.value = false;
    }
}

async function fetchEmployeeCardData() {
    if (!userStore.token || !userStore.id) {
        return;
    }

    employeeCardLoading.value = true;
    employeeCardError.value = '';

    try {
        employeeCard.value = await fetchEmployeeCard(userStore.id);
    } catch (error) {
        const status = error?.response?.status;
        if (status === 401) {
            handleApiError(error, 'Не удалось загрузить карточку сотрудника.');
            return;
        }
        if (status === 403) {
            employeeCardError.value = 'Доступ к документам ограничен.';
            return;
        }
        employeeCardError.value =
            error?.response?.data?.detail || 'Не удалось загрузить документы сотрудника.';
        console.error(error);
    } finally {
        employeeCardLoading.value = false;
    }
}

async function fetchWaiterTurnoverData() {
    if (!userStore.token) {
        return;
    }

    waiterTurnoverLoading.value = true;
    waiterTurnoverError.value = '';
    try {
        waiterTurnover.value = await fetchStaffWaiterTurnoverMetric();
    } catch (error) {
        waiterTurnover.value = null;
        waiterTurnoverError.value = error?.response?.data?.detail || 'Не удалось загрузить оборот';
    } finally {
        waiterTurnoverLoading.value = false;
    }
}

async function openShift() {
    isActionLoading.value = true;
    try {
        const restaurantId = selectedRestaurantId.value ? Number(selectedRestaurantId.value) : null;
        if (requiresRestaurantSelection.value && !restaurantId) {
            toast.error('Выберите ресторан, чтобы начать смену');
            return;
        }

        const positionId = selectedPositionId.value ? Number(selectedPositionId.value) : null;
        if (isMultiSubdivision.value && !positionId) {
            toast.error('Выберите должность, чтобы начать смену');
            return;
        }

        const payload = {
            ...(restaurantId ? { restaurant_id: restaurantId } : {}),
            ...(positionId ? { position_id: positionId } : {}),
        };
        const attendance = await openStaffAttendance(payload);
        setAttendance(attendance);
        toast.success('Смена начата');
        await fetchCurrentAttendance({ showLoader: false });
        await fetchWaiterTurnoverData();
    } catch (error) {
        if (error.response?.status === 409) {
            await fetchCurrentAttendance({ showLoader: false });
            await fetchWaiterTurnoverData();
        }
        handleApiError(error, 'Не удалось открыть смену');
    } finally {
        isActionLoading.value = false;
    }
}

async function closeShift() {
    isActionLoading.value = true;
    try {
        const attendance = await closeStaffAttendance({});
        const durationText = formatDuration(attendance?.duration_minutes);
        setAttendance(null);
        toast.success(durationText ? `Смена завершена. Время: ${durationText}.` : 'Смена завершена');
        await fetchCurrentAttendance({ showLoader: false });
        await fetchWaiterTurnoverData();
    } catch (error) {
        if (error.response?.status === 409) {
            await fetchCurrentAttendance({ showLoader: false });
            await fetchWaiterTurnoverData();
        }
        handleApiError(error, 'Не удалось закрыть смену');
    } finally {
        isActionLoading.value = false;
    }
}

async function handleAction() {
    if (actionDisabled.value) {
        return;
    }

    if (hasOpenShift.value) {
        await closeShift();
    } else {
        await openShift();
    }
}

function handleLogout() {
    setAttendance(null);
    attendances.value = [];
    restaurants.value = [];
    selectedRestaurantId.value = null;
    userStore.logout();
    router.replace({ name: 'user-login' });
}

onMounted(() => {
    if (!userStore.token) {
        router.replace({ name: 'user-login' });
        return;
    }
    if (userStore.isFired) {
        return;
    }
    fetchCurrentAttendance();
    fetchAvailableRestaurants();
    fetchAvailablePositions();
    fetchEmployeeBirthdays();
    fetchEmployeeCardData();
    fetchWaiterTurnoverData();
});

watch(isFired, (fired) => {
    if (!fired) {
        return;
    }
    setAttendance(null);
    attendances.value = [];
});

watch(medicalHasAlerts, (hasAlerts) => {
    medicalExpanded.value = hasAlerts;
}, { immediate: true });

watch(cisHasAlerts, (hasAlerts) => {
    cisExpanded.value = hasAlerts;
}, { immediate: true });

watch(restaurants, () => {
    if (currentAttendance.value?.restaurant_id) {
        updateSelectedRestaurantFromAttendance(currentAttendance.value);
        return;
    }
    selectDefaultRestaurant();
});

watch(isMultiSubdivision, (isMulti) => {
    if (isMulti) {
        fetchAvailablePositions();
    } else {
        positionOptions.value = [];
        selectedPositionId.value = null;
    }
});

watch(positionOptions, () => {
    selectDefaultPosition();
});

onBeforeUnmount(() => {
    stopTimer();
});
</script>

<style lang="scss">
@use '@/assets/styles/pages/time-tracking.scss' as *;
</style>
