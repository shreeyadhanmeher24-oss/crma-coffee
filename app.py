from flask import Flask, render_template, request, redirect, session, flash, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "crma_secret_key"


# ----------------------------
# DATABASE SETUP
# ----------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price TEXT NOT NULL,
        image TEXT NOT NULL,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        items TEXT NOT NULL,
        total TEXT NOT NULL,
        address TEXT,
        payment TEXT,
        status TEXT DEFAULT 'Order Placed'
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]

    if count == 0:
        products = [
            ("Espresso", "₹150", "assets/espresso.jpg", "Strong, bold and rich espresso shot."),
            ("Cappuccino", "₹220", "assets/cappuccino.jpg", "Creamy milk foam with bold espresso."),
            ("Latte", "₹180", "assets/latte.jpg", "Smooth and balanced coffee with milk."),
            ("Cold Brew", "₹250", "assets/coldbrew.jpg", "Refreshing chilled coffee for a cool vibe.")
        ]
        cursor.executemany("""
            INSERT INTO products (name, price, image, description)
            VALUES (?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()


init_db()


# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cart_count = 0
    if "user" in session:
        cursor.execute("SELECT SUM(quantity) FROM cart WHERE user=?", (session["user"],))
        result = cursor.fetchone()[0]
        cart_count = result if result else 0

    conn.close()
    return render_template("index.html", products=products, cart_count=cart_count)


# ----------------------------
# LOGIN (FIXED)
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # ✅ Prevent redirect issue
    if "user" in session:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user"] = username
            flash("Login successful!", "success")
            return redirect("/")
        else:
            flash("Invalid username or password.", "error")
            return redirect("/login")

    return render_template("login.html")


# ----------------------------
# SIGNUP
# ----------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user" in session:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()

            flash("Signup successful! Please login.", "success")
            return redirect("/login")

        except:
            flash("Username already exists.", "error")
            return redirect("/signup")

    return render_template("signup.html")


# ----------------------------
# LOGOUT
# ----------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect("/")


# ----------------------------
# ADD TO CART (FIXED JSON)
# ----------------------------
@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    if "user" not in session:
        return jsonify({"success": False, "message": "Please login first to add items to cart."})

    product_id = request.form["product_id"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cart WHERE user=? AND product_id=?", (session["user"], product_id))
    existing_item = cursor.fetchone()

    if existing_item:
        cursor.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE user=? AND product_id=?
        """, (session["user"], product_id))
    else:
        cursor.execute("""
            INSERT INTO cart (user, product_id, quantity)
            VALUES (?, ?, 1)
        """, (session["user"], product_id))

    conn.commit()

    cursor.execute("SELECT SUM(quantity) FROM cart WHERE user=?", (session["user"],))
    cart_count = cursor.fetchone()[0] or 0

    conn.close()

    return jsonify({"success": True, "cart_count": cart_count})


# ----------------------------
# CART PAGE
# ----------------------------
@app.route("/cart")
def cart():
    if "user" not in session:
        flash("Please login first to view cart.", "error")
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cart.id, products.name, products.price, products.image, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user = ?
    """, (session["user"],))

    cart_items = cursor.fetchall()

    total = 0
    for item in cart_items:
        price = int(item[2].replace("₹", ""))
        quantity = item[4]
        total += price * quantity

    conn.close()

    return render_template("cart.html", cart_items=cart_items, total=total)


# ----------------------------
# UPDATE CART
# ----------------------------
@app.route("/update-cart/<int:cart_id>/<action>")
def update_cart(cart_id, action):
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if action == "increase":
        cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE id=? AND user=?", (cart_id, session["user"]))

    elif action == "decrease":
        cursor.execute("SELECT quantity FROM cart WHERE id=? AND user=?", (cart_id, session["user"]))
        item = cursor.fetchone()

        if item:
            if item[0] > 1:
                cursor.execute("UPDATE cart SET quantity = quantity - 1 WHERE id=? AND user=?", (cart_id, session["user"]))
            else:
                cursor.execute("DELETE FROM cart WHERE id=? AND user=?", (cart_id, session["user"]))

    conn.commit()
    conn.close()
    return redirect("/cart")


# ----------------------------
# REMOVE ITEM
# ----------------------------
@app.route("/remove-from-cart/<int:cart_id>")
def remove_from_cart(cart_id):
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id=? AND user=?", (cart_id, session["user"]))
    conn.commit()
    conn.close()

    flash("Item removed from cart.", "success")
    return redirect("/cart")


# ----------------------------
# FORCE LOGOUT (VERY IMPORTANT)
# ----------------------------
@app.route("/force-logout")
def force_logout():
    session.clear()
    return "Session cleared!"
    

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))