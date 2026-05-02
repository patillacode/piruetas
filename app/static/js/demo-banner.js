document.addEventListener("DOMContentLoaded", () => {
  const banner = document.querySelector(".demo-banner[data-reset-ts]");
  if (!banner) return;

  const resetTs = parseInt(banner.dataset.resetTs, 10);
  const countdown = banner.querySelector(".demo-banner__countdown");

  const tick = () => {
    const remaining = resetTs * 1000 - Date.now();
    if (remaining <= 0) {
      location.reload();
      return;
    }
    const secs = Math.ceil(remaining / 1000);
    if (secs >= 60) {
      const m = Math.floor(secs / 60);
      const s = secs % 60;
      countdown.textContent = `${m}m ${s}s`;
    } else {
      countdown.textContent = `${secs}s`;
    }
  };

  tick();
  setInterval(tick, 1000);
});
