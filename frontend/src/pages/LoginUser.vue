<template>
    <div class="wrapper login">
        <div class="login__container">
            <div class="login__logo">
                <img
                    class="login__logo-image"
                    src="@/assets/images/logo.png"
                    alt="Logo"
                />
            </div>
            <div class="login__input-wrapper">
                <input
                    ref="codeInput"
                    v-model="code"
                    class="login__input"
                    type="password"
                    :inputmode="isCoarsePointer ? 'none' : 'numeric'"
                    pattern="[0-9]*"
                    maxlength="5"
                    placeholder="Введите код"
                    :readonly="isCoarsePointer || isLoading"
                    @input="handleInput"
                    @keyup.enter="handleSubmit"
                    @paste.prevent="handlePaste"
                />
                <Button
                    class="login__scan"
                    color="secondary"
                    size="lg"
                    :loading="isLoading && activeMode === 'scan'"
                    :disabled="isLoading"
                    aria-label="Сканировать отпечаток пальца"
                    title="Сканировать отпечаток пальца"
                    @click="handleFingerprintLogin"
                >
                    <span class="login__scan-icon" aria-hidden="true">
                        <img
                            src="@/assets/images/print.svg"
                            alt="print"
                        />
                    </span>
                </Button>
            </div>
            <div class="login__keyboard">
                <button
                    v-for="key in keypadKeys"
                    :key="key.key"
                    type="button"
                    class="login__key"
                    :class="key.modifier ? `login__key--${key.modifier}` : ''"
                    :disabled="isLoading"
                    @click="handleKeyPress(key.value)"
                >
                    {{ key.label }}
                </button>
            </div>
            <div class="login__actions">
                <Button
                    class="login__submit"
                    color="primary"
                    size="lg"
                    block
                    :loading="isLoading && activeMode === 'login'"
                    @click="handleSubmit"
                >
                    Войти
                </Button>
                <a
                    class="login__download button button--outline button--lg is-block"
                    :href="downloadUrl"
                    target="_blank"
                    rel="noopener"
                >
                    Скачать ZionScan
                </a>
            </div>
            <p v-if="scanStatus" class="login__status">{{ scanStatus }}</p>
            <RouterLink to="/login" class="login__link">Перейти к расширенной авторизации</RouterLink>
        </div>
    </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import { identifyFingerprint, loginStaffByCode } from '@/api';
import { useUserStore } from '@/stores/user';
import { useThemeStore } from '@/stores/theme';
import Button from '@/components/UI-components/Button.vue';

const MAX_LENGTH = 5;

const code = ref('');
const codeInput = ref(null);
const isCoarsePointer = ref(false);
const isLoading = ref(false);
const activeMode = ref(null);
const scanStatus = ref('');
const downloadUrl = '/api/downloads/zionscan';
const router = useRouter();
const toast = useToast();
const userStore = useUserStore();
const themeStore = useThemeStore();

let pointerQuery;

function applyPointerMode(matches) {
    const nextValue = Boolean(matches);
    isCoarsePointer.value = nextValue;

    if (nextValue && codeInput.value) {
        codeInput.value.blur();
    }
}

function handlePointerChange(event) {
    const wasCoarse = isCoarsePointer.value;
    applyPointerMode(event.matches);

    if (wasCoarse && !isCoarsePointer.value && codeInput.value) {
        codeInput.value.focus();
    }
}

const keypadKeys = [
    { key: '1', value: '1', label: '1' },
    { key: '2', value: '2', label: '2' },
    { key: '3', value: '3', label: '3' },
    { key: '4', value: '4', label: '4' },
    { key: '5', value: '5', label: '5' },
    { key: '6', value: '6', label: '6' },
    { key: '7', value: '7', label: '7' },
    { key: '8', value: '8', label: '8' },
    { key: '9', value: '9', label: '9' },
    { key: 'clear', value: 'clear', label: 'Очистить', modifier: 'action' },
    { key: '0', value: '0', label: '0' },
    { key: 'backspace', value: 'backspace', label: '⌫', modifier: 'action' },
];

const scanErrorMessages = {
    device_not_ready: 'Сканер не готов. Проверьте подключение.',
    capture_timeout: 'Отпечаток не получен. Попробуйте снова.',
    finger_mismatch: 'Сканируйте один и тот же палец три раза.',
    fingerprint_already_enrolled: 'Этот отпечаток уже зарегистрирован.',
    no_match: 'Отпечаток не найден.',
    empty_staff_code: 'Сканер не вернул код сотрудника.',
    busy: 'Сканер занят. Попробуйте позже.',
};

function resolveScanError(errorCode) {
    return scanErrorMessages[errorCode] || 'Ошибка сканера.';
}

function handleKeyPress(value) {
    if (isLoading.value) {
        return;
    }

    if (value === 'clear') {
        code.value = '';
        return;
    }

    if (value === 'backspace') {
        code.value = code.value.slice(0, -1);
        return;
    }

    if (code.value.length >= MAX_LENGTH) {
        return;
    }

    code.value += value;
}

