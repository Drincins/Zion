<template>
    <div class="sidebar-menu" :class="{ collapsed: isCollapsed }">
        <div class="sidebar-menu__user">
            <div v-if="!isCollapsed" @click="goToDashboard">
                <p class="sidebar-menu__user-login">
                    <strong>{{ login || '...' }}</strong>
                </p>
                <p class="sidebar-menu__user-name">{{ fullName || 'Пользователь' }}</p>
            </div>
            <div v-else class="sidebar-menu__user-icon" title="Профиль" @click="goToDashboard">
                <BaseIcon name="User" />
            </div>
            <div class="sidebar-menu__user-actions">
                <span class="sidebar-menu__user-settings" @click="goToUser">
                    <BaseIcon name="Settings" />
                </span>
                <span class="sidebar-menu__user-logout" @click="logout">
                    <BaseIcon name="Logout" />
                </span>
            </div>
        </div>
        <ul class="sidebar-menu__list">
            <li v-for="group in visibleMenuGroups" :key="group.key" class="sidebar-menu__group">
                <button
                    type="button"
                    class="sidebar-menu__group-toggle"
                    :class="{ active: isGroupActive(group) }"
                    :title="isCollapsed ? group.label : ''"
                    :aria-expanded="group.directTo ? undefined : isGroupOpen(group.key)"
                    @click="handleGroupClick(group)"
                >
                    <span class="sidebar-menu__group-icon">{{ group.icon }}</span>
                    <span v-if="!isCollapsed" class="sidebar-menu__group-label">{{ group.label }}</span>
                    <BaseIcon v-if="!isCollapsed && !group.directTo" name="Arrow" class="sidebar-menu__group-arrow" />
                </button>
                <Transition name="sidebar-sublist">
                    <ul v-if="!isCollapsed && !group.directTo && isGroupOpen(group.key)" class="sidebar-menu__sublist">
                        <li
                            v-for="item in group.items"
                            :key="item.key"
                            class="sidebar-menu__sublist-item"
                            :class="{ active: isItemActive(item) }"
                            @click="navigateTo(item)"
                        >
                            {{ item.label }}
                        </li>
                    </ul>
                </Transition>
            </li>
        </ul>
        <button class="sidebar-menu__collapse-button" @click="toggleCollapse">
            <BaseIcon name="Arrow" class="sidebar-menu__collapse-button-arrow" />
        </button>
    </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { SIDEBAR_MENU_GROUPS } from '@/router/adminNavigation';
import { isSuperAdminRole as isSuperAdminRoleByName } from '@/utils/roles';

const props = defineProps({
    forceExpanded: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(['goToDashboard', 'goToUser']);

const userStore = useUserStore();
const router = useRouter();
const route = useRoute();

const isCollapsed = ref(false);
const expandedGroups = ref({});

const login = computed(() => userStore.login);
const fullName = computed(() => userStore.fullName);
const isSuperAdminRole = computed(() => isSuperAdminRoleByName(userStore.roleName));

const menuGroups = SIDEBAR_MENU_GROUPS;

const canAccessMenuEntry = (entry) => {
    if (!entry) {
        return false;
    }
    if (entry.requiresSuperAdmin && !isSuperAdminRole.value) {
        return false;
    }
    const permissions = Array.isArray(entry.permissions) ? entry.permissions : [];
    if (permissions.length && !userStore.hasAnyPermission(...permissions)) {
        return false;
    }
    const sectionPermissions = Array.isArray(entry.sectionPermissions) ? entry.sectionPermissions : [];
    if (sectionPermissions.length && !userStore.hasAnyPermission(...sectionPermissions)) {
        return false;
    }
    return true;
};

const visibleMenuGroups = computed(() =>
    menuGroups
        .map((group) => ({
            ...group,
            items: (group.items || []).filter((item) => canAccessMenuEntry(item)),
        }))
        .filter((group) => canAccessMenuEntry(group) && group.items.length > 0),
);

const resolveItemPath = (item) => {
    if (!item?.to) {
        return '';
    }
    return router.resolve(item.to).path;
};

const routeMatchesItemPath = (item) => {
    const activePrefixes = Array.isArray(item?.activePrefixes) ? item.activePrefixes : [];
    const matchesActivePrefix = activePrefixes.some((prefix) => route.path === prefix || route.path.startsWith(`${prefix}/`));
    if (matchesActivePrefix) {
        return true;
    }
    const itemPath = resolveItemPath(item);
    if (!itemPath) {
        return false;
    }
    return route.path === itemPath || route.path.startsWith(`${itemPath}/`);
};

const isItemActive = (item) => {
    if (!routeMatchesItemPath(item)) {
        return false;
    }
    if (item.to.hash) {
        return route.hash === item.to.hash;
    }
    return true;
};

const routeMatchesTarget = (target) => {
    if (!target) {
        return false;
    }
    const targetPath = router.resolve(target).path;
    return route.path === targetPath || route.path.startsWith(`${targetPath}/`);
};

const isGroupActive = (group) => {
    if (group.directTo && routeMatchesTarget(group.directTo)) {
        return true;
    }
    return group.items.some((item) => isItemActive(item));
};
const isGroupOpen = (key) => Boolean(expandedGroups.value[key]);

function handleGroupClick(group) {
    if (!group) {
        return;
    }
    if (group.directTo) {
        navigateTo({ to: group.directTo, openInNew: Boolean(group.directOpenInNew) });
        return;
    }
    toggleGroup(group.key);
}

function toggleGroup(key) {
    if (isCollapsed.value) {
        isCollapsed.value = false;
    }
    expandedGroups.value = {
        ...expandedGroups.value,
        [key]: !expandedGroups.value[key],
    };
}

function toggleCollapse() {
    if (props.forceExpanded) {
        return;
    }
    isCollapsed.value = !isCollapsed.value;
}

function navigateTo(item) {
    if (!item?.to) {
        return;
    }
    const target = router.resolve(item.to);
    if (item.openInNew) {
        window.open(target.href, '_blank');
        return;
    }
    router.push(item.to);
}

function ensureActiveGroupOpen() {
    const activeGroup =
        visibleMenuGroups.value.find((group) => !group.directTo && group.items.some((item) => routeMatchesItemPath(item)))
        || null;
    if (!activeGroup) {
        return;
    }
    expandedGroups.value = {
        ...expandedGroups.value,
        [activeGroup.key]: true,
    };
}

function goToDashboard() {
    emit('goToDashboard');
}

function goToUser() {
    emit('goToUser');
}

function logout() {
    userStore.logout();
    router.push('/login');
}

watch(
    () => props.forceExpanded,
    (value) => {
        if (value) {
            isCollapsed.value = false;
        }
    },
    { immediate: true },
);

watch(
    () => route.fullPath,
    () => {
        ensureActiveGroupOpen();
    },
    { immediate: true },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/components/sidebar.scss' as *;
</style>
