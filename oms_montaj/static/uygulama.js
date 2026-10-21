// Süzgeç kutularında bir seçim yapılınca liste hemen yenilenir.
document.querySelectorAll("form.suzgec select").forEach(function (kutu) {
  kutu.addEventListener("change", function () { kutu.form.submit(); });
});

// Dosya bırakma alanı: seçilen dosyaların adlarını gösterir, üstüne dosya sürüklenince renklenir.
document.querySelectorAll("[data-dosya-alani]").forEach(function (alan) {
  var girdi = alan.querySelector("input[type=file]");
  var secilen = alan.querySelector("[data-secilen]");
  girdi.addEventListener("change", function () {
    var adlar = Array.prototype.map.call(girdi.files, function (dosya) { return dosya.name; });
    secilen.textContent = adlar.length ? adlar.length + " dosya seçildi: " + adlar.join(", ") : "";
    alan.classList.toggle("dolu", adlar.length > 0);
  });
  ["dragenter", "dragover"].forEach(function (olay) {
    girdi.addEventListener(olay, function () { alan.classList.add("uzerinde"); });
  });
  ["dragleave", "drop"].forEach(function (olay) {
    girdi.addEventListener(olay, function () { alan.classList.remove("uzerinde"); });
  });
});

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
