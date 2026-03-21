<template>
    <div class="admin-page kitchen-sales-report-fields-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Поля отчета Продажи</h1>
                <p class="admin-page__subtitle">
                    Включайте и отключайте доступные поля для конструктора отчета и фильтров.
                </p>
            </div>
            <div class="admin-page__header-actions">
                <Button color="ghost" @click="resetToDefault">Сбросить</Button>
                <Button @click="saveSettings">Сохранить</Button>
            </div>
        </header>

        <section class="admin-page__section">
            <h3 class="kitchen-sales-report-fields-page__section-title">Фильтры</h3>
            <div class="kitchen-sales-report-fields-page__grid">
                <label
                    v-for="field in filterFields"
                    :key="`filter-${field.value}`"
                    class="kitchen-sales-report-fields-page__item"
                >
                    <Checkbox
                        :model-value="settings.filters[field.value]"
                        :label="field.label"
                        @update:model-value="(value) => updateField('filters', field.value, value)"
                    />
                </label>
            </div>
        </section>

        <section class="admin-page__section">
            <h3 class="kitchen-sales-report-fields-page__section-title">Строки и столбцы</h3>
            <div class="kitchen-sales-report-fields-page__grid">
                <label
                    v-for="field in dimensionFields"
                    :key="`dimension-${field.key}`"
                    class="kitchen-sales-report-fields-page__item"
                >
                    <Checkbox
                        :model-value="settings.dimensions[field.key]"
                        :label="field.label"
                        @update:model-value="(value) => updateField('dimensions', field.key, value)"
                    />
                </label>
            </div>
        </section>

        <section class="admin-page__section">
            <h3 class="kitchen-sales-report-fields-page__section-title">Показатели</h3>
            <div class="kitchen-sales-report-fields-page__grid">
                <label
                    v-for="field in metricFields"
                    :key="`metric-${field.key}`"
                    class="kitchen-sales-report-fields-page__item"
                >
                    <Checkbox
                        :model-value="settings.metrics[field.key]"
                        :label="field.label"
                        @update:model-value="(value) => updateField('metrics', field.key, value)"
                    />
                </label>
            </div>
        </section>
    </div>
</template>

<script setup>
import { reactive } from 'vue';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import {
    SALES_REPORT_FIELD_CATALOG,
    getDefaultSalesReportFieldSettings,
    loadSalesReportFieldSettings,
    saveSalesReportFieldSettings,
} from './salesReportFieldSettings';

const toast = useToast();

const filterFields = SALES_REPORT_FIELD_CATALOG.filters;
const dimensionFields = SALES_REPORT_FIELD_CATALOG.dimensions;
const metricFields = SALES_REPORT_FIELD_CATALOG.metrics;

const settings = reactive(loadSalesReportFieldSettings());

function overwriteSettings(nextValue) {
    settings.filters = { ...(nextValue.filters || {}) };
    settings.dimensions = { ...(nextValue.dimensions || {}) };
    settings.metrics = { ...(nextValue.metrics || {}) };
}

function updateField(section, key, checked) {
    settings[section] = {
        ...settings[section],
        [key]: Boolean(checked),
    };
}

function resetToDefault() {
    overwriteSettings(getDefaultSalesReportFieldSettings());
    toast.success('Настройки полей сброшены');
}

function saveSettings() {
    const normalized = saveSalesReportFieldSettings({
        filters: settings.filters,
        dimensions: settings.dimensions,
        metrics: settings.metrics,
    });
    overwriteSettings(normalized);
    toast.success('Настройки полей сохранены');
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-sales-report-fields' as *;
</style>
