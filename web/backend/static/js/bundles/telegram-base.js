/* Source: js/telegram/sdk-init.js */
(function telegramSdkInitModule() {
  const ns = (window.__msiTelegramInit = window.__msiTelegramInit || {});

  ns.getWebApp = function getWebApp() {
    const telegram = window.Telegram;
    return telegram && telegram.WebApp ? telegram.WebApp : null;
  };

  ns.isMiniApp = function isMiniApp(webApp) {
    if (!webApp) {
      return false;
    }
    const initData = typeof webApp.initData === "string" ? webApp.initData.trim() : "";
    const hasQueryInitData = /(?:^|[?&])tgWebAppData=/.test(window.location.search);
    const platform = typeof webApp.platform === "string" ? webApp.platform.trim() : "";
    return Boolean(initData) || hasQueryInitData || Boolean(platform);
  };

  ns.runWithWebApp = function runWithWebApp(onReady, retriesLeft) {
    const webApp = ns.getWebApp();
    if (!webApp || !ns.isMiniApp(webApp)) {
      if (Number(retriesLeft) > 0) {
        window.setTimeout(function () {
          ns.runWithWebApp(onReady, Number(retriesLeft) - 1);
        }, 80);
      }
      return;
    }
    onReady(webApp);
  };
})();;

/* Source: js/telegram/safe-area.js */
(function telegramSafeAreaModule() {
  const ns = (window.__msiTelegramInit = window.__msiTelegramInit || {});

  function resolveInset(rawValue) {
    const numericValue = Number(rawValue);
    if (!Number.isFinite(numericValue) || numericValue <= 0) {
      return 0;
    }
    return numericValue;
  }

  ns.createSafeAreaController = function createSafeAreaController(webApp) {
    const cssPixelValues = Object.create(null);
    let scheduledFrame = 0;

    function setCssPixelVar(name, rawValue) {
      const safeValue = Math.max(0, Math.round(resolveInset(rawValue)));
      const nextValue = `${safeValue}px`;
      if (cssPixelValues[name] === nextValue) {
        return;
      }
      cssPixelValues[name] = nextValue;
      document.documentElement.style.setProperty(name, nextValue);
    }

    function readInsets() {
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

      const safeTop = resolveInset(safeAreaInset.top);
      const safeRight = resolveInset(safeAreaInset.right);
      const safeBottom = resolveInset(safeAreaInset.bottom);
      const safeLeft = resolveInset(safeAreaInset.left);

      const contentTop = resolveInset(contentSafeAreaInset.top);
      const contentRight = resolveInset(contentSafeAreaInset.right);
      const contentBottom = resolveInset(contentSafeAreaInset.bottom);
      const contentLeft = resolveInset(contentSafeAreaInset.left);

      return {
        safeTop,
        safeRight,
        safeBottom,
        safeLeft,
        contentTop,
        contentRight,
        contentBottom,
        contentLeft,
        mergedTop: Math.max(safeTop, contentTop),
        mergedRight: Math.max(safeRight, contentRight),
        mergedBottom: Math.max(safeBottom, contentBottom),
        mergedLeft: Math.max(safeLeft, contentLeft),
      };
    }

    function syncSafeAreaInsets() {
      const insets = readInsets();

      // Canonical Telegram variables.
      setCssPixelVar("--tg-safe-area-inset-top", insets.safeTop);
      setCssPixelVar("--tg-safe-area-inset-right", insets.safeRight);
      setCssPixelVar("--tg-safe-area-inset-bottom", insets.safeBottom);
      setCssPixelVar("--tg-safe-area-inset-left", insets.safeLeft);
      setCssPixelVar("--tg-content-safe-area-inset-top", insets.contentTop);
      setCssPixelVar("--tg-content-safe-area-inset-right", insets.contentRight);
      setCssPixelVar("--tg-content-safe-area-inset-bottom", insets.contentBottom);
      setCssPixelVar("--tg-content-safe-area-inset-left", insets.contentLeft);

      // Normalized app-level variables. Top/left/right/bottom insets are additive
      // (device safe area + Telegram chrome). Safe values are max() fallback edges.
      setCssPixelVar("--safe-top", insets.mergedTop);
      setCssPixelVar("--safe-right", insets.mergedRight);
      setCssPixelVar("--safe-bottom", insets.mergedBottom);
      setCssPixelVar("--safe-left", insets.mergedLeft);
      setCssPixelVar("--app-safe-top", insets.mergedTop);
      setCssPixelVar("--app-safe-right", insets.mergedRight);
      setCssPixelVar("--app-safe-bottom", insets.mergedBottom);
      setCssPixelVar("--app-safe-left", insets.mergedLeft);
      setCssPixelVar("--app-top-inset", insets.safeTop + insets.contentTop);
      setCssPixelVar("--app-right-inset", insets.safeRight + insets.contentRight);
      setCssPixelVar("--app-bottom-inset", insets.safeBottom + insets.contentBottom);
      setCssPixelVar("--app-left-inset", insets.safeLeft + insets.contentLeft);
    }

    function syncVisualViewport() {
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
    }

    function syncAppHeight() {
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
        setCssPixelVar("--tg-viewport-height", resolvedHeight);
      }
    }

    function scheduleSync(afterSync) {
      if (scheduledFrame) {
        return;
      }
      scheduledFrame = window.requestAnimationFrame(function () {
        scheduledFrame = 0;
        syncAppHeight();
        if (typeof afterSync === "function") {
          afterSync();
        }
      });
    }

    return {
      syncAppHeight,
      scheduleSync,
    };
  };
})();;

