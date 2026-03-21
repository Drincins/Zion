<template>
    <div class="input input--date">
        <label v-if="label" class="input-label">
            {{ label }}
        </label>
        <div ref="root" class="input-control input-date">
            <input
                v-bind="attrs"
                :id="fieldId"
                class="input-field input-field--date"
                type="text"
                inputmode="numeric"
                :autocomplete="attrs.autocomplete"
                :value="inputText"
                :placeholder="placeholder"
                :readonly="isReadOnly"
                :disabled="isDisabled"
                :aria-expanded="isOpen.toString()"
                aria-haspopup="dialog"
                :aria-controls="panelId"
                @focus="open"
                @click="open"
                @keydown="onInputKeydown"
                @input="onTextInput"
                @blur="onTextBlur"
            />
            <span class="input-date__icon" aria-hidden="true"></span>
        </div>
        <Teleport to="body">
            <Transition name="input-date">
                <div
                    v-if="isOpen"
                    :id="panelId"
                    ref="panel"
                    class="input-date__panel"
                    role="dialog"
                    :style="panelStyle"
                >
                    <div class="input-date__header">
                        <button
                            type="button"
                            class="input-date__nav"
                            :aria-label="prevLabel"
                            @click="navigate(-1)"
                        >
                            <BaseIcon name="Arrow" class="input-date__nav-icon" />
                        </button>
                        <button
                            type="button"
                            class="input-date__title input-date__title-button"
                            @click="toggleView"
                        >
                            {{ headerLabel }}
                        </button>
                        <button
                            type="button"
                            class="input-date__nav input-date__nav--next"
                            :aria-label="nextLabel"
                            @click="navigate(1)"
                        >
                            <BaseIcon name="Arrow" class="input-date__nav-icon input-date__nav-icon--next" />
                        </button>
                    </div>
                    <div v-if="isDateType && viewMode === 'days'">
                        <div class="input-date__weekdays">
                            <span
                                v-for="weekday in weekdays"
                                :key="weekday"
                                class="input-date__weekday"
                            >
                                {{ weekday }}
                            </span>
                        </div>
                        <div class="input-date__grid">
                            <button
                                v-for="day in calendarDays"
                                :key="day.key"
                                type="button"
                                class="input-date__day"
                                :class="{
                                    'is-outside': day.isOutside,
                                    'is-today': day.isToday,
                                    'is-selected': day.isSelected,
                                }"
                                :disabled="day.isDisabled"
                                @click="selectDate(day)"
                            >
                                {{ day.label }}
                            </button>
                        </div>
                    </div>
                    <div v-else-if="viewMode === 'months'" class="input-date__months">
                        <button
                            v-for="month in months"
                            :key="month.value"
                            type="button"
                            class="input-date__month"
                            :class="{ 'is-selected': month.isSelected }"
                            @click="selectMonth(month.value)"
                        >
                            {{ month.label }}
                        </button>
                    </div>
                    <div v-else class="input-date__years">
                        <button
                            v-for="year in years"
                            :key="year"
                            type="button"
                            class="input-date__year"
                            :class="{ 'is-selected': year === activeYear }"
                            @click="selectYear(year)"
                        >
                            {{ year }}
                        </button>
                    </div>
                </div>
            </Transition>
        </Teleport>
    </div>
</template>

<script setup>
import { computed, onMounted, ref, useAttrs, watch } from 'vue';
import { useFloatingPanel } from '@/composables/useFloatingPanel';
import BaseIcon from './BaseIcon.vue';

const props = defineProps({
    modelValue: {
        type: [String, Number],
        default: '',
    },
    label: {
        type: String,
        default: '',
    },
    type: {
        type: String,
        default: 'date',
    },
    placeholder: {
        type: String,
        default: '',
    },
});

