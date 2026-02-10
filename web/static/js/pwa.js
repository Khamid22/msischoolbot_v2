(function () {
  function isTelegramMiniApp(webApp) {
    if (!webApp) {
      return false;
    }
    const initData = typeof webApp.initData === "string" ? webApp.initData.trim() : "";
    const hasQueryInitData = /(?:^|[?&])tgWebAppData=/.test(window.location.search);
    return Boolean(initData) || hasQueryInitData;
  }

  document.addEventListener("DOMContentLoaded", function () {
    const webApp = typeof Telegram !== "undefined" ? Telegram.WebApp : null;
    if (
      isTelegramMiniApp(webApp) &&
      typeof webApp.disableVerticalSwipes === "function"
    ) {
      webApp.disableVerticalSwipes();
    }
  });

  function initTelegramMiniApp() {
    const telegram = window.Telegram;
    const webApp = telegram && telegram.WebApp;
    if (!webApp || !isTelegramMiniApp(webApp)) {
      document.documentElement.classList.remove("tg-miniapp");
      document.body.classList.remove("tg-miniapp");
      return;
    }

    document.documentElement.classList.add("tg-miniapp");
    document.body.classList.add("tg-miniapp");

    const supportsSwipeLock = typeof webApp.disableVerticalSwipes === "function";
    const resolveViewportHeight = function () {
      const stableHeight = Number(webApp.viewportStableHeight || 0);
      if (Number.isFinite(stableHeight) && stableHeight > 0) {
        return stableHeight;
      }

      const viewportHeight = Number(webApp.viewportHeight || 0);
      if (Number.isFinite(viewportHeight) && viewportHeight > 0) {
        return viewportHeight;
      }
      return 0;
    };

    const applyViewportHeight = function () {
      const viewportHeight = resolveViewportHeight();
      if (viewportHeight <= 0) {
        return;
      }

      const heightValue = `${Math.round(viewportHeight)}px`;
      document.documentElement.style.setProperty("--tg-app-height", heightValue);
      document.documentElement.style.height = heightValue;
      document.body.style.height = heightValue;
    };

    const applyViewportLock = function () {
      applyViewportHeight();

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
    window.setTimeout(applyViewportLock, 120);
    window.setTimeout(applyViewportLock, 420);

    if (typeof webApp.onEvent === "function") {
      webApp.onEvent("viewportChanged", applyViewportLock);
    }

    let touchStartY = 0;
    let touchStartX = 0;

    function findScrollableParent(target) {
      let node = target;
      while (node && node !== document.body) {
        if (!(node instanceof HTMLElement)) {
          node = node && node.parentElement;
          continue;
        }

        const style = window.getComputedStyle(node);
        const canScrollY =
          (style.overflowY === "auto" || style.overflowY === "scroll") &&
          node.scrollHeight > node.clientHeight + 1;
        if (canScrollY) {
          return node;
        }
        node = node.parentElement;
      }
      return null;
    }

    function resolveRootScroller() {
      const dashboardWrap = document.querySelector(".dashboard-wrap");
      if (dashboardWrap instanceof HTMLElement) {
        return dashboardWrap;
      }

      const homeWrap = document.querySelector(".home-wrap");
      if (homeWrap instanceof HTMLElement) {
        return homeWrap;
      }

      return null;
    }

    document.addEventListener(
      "touchstart",
      function (event) {
        if (!event.touches || event.touches.length !== 1) {
          return;
        }
        touchStartX = event.touches[0].clientX;
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

        const currentX = event.touches[0].clientX;
        const currentY = event.touches[0].clientY;
        const deltaX = currentX - touchStartX;
        const deltaY = currentY - touchStartY;
        const isHorizontalGesture = Math.abs(deltaX) > Math.abs(deltaY);
        if (isHorizontalGesture) {
          return;
        }

        const pullingDown = currentY > touchStartY;
        if (!pullingDown) {
          return;
        }

        const scrollableParent = findScrollableParent(event.target);
        const rootScroller = resolveRootScroller();
        const atTop = scrollableParent
          ? scrollableParent.scrollTop <= 0
          : rootScroller
            ? rootScroller.scrollTop <= 0
            : true;

        if (atTop && event.cancelable) {
          event.preventDefault();
          applyViewportLock();
        }
      },
      { passive: false }
    );
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
