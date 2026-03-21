<template>
    <div class="user-info">
        <!-- Личные данные -->
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
                        &nbsp;{{ user.restaurants.map((r) => r.name).join(', ') }}
                    </span>
                    <span v-else>-</span>
                </p>
            </div>
            <div v-else>
                <p>Загрузка...</p>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { fetchUser } from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import { isSystemLevelRole } from '@/utils/roles';

const props = defineProps({
    section: {
        type: String,
        default: 'all',
    },
});

const userStore = useUserStore();
const toast = useToast();

const showProfile = computed(() => props.section === 'all' || props.section === 'profile');

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

onMounted(() => {
    if (showProfile.value && userStore.id) {
        loadUser(userStore.id);
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/user-info.scss' as *;
</style>
