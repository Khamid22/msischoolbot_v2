(function () {
  if (window.__msiTelegramMiniAppInitDone) {
    return;
  }

  const telegram = window.Telegram;
  const webApp = telegram && telegram.WebApp;
  if (!webApp) {
    return;
  }

  const initData = typeof webApp.initData === "string" ? webApp.initData.trim() : "";
  const hasQueryInitData = /(?:^|[?&])tgWebAppData=/.test(window.location.search);
  const isMiniApp = Boolean(initData) || hasQueryInitData;
  if (!isMiniApp) {
    return;
  }

  window.__msiTelegramMiniAppInitDone = true;
  window.__msiIsTelegramMiniApp = true;

  let scheduledFrame = 0;
  let lastHeightValue = "";
  let viewportPrepared = false;
  let fullscreenRequested = false;

  const setAppHeight = function () {
    const stableHeight = Number(webApp.viewportStableHeight || 0);
    const viewportHeight = Number(webApp.viewportHeight || 0);
    const fallbackHeight = Number(window.innerHeight || 0);
    const resolvedHeight =
      (Number.isFinite(stableHeight) && stableHeight > 0 && stableHeight) ||
      (Number.isFinite(viewportHeight) && viewportHeight > 0 && viewportHeight) ||
      (Number.isFinite(fallbackHeight) && fallbackHeight > 0 && fallbackHeight) ||
      0;
    if (resolvedHeight > 0) {
      const nextHeightValue = `${Math.round(resolvedHeight)}px`;
      if (nextHeightValue !== lastHeightValue) {
        lastHeightValue = nextHeightValue;
        document.documentElement.style.setProperty("--tg-app-height", nextHeightValue);
      }
    }
  };

  const prepareViewport = function () {
    setAppHeight();
    if (viewportPrepared) {
      return;
    }

    viewportPrepared = true;
    setAppHeight();
    try {
      webApp.expand();
    } catch (_error) {
      // Ignore Telegram viewport errors.
    }
    if (typeof webApp.disableVerticalSwipes === "function") {
      try {
        webApp.disableVerticalSwipes();
      } catch (_error) {
        // Ignore Telegram swipe setup errors.
      }
    }
  };

  const requestFullscreenIfAvailable = function () {
    if (fullscreenRequested) {
      return;
    }

    if (webApp.isFullscreen === true) {
      fullscreenRequested = true;
      return;
    }

    if (typeof webApp.requestFullscreen !== "function") {
      return;
    }

    fullscreenRequested = true;
    try {
      webApp.requestFullscreen();
    } catch (_error) {
      // Ignore Telegram fullscreen errors on clients that reject the request.
    }
  };

  const scheduleHeightSync = function () {
    if (scheduledFrame) {
      return;
    }
    scheduledFrame = window.requestAnimationFrame(function () {
      scheduledFrame = 0;
      setAppHeight();
    });
  };

  document.documentElement.classList.add("tg-miniapp");
  document.body.classList.add("tg-miniapp");
  prepareViewport();

  const loginTelegramUserIdInput = document.getElementById("loginTelegramUserId");
  const telegramUserId =
    webApp &&
    webApp.initDataUnsafe &&
    webApp.initDataUnsafe.user &&
    Number(webApp.initDataUnsafe.user.id);
  if (
    loginTelegramUserIdInput &&
    Number.isInteger(telegramUserId) &&
    telegramUserId > 0
  ) {
    loginTelegramUserIdInput.value = String(telegramUserId);

    const currentUrl = new URL(window.location.href);
    const loggedOut = currentUrl.searchParams.get("logged_out") === "1";
    const currentTelegramUserId = Number(currentUrl.searchParams.get("tg_user_id"));
    if (!loggedOut && currentTelegramUserId !== telegramUserId) {
      currentUrl.searchParams.set("tg_user_id", String(telegramUserId));
      window.location.replace(currentUrl.toString());
      return;
    }
  }

  if (typeof webApp.onEvent === "function") {
    webApp.onEvent("viewportChanged", scheduleHeightSync);
    webApp.onEvent("fullscreenChanged", scheduleHeightSync);
  }
  window.addEventListener("resize", scheduleHeightSync, { passive: true });
  window.setTimeout(setAppHeight, 180);

  try {
    webApp.ready();
  } catch (_error) {
    // Ignore Telegram ready errors.
  }

  window.setTimeout(function () {
    requestFullscreenIfAvailable();
    scheduleHeightSync();
  }, 40);
})();
