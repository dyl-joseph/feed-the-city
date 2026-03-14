// --- Helpers ---
function $(id) { return document.getElementById(id); }

async function api(url, opts = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...opts,
        body: opts.body ? JSON.stringify(opts.body) : undefined
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Request failed');
    return data;
}

// --- Status Polling ---
let cachedIngredients = [];

async function updateStatus() {
    try {
        const data = await api('/api/status');
        cachedIngredients = data.ingredients;

        // Volunteer page: show what's needed
        if ($('needs-list') && data.ingredients.length > 0) {
            $('needs-list').innerHTML = data.ingredients.map(ing => {
                const pct = ing.total_needed > 0 ? (ing.total_bought / ing.total_needed * 100) : 0;
                const done = pct >= 100;
                return `
                    <div class="bg-white rounded-lg border p-3 ${done ? 'opacity-50' : ''}">
                        <div class="flex justify-between text-sm mb-1">
                            <span class="font-medium">${ing.name}</span>
                            <span class="${done ? 'text-green-600' : 'text-gray-600'}">
                                ${Math.ceil(ing.total_bought)} / ${Math.ceil(ing.total_needed)} ${ing.unit}
                                ${done ? ' ✓' : ''}
                            </span>
                        </div>
                        <div class="w-full bg-gray-200 rounded-full h-2">
                            <div class="h-2 rounded-full transition-all duration-500 ${done ? 'bg-green-500' : 'bg-yellow-500'}"
                                 style="width: ${Math.min(100, pct)}%"></div>
                        </div>
                        ${ing.remaining > 0 && data.target_enabled
                            ? `<div class="text-xs text-gray-500 mt-1">Still need ~${Math.ceil(ing.remaining)} ${ing.unit}${ing.display_note ? ' — ' + ing.display_note : ''}</div>`
                            : ''}
                    </div>
                `;
            }).join('');

            // Build purchase input fields
            buildItemInputs(data.ingredients);
        } else if ($('needs-list') && data.ingredients.length === 0) {
            $('needs-list').innerHTML = '<p class="text-gray-400 text-sm">No ingredients set up yet. Ask an admin to configure the recipe.</p>';
        }

        // Dashboard
        if ($('ingredient-progress')) {
            $('dash-purchase-count').textContent = data.total_purchases;

            if (data.ingredients.length > 0) {
                $('ingredient-progress').innerHTML = data.ingredients.map(ing => {
                    const pct = ing.total_needed > 0 ? (ing.total_bought / ing.total_needed * 100) : 0;
                    const done = pct >= 100;
                    return `
                        <div class="bg-white rounded-xl shadow p-3">
                            <div class="flex justify-between text-sm mb-1">
                                <span class="font-semibold">${ing.name}</span>
                                <span>${Math.ceil(ing.total_bought)} / ${Math.ceil(ing.total_needed)} ${ing.unit}</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-3">
                                <div class="h-3 rounded-full transition-all duration-500 ${done ? 'bg-green-500' : 'bg-yellow-500'}"
                                     style="width: ${Math.min(100, pct)}%"></div>
                            </div>
                            <div class="text-xs text-gray-500 mt-1">${Math.round(pct)}% covered</div>
                        </div>
                    `;
                }).join('');
            } else {
                $('ingredient-progress').innerHTML = '<p class="text-gray-400 text-sm">No ingredients configured.</p>';
            }
        }
    } catch (e) {
        console.error('Status poll failed:', e);
    }
}

function buildItemInputs(ingredients) {
    const container = $('item-inputs');
    if (!container || container.dataset.built === 'true') return;

    container.innerHTML = ingredients.map(ing => `
        <div class="flex items-center gap-2 bg-gray-50 p-2 rounded-lg">
            <label class="flex-1 text-sm font-medium">${ing.name}
                <span class="text-gray-400 font-normal">(${ing.unit})</span>
            </label>
            <input type="number" step="any" min="0" placeholder="0"
                   data-ingredient-id="${ing.id}"
                   class="item-qty w-24 p-2 border rounded text-right text-sm">
        </div>
    `).join('');
    container.dataset.built = 'true';
}

