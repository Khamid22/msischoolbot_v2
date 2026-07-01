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
})();