const emit = defineEmits(['update:modelValue']);
const attrs = useAttrs();
const root = ref(null);
const panel = ref(null);
const isOpen = ref(false);
const viewMode = ref('days');
const inputText = ref('');
const activeMonth = ref(new Date());
const monthFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' });
const monthShortFormatter = new Intl.DateTimeFormat('ru-RU', { month: 'short' });
const weekdayFormatter = new Intl.DateTimeFormat('ru-RU', { weekday: 'short' });

const isDateType = computed(() => props.type === 'date');
const isMonthType = computed(() => props.type === 'month');
const isDisabled = computed(() => attrs.disabled !== undefined && attrs.disabled !== false);
const isReadOnly = computed(() => attrs.readonly !== undefined && attrs.readonly !== false);
const fieldId = computed(() => attrs.id || undefined);
const panelUid = `date-panel-${Math.random().toString(36).slice(2, 9)}`;
const panelId = computed(() => (fieldId.value ? `${fieldId.value}-panel` : panelUid));
const selectedKey = computed(() => normalizeModelValue(props.modelValue));
const activeYear = computed(() => activeMonth.value.getFullYear());
const yearRangeStart = ref(getYearRangeStart(activeYear.value));
const monthLabel = computed(() => {
    const label = monthFormatter.format(activeMonth.value);
    return label.charAt(0).toUpperCase() + label.slice(1);
});
const headerLabel = computed(() => {
    if (viewMode.value === 'days') {
        return monthLabel.value;
    }
    if (viewMode.value === 'months') {
        return String(activeYear.value);
    }
    const start = yearRangeStart.value;
    return `${start}-${start + 11}`;
});
const prevLabel = computed(() => {
    if (viewMode.value === 'days') {
        return 'Previous month';
    }
    if (viewMode.value === 'months') {
        return 'Previous year';
    }
    return 'Previous 12 years';
});
const nextLabel = computed(() => {
    if (viewMode.value === 'days') {
        return 'Next month';
    }
    if (viewMode.value === 'months') {
        return 'Next year';
    }
    return 'Next 12 years';
});
const weekdays = computed(() => {
    const start = new Date(2024, 0, 1);
    const labels = [];
    for (let i = 0; i < 7; i += 1) {
        const date = new Date(start);
        date.setDate(start.getDate() + i);
        labels.push(weekdayFormatter.format(date));
    }
    return labels;
});
const months = computed(() => {
    const year = activeYear.value;
    return Array.from({ length: 12 }, (_, index) => {
        const date = new Date(year, index, 1);
        return {
            value: index,
            label: formatMonthLabel(date),
            isSelected: index === activeMonth.value.getMonth(),
        };
    });
});
const years = computed(() => {
    return Array.from({ length: 12 }, (_, index) => yearRangeStart.value + index);
});
const minKey = computed(() => normalizeModelValue(attrs.min));
const maxKey = computed(() => normalizeModelValue(attrs.max));
const todayKey = computed(() => normalizeModelValue(new Date()));

function pad(value) {
    return String(value).padStart(2, '0');
}

function formatMonthLabel(date) {
    const label = monthShortFormatter.format(date).replace('.', '');
    return label.charAt(0).toUpperCase() + label.slice(1);
}

function getYearRangeStart(year) {
    return year - (year % 12);
}

