(function telegramOrchestrator() {
  if (window.__msiTelegramMiniAppInitDone) {
    return;
  }

  const ns = window.__msiTelegramInit || {};
  if (
    typeof ns.runWithWebApp !== "function" ||
    typeof ns.createSafeAreaController !== "function" ||
    typeof ns.createFullscreenController !== "function" ||
    typeof ns.createSwipeController !== "function" ||
    typeof ns.createBackButtonController !== "function"
  ) {
    return;
  }

  function hydrateLoginTelegramUserId(webApp) {
    const input = document.getElementById("loginTelegramUserId");
    const telegramUserId =
      webApp &&
      webApp.initDataUnsafe &&
      webApp.initDataUnsafe.user &&
      Number(webApp.initDataUnsafe.user.id);

    if (!input || !Number.isInteger(telegramUserId) || telegramUserId <= 0) {
      return;
    }

    input.value = String(telegramUserId);
    const currentUrl = new URL(window.location.href);
    const loggedOut = currentUrl.searchParams.get("logged_out") === "1";
    const currentTelegramUserId = Number(currentUrl.searchParams.get("tg_user_id"));
    if (!loggedOut && currentTelegramUserId !== telegramUserId) {
      currentUrl.searchParams.set("tg_user_id", String(telegramUserId));
      window.location.replace(currentUrl.toString());
    }
  }

  ns.runWithWebApp(
    function onReady(webApp) {
      if (window.__msiTelegramMiniAppInitDone) {
        return;
      }
      window.__msiTelegramMiniAppInitDone = true;
      window.__msiIsTelegramMiniApp = true;

      document.documentElement.classList.add("tg-miniapp");
      document.body.classList.add("tg-miniapp");

      const safeArea = ns.createSafeAreaController(webApp);
      const fullscreen = ns.createFullscreenController(webApp);
      const swipe = ns.createSwipeController(webApp);
      const backButton = ns.createBackButtonController(webApp);

      safeArea.syncAppHeight();
      try {
        webApp.expand();
      } catch (_error) {
        // Ignore viewport expansion failures.
      }
      fullscreen.requestFullscreenIfAvailable();
      swipe.enforceSwipeLock();
      swipe.bindCollapseFallback();
      backButton.configureFromDocument();
      hydrateLoginTelegramUserId(webApp);

      const scheduleSync = function scheduleSync() {
        safeArea.scheduleSync(swipe.afterSync);
      };

      if (typeof webApp.onEvent === "function") {
        webApp.onEvent("viewportChanged", scheduleSync);
        webApp.onEvent("fullscreenChanged", scheduleSync);
        webApp.onEvent("safeAreaChanged", scheduleSync);
        webApp.onEvent("contentSafeAreaChanged", scheduleSync);
      }
      window.addEventListener("resize", scheduleSync, { passive: true });
      if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", scheduleSync, {
          passive: true,
        });
        window.visualViewport.addEventListener("scroll", scheduleSync, {
          passive: true,
        });
      }

      try {
        webApp.ready();
      } catch (_error) {
        // Ignore ready() failures on unsupported clients.
      }

      window.setTimeout(scheduleSync, 120);
      window.setTimeout(scheduleSync, 420);
    },
    24
  );
})();
