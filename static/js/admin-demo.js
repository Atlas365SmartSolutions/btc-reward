(function () {
  const mountNode = document.getElementById('system-record-root');
  if (!mountNode) {
    return;
  }

  mountNode.textContent = mountNode.dataset.message || '';
})();
