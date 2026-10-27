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
