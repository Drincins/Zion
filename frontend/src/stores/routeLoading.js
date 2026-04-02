import { readonly, ref } from 'vue';

const pendingNavigations = ref(0);
const pendingApiRequests = ref(0);
const isRouteLoading = ref(false);
const SHOW_DELAY_MS = 320;
const MIN_VISIBLE_MS = 140;
const HIDE_GRACE_MS = 80;
let visibleSince = 0;
let hideTimer = null;
let showTimer = null;

function getPendingCount() {
    return pendingNavigations.value + pendingApiRequests.value;
}

function clearHideTimer() {
    if (!hideTimer) {
        return;
    }
    globalThis.clearTimeout(hideTimer);
    hideTimer = null;
}

function clearShowTimer() {
    if (!showTimer) {
        return;
    }
    globalThis.clearTimeout(showTimer);
    showTimer = null;
}

function showLoading() {
    clearHideTimer();
    clearShowTimer();
    if (isRouteLoading.value) {
        return;
    }
    isRouteLoading.value = true;
    visibleSince = Date.now();
}

function scheduleShowLoading() {
    clearHideTimer();
    if (isRouteLoading.value || showTimer) {
        return;
    }
    showTimer = globalThis.setTimeout(() => {
        showTimer = null;
        if (getPendingCount() > 0) {
            showLoading();
        }
    }, SHOW_DELAY_MS);
}

function hideLoadingWithMinDuration() {
    clearShowTimer();
    if (!isRouteLoading.value) {
        return;
    }
    const elapsed = Date.now() - visibleSince;
    const waitForMinVisibleMs = Math.max(0, MIN_VISIBLE_MS - elapsed);
    const waitMs = Math.max(waitForMinVisibleMs, HIDE_GRACE_MS);
    clearHideTimer();
    hideTimer = globalThis.setTimeout(() => {
        hideTimer = null;
        if (getPendingCount() === 0) {
            isRouteLoading.value = false;
        }
    }, waitMs);
}

export function beginRouteLoading() {
    pendingNavigations.value += 1;
    scheduleShowLoading();
}

export function endRouteLoading() {
    pendingNavigations.value = Math.max(0, pendingNavigations.value - 1);
    if (getPendingCount() === 0) {
        hideLoadingWithMinDuration();
    }
}

export function resetRouteLoading() {
    pendingNavigations.value = 0;
    if (getPendingCount() === 0) {
        clearHideTimer();
        clearShowTimer();
        isRouteLoading.value = false;
        return;
    }
    scheduleShowLoading();
}

export function beginApiLoading() {
    pendingApiRequests.value += 1;
    scheduleShowLoading();
}

export function endApiLoading() {
    pendingApiRequests.value = Math.max(0, pendingApiRequests.value - 1);
    if (getPendingCount() === 0) {
        hideLoadingWithMinDuration();
    }
}

export function useRouteLoadingState() {
    return readonly(isRouteLoading);
}
