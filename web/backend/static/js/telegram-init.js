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

  // Hand the *signed* initData to the server. The backend verifies its HMAC
  // before trusting the Telegram identity, so we never send a forgeable raw id.
  function authenticateWithTelegram(webApp) {
    const initData = webApp && typeof webApp.initData === "string" ? webApp.initData : "";
    if (!initData) {
      return;
    }

    // Stash the signed blob on the login form so credential login can link the
    // Telegram account through the same server-side verification.
    const initDataInput = document.getElementById("loginTelegramInitData");
    if (initDataInput) {
      initDataInput.value = initData;
    }

    // Skip silent auto-login right after an explicit logout.
    const currentUrl = new URL(window.location.href);
    if (currentUrl.searchParams.get("logged_out") === "1") {
      return;
    }

    const body = new URLSearchParams();
    body.set("init_data", initData);
    fetch("/auth/telegram", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      credentials: "same-origin",
      body: body.toString(),
    })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (data) {
        if (data && data.ok && data.redirect) {
          const targetUrl = new URL(data.redirect, window.location.href);
          const currentUrl = new URL(window.location.href);
          if (targetUrl.href !== currentUrl.href) {
            window.location.replace(targetUrl.href);
          }
        }
      })
      .catch(function () {
        // Network failures fall back to the manual login form.
      });
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
      authenticateWithTelegram(webApp);

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
