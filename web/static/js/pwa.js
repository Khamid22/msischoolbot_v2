(function () {
  if (!('serviceWorker' in navigator)) {
    return;
  }

  window.addEventListener('load', async function () {
    try {
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map(function (registration) {
        return registration.unregister();
      }));

      if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map(function (key) {
          return caches.delete(key);
        }));
      }
    } catch (error) {
      console.error('PWA cache cleanup failed:', error);
    }
  });
})();