function toIso(date) {
    if (!date) {
        return '';
    }
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function toDisplay(date) {
    if (!date) {
        return '';
    }
    return `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()}`;
}

function toMonthIso(date) {
    if (!date) {
        return '';
    }
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}`;
}

function toMonthDisplay(date) {
    if (!date) {
        return '';
    }
    return `${pad(date.getMonth() + 1)}.${date.getFullYear()}`;
}

function parseDateParts(year, month, day) {
    const value = new Date(year, month - 1, day);
    if (
        value.getFullYear() !== year ||
        value.getMonth() !== month - 1 ||
        value.getDate() !== day
    ) {
        return null;
    }
    return value;
}

function parseIsoDate(value) {
    if (typeof value !== 'string') {
        return null;
    }
    const match = value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) {
        return null;
    }
    return parseDateParts(Number(match[1]), Number(match[2]), Number(match[3]));
}

function parseDotDate(value) {
    if (typeof value !== 'string') {
        return null;
    }
    const match = value.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (!match) {
        return null;
    }
    return parseDateParts(Number(match[3]), Number(match[2]), Number(match[1]));
}

function parseAnyDate(value) {
    return parseIsoDate(value) || parseDotDate(value);
}

function parseMonthParts(year, month) {
    const value = new Date(year, month - 1, 1);
    if (value.getFullYear() !== year || value.getMonth() !== month - 1) {
        return null;
    }
    return value;
}

function parseIsoMonth(value) {
    if (typeof value !== 'string') {
        return null;
    }
    const match = value.match(/^(\d{4})-(\d{2})$/);
    if (!match) {
        return null;
    }
    return parseMonthParts(Number(match[1]), Number(match[2]));
}

function parseDotMonth(value) {
    if (typeof value !== 'string') {
        return null;
    }
    const match = value.match(/^(\d{2})\.(\d{4})$/);
    if (!match) {
        return null;
    }
    return parseMonthParts(Number(match[2]), Number(match[1]));
}

function parseAnyMonth(value) {
    const parsedMonth = parseIsoMonth(value) || parseDotMonth(value);
    if (parsedMonth) {
        return parsedMonth;
    }
    const parsedDate = parseAnyDate(value);
    return parsedDate ? startOfMonth(parsedDate) : null;
}

function normalizeToIso(value) {
    if (value instanceof Date) {
        return toIso(value);
    }
    const parsed = parseAnyDate(String(value ?? '').trim());
    return parsed ? toIso(parsed) : '';
}

function normalizeToMonth(value) {
    if (value instanceof Date) {
        return toMonthIso(value);
    }
    const parsed = parseAnyMonth(String(value ?? '').trim());
    return parsed ? toMonthIso(parsed) : '';
}

function normalizeModelValue(value) {
    return isMonthType.value ? normalizeToMonth(value) : normalizeToIso(value);
}

function formatDateInput(value) {
    const raw = String(value ?? '').trim();
    const isoParsed = parseIsoDate(raw);
    if (isoParsed) {
        return toDisplay(isoParsed);
    }
    const digits = raw.replace(/\D/g, '').slice(0, 8);
    if (!digits) {
        return '';
    }
    const parts = [digits.slice(0, 2)];
    if (digits.length > 2) {
        parts.push(digits.slice(2, 4));
    }
    if (digits.length > 4) {
        parts.push(digits.slice(4, 8));
    }
    return parts.filter(Boolean).join('.');
}

function formatMonthInput(value) {
    const raw = String(value ?? '').trim();
    const isoParsed = parseIsoMonth(raw);
    if (isoParsed) {
        return toMonthDisplay(isoParsed);
    }
    const digits = raw.replace(/\D/g, '').slice(0, 6);
    if (!digits) {
        return '';
    }
    const parts = [digits.slice(0, 2)];
    if (digits.length > 2) {
        parts.push(digits.slice(2, 6));
    }
    return parts.filter(Boolean).join('.');
}

function parseTypedValue(value) {
    return isMonthType.value ? parseAnyMonth(value) : parseAnyDate(value);
}

function formatTypedValue(date) {
    return isMonthType.value ? toMonthDisplay(date) : toDisplay(date);
}

function toTypedModelValue(date) {
    return isMonthType.value ? toMonthIso(date) : toIso(date);
}

function syncInputText(value) {
    const parsed = parseTypedValue(String(value ?? '').trim());
    inputText.value = parsed ? formatTypedValue(parsed) : '';
}

function startOfMonth(date) {
    return new Date(date.getFullYear(), date.getMonth(), 1);
}

function syncMonth(value) {
    const parsed = parseTypedValue(String(value ?? '').trim());
    activeMonth.value = parsed ? startOfMonth(parsed) : startOfMonth(new Date());
}

function isOutOfRange(key) {
    if (minKey.value && key < minKey.value) {
        return true;
    }
    if (maxKey.value && key > maxKey.value) {
        return true;
    }
    return false;
}

const calendarDays = computed(() => {
    const date = activeMonth.value;
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const startOffset = (firstDay.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrev = new Date(year, month, 0).getDate();
    const totalDays = 42;
    const days = [];

    for (let i = 0; i < totalDays; i += 1) {
        const dayNumber = i - startOffset + 1;
        let currentDate = null;
        let isOutside = false;

        if (dayNumber <= 0) {
            currentDate = new Date(year, month - 1, daysInPrev + dayNumber);
            isOutside = true;
        } else if (dayNumber > daysInMonth) {
            currentDate = new Date(year, month + 1, dayNumber - daysInMonth);
            isOutside = true;
        } else {
            currentDate = new Date(year, month, dayNumber);
        }

        const key = toIso(currentDate);
        const isDisabledDay = isDisabled.value || isOutOfRange(key);

        days.push({
            key,
            label: currentDate.getDate(),
            isOutside,
            isSelected: key === selectedKey.value,
            isToday: key === todayKey.value,
            isDisabled: isDisabledDay,
        });
    }

    return days;
});

function open() {
    if (isDisabled.value || isReadOnly.value) {
        return;
    }
    if (!isOpen.value) {
        viewMode.value = isMonthType.value ? 'months' : 'days';
        isOpen.value = true;
    }
}

function close({ commit = true } = {}) {
    if (!isOpen.value) {
        return;
    }
    isOpen.value = false;
    if (commit) {
        commitInput();
    }
}

const { floatingStyle: panelStyle } = useFloatingPanel({
    rootRef: root,
    panelRef: panel,
    isOpen,
    triggerSelector: '.input-field--date',
    onRequestClose: () => close({ commit: true }),
    computeStyle: ({ rect, panelElement, viewportHeight, viewportWidth }) => {
        const maxHeight = 360;
        const panelHeight = panelElement ? panelElement.scrollHeight : maxHeight;
        const safeViewportWidth = Number.isFinite(viewportWidth) ? viewportWidth : (window.innerWidth || document.documentElement.clientWidth || 0);
        const minPanelWidth = 260;
        const desiredWidth = Math.max(minPanelWidth, rect.width);
        const maxPanelWidth = Math.max(minPanelWidth, safeViewportWidth - 16);
        const panelWidth = Math.min(desiredWidth, maxPanelWidth);
        const spaceBelow = viewportHeight - rect.bottom - 8;
        const spaceAbove = rect.top - 8;
        const showAbove = spaceBelow < Math.min(maxHeight, panelHeight) && spaceAbove > spaceBelow;
        const available = showAbove ? spaceAbove : spaceBelow;
        const height = Math.min(maxHeight, Math.max(220, available));
        const top = showAbove ? rect.top - height - 8 : rect.bottom + 8;
        const left = Math.min(
            Math.max(8, rect.left),
            Math.max(8, safeViewportWidth - panelWidth - 8),
        );

        return {
            top: `${Math.max(8, top)}px`,
            left: `${left}px`,
            width: `${panelWidth}px`,
            '--date-max-height': `${height}px`
        };
    }
});

function shiftMonth(delta) {
    const date = activeMonth.value;
    activeMonth.value = new Date(date.getFullYear(), date.getMonth() + delta, 1);
}

function shiftYear(delta) {
    activeMonth.value = new Date(activeYear.value + delta, activeMonth.value.getMonth(), 1);
}

function shiftYearRange(delta) {
    yearRangeStart.value += delta;
}

function navigate(delta) {
    if (isMonthType.value) {
        if (viewMode.value === 'months') {
            shiftYear(delta);
            return;
        }
        shiftYearRange(delta * 12);
        return;
    }
    if (viewMode.value === 'days') {
        shiftMonth(delta);
        return;
    }
    if (viewMode.value === 'months') {
        shiftYear(delta);
        return;
    }
    shiftYearRange(delta * 12);
}

function toggleView() {
    if (isMonthType.value) {
        viewMode.value = viewMode.value === 'years' ? 'months' : 'years';
        return;
    }
    if (viewMode.value === 'days') {
        viewMode.value = 'months';
        return;
    }
    if (viewMode.value === 'months') {
        viewMode.value = 'years';
        return;
    }
    viewMode.value = 'months';
}

function selectMonth(monthIndex) {
    if (isMonthType.value) {
        const value = new Date(activeYear.value, monthIndex, 1);
        const key = toMonthIso(value);
        if (isOutOfRange(key)) {
            return;
        }
        emit('update:modelValue', key);
        inputText.value = toMonthDisplay(value);
        close({ commit: false });
        return;
    }
    activeMonth.value = new Date(activeYear.value, monthIndex, 1);
    viewMode.value = 'days';
}

function selectYear(year) {
    activeMonth.value = new Date(year, activeMonth.value.getMonth(), 1);
    viewMode.value = 'months';
}

function selectDate(day) {
    if (!isDateType.value) {
        return;
    }
    if (day.isDisabled) {
        return;
    }
    emit('update:modelValue', day.key);
    inputText.value = toDisplay(parseIsoDate(day.key));
    close({ commit: false });
}

function commitInput() {
    const trimmed = inputText.value.trim();
    if (!trimmed) {
        emit('update:modelValue', '');
        return;
    }
    const parsed = parseTypedValue(trimmed);
    if (!parsed) {
        syncInputText(props.modelValue);
        return;
    }
    const key = toTypedModelValue(parsed);
    if (isOutOfRange(key)) {
        syncInputText(props.modelValue);
        return;
    }
    emit('update:modelValue', key);
    inputText.value = formatTypedValue(parsed);
    activeMonth.value = startOfMonth(parsed);
}

function onTextInput(event) {
    const formatted = isMonthType.value ? formatMonthInput(event.target.value) : formatDateInput(event.target.value);
    inputText.value = formatted;
    if (event.target.value !== formatted) {
        event.target.value = formatted;
    }
}

function onTextBlur() {
    if (!isOpen.value) {
        commitInput();
    }
}

function onInputKeydown(event) {
    if (event.key === 'Escape') {
        close({ commit: false });
        return;
    }
    if (event.key === 'Enter') {
        event.preventDefault();
        commitInput();
        close({ commit: false });
        return;
    }
    if (event.key === 'ArrowDown' || event.key === ' ') {
        event.preventDefault();
        open();
        return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey) {
        return;
    }
    if (
        event.key === 'Backspace' ||
        event.key === 'Delete' ||
        event.key === 'Tab' ||
        event.key === 'ArrowLeft' ||
        event.key === 'ArrowRight' ||
        event.key === 'ArrowUp' ||
        event.key === 'ArrowDown' ||
        event.key === 'Home' ||
        event.key === 'End'
    ) {
        return;
    }
    if (!/^\d$/.test(event.key)) {
        event.preventDefault();
    }
}

onMounted(() => {
    syncInputText(props.modelValue);
    syncMonth(props.modelValue);
});

watch(
    () => props.modelValue,
    (value) => {
        syncInputText(value);
        if (!isOpen.value) {
            syncMonth(value);
        }
    },
);

watch(viewMode, (value) => {
    if (value === 'years') {
        yearRangeStart.value = getYearRangeStart(activeYear.value);
    }
});

</script>

<style lang="scss">
@use '@/assets/styles/components/ui-components/input.scss' as *;
</style>
