(function () {
  const local = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  window.KAIZEN_API_BASE = local ? '' : 'https://kaizen-ai-api.onrender.com';
})();
