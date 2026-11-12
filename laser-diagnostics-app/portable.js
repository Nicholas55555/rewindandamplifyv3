/* Portable-export adapter. The folder app and its scientific data are unchanged. */
'use strict';
(() => {
  const registry = JSON.parse(document.getElementById('portable-files').textContent);
  const urls = new Map();
  function fileUrl(path) {
    if (!urls.has(path)) {
      const file = registry.files[path];
      const binary = atob(registry.blobs[file.sha256]);
      const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
      urls.set(path, URL.createObjectURL(new Blob([bytes], {type: file.mime})));
    }
    return urls.get(path);
  }
  function resolveLink(link) {
    const path = link.getAttribute('href');
    const file = registry.files[path];
    if (!file) return;
    link.dataset.portablePath = path;
    link.href = fileUrl(path);
    if (path.startsWith('assets/') && !link.hasAttribute('download')) {
      link.title = 'Open embedded media: ' + path;
      return;
    }
    link.download = file.filename;
    link.removeAttribute('target');
    link.title = 'Save embedded file: ' + path;
  }
  function resolveLinks(root = document) {
    if (root.matches?.('a[href]')) resolveLink(root);
    root.querySelectorAll?.('a[href]').forEach(resolveLink);
  }
  resolveLinks();
  const observer = new MutationObserver(records => {
    for (const record of records) {
      if (record.type === 'attributes') resolveLink(record.target);
      else record.addedNodes.forEach(resolveLinks);
    }
  });
  observer.observe(document.body, {subtree: true, childList: true, attributes: true, attributeFilter: ['href']});
  // Cover a programmatically changed href even before the observer microtask.
  document.addEventListener('click', event => {
    const link = event.target.closest?.('a[href]');
    if (link) resolveLink(link);
  }, true);
  window.PORTABLE_DEMO = {files: registry.files, ready: Promise.resolve(), resolveLinks};
})();
