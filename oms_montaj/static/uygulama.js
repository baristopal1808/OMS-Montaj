// Süzgeç kutularında bir seçim yapılınca liste hemen yenilenir.
document.querySelectorAll("form.suzgec select, form[data-otomatik] select").forEach(function (kutu) {
  kutu.addEventListener("change", function () { kutu.form.submit(); });
});

// Tablolarda satırın tamamı tıklanır; satırdaki bağlantılar (ürün kutucukları) kendi yerine gider.
document.querySelectorAll("tr[data-adres]").forEach(function (satir) {
  satir.addEventListener("click", function (olay) {
    if (olay.target.closest("a")) return;
    window.location.href = satir.dataset.adres;
  });
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

// Ürün sayfasında aşama geri alınırken not (sebep) zorunlu olur; sunucu da aynı kuralı denetler.
document.querySelectorAll("[data-asama-formu]").forEach(function (form) {
  var secim = form.querySelector("select[name=asama]");
  var not = form.querySelector("textarea[name=not]");
  var ipucu = form.querySelector("[data-not-ipucu]");
  var ilkIpucu = ipucu.textContent;
  function ayarla() {
    var geri = Number(secim.selectedOptions[0].dataset.sira) < Number(secim.dataset.simdiki);
    not.required = geri;
    not.placeholder = geri ? "Aşamayı neden geri alıyorsunuz? Örneğin: testte hidrolik kaçak çıktı" : "Örneğin: kabin boyadan geldi, montaja başlandı";
    ipucu.textContent = geri ? "(geri alırken sebebi zorunlu)" : ilkIpucu;
    ipucu.classList.toggle("zorunlu", geri);
  }
  secim.addEventListener("change", ayarla);
  ayarla();
});

// Form hazırlama: listeden bir vibro çakıcı seçilince seri no'su da gelir.
document.querySelectorAll("[data-form-hazirla]").forEach(function (form) {
  var vibro = form.querySelector("[data-vibro]");
  var seri = form.querySelector("[data-vibro-seri]");
  if (!vibro || !seri) return;
  vibro.addEventListener("change", function () {
    var secenek = Array.prototype.find.call(vibro.list.options, function (o) { return o.value === vibro.value; });
    if (secenek) seri.value = secenek.dataset.seri || "";
  });
});

// Adres bir açılır bölümü gösteriyorsa (#ekle gibi) bölüm açık gelir
(function () {
  var hedef = location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if (hedef && hedef.tagName === "DETAILS") hedef.open = true;
})();

// Bilgisayarda sol menü: düğme menüyü genişletir ya da daraltır (yalnızca simgeler); seçim tarayıcıda saklanır.
// Dar menüde simgenin üzerine gelince adı ipucu olarak görünür.
document.querySelectorAll("[data-menu-sabitle]").forEach(function (dugme) {
  var kok = document.documentElement;
  var ogeler = document.querySelectorAll(".yan-menu a, .yan-alt a, .yan-alt button");
  function goster() {
    var sabit = kok.classList.contains("menu-sabit");
    dugme.setAttribute("aria-expanded", sabit ? "true" : "false");
    dugme.title = sabit ? "Menüyü daralt (yalnızca simgeler)" : "Menüyü genişlet";
    ogeler.forEach(function (oge) {
      var ad = oge.querySelector("span");
      if (sabit) oge.removeAttribute("title");
      else if (ad) oge.title = ad.textContent.trim();
    });
  }
  dugme.addEventListener("click", function () {
    var sabit = kok.classList.toggle("menu-sabit");
    try { localStorage.setItem("omsMenuSabit", sabit ? "1" : "0"); } catch (e) {}
    goster();
  });
  goster();
});

// Aydınlık / karanlık tema: sağ üstteki düğme değiştirir, seçim tarayıcıda saklanır. Seçim yapılmamışsa
// bilgisayarın ya da telefonun ayarı izlenir (ilk seçim taban.html'de, sayfa çizilmeden yapılır).
(function () {
  var kok = document.documentElement;
  var dugmeler = document.querySelectorAll("[data-tema-dugmesi]");
  var sistem = window.matchMedia ? matchMedia("(prefers-color-scheme: dark)") : null;
  function goster() {
    var koyu = kok.dataset.tema === "koyu";
    dugmeler.forEach(function (dugme) {
      dugme.setAttribute("aria-checked", koyu ? "true" : "false");
      dugme.title = koyu ? "Aydınlık temaya geç" : "Karanlık temaya geç";
    });
  }
  dugmeler.forEach(function (dugme) {
    dugme.addEventListener("click", function () {
      kok.dataset.tema = kok.dataset.tema === "koyu" ? "acik" : "koyu";
      try { localStorage.setItem("omsTema", kok.dataset.tema); } catch (e) {}
      goster();
    });
  });
  if (sistem && sistem.addEventListener) {
    sistem.addEventListener("change", function () {
      var secim = null;
      try { secim = localStorage.getItem("omsTema"); } catch (e) {}
      if (secim !== "koyu" && secim !== "acik") { kok.dataset.tema = sistem.matches ? "koyu" : "acik"; goster(); }
    });
  }
  goster();
})();

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

// Yapılacaklar (ve ürün sayfasındaki uyarılar): cevap sayfa yenilenmeden kaydedilir, sayfa yerinde kalır.
// Cevaplanan sorunun yerinde "Kaydedildi" yazar; menüdeki ve süzgeçlerdeki sayılar azalır.
function sayiyiAzalt(secici) {
  document.querySelectorAll(secici).forEach(function (sayi) {
    sayi.textContent = Math.max(0, parseInt(sayi.textContent, 10) - 1);
  });
}

document.querySelectorAll("form[data-yerinde]").forEach(function (form) {
  var kutu = form.closest("[data-yapilacak]");
  var hata = form.querySelector("[data-hata]");
  var dugme = form.querySelector("button[type=submit]");
  form.addEventListener("submit", function (olay) {
    olay.preventDefault();
    if (dugme.disabled) return;
    dugme.disabled = true;
    fetch(form.action, { method: "POST", body: new FormData(form), headers: { "Accept": "application/json" } })
      .then(function (yanit) {
        if (!yanit.ok) throw new Error(yanit.status);
        return yanit.json();
      })
      .then(function (sonuc) {
        if (!sonuc.tamam) {
          hata.textContent = sonuc.mesaj;
          hata.hidden = false;
          return;
        }
        var not = document.createElement("p");
        not.className = "yapilacak-tamam";
        not.textContent = "✓ " + sonuc.mesaj;
        form.replaceWith(not);
        kutu.classList.add("kaydedildi");
        sayiyiAzalt('[data-sayi-konu="' + kutu.dataset.konu + '"], [data-sayi-aile="' + kutu.dataset.aile + '"]');
        sayiyiAzalt("[data-sayi-tumu-konu], [data-sayi-tumu-aile]");
        var menu = document.querySelector(".menu-sayi");
        if (menu) {
          if (sonuc.sayi) menu.textContent = sonuc.sayi;
          else menu.remove();
        }
      })
      .catch(function () {
        hata.textContent = "Kaydedilemedi. Sayfayı yenileyip yeniden deneyin.";
        hata.hidden = false;
      })
      .finally(function () { dugme.disabled = false; });
  });
});

// Asistanın sohbet kutusu (sağ alt): açılıp kapanır, açık kaldıysa sayfa değişince de açık gelir.
// Soru sayfa yenilenmeden gönderilir; cevap balonu sunucudan HTML olarak gelir.
(function () {
  var kutu = document.querySelector("[data-asistan]");
  if (!kutu) return;
  var acDugmesi = kutu.querySelector("[data-asistan-ac]");
  var mesajlar = kutu.querySelector("[data-asistan-mesajlar]");
  var form = kutu.querySelector("[data-asistan-form]");
  var alan = form.querySelector("textarea");
  var gonder = form.querySelector("button");
  var ozet = kutu.querySelector("[data-asistan-ozet]");

  function hatirla(acik) {
    try { sessionStorage.setItem("asistanAcik", acik ? "1" : ""); } catch (hata) { /* tarayıcı saklamaya izin vermiyor */ }
  }

  function ac(acik) {
    kutu.classList.toggle("acik", acik);
    acDugmesi.setAttribute("aria-expanded", acik ? "true" : "false");
    hatirla(acik);
    if (acik) {
      mesajlar.scrollTop = mesajlar.scrollHeight;
      alan.focus();
    }
  }

  function balon(sinif, metin) {
    var div = document.createElement("div");
    div.className = "ak-balon " + sinif;
    div.textContent = metin;
    mesajlar.appendChild(div);
    mesajlar.scrollTop = mesajlar.scrollHeight;
    return div;
  }

  acDugmesi.addEventListener("click", function () {
    // Karşılama mesajı yalnızca düğmeyle açılınca kayarak belirir.
    kutu.classList.add("canli");
    setTimeout(function () { kutu.classList.remove("canli"); }, 700);
    ac(!kutu.classList.contains("acik"));
  });
  kutu.querySelector("[data-asistan-kapat]").addEventListener("click", function () { ac(false); });
  try { if (sessionStorage.getItem("asistanAcik")) ac(true); } catch (hata) { /* yok sayılır */ }
  // Açılış canlandırması yalnızca düğmeye basınca oynar; sayfa değişince açık gelen kutu hemen görünür.
  requestAnimationFrame(function () {
    requestAnimationFrame(function () { kutu.classList.add("hazir"); });
  });

  alan.addEventListener("keydown", function (olay) {
    if (olay.key === "Enter" && !olay.shiftKey) {
      olay.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", function (olay) {
    olay.preventDefault();
    var soru = alan.value.trim();
    if (!soru || gonder.disabled) return;
    var veri = new FormData(form);
    balon("ak-soru", soru);
    var bekleme = balon("ak-cevap ak-yaziyor", "Kayıtlara bakıyorum…");
    alan.value = "";
    gonder.disabled = true;
    fetch(form.action, { method: "POST", body: veri, headers: { "Accept": "application/json" } })
      .then(function (yanit) {
        if (!yanit.ok) throw new Error(yanit.status);
        return yanit.json();
      })
      .then(function (sonuc) {
        bekleme.outerHTML = sonuc.cevap;
        ozet.textContent = sonuc.ozet;
      })
      .catch(function () {
        bekleme.className = "ak-balon ak-hata";
        bekleme.textContent = "Cevap alınamadı. Sayfayı yenileyip yeniden deneyin.";
      })
      .finally(function () {
        gonder.disabled = false;
        mesajlar.scrollTop = mesajlar.scrollHeight;
        alan.focus();
      });
  });

  kutu.querySelector("[data-asistan-yeni]").addEventListener("submit", function (olay) {
    olay.preventDefault();
    fetch(this.action, { method: "POST", body: new FormData(this) }).then(function () {
      // Karşılama mesajı kalır, konuşma temizlenir.
      while (mesajlar.children.length > 1) mesajlar.removeChild(mesajlar.lastChild);
      alan.focus();
    });
  });
})();

// Geri alınması zor işlemlerde (stok makinesini siparişe atamak gibi) gönderilmeden önce onay sorulur.
document.addEventListener("submit", function (olay) {
  var form = olay.target;
  if (form.dataset && form.dataset.onay && !window.confirm(form.dataset.onay)) olay.preventDefault();
});
