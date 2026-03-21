function normalizeExtension(value) {
    return String(value || '').trim().toLowerCase().replace(/^\./, '');
}

function normalizeMimeType(value) {
    return String(value || '').trim().toLowerCase();
}

function isKnowledgeBaseWordDocument(item) {
    const extension = normalizeExtension(item?.extension);
    if (extension === 'doc' || extension === 'docx' || extension === 'rtf' || extension === 'odt') {
        return true;
    }
    const mimeType = normalizeMimeType(item?.mime_type);
    return mimeType.includes('word') || mimeType.includes('wordprocessingml');
}

function isKnowledgeBaseSpreadsheetDocument(item) {
    if (item?.preview_type === 'spreadsheet') {
        return true;
    }
    const extension = normalizeExtension(item?.extension);
    if (extension === 'xls' || extension === 'xlsx' || extension === 'csv' || extension === 'ods') {
        return true;
    }
    const mimeType = normalizeMimeType(item?.mime_type);
    return mimeType.includes('spreadsheet') || mimeType.includes('excel') || mimeType.includes('sheet');
}

export {
    isKnowledgeBaseSpreadsheetDocument,
    isKnowledgeBaseWordDocument,
};
