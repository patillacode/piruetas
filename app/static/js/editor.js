import { Editor } from 'https://esm.sh/@tiptap/core@2';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2';
import Image from 'https://esm.sh/@tiptap/extension-image@2';
import Link from 'https://esm.sh/@tiptap/extension-link@2';
import Placeholder from 'https://esm.sh/@tiptap/extension-placeholder@2';

let editor = null;
let saveTimer = null;
let toastTimer = null;
let entryExists = !!(window.PIRUETAS?.entryExists);

// ── word count ──
function getWordCount(text) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function updateWordCount() {
  if (!editor) return;
  const count = getWordCount(editor.getText());
  const s = window.PIRUETAS?.strings || {};
  const el = document.getElementById('word-count');
  if (el) el.textContent = `${count} ${count === 1 ? (s.wordSingular || 'word') : (s.wordPlural || 'words')}`;
}

// ── save toast ──
function showToast(msg, isError = false) {
  const el = document.getElementById('save-toast');
  if (!el) return;
  clearTimeout(toastTimer);
  el.textContent = msg;
  el.classList.toggle('error', isError);
  el.classList.add('show');
  if (!isError) {
    toastTimer = setTimeout(() => el.classList.remove('show'), 2000);
  }
}

// ── delete button ──
function updateDeleteBtn() {
  const btn = document.getElementById('delete-btn');
  if (btn) btn.hidden = !entryExists;
}

// ── auto-save ──
async function save() {
  if (!editor || !window.PIRUETAS?.saveUrl) return;
  const content = editor.getHTML();
  try {
    const res = await fetch(window.PIRUETAS.saveUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    if (res.ok) entryExists = true;
    const s = window.PIRUETAS?.strings || {};
    showToast(res.ok ? (s.saved || 'Saved') : (s.errorSaving || 'Error saving'), !res.ok);
    if (res.ok) updateDeleteBtn();
  } catch {
    const s = window.PIRUETAS?.strings || {};
    showToast(s.errorSaving || 'Error saving', true);
  }
}

function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, 2000);
}

// ── toolbar ──
function updateToolbar() {
  if (!editor) return;
  document.querySelectorAll('#editor-toolbar [data-action]').forEach(btn => {
    const a = btn.dataset.action;
    if (a === 'bold') btn.classList.toggle('active', editor.isActive('bold'));
    else if (a === 'italic') btn.classList.toggle('active', editor.isActive('italic'));
    else if (a === 'link') btn.classList.toggle('active', editor.isActive('link'));
    else if (a === 'undo') btn.disabled = !editor.can().undo();
    else if (a === 'redo') btn.disabled = !editor.can().redo();
  });
}

function handleToolbarClick(e) {
  const btn = e.target.closest('[data-action]');
  if (!btn || !editor) return;
  e.preventDefault();
  const a = btn.dataset.action;
  if (a === 'bold') editor.chain().focus().toggleBold().run();
  else if (a === 'italic') editor.chain().focus().toggleItalic().run();
  else if (a === 'link') {
    const url = prompt('Enter URL:');
    if (url) editor.chain().focus().setLink({ href: url }).run();
    else editor.chain().focus().unsetLink().run();
  } else if (a === 'undo') editor.chain().focus().undo().run();
  else if (a === 'redo') editor.chain().focus().redo().run();
  else if (a === 'image') triggerImageUpload();
}

// ── image upload ──
async function uploadAndInsertImage(file) {
  const form = new FormData();
  form.append('file', file);
  try {
    const res = await fetch('/upload', { method: 'POST', body: form });
    if (res.ok) {
      const { url } = await res.json();
      if (url && /^(\/|https:\/\/)/.test(url)) {
        editor.chain().focus().setImage({ src: url }).run();
      }
    }
  } catch {
    const s = window.PIRUETAS?.strings || {};
    showToast(s.errorSaving || 'Error saving', true);
  }
}

function triggerImageUpload() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'image/jpeg,image/png,image/gif,image/webp';
  input.onchange = () => { if (input.files[0]) uploadAndInsertImage(input.files[0]); };
  input.click();
}

// ── drag & drop ──
function setupDragDrop(wrapper) {
  const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  wrapper.addEventListener('dragover', (e) => {
    if ([...e.dataTransfer.types].includes('Files')) {
      e.preventDefault();
      wrapper.classList.add('drag-over');
    }
  });
  wrapper.addEventListener('dragleave', (e) => {
    if (!wrapper.contains(e.relatedTarget)) wrapper.classList.remove('drag-over');
  });
  wrapper.addEventListener('drop', async (e) => {
    wrapper.classList.remove('drag-over');
    const files = [...e.dataTransfer.files].filter(f => IMAGE_TYPES.includes(f.type));
    if (!files.length) return;
    e.preventDefault();
    editor.commands.focus();
    for (const file of files) await uploadAndInsertImage(file);
  });
}

