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
    return Boolean(initData) || hasQueryInitData;
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
      .register("/static/js/sw.js")
      .catch(function (error) {
        console.error("Service worker registration failed:", error);
      });
  });
})();
