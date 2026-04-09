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
  let viewportPrepared = false;
  let fullscreenRequested = false;
  let nativeBackHandler = null;
  let backFallbackTimer = 0;
  const cssPixelValues = Object.create(null);

  const setCssPixelVar = function (name, rawValue) {
    const numericValue = Number(rawValue);
    const safeValue =
      Number.isFinite(numericValue) && numericValue > 0 ? numericValue : 0;
    const nextValue = `${Math.round(safeValue)}px`;
    if (cssPixelValues[name] === nextValue) {
      return;
    }
    cssPixelValues[name] = nextValue;
    document.documentElement.style.setProperty(name, nextValue);
  };

  const resolveInsetValue = function (rawValue) {
    const numericValue = Number(rawValue);
    if (!Number.isFinite(numericValue) || numericValue <= 0) {
      return 0;
    }
    return numericValue;
  };

  const syncSafeAreaInsets = function () {
    const safeAreaInset =
      webApp && webApp.safeAreaInset && typeof webApp.safeAreaInset === "object"
        ? webApp.safeAreaInset
        : {};
    const contentSafeAreaInset =
      webApp &&
      webApp.contentSafeAreaInset &&
      typeof webApp.contentSafeAreaInset === "object"
        ? webApp.contentSafeAreaInset
        : {};

    setCssPixelVar("--tg-safe-area-top", resolveInsetValue(safeAreaInset.top));
    setCssPixelVar("--tg-safe-area-right", resolveInsetValue(safeAreaInset.right));
    setCssPixelVar("--tg-safe-area-bottom", resolveInsetValue(safeAreaInset.bottom));
    setCssPixelVar("--tg-safe-area-left", resolveInsetValue(safeAreaInset.left));
    setCssPixelVar(
      "--tg-content-safe-area-top",
      resolveInsetValue(contentSafeAreaInset.top)
    );
    setCssPixelVar(
      "--tg-content-safe-area-right",
      resolveInsetValue(contentSafeAreaInset.right)
    );
    setCssPixelVar(
      "--tg-content-safe-area-bottom",
      resolveInsetValue(contentSafeAreaInset.bottom)
    );
    setCssPixelVar(
      "--tg-content-safe-area-left",
      resolveInsetValue(contentSafeAreaInset.left)
    );
  };

  const syncVisualViewport = function () {
    const visualViewport = window.visualViewport;
    const fallbackHeight = Number(
      window.innerHeight || document.documentElement.clientHeight || 0
    );

    if (!visualViewport) {
      setCssPixelVar("--tg-visual-viewport-height", fallbackHeight);
      setCssPixelVar("--tg-visual-viewport-offset-top", 0);
      setCssPixelVar("--tg-visual-viewport-bottom-offset", 0);
      return;
    }

    const visualHeight = Number(visualViewport.height || 0);
    const visualOffsetTop = Number(visualViewport.offsetTop || 0);
    const layoutViewportHeight =
      (Number.isFinite(fallbackHeight) && fallbackHeight > 0 && fallbackHeight) ||
      visualHeight ||
      0;
    const bottomOffset = Math.max(
      0,
      layoutViewportHeight - (visualHeight + visualOffsetTop)
    );

    setCssPixelVar(
      "--tg-visual-viewport-height",
      (Number.isFinite(visualHeight) && visualHeight > 0 && visualHeight) ||
        layoutViewportHeight
    );
    setCssPixelVar("--tg-visual-viewport-offset-top", visualOffsetTop);
    setCssPixelVar("--tg-visual-viewport-bottom-offset", bottomOffset);
  };

  const setAppHeight = function () {
    syncSafeAreaInsets();
    syncVisualViewport();

    const stableHeight = Number(webApp.viewportStableHeight || 0);
    const viewportHeight = Number(webApp.viewportHeight || 0);
    const visualViewportHeight = Number(
      (window.visualViewport && window.visualViewport.height) || 0
    );
    const fallbackHeight = Number(
      window.innerHeight || document.documentElement.clientHeight || 0
    );
    const resolvedHeight =
      (Number.isFinite(visualViewportHeight) &&
        visualViewportHeight > 0 &&
        visualViewportHeight) ||
      (Number.isFinite(viewportHeight) && viewportHeight > 0 && viewportHeight) ||
      (Number.isFinite(stableHeight) && stableHeight > 0 && stableHeight) ||
      (Number.isFinite(fallbackHeight) && fallbackHeight > 0 && fallbackHeight) ||
      0;
    if (resolvedHeight > 0) {
      setCssPixelVar("--tg-app-height", resolvedHeight);
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

  const clearBackFallbackTimer = function () {
    if (!backFallbackTimer) {
      return;
    }

    window.clearTimeout(backFallbackTimer);
    backFallbackTimer = 0;
  };

  const hideNativeBackButton = function () {
    const backButton = webApp.BackButton;
    clearBackFallbackTimer();
    document.body.classList.remove("tg-native-back");
    if (!backButton) {
      nativeBackHandler = null;
      return;
    }

    if (nativeBackHandler && typeof backButton.offClick === "function") {
      try {
        backButton.offClick(nativeBackHandler);
      } catch (_error) {
        // Ignore Telegram back button cleanup errors.
      }
    }

    if (typeof backButton.hide === "function") {
      try {
        backButton.hide();
      } catch (_error) {
        // Ignore Telegram back button visibility errors.
      }
    }

    nativeBackHandler = null;
  };

  const configureNativeBackButton = function () {
    hideNativeBackButton();
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
  configureNativeBackButton();

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
    webApp.onEvent("safeAreaChanged", scheduleHeightSync);
    webApp.onEvent("contentSafeAreaChanged", scheduleHeightSync);
  }
  window.addEventListener("resize", scheduleHeightSync, { passive: true });
  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", scheduleHeightSync, {
      passive: true,
    });
    window.visualViewport.addEventListener("scroll", scheduleHeightSync, {
      passive: true,
    });
  }
  window.addEventListener("pagehide", clearBackFallbackTimer, { passive: true });
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
