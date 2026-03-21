<template>
    <div class="admin-page kitchen-dashboard">
        <header class="admin-page__header kitchen-dashboard__header">
            <div class="kitchen-dashboard__header-main">
                <p class="kitchen-dashboard__eyebrow">Продажи</p>
                <h1 class="admin-page__title">Дашборд</h1>
                <p class="admin-page__subtitle">
                    Быстрый вход в отчеты и настройки продаж в едином стиле интерфейса.
                </p>
            </div>

            <div class="admin-page__header-actions kitchen-dashboard__header-actions">
                <Button
                    color="secondary"
                    size="sm"
                    :disabled="!availableCards.length"
                    @click="openFirstAvailable"
                >
                    Открыть первый доступный раздел
                </Button>
                <Button
                    color="ghost"
                    size="sm"
                    :disabled="!canOpenSettings"
                    @click="goTo({ path: '/admin/kitchen/settings' })"
                >
                    Настройки продаж
                </Button>
            </div>
        </header>

        <section class="kitchen-dashboard__stats">
            <article class="kitchen-dashboard__stat-card">
                <p class="kitchen-dashboard__stat-label">Доступно разделов</p>
                <p class="kitchen-dashboard__stat-value">{{ availableCards.length }} / {{ totalCardsCount }}</p>
            </article>
            <article class="kitchen-dashboard__stat-card">
                <p class="kitchen-dashboard__stat-label">Отчеты</p>
                <p class="kitchen-dashboard__stat-value">{{ availableSalesCardsCount }} / {{ salesCards.length }}</p>
            </article>
            <article class="kitchen-dashboard__stat-card">
                <p class="kitchen-dashboard__stat-label">Справочники</p>
                <p class="kitchen-dashboard__stat-value">
                    {{ availableSettingsCardsCount }} / {{ settingsCards.length }}
                </p>
            </article>
            <article class="kitchen-dashboard__stat-card">
                <p class="kitchen-dashboard__stat-label">Уровень доступа</p>
                <p class="kitchen-dashboard__stat-value">{{ accessLevelLabel }}</p>
            </article>
        </section>

        <section class="kitchen-dashboard__panel">
            <header class="kitchen-dashboard__panel-header">
                <h2 class="kitchen-dashboard__panel-title">Отчеты</h2>
                <p class="kitchen-dashboard__panel-subtitle">Быстрый переход к рабочим экранам аналитики.</p>
            </header>
            <div class="kitchen-dashboard__card-grid">
                <article
                    v-for="card in salesCards"
                    :key="card.key"
                    class="kitchen-dashboard__card"
                    :class="{ 'is-disabled': !card.canOpen }"
                >
                    <div class="kitchen-dashboard__card-top">
                        <p class="kitchen-dashboard__card-eyebrow">{{ card.subtitle }}</p>
                        <span class="kitchen-dashboard__card-status" :class="{ 'is-disabled': !card.canOpen }">
                            {{ card.canOpen ? 'Доступно' : 'Нет доступа' }}
                        </span>
                    </div>
                    <h3 class="kitchen-dashboard__card-title">{{ card.title }}</h3>
                    <p class="kitchen-dashboard__card-description">{{ card.description }}</p>
                    <div class="kitchen-dashboard__card-actions">
                        <Button
                            size="sm"
                            :color="card.canOpen ? 'secondary' : 'ghost'"
                            :disabled="!card.canOpen"
                            @click="goTo(card.target)"
                        >
                            Открыть
                        </Button>
                    </div>
                </article>
            </div>
        </section>

        <section class="kitchen-dashboard__panel">
            <header class="kitchen-dashboard__panel-header">
                <h2 class="kitchen-dashboard__panel-title">Настройки</h2>
                <p class="kitchen-dashboard__panel-subtitle">Справочники и параметры синхронизации с iiko.</p>
            </header>
            <div class="kitchen-dashboard__card-grid">
                <article
                    v-for="card in settingsCards"
                    :key="card.key"
                    class="kitchen-dashboard__card"
                    :class="{ 'is-disabled': !card.canOpen }"
                >
                    <div class="kitchen-dashboard__card-top">
                        <p class="kitchen-dashboard__card-eyebrow">{{ card.subtitle }}</p>
                        <span class="kitchen-dashboard__card-status" :class="{ 'is-disabled': !card.canOpen }">
                            {{ card.canOpen ? 'Доступно' : 'Нет доступа' }}
                        </span>
                    </div>
                    <h3 class="kitchen-dashboard__card-title">{{ card.title }}</h3>
                    <p class="kitchen-dashboard__card-description">{{ card.description }}</p>
                    <div class="kitchen-dashboard__card-actions">
                        <Button
                            size="sm"
                            :color="card.canOpen ? 'secondary' : 'ghost'"
                            :disabled="!card.canOpen"
                            @click="goTo(card.target)"
                        >
                            Открыть
                        </Button>
                    </div>
                </article>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import Button from '@/components/UI-components/Button.vue';
