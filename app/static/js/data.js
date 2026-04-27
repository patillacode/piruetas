const strings = window.PIRUETAS_DATA.strings;

const scopeEl = document.getElementById('export-scope');
const yearEl = document.getElementById('export-year');
const monthEl = document.getElementById('export-month');

function updateExportVisibility() {
    const s = scopeEl.value;
    yearEl.hidden = !['year', 'month'].includes(s);
    monthEl.hidden = s !== 'month';
}
scopeEl.addEventListener('change', updateExportVisibility);
updateExportVisibility();

const exportModal = document.getElementById('export-modal');
exportModal.addEventListener('click', (ev) => {
    if (ev.target === exportModal || ev.target.id === 'export-modal-close') {
        exportModal.hidden = true;
    }
});

document.getElementById('export-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const res = await fetch('/account/export/preview', { method: 'POST', body: data });
    const json = await res.json();
    const body = document.getElementById('export-modal-body');
    const actions = document.getElementById('export-modal-actions');

    body.textContent = '';
    actions.textContent = '';

    if (json.count === 0) {
        body.textContent = strings.noEntriesFound;
        const closeBtn = document.createElement('button');
        closeBtn.className = 'btn-ghost';
        closeBtn.id = 'export-modal-close';
        closeBtn.textContent = strings.close;
        actions.appendChild(closeBtn);
    } else {
        body.textContent = strings.exportFound
            .replace('{count}', json.count)
            .replace('{entries}', json.count === 1 ? strings.entrySingular : strings.entryPlural)
            .replace('{scope_label}', json.scope_label);

        const closeBtn = document.createElement('button');
        closeBtn.className = 'btn-ghost';
        closeBtn.id = 'export-modal-close';
        closeBtn.textContent = strings.close;
        actions.appendChild(closeBtn);

        const textLink = document.createElement('a');
        textLink.href = json.text_url;
        textLink.className = 'btn btn-primary export-download-btn';
        textLink.textContent = strings.downloadText;
        actions.appendChild(textLink);

        const jsonLink = document.createElement('a');
        jsonLink.href = json.json_url;
        jsonLink.className = 'btn btn-primary export-download-btn';
        jsonLink.textContent = strings.downloadJson;
        actions.appendChild(jsonLink);
    }

    const modal = document.getElementById('export-modal');
    modal.hidden = false;
});

const deleteScopeEl = document.getElementById('delete-scope');
const deleteYearEl = document.getElementById('delete-year');
const deleteMonthEl = document.getElementById('delete-month');

function updateDeleteVisibility() {
    const s = deleteScopeEl.value;
    deleteYearEl.hidden = !['year', 'month'].includes(s);
    deleteMonthEl.hidden = s !== 'month';
}
deleteScopeEl.addEventListener('change', updateDeleteVisibility);
updateDeleteVisibility();

const deleteModal = document.getElementById('delete-modal');
deleteModal.addEventListener('click', (ev) => {
    if (ev.target === deleteModal || ev.target.closest('#delete-modal-cancel')) {
        deleteModal.hidden = true;
    }
});

document.getElementById('delete-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const res = await fetch('/account/delete/preview', { method: 'POST', body: new FormData(e.target) });
    const json = await res.json();
    const count = json.count;
    const entries = count === 1 ? strings.entrySingular : strings.entryPlural;

    const body = document.getElementById('delete-modal-body');
    const warning = document.getElementById('delete-modal-warning');
    const actions = document.getElementById('delete-modal-actions');

    body.textContent = strings.deleteConfirmMsg
        .replace('{count}', count)
        .replace('{entries}', entries);

    warning.textContent = strings.deleteExportWarning;

    actions.textContent = '';
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn-ghost';
    cancelBtn.id = 'delete-modal-cancel';
    cancelBtn.textContent = strings.cancel;
    actions.appendChild(cancelBtn);

    if (count > 0) {
        const confirmBtn = document.createElement('button');
        confirmBtn.className = 'btn btn-danger';
        confirmBtn.textContent = strings.deleteConfirmBtn
            .replace('{count}', count)
            .replace('{entries}', entries);
        confirmBtn.addEventListener('click', async () => {
            const confirmData = new FormData(document.getElementById('delete-form'));
            const confirmRes = await fetch('/account/delete/confirm', { method: 'POST', body: confirmData });
            if (!confirmRes.ok) return;
            const confirmJson = await confirmRes.json();
            deleteModal.hidden = true;
            const successEl = document.getElementById('delete-success');
            successEl.textContent = strings.entriesDeleted
                .replace('{count}', confirmJson.deleted)
                .replace('{entries}', confirmJson.deleted === 1 ? strings.entrySingular : strings.entryPlural);
            successEl.hidden = false;
        });
        actions.appendChild(confirmBtn);
    }

    deleteModal.hidden = false;
});
