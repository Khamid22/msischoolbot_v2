(function() {
  // Check if running in Telegram Mini App
  if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    
    // Expand the mini app to full height
    tg.expand();
    
    // Disable vertical swipes (prevents closing on scroll)
    tg.disableVerticalSwipes();
    
    // Add class to html for CSS targeting
    document.documentElement.classList.add('tg-miniapp');
    document.body.classList.add('tg-miniapp');
    
    // Set the viewport height
    const setAppHeight = () => {
      const height = tg.viewportStableHeight || window.innerHeight;
      document.documentElement.style.setProperty('--tg-app-height', `${height}px`);
    };
    
    setAppHeight();
    tg.onEvent('viewportChanged', setAppHeight);
    
    // Tell Telegram the app is ready
    tg.ready();
  }
})();
