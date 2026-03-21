<template>
    <div class="admin-layout">
        <template v-if="isFired">
            <div class="admin-layout__blocked">
                <div class="admin-layout__blocked-card">
                    <p class="admin-layout__blocked-text">Доступ запрещен, вы уволены</p>
                    <Button color="primary" size="lg" @click="goToLogin">
                        Вернуться на авторизацию
                    </Button>
                </div>
            </div>
        </template>
        <template v-else>
            <button
                v-if="isMobile"
                type="button"
                class="burger-button"
                :class="{ 'is-open': isSidebarOpen }"
                :aria-expanded="isSidebarOpen"
                aria-controls="admin-sidebar"
                aria-label="Toggle menu"
                @click="toggleSidebar"
            >
                <span class="burger-button__line" />
                <span class="burger-button__line" />
                <span class="burger-button__line" />
            </button>
            <div
                v-if="isMobile"
                class="sidebar-overlay"
                :class="{ 'is-open': isSidebarOpen }"
                @click="closeSidebar"
            />
            <div id="admin-sidebar" class="sidebar" :class="{ 'is-open': isSidebarOpen }">
                <Sidebar
                    :force-expanded="isMobile"
                    @go-to-user="goToUser"
                    @go-to-dashboard="goToDashboard"
                />
            </div>
            <div class="main">
                <section class="content">
                    <router-view />
                </section>
            </div>
        </template>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Sidebar from '@/components/Sidebar.vue';
import Button from '@/components/UI-components/Button.vue';
import { useUserStore } from '@/stores/user';
const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const isFired = computed(() => userStore.isFired);

const isMobile = ref(false);
const isSidebarOpen = ref(false);
let mediaQuery;

const updateIsMobile = () => {
    if (!mediaQuery) {
        return;
    }
    isMobile.value = mediaQuery.matches;
    if (!isMobile.value) {
        isSidebarOpen.value = false;
    }
};

const goToUser = () => router.push('/admin/user');
const goToDashboard = () => router.push('/admin');
const goToLogin = () => {
    userStore.logout();
    router.replace({ name: 'login' });
};

const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value;
};

const closeSidebar = () => {
    isSidebarOpen.value = false;
};

watch(
    () => route.fullPath,
    () => {
        if (isMobile.value) {
            isSidebarOpen.value = false;
        }
    },
);

onMounted(() => {
    mediaQuery = window.matchMedia('(max-width: 1120px)');
    updateIsMobile();
    if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', updateIsMobile);
    } else if (mediaQuery.addListener) {
        mediaQuery.addListener(updateIsMobile);
    }
});

onBeforeUnmount(() => {
    if (!mediaQuery) {
        return;
    }
    if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', updateIsMobile);
    } else if (mediaQuery.removeListener) {
        mediaQuery.removeListener(updateIsMobile);
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/layouts/admin-layout.scss' as *;
</style>
