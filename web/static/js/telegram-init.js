(function () {
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
      document.documentElement.style.setProperty("--tg-app-height", `${Math.round(resolvedHeight)}px`);
    }
  };

  const applyViewportLock = function () {
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

  document.documentElement.classList.add("tg-miniapp");
  document.body.classList.add("tg-miniapp");
  applyViewportLock();

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
  }

  if (typeof webApp.onEvent === "function") {
    webApp.onEvent("viewportChanged", applyViewportLock);
  }
  window.addEventListener("resize", setAppHeight, { passive: true });
  window.setTimeout(applyViewportLock, 120);
  window.setTimeout(applyViewportLock, 360);

  try {
    webApp.ready();
  } catch (_error) {
    // Ignore Telegram ready errors.
  }
})();
