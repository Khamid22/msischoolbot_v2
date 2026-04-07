(function () {
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
