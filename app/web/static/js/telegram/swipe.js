(function telegramSwipeModule() {
  const ns = (window.__msiTelegramInit = window.__msiTelegramInit || {});

  ns.createSwipeController = function createSwipeController(webApp) {
    let swipeLockApplied = false;
    let collapseFallbackBound = false;

    function enforceSwipeLock() {
      if (typeof webApp.disableVerticalSwipes !== "function") {
        return;
      }
      try {
        webApp.disableVerticalSwipes();
        swipeLockApplied = true;
      } catch (_error) {
        // Ignore unsupported Telegram clients.
      }
    }

    function ensureDocumentIsScrollable() {
      const viewportHeight = Number(
        window.innerHeight || document.documentElement.clientHeight || 0
      );
      const documentHeight = Number(document.documentElement.scrollHeight || 0);
      if (viewportHeight > 0 && documentHeight <= viewportHeight) {
        document.documentElement.style.setProperty("min-height", "calc(100dvh + 1px)");
        document.body.style.setProperty("min-height", "calc(100dvh + 1px)");
      }
    }

    function preventCollapseOnTopSwipe() {
      if (window.scrollY <= 0) {
        window.scrollTo(0, 1);
      }
    }

    function bindCollapseFallback() {
      if (collapseFallbackBound || typeof webApp.disableVerticalSwipes === "function") {
        return;
      }
      collapseFallbackBound = true;
      ensureDocumentIsScrollable();
      window.setTimeout(ensureDocumentIsScrollable, 100);
      document.addEventListener("touchstart", preventCollapseOnTopSwipe, {
        passive: true,
      });
      window.addEventListener("resize", ensureDocumentIsScrollable, { passive: true });
    }

    function afterSync() {
      if (!swipeLockApplied || webApp.isFullscreen === true) {
        enforceSwipeLock();
      }
    }

    return {
      enforceSwipeLock,
      bindCollapseFallback,
      afterSync,
    };
  };
})();