function startPolling() {
    updateStatus();
    setInterval(updateStatus, 10000);
}

// --- Volunteer Page ---
function initVolunteer() {
    if (!$('purchase-form')) return;

    $('vol-name').value = localStorage.getItem('volName') || '';
    $('vol-phone').value = localStorage.getItem('volPhone') || '';

    $('purchase-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = $('vol-name').value.trim();
        const phone = $('vol-phone').value.trim();

        const items = [];
        document.querySelectorAll('.item-qty').forEach(input => {
            const qty = parseFloat(input.value);
            if (qty > 0) {
                items.push({
                    ingredient_id: parseInt(input.dataset.ingredientId),
                    quantity: qty
                });
            }
        });

        if (items.length === 0) {
            $('form-error').textContent = 'Enter at least one item quantity.';
            $('form-error').classList.remove('hidden');
            return;
        }

        $('form-error').classList.add('hidden');
        $('purchase-btn').disabled = true;
        $('purchase-btn').textContent = 'Logging...';

        try {
            await api('/api/purchase', {
                method: 'POST',
                body: { name, phone, items }
            });
            localStorage.setItem('volName', name);
            localStorage.setItem('volPhone', phone);

            $('purchase-form-section').classList.add('hidden');
            $('needs-section').classList.add('hidden');
            $('thankyou-section').classList.remove('hidden');
            updateStatus();
        } catch (err) {
            $('form-error').textContent = err.message;
            $('form-error').classList.remove('hidden');
        } finally {
            $('purchase-btn').disabled = false;
            $('purchase-btn').textContent = 'Log Purchase';
        }
    });

    $('new-purchase-btn').addEventListener('click', () => {
        $('thankyou-section').classList.add('hidden');
        $('purchase-form-section').classList.remove('hidden');
        $('needs-section').classList.remove('hidden');
        // Reset qty inputs
        document.querySelectorAll('.item-qty').forEach(i => i.value = '');
    });
}

// --- Dashboard ---
async function initDashboard() {
    updateStatus();
    loadPurchases();
    setInterval(() => { updateStatus(); loadPurchases(); }, 10000);
}

async function loadPurchases() {
    try {
        const purchases = await api('/api/purchases');
        if (purchases.length === 0) {
            $('no-purchases').classList.remove('hidden');
            $('purchases-list').innerHTML = '';
            return;
        }
        $('no-purchases').classList.add('hidden');
        $('purchases-list').innerHTML = purchases.map(p => {
            const itemStr = p.items.map(i => `${Math.ceil(i.quantity)} ${i.unit} ${i.name}`).join(', ');
            return `<div class="p-2 bg-gray-50 rounded">
                <span class="font-medium">${p.volunteer_name}</span>
                <span class="text-gray-400 ml-1 text-xs">${itemStr}</span>
            </div>`;
        }).join('');
    } catch (e) {
        console.error('Failed to load purchases:', e);
    }
}

// --- Admin ---
function initAdmin() {
    if (!$('login-form')) return;

    api('/api/admin/recipe').then(data => {
        $('admin-login').classList.add('hidden');
        $('admin-panel').classList.remove('hidden');
        populateAdmin(data);
    }).catch(() => {});

    $('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            await api('/api/admin/login', {
                method: 'POST',
                body: { password: $('admin-password').value }
            });
            const data = await api('/api/admin/recipe');
            $('admin-login').classList.add('hidden');
            $('admin-panel').classList.remove('hidden');
            populateAdmin(data);
        } catch (err) {
            $('login-error').textContent = err.message;
            $('login-error').classList.remove('hidden');
        }
    });

    $('add-ingredient-btn').addEventListener('click', () => addIngredientRow({}));
    $('save-recipe-btn').addEventListener('click', saveRecipe);

    $('target-toggle').addEventListener('change', () => {
        const on = $('target-toggle').checked;
        $('toggle-label').textContent = on ? 'Enabled' : 'Disabled';
        $('target-input').disabled = !on;
        $('target-input').classList.toggle('opacity-50', !on);
    });

    $('reset-claims-btn').addEventListener('click', async () => {
        if (!confirm('Delete ALL purchase logs? This cannot be undone.')) return;
        try {
            await api('/api/admin/reset', { method: 'POST' });
            $('save-status').textContent = 'All purchases reset.';
            $('save-status').className = 'text-sm text-center text-red-600';
        } catch (err) {
            alert(err.message);
        }
    });
}

