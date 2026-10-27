/* Progressive enhancement: all content is visible without scripting. */
(() => {
  if (!('IntersectionObserver' in window) || !Element.prototype.animate) return;
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const running = new Set();
  const toggle = document.querySelector('.motion-toggle');
  let userPaused = false;
  let heroVisible = true;
  const updatePause = () => document.documentElement.classList.toggle(
    'motion-paused', userPaused || document.hidden || !heroVisible || preference.matches
  );
  if (toggle) {
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
      userPaused = !userPaused;
      toggle.setAttribute('aria-pressed', String(userPaused));
      toggle.textContent = userPaused ? 'Resume motion' : 'Pause motion';
      updatePause();
    });
  }
  const heroObserver = new IntersectionObserver((entries) => {
    heroVisible = entries[0].isIntersecting;
    updatePause();
  });
  const hero = document.querySelector('.hero');
  if (hero) heroObserver.observe(hero);
  updatePause();
  document.documentElement.classList.add('motion-enabled');
  const details = document.querySelectorAll(
    '#demo .section-top, section:not(#demo) > .section-top > p, .console, .engineering-steps article, .outcomes > div, ' +
    '.platform-evidence > div, .learning-copy > p, .learning-flow, ' +
    '.comparison, .eval-principles > div, .video-placeholder'
  );
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      if (preference.matches || entry.target.contains(document.activeElement)) continue;
      const animation = entry.target.animate(
        [{opacity: 0.2, transform: 'translateY(14px)'}, {opacity: 1, transform: 'translateY(0)'}],
        {duration: 420, easing: 'cubic-bezier(.2,.7,.2,1)'}
      );
      running.add(animation);
      animation.finished.then(() => running.delete(animation), () => running.delete(animation));
    }
  }, {threshold: 0, rootMargin: '0px 0px -32px 0px'});
  for (const detail of details) {
    // Keep initial viewport content immediately visible, including deep links.
    const box = detail.getBoundingClientRect();
    if (box.top >= window.innerHeight) observer.observe(detail);
  }
  const finishMotion = () => {
    for (const animation of running) animation.cancel();
    running.clear();
  };
  preference.addEventListener('change', () => { if (preference.matches) finishMotion(); updatePause(); });
  document.addEventListener('focusin', finishMotion);
  document.addEventListener('visibilitychange', () => {
    updatePause();
    if (document.hidden) finishMotion();
  });
  window.addEventListener('beforeprint', finishMotion);
})();
