function toggleFooterAccordion(btn, panelId) {
  if (window.innerWidth >= 1024) return;
  const panel = document.getElementById(panelId);
  const expanded = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', !expanded);
  if (!expanded) {
    panel.style.maxHeight = panel.scrollHeight + 'px';
  } else {
    panel.style.maxHeight = '0';
  }
}
window.addEventListener('resize', function () {
  if (window.innerWidth >= 1024) {
    document.getElementById('footer-company-links').style.maxHeight = null;
  } else {
    document.getElementById('footer-company-links').style.maxHeight = '0';
  }
});
