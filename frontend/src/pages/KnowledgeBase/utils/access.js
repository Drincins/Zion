const ACCESS_SCOPE_KEYS = ['position_ids', 'user_ids', 'restaurant_ids'];

const ACCESS_SUMMARY_LABELS = {
    none: '\u0411\u0435\u0437 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u0439',
    positions: '\u0414\u043e\u043b\u0436\u043d\u043e\u0441\u0442\u0438',
    users: '\u0421\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u0438',
    restaurants: '\u0420\u0435\u0441\u0442\u043e\u0440\u0430\u043d\u044b',
};

function normalizeKnowledgeBaseIds(value) {
    if (!Array.isArray(value)) {
        return [];
    }
    const unique = new Set();
    value.forEach((item) => {
        const parsed = Number(item);
        if (Number.isFinite(parsed) && parsed > 0) {
            unique.add(parsed);
        }
    });
    return Array.from(unique).sort((a, b) => a - b);
}

function normalizeKnowledgeBaseAccess(value) {
    return {
        role_ids: [],
        position_ids: normalizeKnowledgeBaseIds(value?.position_ids),
        user_ids: normalizeKnowledgeBaseIds(value?.user_ids),
        restaurant_ids: normalizeKnowledgeBaseIds(value?.restaurant_ids),
    };
}

function areKnowledgeBaseAccessEqual(left, right) {
    const normalizedLeft = normalizeKnowledgeBaseAccess(left);
    const normalizedRight = normalizeKnowledgeBaseAccess(right);
    return ACCESS_SCOPE_KEYS.every((scopeKey) =>
        arraysEqual(normalizedLeft[scopeKey], normalizedRight[scopeKey]),
    );
}

function summarizeKnowledgeBaseAccess(value) {
    const payload = normalizeKnowledgeBaseAccess(value);
    const total = payload.position_ids.length
        + payload.user_ids.length
        + payload.restaurant_ids.length;
    if (!total) {
        return ACCESS_SUMMARY_LABELS.none;
    }
    return [
        payload.position_ids.length ? `${ACCESS_SUMMARY_LABELS.positions}: ${payload.position_ids.length}` : null,
        payload.user_ids.length ? `${ACCESS_SUMMARY_LABELS.users}: ${payload.user_ids.length}` : null,
        payload.restaurant_ids.length ? `${ACCESS_SUMMARY_LABELS.restaurants}: ${payload.restaurant_ids.length}` : null,
    ].filter(Boolean).join(', ');
}

function arraysEqual(left, right) {
    if (!Array.isArray(left) || !Array.isArray(right)) {
        return false;
    }
    if (left.length !== right.length) {
        return false;
    }
    for (let index = 0; index < left.length; index += 1) {
        if (Number(left[index]) !== Number(right[index])) {
            return false;
        }
    }
    return true;
}

export {
    areKnowledgeBaseAccessEqual,
    normalizeKnowledgeBaseAccess,
    summarizeKnowledgeBaseAccess,
};
