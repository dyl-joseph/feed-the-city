import math
import os
from flask import Flask, render_template, request, jsonify, session

from db import get_db, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if os.environ.get('VERCEL'):
    app.config['SESSION_COOKIE_SECURE'] = True
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'feedthecity')


def query(db, sql, params=()):
    cursor = db.execute(sql, params)
    cols = [d[0] for d in cursor.description] if cursor.description else []
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

def query_one(db, sql, params=()):
    rows = query(db, sql, params)
    return rows[0] if rows else None


# --- Pages ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')


# --- API ---

@app.route('/api/status')
def api_status():
    db = get_db()
    recipe = query_one(db, "SELECT target_sandwiches, target_enabled FROM recipe WHERE id=1")
    target = recipe['target_sandwiches'] if recipe else 1500
    target_enabled = bool(recipe['target_enabled']) if recipe else True

    ingredients = []
    for ing in query(db, "SELECT * FROM ingredient ORDER BY name"):
        bought = query_one(db,
            "SELECT COALESCE(SUM(pi.quantity), 0) as total FROM purchase_item pi WHERE pi.ingredient_id=?",
            (ing['id'],)
        )['total']
        needed = ing['qty_per_sandwich'] * target
        ing['total_bought'] = bought
        ing['total_needed'] = needed
        ing['remaining'] = max(0, needed - bought)
        ingredients.append(ing)

    total_purchases = query_one(db, "SELECT COUNT(*) as c FROM purchase")['c']
    db.close()

    return jsonify({
        'target': target,
        'target_enabled': target_enabled,
        'ingredients': ingredients,
        'total_purchases': total_purchases
    })


@app.route('/api/purchase', methods=['POST'])
def api_purchase():
    data = request.json
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    items = data.get('items', [])

    if not name or not phone:
        return jsonify({'error': 'Name and phone required'}), 400
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO purchase (volunteer_name, volunteer_phone) VALUES (?, ?)",
            (name, phone)
        )
        purchase_id = cursor.lastrowid

        for item in items:
            ing_id = item.get('ingredient_id')
            qty = item.get('quantity', 0)
            if not ing_id or not qty or float(qty) <= 0:
                continue
            db.execute(
                "INSERT INTO purchase_item (purchase_id, ingredient_id, quantity) VALUES (?, ?, ?)",
                (purchase_id, int(ing_id), float(qty))
            )

        db.commit()
        db.close()
        return jsonify({'purchase_id': purchase_id}), 201
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/purchases')
def api_purchases():
    db = get_db()
    purchases = []
    for p in query(db, "SELECT * FROM purchase ORDER BY created_at DESC LIMIT 50"):
        p['items'] = query(db, """
            SELECT pi.quantity, i.name, i.unit
            FROM purchase_item pi JOIN ingredient i ON pi.ingredient_id = i.id
            WHERE pi.purchase_id = ?
        """, (p['id'],))
        purchases.append(p)
    db.close()
    return jsonify(purchases)


# --- Admin ---

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    if data.get('password') == ADMIN_PASSWORD:
        return jsonify({'success': True, 'token': ADMIN_PASSWORD})
    return jsonify({'error': 'Wrong password'}), 401


def require_admin():
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_PASSWORD:
        return jsonify({'error': 'Unauthorized'}), 401
    return None


@app.route('/api/admin/recipe', methods=['GET'])
def get_recipe():
    auth = require_admin()
    if auth:
        return auth
    db = get_db()
    recipe = query_one(db, "SELECT target_sandwiches, target_enabled FROM recipe WHERE id=1")
    ingredients = query(db, "SELECT * FROM ingredient ORDER BY name")
    db.close()
    return jsonify({
        'target_sandwiches': recipe['target_sandwiches'],
        'target_enabled': bool(recipe['target_enabled']),
        'ingredients': ingredients
    })


@app.route('/api/admin/recipe', methods=['POST'])
def update_recipe():
    auth = require_admin()
    if auth:
        return auth
    data = request.json
    db = get_db()

    try:
        if 'target_sandwiches' in data:
            db.execute("UPDATE recipe SET target_sandwiches=? WHERE id=1", (int(data['target_sandwiches']),))

        if 'target_enabled' in data:
            db.execute("UPDATE recipe SET target_enabled=? WHERE id=1", (1 if data['target_enabled'] else 0,))

        if 'ingredients' in data:
            db.execute("DELETE FROM ingredient")
            for ing in data['ingredients']:
                db.execute(
                    "INSERT INTO ingredient (name, qty_per_sandwich, unit, package_size, package_unit, display_note) VALUES (?, ?, ?, ?, ?, ?)",
                    (ing['name'], float(ing['qty_per_sandwich']), ing['unit'],
                     float(ing['package_size']) if ing.get('package_size') else None,
                     ing.get('package_unit'), ing.get('display_note'))
                )

        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        db.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/reset', methods=['POST'])
def admin_reset():
    auth = require_admin()
    if auth:
        return auth
    db = get_db()
    db.execute("DELETE FROM purchase_item")
    db.execute("DELETE FROM purchase")
    db.commit()
    db.close()
    return jsonify({'success': True})


# Init DB on import for serverless (runs once per cold start)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)
