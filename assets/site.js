// Pass utm_* tags from the page URL on to Google Play's referrer, so Play Console credits the post
// that sent the visit. Without tags, each button keeps its own utm_medium (the page it is on).
(function () {
  var q = new URLSearchParams(location.search), tags = [];
  q.forEach(function (v, k) { if (k.indexOf("utm_") === 0) tags.push(k + "=" + v); });
  if (!tags.length) return;
  var ref = encodeURIComponent(tags.join("&"));
  document.querySelectorAll("a[data-play]").forEach(function (a) {
    a.href = a.href.replace(/([?&])referrer=[^&]*/, "$1referrer=" + ref);
  });
})();

// Email signup: the block stays hidden until data-endpoint on #signup holds the provider's form URL.
// The form posts into a hidden iframe, so no backend or CORS is needed.
(function () {
  var box = document.getElementById("signup");
  var url = box && (box.getAttribute("data-endpoint") || "").trim();
  if (!url || url.indexOf("https://") !== 0) return;
  var form = box.querySelector("form"), email = form.querySelector('input[type="email"]');
  var trap = form.querySelector(".su-trap input"), note = box.querySelector(".su-status"), btn = form.querySelector("button");
  form.action = url;
  email.name = box.getAttribute("data-field") || "email_address";
  box.hidden = false;
  form.addEventListener("submit", function (e) {
    if (trap.value) { e.preventDefault(); return; }
    setTimeout(function () {
      form.reset();
      btn.disabled = true;
      note.textContent = "Almost there. Check your inbox and tap the link to confirm.";
      setTimeout(function () { btn.disabled = false; }, 4000);
    }, 0);
  });
})();
