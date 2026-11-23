/* =============================================
   Mini-Amazon Storefront – JavaScript
   ============================================= */

document.addEventListener('DOMContentLoaded', () => {
    refreshCartCount();
});

function refreshCartCount() {
    fetch('/api/cart')
        .then(r => r.json())
        .then(items => {
            const count = items.reduce((sum, i) => sum + (parseInt(i.quantity) || 0), 0);
            const badge = document.getElementById('cart-count');
            if (badge) {
                badge.textContent = count;
            }
        })
        .catch(() => { });
}

function addToCart(productId, qty) {
    const parsedQty = parseInt(qty) > 0 ? parseInt(qty) : 1;
    fetch(`/api/cart/add?product_id=${productId}&quantity=${parsedQty}`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            refreshCartCount();
            showToast(`✓ Added to cart (Quantity: ${data.quantity})`);
        })
        .catch(() => showToast('Error adding item to cart'));
}

function buyNow(productId, qty) {
    const parsedQty = parseInt(qty) > 0 ? parseInt(qty) : 1;
    fetch(`/api/cart/add?product_id=${productId}&quantity=${parsedQty}`, { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            window.location.href = '/checkout';
        })
        .catch(() => {
            window.location.href = '/cart';
        });
}

function updateCart(productId, qty) {
    let parsedQty = parseInt(qty);
    if (isNaN(parsedQty) || parsedQty < 0) {
        parsedQty = 1;
    }

    fetch(`/api/cart/update?product_id=${productId}&quantity=${parsedQty}`, { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            refreshCartCount();
            location.reload();
        })
        .catch(() => showToast('Error updating item quantity'));
}

function removeFromCart(productId) {
    fetch(`/api/cart/remove?product_id=${productId}`, { method: 'POST' })
        .then(r => r.json())
        .then(() => {
            refreshCartCount();
            location.reload();
        })
        .catch(() => showToast('Error removing item from cart'));
}

function placeOrder() {
    const btn = document.querySelector('.place-order-btn') || document.querySelector('.primary-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Processing order...';
    }

    fetch('/api/checkout', { method: 'POST' })
        .then(r => {
            if (r.status === 401) {
                showToast('Please sign in to complete checkout.');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 800);
                return null;
            }
            return r.json().then(data => ({ status: r.status, data }));
        })
        .then(res => {
            if (!res) return;
            if (res.status === 200 && res.data.status === 'order_created') {
                showToast(`🎉 Order #${res.data.order_id} placed! Total: $${res.data.total.toFixed(2)}`);
                setTimeout(() => {
                    window.location.href = '/orders';
                }, 1200);
            } else {
                showToast(res.data.detail || 'Checkout failed. Please try again.');
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Place your order';
                }
            }
        })
        .catch(() => {
            showToast('Checkout communication error.');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Place your order';
            }
        });
}

/* Toast notification */
function showToast(msg) {
    let toast = document.getElementById('mini-amazon-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'mini-amazon-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            background: #131921;
            color: #ffffff;
            padding: 0.9rem 1.6rem;
            border-radius: 8px;
            font-size: 0.95rem;
            font-weight: 500;
            z-index: 99999;
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
            border-left: 4px solid #ff9900;
            transition: opacity 0.3s ease, transform 0.3s ease;
            transform: translateY(0);
        `;
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
    }, 3200);
}
