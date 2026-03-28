<template>
    <div class="user-info">
        <section v-if="showProfile" class="user-info__card">
            <h3 class="h3 user-info__card-title">Личные данные пользователя</h3>
            <div v-if="user">
                <p class="user-info__card-data"><strong class="user-info__card-strong">Имя:</strong> {{ user.first_name }}</p>
                <p class="user-info__card-data"><strong class="user-info__card-strong">Фамилия:</strong> {{ user.last_name }}</p>
                <p class="user-info__card-data"><strong class="user-info__card-strong">Логин:</strong> {{ user.username }}</p>
                <p
                    v-if="canViewSensitiveStaffFields"
                    class="user-info__card-data"
                >
                    <strong class="user-info__card-strong">Код iiko:</strong> {{ user.iiko_code }}
                </p>
                <p class="user-info__card-data">
                    <strong class="user-info__card-strong">Пол:</strong> {{ formatGender(user.gender) }}
                </p>
                <p v-if="canViewSensitiveStaffFields" class="user-info__card-data">
                    <strong class="user-info__card-strong">Роль:</strong> {{ user.role ? user.role.name : '-' }}
                </p>
                <p class="user-info__card-data">
                    <strong class="user-info__card-strong">Рестораны:</strong>
                    <span v-if="user.restaurants && user.restaurants.length">
                        &nbsp;{{ user.restaurants.map((restaurant) => restaurant.name).join(', ') }}
                    </span>
                    <span v-else>-</span>
                </p>
            </div>
            <div v-else>
                <p>Загрузка...</p>
            </div>
        </section>

        <section v-if="canCustomizeInterfaceTheme" class="user-info__card user-info__theme-card">
            <h3 class="h3 user-info__card-title">Тема интерфейса</h3>
            <p class="user-info__theme-note">Настройка сохраняется в вашем аккаунте и не влияет на других сотрудников.</p>
            <Select
                :model-value="themeStore.interfaceTheme"
                label="Текущая тема интерфейса"
                :options="interfaceThemeOptions"
                :disabled="themeStore.isSaving"
                placeholder="Выберите тему"
                @update:model-value="handleInterfaceThemeChange"
            />
            <p class="user-info__theme-hint">Для пользователей без админки всегда используется классическая тема.</p>
        </section>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { fetchUser } from '@/api';
import { useToast } from 'vue-toastification';
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

const genderOptions = [
    { value: 'male', label: 'Мужской' },
    { value: 'female', label: 'Женский' },
];

const genderLabels = genderOptions.reduce((acc, option) => {
    acc[option.value] = option.label;
    return acc;
}, {});

const formatGender = (value) => genderLabels[value] ?? '-';

async function loadUser(userId) {
    try {
        user.value = await fetchUser(userId);
    } catch {
        toast.error('Не удалось загрузить данные пользователя');
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

onMounted(async () => {
    const tasks = [];
    if (showProfile.value && userStore.id) {
        tasks.push(loadUser(userStore.id));
    }
    if (userStore.isAuthenticated && !themeStore.isLoaded) {
        tasks.push(themeStore.bootstrapTheme());
    }
    if (tasks.length) {
        await Promise.all(tasks);
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/user-info.scss' as *;
</style>
