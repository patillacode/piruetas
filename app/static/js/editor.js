import { Editor } from 'https://esm.sh/@tiptap/core@2';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@2';
import Image from 'https://esm.sh/@tiptap/extension-image@2';
import Link from 'https://esm.sh/@tiptap/extension-link@2';
import Placeholder from 'https://esm.sh/@tiptap/extension-placeholder@2';

let editor = null;
let saveTimer = null;
let toastTimer = null;

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

// ── auto-save ──
async function save() {
  if (!editor || !window.PIRUETAS?.saveUrl) return;
  const content = editor.getHTML();
  const word_count = getWordCount(editor.getText());
  try {
    const res = await fetch(window.PIRUETAS.saveUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content, word_count }),
    });
    const s = window.PIRUETAS?.strings || {};
    showToast(res.ok ? (s.saved || 'Saved') : (s.errorSaving || 'Error saving'), !res.ok);
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
  } catch { /* silent */ }
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

// ── share ──
function setupShare() {
  const btns = [
    document.getElementById('share-btn'),
    document.getElementById('share-btn-mobile'),
  ].filter(Boolean);
  const popup = document.getElementById('share-popup');
  const urlInput = document.getElementById('share-url');
  const copyBtn = document.getElementById('copy-share-btn');
  if (!btns.length || !popup) return;

  btns.forEach(btn => btn.addEventListener('click', async () => {
    const saveUrl = window.PIRUETAS?.saveUrl;
    if (!saveUrl) return;
    if (!popup.hidden) { popup.hidden = true; return; }
    try {
      const res = await fetch(saveUrl + '/share', { method: 'POST' });
      if (!res.ok) return;
      const { url } = await res.json();
      urlInput.value = window.location.origin + url;
      if (window.innerWidth <= 768) {
        popup.style.top = '64px';
        popup.style.left = '8px';
        popup.style.right = '8px';
        popup.style.width = 'auto';
      } else {
        popup.style.right = '';
        popup.style.width = '';
        const rect = btn.getBoundingClientRect();
        popup.style.top = `${rect.bottom + 6}px`;
        popup.style.left = `${Math.max(8, rect.left - 20)}px`;
      }
      popup.hidden = false;
      urlInput.select();
    } catch { /* silent */ }
  }));

  document.addEventListener('click', (e) => {
    if (!popup.hidden && !popup.contains(e.target) && !btns.includes(e.target)) {
      popup.hidden = true;
    }
  });

  copyBtn?.addEventListener('click', () => {
    navigator.clipboard.writeText(urlInput.value);
    const s = window.PIRUETAS?.strings || {};
    copyBtn.textContent = s.copied || 'Copied!';
    setTimeout(() => { copyBtn.textContent = s.copy || 'Copy'; }, 1500);
  });
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

  const toolbar = document.getElementById('editor-toolbar');
  if (toolbar) toolbar.addEventListener('mousedown', handleToolbarClick);

  const wrapper = document.querySelector('.editor-wrapper');
  if (wrapper) setupDragDrop(wrapper);

  setupShare();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
window.addEventListener('beforeunload', () => editor?.destroy());