import { useUserStore } from '@/stores/user';

const router = useRouter();
const userStore = useUserStore();

const SALES_CARD_CONFIG = [
    {
        key: 'sales-report',
        title: 'Продажи',
        subtitle: 'Конструктор отчета',
        description: 'Соберите отчет по продажам с фильтрами, группировками и пользовательскими метриками.',
        target: { name: 'kitchen-sales-report' },
    },
    {
        key: 'revenue-report',
        title: 'Выручка',
        subtitle: 'Методы оплаты',
        description: 'Проверьте динамику реальных оплат по датам и методам с итогами по периоду.',
        target: { name: 'kitchen-revenue-report' },
    },
];

const SETTINGS_CARD_CONFIG = [
    {
        key: 'settings-main',
        title: 'Общие настройки',
        subtitle: 'Раздел настроек',
        description: 'Вход в настройки продаж со всеми связанными справочниками.',
        target: { path: '/admin/kitchen/settings' },
    },
    {
        key: 'settings-nomenclature',
        title: 'Номенклатура',
        subtitle: 'Справочник блюд',
        description: 'Управление блюдами, категориями и позициями для аналитики продаж.',
        target: { name: 'kitchen-settings-nomenclature' },
    },
    {
        key: 'settings-tables',
        title: 'Столы',
        subtitle: 'Справочник залов',
        description: 'Настройка залов, столов и точек продаж для корректной разбивки отчетов.',
        target: { name: 'kitchen-settings-tables' },
    },
    {
        key: 'settings-payment-types',
        title: 'Типы оплат',
        subtitle: 'Финансовые справочники',
        description: 'Проверьте и синхронизируйте методы оплаты для корректной выручки.',
        target: { name: 'kitchen-settings-payment-types' },
    },
    {
        key: 'settings-report-fields',
        title: 'Поля отчетов',
        subtitle: 'Конструктор данных',
        description: 'Выбор полей и настроек отображения данных для отчетов по продажам.',
        target: { name: 'kitchen-settings-report-fields' },
    },
    {
        key: 'settings-sales-accounting',
        title: 'Учет продаж',
        subtitle: 'Синхронизация iiko',
        description: 'Параметры интеграции и синхронизации данных между системой и iiko.',
        target: { name: 'kitchen-settings-sales-accounting' },
    },
    {
        key: 'settings-non-cash-limits',
        title: 'Лимиты безнала',
        subtitle: 'Контроль ограничений',
        description: 'Настройка лимитов безналичных оплат для контроля операций по ресторанам.',
        target: { name: 'kitchen-settings-non-cash-limits' },
    },
];

const salesCards = computed(() => SALES_CARD_CONFIG.map((card) => enrichCardWithAccess(card)));
const settingsCards = computed(() => SETTINGS_CARD_CONFIG.map((card) => enrichCardWithAccess(card)));

const availableCards = computed(() =>
    [...salesCards.value, ...settingsCards.value].filter((card) => card.canOpen),
);

const availableSalesCardsCount = computed(
    () => salesCards.value.filter((card) => card.canOpen).length,
);
const availableSettingsCardsCount = computed(
    () => settingsCards.value.filter((card) => card.canOpen).length,
);

const totalCardsCount = computed(() => salesCards.value.length + settingsCards.value.length);
const canOpenSettings = computed(() => canAccessTarget({ path: '/admin/kitchen/settings' }));
const accessLevelLabel = computed(() => {
    if (userStore.hasAnyPermission('iiko.manage', 'sales.report.manage')) {
        return 'Расширенный';
    }
    if (availableCards.value.length) {
        return 'Чтение';
    }
    return 'Нет доступа';
});

function enrichCardWithAccess(card) {
    return {
        ...card,
        canOpen: canAccessTarget(card.target),
    };
}

function canAccessTarget(target) {
    if (!target) {
        return false;
    }
    let resolvedRoute;
    try {
        resolvedRoute = router.resolve(target);
    } catch {
        return false;
    }

    if (!resolvedRoute?.matched?.length) {
        return false;
    }

    const routePermissions = Array.isArray(resolvedRoute.meta?.permissions)
        ? resolvedRoute.meta.permissions
        : [];
    const sectionPermissions = Array.isArray(resolvedRoute.meta?.sectionPermissions)
        ? resolvedRoute.meta.sectionPermissions
        : [];

    const routeAllowed = !routePermissions.length || userStore.hasAnyPermission(...routePermissions);
    const sectionAllowed =
        !sectionPermissions.length || userStore.hasAnyPermission(...sectionPermissions);

    return routeAllowed && sectionAllowed;
}

function goTo(target) {
    if (!target || !canAccessTarget(target)) {
        return;
    }
    router.push(target);
}

function openFirstAvailable() {
    if (!availableCards.value.length) {
        return;
    }
    goTo(availableCards.value[0].target);
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-dashboard' as *;
</style>
