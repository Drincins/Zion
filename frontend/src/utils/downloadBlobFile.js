export function downloadBlobFile(blobPayload, fileName, options = {}) {
    if (!fileName) {
        return;
    }

    const blob =
        blobPayload instanceof Blob
            ? blobPayload
            : new Blob([blobPayload], options.type ? { type: options.type } : undefined);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
}