function populateAdmin(data) {
    $('target-input').value = data.target_sandwiches;
    $('target-toggle').checked = data.target_enabled;
    $('toggle-label').textContent = data.target_enabled ? 'Enabled' : 'Disabled';
    $('target-input').disabled = !data.target_enabled;
    $('target-input').classList.toggle('opacity-50', !data.target_enabled);

    $('ingredients-editor').innerHTML = '';
    if (data.ingredients.length === 0) {
        addIngredientRow({});
    } else {
        data.ingredients.forEach(ing => addIngredientRow(ing));
    }
}

function addIngredientRow(ing) {
    const div = document.createElement('div');
    div.className = 'bg-gray-50 p-3 rounded-lg space-y-2 ingredient-row';
    div.innerHTML = `
        <div class="flex gap-2">
            <input type="text" placeholder="Name (e.g. Bread)" value="${ing.name || ''}"
                   class="ing-name flex-1 p-2 border rounded text-sm">
            <button class="remove-ing text-red-400 text-sm px-2">✕</button>
        </div>
        <div class="grid grid-cols-3 gap-2">
            <input type="number" step="any" placeholder="Qty/sandwich" value="${ing.qty_per_sandwich || ''}"
                   class="ing-qty p-2 border rounded text-sm">
            <input type="text" placeholder="Unit" value="${ing.unit || ''}"
                   class="ing-unit p-2 border rounded text-sm">
            <input type="text" placeholder="Note" value="${ing.display_note || ''}"
                   class="ing-note p-2 border rounded text-sm">
        </div>
        <div class="grid grid-cols-2 gap-2">
            <input type="number" step="any" placeholder="Package size" value="${ing.package_size || ''}"
                   class="ing-pkg-size p-2 border rounded text-sm">
            <input type="text" placeholder="Package unit (e.g. loaf)" value="${ing.package_unit || ''}"
                   class="ing-pkg-unit p-2 border rounded text-sm">
        </div>
    `;
    div.querySelector('.remove-ing').addEventListener('click', () => div.remove());
    $('ingredients-editor').appendChild(div);
}

async function saveRecipe() {
    const rows = document.querySelectorAll('.ingredient-row');
    const ingredients = [];
    for (const row of rows) {
        const name = row.querySelector('.ing-name').value.trim();
        const qty = row.querySelector('.ing-qty').value;
        const unit = row.querySelector('.ing-unit').value.trim();
        if (!name || !qty || !unit) continue;
        ingredients.push({
            name,
            qty_per_sandwich: parseFloat(qty),
            unit,
            package_size: row.querySelector('.ing-pkg-size').value || null,
            package_unit: row.querySelector('.ing-pkg-unit').value.trim() || null,
            display_note: row.querySelector('.ing-note').value.trim() || null
        });
    }

    try {
        await api('/api/admin/recipe', {
            method: 'POST',
            body: {
                target_sandwiches: parseInt($('target-input').value),
                target_enabled: $('target-toggle').checked,
                ingredients
            }
        });
        $('save-status').textContent = 'Saved!';
        $('save-status').className = 'text-sm text-center text-green-600';
    } catch (err) {
        $('save-status').textContent = err.message;
        $('save-status').className = 'text-sm text-center text-red-600';
    }
}

// --- Boot ---
document.addEventListener('DOMContentLoaded', () => {
    initVolunteer();
    startPolling();
});
