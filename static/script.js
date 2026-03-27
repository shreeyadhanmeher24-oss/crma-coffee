document.addEventListener("DOMContentLoaded", () => {
  const cartCount = document.getElementById("cart-count");
  const cartBtn = document.getElementById("cart-btn");
  const searchInput = document.getElementById("search-input");
  const products = document.querySelectorAll(".product");
  const addCartButtons = document.querySelectorAll(".add-cart-btn");
  const quickViewButtons = document.querySelectorAll(".quick-view-btn");

  // ✅ SAFE LOGIN CHECK (FIXED)
  const loggedIn = (typeof isLoggedIn !== "undefined" && isLoggedIn === true);

  // MODAL ELEMENTS
  const productModal = document.getElementById("productModal");
  const closeModal = document.getElementById("closeModal");
  const modalImage = document.getElementById("modalImage");
  const modalName = document.getElementById("modalName");
  const modalPrice = document.getElementById("modalPrice");
  const modalDescription = document.getElementById("modalDescription");
  const modalAddToCart = document.getElementById("modalAddToCart");

  // TOAST ELEMENTS
  const toastBox = document.getElementById("toastBox");
  const toastTitle = document.getElementById("toastTitle");
  const toastMessage = document.getElementById("toastMessage");

  let currentProductId = null;
  let toastTimeout;

  // ----------------------------
  // SHOW TOAST FUNCTION
  // ----------------------------
  function showToast(title, message) {
    if (!toastBox) return;

    toastTitle.textContent = title;
    toastMessage.textContent = message;

    toastBox.classList.add("show-toast");

    clearTimeout(toastTimeout);

    toastTimeout = setTimeout(() => {
      toastBox.classList.remove("show-toast");
    }, 2500);
  }

  // ----------------------------
  // CART NAV CLICK (FIXED)
  // ----------------------------
  if (cartBtn) {
    cartBtn.addEventListener("click", () => {
      if (loggedIn) {
        window.location.href = "/cart";
      } else {
        showToast("Login Required", "Please login first to view your cart.");
        setTimeout(() => {
          window.location.href = "/login";
        }, 1000);
      }
    });
  }

  // ----------------------------
  // ADD TO CART FUNCTION (FIXED)
  // ----------------------------
  function addToCart(productId, productName = "Item") {
    if (!loggedIn) {
      showToast("Login Required", "Please login first to add items to cart.");
      setTimeout(() => {
        window.location.href = "/login";
      }, 1000);
      return;
    }

    fetch("/add-to-cart", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: `product_id=${productId}`
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        if (cartCount) {
          cartCount.textContent = data.cart_count;
        }

        showToast("Added to Cart ☕", `${productName} has been added successfully.`);
      } else {
        showToast("Oops!", data.message);
      }
    })
    .catch(error => {
      console.error("Error:", error);
      showToast("Error", "Something went wrong. Please try again.");
    });
  }

  // ----------------------------
  // NORMAL ADD TO CART BUTTONS
  // ----------------------------
  addCartButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const productId = button.getAttribute("data-product-id");
      const productCard = button.closest(".product");
      const productName = productCard.getAttribute("data-name");
      addToCart(productId, productName);
    });
  });

  // ----------------------------
  // QUICK VIEW MODAL
  // ----------------------------
  quickViewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const productCard = button.closest(".product");

      const productId = productCard.getAttribute("data-id");
      const productName = productCard.getAttribute("data-name");
      const productPrice = productCard.getAttribute("data-price");
      const productImage = productCard.getAttribute("data-image");
      const productDescription = productCard.getAttribute("data-description");

      currentProductId = productId;

      modalImage.src = productImage;
      modalName.textContent = productName;
      modalPrice.textContent = productPrice;
      modalDescription.textContent = productDescription;

      modalAddToCart.setAttribute("data-product-name", productName);

      productModal.classList.add("show-modal");
    });
  });

  // ----------------------------
  // MODAL ADD TO CART
  // ----------------------------
  if (modalAddToCart) {
    modalAddToCart.addEventListener("click", () => {
      if (currentProductId) {
        const productName = modalAddToCart.getAttribute("data-product-name") || "Item";
        addToCart(currentProductId, productName);
      }
    });
  }

  // ----------------------------
  // CLOSE MODAL
  // ----------------------------
  if (closeModal) {
    closeModal.addEventListener("click", () => {
      productModal.classList.remove("show-modal");
    });
  }

  if (productModal) {
    productModal.addEventListener("click", (e) => {
      if (e.target === productModal) {
        productModal.classList.remove("show-modal");
      }
    });
  }

  // ----------------------------
  // SEARCH FILTER
  // ----------------------------
  if (searchInput) {
    searchInput.addEventListener("keyup", () => {
      const value = searchInput.value.toLowerCase();

      products.forEach((product) => {
        const productName = product.getAttribute("data-name-search");

        if (productName.includes(value)) {
          product.style.display = "block";
        } else {
          product.style.display = "none";
        }
      });
    });
  }
});