function handleInput(event) {
    if (isLoading.value) {
        return;
    }

    const digitsOnly = event.target.value.replace(/\D/g, '');
    code.value = digitsOnly.slice(0, MAX_LENGTH);
}

function handlePaste(event) {
    const pasted = event.clipboardData?.getData('text') ?? '';
    const digitsOnly = pasted.replace(/\D/g, '');

    if (!digitsOnly) {
        return;
    }

    const nextValue = `${code.value}${digitsOnly}`.slice(0, MAX_LENGTH);
    code.value = nextValue;
}

async function submitCode(
    codeValue,
    { setLoading = true, authMethod = null, fingerprintScore = null, fingerprintSlot = null } = {},
) {
    if (setLoading) {
        if (isLoading.value) {
            return;
        }
        isLoading.value = true;
        activeMode.value = 'login';
        scanStatus.value = '';
    }

    try {
        const data = await loginStaffByCode(codeValue, {
            authMethod,
            fingerprintScore,
            fingerprintSlot,
        });
        const { user } = data;

        const restaurantsFromUser = Array.isArray(user?.restaurants)
            ? user.restaurants
                  .map((restaurant) => Number(restaurant?.id))
                  .filter((id) => Number.isFinite(id))
            : Array.isArray(user?.restaurant_ids)
                ? user.restaurant_ids
                      .map((id) => Number(id))
                      .filter((id) => Number.isFinite(id))
                : [];

        userStore.setUser({
            id: user.id,
            login: user.username ?? '',
            firstName: user.first_name ?? '',
            lastName: user.last_name ?? '',
            fullName: `${user.first_name ?? ''} ${user.last_name ?? ''}`.trim(),
            roleName: user.role_name ?? '',
            positionName: user.position_name ?? '',
            positionId: user.position_id ?? null,
            rate: typeof user.rate === 'number' ? user.rate : null,
            hasFullRestaurantAccess: Boolean(user?.has_full_restaurant_access),
            hasGlobalAccess: Boolean(user?.has_global_access),
            restaurantIds: restaurantsFromUser,
            workplaceRestaurantId: user?.workplace_restaurant_id ?? null,
            restaurantSubdivisionId: user?.restaurant_subdivision_id ?? null,
            restaurantSubdivisionName: user?.restaurant_subdivision_name ?? '',
            restaurantSubdivisionIsMulti: Boolean(user?.restaurant_subdivision_is_multi),
            isFired: Boolean(user?.fired ?? user?.is_fired ?? user?.isFired),
        });

        toast.success('Успешный вход');
        await themeStore.bootstrapTheme();
        router.push({ name: 'time-tracking' });
    } catch (error) {
        if (error.response?.status === 401) {
            toast.error('Неверный табельный код');
        } else if (error.response?.data?.detail) {
            toast.error(error.response.data.detail);
        } else {
            toast.error('Не удалось выполнить вход');
        }
        code.value = '';
    } finally {
        if (setLoading) {
            isLoading.value = false;
            activeMode.value = null;
        }
    }
}

async function handleFingerprintLogin() {
    if (isLoading.value) {
        return;
    }

    isLoading.value = true;
    activeMode.value = 'scan';
    scanStatus.value = 'Приложите палец к сканеру';

    try {
        const scanResult = await identifyFingerprint();
        if (!scanResult || scanResult.ok === false) {
            toast.error(resolveScanError(scanResult?.error));
            return;
        }

        const staffCode = String(scanResult.staff_code || '').trim();
        if (!staffCode) {
            toast.error(resolveScanError('empty_staff_code'));
            return;
        }

        code.value = staffCode;
        scanStatus.value = 'Выполняю вход...';
        await submitCode(staffCode, {
            setLoading: false,
            authMethod: 'fingerprint',
            fingerprintScore: scanResult.score,
            fingerprintSlot: scanResult.slot,
        });
    } catch (error) {
        if (error?.message === 'Network Error' || error?.code === 'ERR_NETWORK') {
            toast.error('Локальный агент не доступен.');
        } else {
            toast.error(resolveScanError(error?.message));
        }
    } finally {
        isLoading.value = false;
        activeMode.value = null;
        scanStatus.value = '';
    }
}

function handleSubmit() {
    submitCode(code.value);
}

onMounted(() => {
    if (typeof window !== 'undefined' && 'matchMedia' in window) {
        pointerQuery = window.matchMedia('(pointer: coarse)');
        applyPointerMode(pointerQuery.matches);

        if ('addEventListener' in pointerQuery) {
            pointerQuery.addEventListener('change', handlePointerChange);
        } else if ('addListener' in pointerQuery) {
            pointerQuery.addListener(handlePointerChange);
        }
    }

    if (!isCoarsePointer.value && codeInput.value) {
        codeInput.value.focus();
    }
});

onBeforeUnmount(() => {
    if (!pointerQuery) {
        return;
    }

    if ('removeEventListener' in pointerQuery) {
        pointerQuery.removeEventListener('change', handlePointerChange);
    } else if ('removeListener' in pointerQuery) {
        pointerQuery.removeListener(handlePointerChange);
    }
});
</script>

<style lang="scss">
@use '@/assets/styles/pages/login-user.scss' as *;
</style>
