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
})();