/* Source: js/telegram/fullscreen.js */
(function telegramFullscreenModule() {
  const ns = (window.__msiTelegramInit = window.__msiTelegramInit || {});

  ns.createFullscreenController = function createFullscreenController(webApp) {
    let fullscreenRequested = false;

    function requestFullscreenIfAvailable() {
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
        // Ignore clients that reject fullscreen.
      }
    }

    return {
      requestFullscreenIfAvailable,
    };
  };
})();;

/* Source: js/telegram/swipe.js */
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
})();;

/* Source: js/telegram/back-button.js */
(function telegramBackButtonModule() {
  const ns = (window.__msiTelegramInit = window.__msiTelegramInit || {});

  ns.createBackButtonController = function createBackButtonController(webApp) {
    const backButton = webApp && webApp.BackButton ? webApp.BackButton : null;
    let currentHandler = null;

    function removeHandler() {
      if (!backButton || !currentHandler || typeof backButton.offClick !== "function") {
        currentHandler = null;
        return;
      }
      try {
        backButton.offClick(currentHandler);
      } catch (_error) {
        // Ignore Telegram cleanup failures.
      }
      currentHandler = null;
    }

    function hide() {
      removeHandler();
      document.body.classList.remove("tg-native-back");
      if (!backButton || typeof backButton.hide !== "function") {
        return;
      }
      try {
        backButton.hide();
      } catch (_error) {
        // Ignore Telegram API errors.
      }
    }

    function show(handler) {
      if (!backButton || typeof backButton.show !== "function") {
        return;
      }
      removeHandler();
      currentHandler = handler;
      if (typeof backButton.onClick === "function") {
        try {
          backButton.onClick(currentHandler);
        } catch (_error) {
          currentHandler = null;
        }
      }
      try {
        backButton.show();
        document.body.classList.add("tg-native-back");
      } catch (_error) {
        // Ignore Telegram API errors.
      }
    }

    function configureFromDocument() {
      const mode = String(document.body.getAttribute("data-tg-back-mode") || "")
        .trim()
        .toLowerCase();
      const backUrl = String(document.body.getAttribute("data-tg-back-url") || "").trim();

      if (mode === "history" && window.history.length > 1) {
        show(function () {
          window.history.back();
        });
        return;
      }
      if (backUrl) {
        show(function () {
          window.location.assign(backUrl);
        });
        return;
      }
      hide();
    }

    return {
      configureFromDocument,
      hide,
    };
  };
})();;

/* Source: js/telegram-init.js */
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

    const pageName = document.body ? String(document.body.dataset.reactPage || "") : "";
    const currentUrl = new URL(window.location.href);

    // Skip silent auto-login right after an explicit logout so staff can use
    // manual credentials inside Telegram without being bounced back to the
    // linked parent/student account.
    if (currentUrl.searchParams.get("logged_out") === "1") {
      try {
        window.sessionStorage.setItem("msiManualLoginMode", "1");
      } catch (_error) {
        // Ignore storage failures; the URL guard still protects this page load.
      }
      return;
    }

    // Telegram auto-auth is only a login-page convenience. Running it on admin,
    // parent, or student pages can replace an intentional session with whichever
    // account is linked to the current Telegram user.
    if (pageName !== "login") {
      return;
    }

    try {
      if (window.sessionStorage.getItem("msiManualLoginMode") === "1") {
        return;
      }
    } catch (_error) {
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
})();;

/* Source: js/pwa.js */
(function () {
  function unregisterServiceWorkers() {
    if (!("serviceWorker" in navigator)) {
      return;
    }

    navigator.serviceWorker
      .getRegistrations()
      .then(function (registrations) {
        return Promise.all(
          registrations.map(function (registration) {
            return registration.unregister();
          })
        );
      })
      .catch(function () {
        return null;
      });
  }

  function isTelegramMiniApp(webApp) {
    if (!webApp) {
      return false;
    }
    const initData = typeof webApp.initData === "string" ? webApp.initData.trim() : "";
    const hasQueryInitData = /(?:^|[?&])tgWebAppData=/.test(window.location.search);
    const platform = typeof webApp.platform === "string" ? webApp.platform.trim() : "";
    return Boolean(initData) || hasQueryInitData || Boolean(platform);
  }

  const webApp = typeof Telegram !== "undefined" ? Telegram.WebApp : null;
  if (isTelegramMiniApp(webApp)) {
    unregisterServiceWorkers();
    return;
  }

  if (!("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", function () {
    navigator.serviceWorker
      .register("/sw.js", { updateViaCache: "none" })
      .catch(function (error) {
        console.error("Service worker registration failed:", error);
      });
  });
})();
