(function () {
  function initTelegramMiniApp() {
    const telegram = window.Telegram;
    const webApp = telegram && telegram.WebApp;
    if (!webApp) {
      return;
    }

    document.documentElement.classList.add("tg-miniapp");
    document.body.classList.add("tg-miniapp");

    const supportsSwipeLock = typeof webApp.disableVerticalSwipes === "function";

    const applyViewportLock = function () {
      try {
        webApp.expand();
      } catch (_error) {
        // Ignore Telegram viewport errors.
      }

      if (supportsSwipeLock) {
        try {
          webApp.disableVerticalSwipes();
        } catch (_error) {
          // Ignore Telegram swipe setup errors.
        }
      }
    };

    try {
      webApp.ready();
    } catch (_error) {
      // Ignore Telegram ready errors.
    }

    applyViewportLock();

    if (typeof webApp.onEvent === "function") {
      webApp.onEvent("viewportChanged", applyViewportLock);
    }

    if (!supportsSwipeLock) {
      let touchStartY = 0;
      document.addEventListener(
        "touchstart",
        function (event) {
          if (!event.touches || event.touches.length !== 1) {
            return;
          }
          touchStartY = event.touches[0].clientY;
        },
        { passive: true }
      );

      document.addEventListener(
        "touchmove",
        function (event) {
          if (!event.touches || event.touches.length !== 1) {
            return;
          }

          const currentY = event.touches[0].clientY;
          const pullingDown = currentY > touchStartY;
          const scrollElement = document.scrollingElement || document.documentElement;
          const atTop = (scrollElement && scrollElement.scrollTop <= 0) || false;
          if (pullingDown && atTop) {
            event.preventDefault();
          }
        },
        { passive: false }
      );
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initTelegramMiniApp, {
      once: true,
    });
  } else {
    initTelegramMiniApp();
  }

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