// ── delete ──
function setupDelete() {
  const deleteBtn = document.getElementById('delete-btn');
  const sheetDeleteBtn = document.getElementById('sheet-delete-btn');
  const modal = document.getElementById('delete-modal');
  const cancelBtn = document.getElementById('delete-modal-cancel');
  const confirmBtn = document.getElementById('delete-modal-confirm');
  const warning = document.getElementById('delete-modal-warning');
  if (!modal || !confirmBtn) return;

  const cfg = window.PIRUETAS;

  function openModal() {
    const isShared = !!(cfg.shareToken);
    warning.hidden = !isShared;
    modal.hidden = false;
    cancelBtn.focus();
  }

  function closeModal() {
    modal.hidden = true;
  }

  deleteBtn?.addEventListener('click', openModal);
  sheetDeleteBtn?.addEventListener('click', () => {
    window._closeSheet?.();
    setTimeout(openModal, 290);
  });
  cancelBtn?.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !modal.hidden) closeModal(); });

  confirmBtn.addEventListener('click', async () => {
    confirmBtn.disabled = true;
    try {
      if (cfg.shareToken) {
        await fetch(cfg.saveUrl + '/share', { method: 'DELETE' });
        cfg.shareToken = '';
      }
      const res = await fetch(cfg.saveUrl, { method: 'DELETE' });
      if (res.ok) {
        if (cfg.entryDate) {
          const [, , d] = cfg.entryDate.split('-').map(Number);
          window.calendarRemoveEntry?.(d);
        }
        window.location.href = '/';
      } else {
        showToast(cfg.strings.errorSaving || 'Error', true);
        confirmBtn.disabled = false;
        closeModal();
      }
    } catch {
      showToast(cfg.strings.errorSaving || 'Error', true);
      confirmBtn.disabled = false;
      closeModal();
    }
  });
}

// ── share ──
function setupShare() {
  const shareBtn = document.getElementById('share-btn');
  const shareBtnMobile = document.getElementById('share-btn-mobile');
  const copyLinkBtn = document.getElementById('copy-link-btn');
  const sheetCopyLink = document.getElementById('sheet-copy-link');
  if (!shareBtn) return;

  const cfg = window.PIRUETAS;
  const strings = cfg.strings;
  let isShared = !!(cfg.shareToken);
  let shareUrl = isShared ? `${location.origin}/share/${cfg.shareToken}` : null;

  function updateUI() {
    shareBtn.textContent = isShared ? strings.unpublish : strings.publish;
    shareBtn.classList.toggle('tbtn--active', isShared);
    if (copyLinkBtn) copyLinkBtn.hidden = !isShared;
    if (sheetCopyLink) sheetCopyLink.hidden = !isShared;
    if (shareBtnMobile) shareBtnMobile.textContent = isShared ? strings.unpublish : strings.publish;
    cfg.shareToken = isShared ? cfg.shareToken : '';
  }

  updateUI();

  // ── share modal ──
  const shareModal = document.getElementById('share-modal');
  const shareModalUrl = document.getElementById('share-modal-url');
  const shareModalCopy = document.getElementById('share-modal-copy');
  const shareModalClose = document.getElementById('share-modal-close');

  function openShareModal(url) {
    if (shareModalUrl) shareModalUrl.value = url;
    if (shareModal) shareModal.hidden = false;
  }
  function closeShareModal() {
    if (shareModal) shareModal.hidden = true;
  }

  shareModalCopy?.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(shareUrl || ''); } catch {}
    showToast(strings.copied);
    closeShareModal();
  });
  shareModalClose?.addEventListener('click', closeShareModal);
  shareModal?.addEventListener('click', (e) => { if (e.target === shareModal) closeShareModal(); });

  // ── unshare modal ──
  const unshareModal = document.getElementById('unshare-modal');
  const unshareCancel = document.getElementById('unshare-modal-cancel');
  const unshareConfirm = document.getElementById('unshare-modal-confirm');

  function openUnshareModal() {
    if (unshareModal) unshareModal.hidden = false;
  }
  function closeUnshareModal() {
    if (unshareModal) unshareModal.hidden = true;
  }

  unshareCancel?.addEventListener('click', closeUnshareModal);
  unshareModal?.addEventListener('click', (e) => { if (e.target === unshareModal) closeUnshareModal(); });
  unshareConfirm?.addEventListener('click', async () => {
    try {
      await fetch(cfg.saveUrl + '/share', { method: 'DELETE' });
      isShared = false;
      shareUrl = null;
      updateUI();
    } catch {
      showToast(strings.errorSaving || 'Error', true);
    }
    closeUnshareModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeShareModal();
      closeUnshareModal();
    }
  });

  shareBtn.addEventListener('click', async () => {
    if (isShared) {
      openUnshareModal();
    } else {
      try {
        const res = await fetch(cfg.saveUrl + '/share', { method: 'POST' });
        if (!res.ok) return;
        const data = await res.json();
        cfg.shareToken = data.url.split('/').pop();
        shareUrl = location.origin + data.url;
        isShared = true;
        updateUI();
        openShareModal(shareUrl);
      } catch {
        showToast(strings.errorSaving || 'Error', true);
      }
    }
  });

  async function copyLink() {
    if (shareUrl) {
      try { await navigator.clipboard.writeText(shareUrl); } catch {}
      showToast(strings.copied);
    }
  }

  copyLinkBtn?.addEventListener('click', copyLink);
  sheetCopyLink?.addEventListener('click', () => { copyLink(); window._closeSheet?.(); });
  shareBtnMobile?.addEventListener('click', () => shareBtn.click());
}

// ── init ──
function init() {
  if (!window.PIRUETAS) return;

  editor = new Editor({
    element: document.getElementById('editor'),
    extensions: [
      StarterKit,
      Image,
      Link.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder: window.PIRUETAS.strings?.placeholder || 'Write anything...' }),
    ],
    content: window.PIRUETAS.entryContent || '',
    onUpdate: () => { updateWordCount(); scheduleSave(); updateToolbar(); },
    onSelectionUpdate: updateToolbar,
  });

  updateWordCount();
  updateToolbar();
  updateDeleteBtn();

  const toolbar = document.getElementById('editor-toolbar');
  if (toolbar) toolbar.addEventListener('mousedown', handleToolbarClick);

  const wrapper = document.querySelector('.editor-wrapper');
  if (wrapper) setupDragDrop(wrapper);

  setupDelete();
  setupShare();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
window.addEventListener('beforeunload', () => editor?.destroy());
