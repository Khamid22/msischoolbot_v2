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
})();
