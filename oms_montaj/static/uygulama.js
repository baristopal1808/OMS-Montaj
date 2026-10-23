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
