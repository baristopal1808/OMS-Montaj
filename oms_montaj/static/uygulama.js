// Telefonda yan menüyü açıp kapatır. Bilgisayarda menü hep açıktır; bu düğme orada görünmez.
(function () {
  var dugme = document.querySelector(".menu-dugme");
  var perde = document.querySelector("[data-menu-kapat]");
  if (!dugme) return;

  function ayarla(acik) {
    document.body.classList.toggle("menu-acik", acik);
    dugme.setAttribute("aria-expanded", acik ? "true" : "false");
  }

  dugme.addEventListener("click", function () {
    ayarla(!document.body.classList.contains("menu-acik"));
  });
  perde.addEventListener("click", function () { ayarla(false); });
  document.addEventListener("keydown", function (olay) {
    if (olay.key === "Escape") ayarla(false);
  });
})();
