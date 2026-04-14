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
})();
