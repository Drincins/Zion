<template>
    <div class="birthday">
        <div class="birthday__grid">
            <section class="birthday__card">
                <header
                    class="birthday__card-header birthday__card-header--toggle"
                    role="button"
                    tabindex="0"
                    :aria-expanded="isMonthExpanded"
                    @click="toggleMonthBirthdays"
                    @keydown.enter.prevent="toggleMonthBirthdays"
                    @keydown.space.prevent="toggleMonthBirthdays"
                >
                    <div>
                        <p class="birthday__section-label">Текущий месяц</p>
                        <h3 class="birthday__card-title">Именинники месяца</h3>
                    </div>
                    <div class="birthday__header-actions">
                        <span class="birthday__badge">{{ birthdaysThisMonth.length }}</span>
                    </div>
                </header>
                <Transition
                    @enter="onMonthCollapseEnter"
                    @after-enter="onMonthCollapseAfterEnter"
                    @leave="onMonthCollapseLeave"
                    @after-leave="onMonthCollapseAfterLeave"
                >
                    <div v-if="isMonthExpanded" class="birthday__card-body birthday__card-body--collapsible">
                        <div v-if="isLoading" class="birthday__state">Загрузка сотрудников...</div>
                        <div v-else-if="loadError" class="birthday__state birthday__state--error">{{ loadError }}</div>
                        <Table v-else-if="birthdaysThisMonth.length" class="birthday__table">
                            <thead>
                                <tr>
                                    <th>Сотрудник</th>
                                    <th>Должность</th>
                                    <th>Дата</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="item in birthdaysThisMonth" :key="item.id">
                                    <td>{{ item.name }}</td>
                                    <td>{{ item.position }}</td>
                                    <td>{{ item.formattedDate }}</td>
                                </tr>
                            </tbody>
                        </Table>
                        <p v-else class="birthday__state">В этом месяце пока нет именинников.</p>
                    </div>
                </Transition>
            </section>

            <section class="birthday__card">
                <header class="birthday__card-header">
                    <div>
                        <p class="birthday__section-label">Сегодня</p>
                        <h3 class="birthday__card-title">Именинники дня</h3>
                    </div>
                    <span class="birthday__badge">{{ birthdaysToday.length }}</span>
                </header>
                <div class="birthday__card-body">
                    <div v-if="isLoading" class="birthday__state">Загрузка сотрудников...</div>
                    <div v-else-if="loadError" class="birthday__state birthday__state--error">{{ loadError }}</div>
                    <Table v-else-if="birthdaysToday.length" class="birthday__table">
                        <thead>
                            <tr>
                                <th>Сотрудник</th>
                                <th>Должность</th>
                                <th>Дата</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="item in birthdaysToday" :key="item.id">
                                <td>
                                    <button
                                        type="button"
                                        class="birthday__name-button"
                                        :disabled="!item.employeeId"
                                        @click="openEmployeeCard(item)"
                                    >
                                        {{ item.name }}
                                    </button>
                                </td>
                                <td>{{ item.position }}</td>
                                <td>{{ item.formattedDate }}</td>
                            </tr>
                        </tbody>
                    </Table>
                    <p v-else class="birthday__state">Сегодня нет именинников.</p>
                </div>
            </section>
        </div>

        <div v-if="isEmployeeOverlayOpen" class="birthday__employee-modal">
            <EmployeesPage modal-only />
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { fetchAllEmployees } from '@/api';
import EmployeesPage from '@/pages/AdminLayout/Employees/EmployeesPage.vue';
import Table from '@/components/UI-components/Table.vue';

const router = useRouter();
const route = useRoute();

const employees = ref([]);
const isLoading = ref(false);
const loadError = ref('');
const isMonthExpanded = ref(false);

const isEmployeeOverlayOpen = computed(() => Boolean(route.query.employeeId));

const today = new Date();
const todayMonth = today.getMonth();
const todayDay = today.getDate();

const birthdayEntries = computed(() =>
    employees.value
        .map((employee) => {
            const birthDate = parseBirthDate(employee?.birth_date);
            if (!birthDate) return null;

            const employeeId = resolveEmployeeId(employee);
            return {
                id:
                    employeeId ??
                    employee?.staff_code ??
                    employee?.username ??
                    `${employee?.last_name ?? ''}${employee?.first_name ?? ''}${employee?.birth_date ?? ''}`,
                employeeId,
                name: formatFullName(employee),
                position: employee.position_name || '-',
                birthDate,
                formattedDate: formatBirthdayDate(birthDate),
            };
        })
        .filter(Boolean),
);

const birthdaysThisMonth = computed(() =>
    birthdayEntries.value
        .filter((item) => item.birthDate.getMonth() === todayMonth)
        .sort((a, b) => a.birthDate.getDate() - b.birthDate.getDate()),
);

const birthdaysToday = computed(() =>
    birthdayEntries.value.filter(
        (item) => item.birthDate.getMonth() === todayMonth && item.birthDate.getDate() === todayDay,
    ),
);

onMounted(() => {
    loadEmployees();
});

function toggleMonthBirthdays() {
    isMonthExpanded.value = !isMonthExpanded.value;
}

function onMonthCollapseEnter(el) {
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

function onMonthCollapseAfterEnter(el) {
    el.style.height = '';
    el.style.opacity = '';
    el.style.transform = '';
    el.style.overflow = '';
}

function onMonthCollapseLeave(el) {
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

function onMonthCollapseAfterLeave(el) {
    el.style.height = '';
    el.style.opacity = '';
    el.style.transform = '';
    el.style.overflow = '';
}

function openEmployeeCard(item) {
    const employeeId = Number(item?.employeeId ?? item?.id ?? item?.user_id);
    if (!Number.isFinite(employeeId)) {
        return;
    }
    router.replace({
        query: {
            ...route.query,
            employeeId: String(employeeId),
        },
    });
}

async function loadEmployees() {
    isLoading.value = true;
    loadError.value = '';
    try {
        const { items } = await fetchAllEmployees({ limit: 250 });
        employees.value = items ?? [];
    } catch (error) {
        console.error(error);
        loadError.value =
            error?.response?.data?.detail || 'Не удалось загрузить сотрудников';
    } finally {
        isLoading.value = false;
    }
}

function resolveEmployeeId(employee) {
    const id = Number(employee?.id ?? employee?.user_id);
    return Number.isFinite(id) ? id : null;
}

function parseBirthDate(value) {
    if (!value) return null;
    const [year, month, day] = value.split('-').map(Number);
    if (!year || !month || !day) return null;
    return new Date(year, month - 1, day);
}

function formatFullName(employee) {
    if (!employee) return '-';
    const parts = [employee.last_name, employee.first_name, employee.middle_name].filter(Boolean);
    return parts.length ? parts.join(' ') : employee.username || '-';
}

function formatBirthdayDate(date) {
    return date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long' });
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/birthday' as *;
</style>
