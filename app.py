from flask import Flask, render_template, request, redirect, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "crma_secret_key"


# ----------------------------
# DATABASE SETUP
# ----------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    # PRODUCTS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price TEXT NOT NULL,
        image TEXT NOT NULL,
        description TEXT
    )
    """)

    # CART TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1
    )
    """)

    # ORDERS TABLE
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

    # INSERT PRODUCTS ONLY IF EMPTY
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
# LOGIN
# ----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
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
    session.pop("user", None)
    flash("Logged out successfully.", "success")
    return redirect("/")


# ----------------------------
# ADD TO CART
# ----------------------------
@app.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    if "user" not in session:
        return {"success": False, "message": "Please login first to add items to cart."}

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

    return {"success": True, "cart_count": cart_count}


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
# UPDATE CART QUANTITY
# ----------------------------
@app.route("/update-cart/<int:cart_id>/<action>")
def update_cart(cart_id, action):
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if action == "increase":
        cursor.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE id = ? AND user = ?
        """, (cart_id, session["user"]))

    elif action == "decrease":
        cursor.execute("""
            SELECT quantity FROM cart
            WHERE id = ? AND user = ?
        """, (cart_id, session["user"]))
        item = cursor.fetchone()

        if item:
            if item[0] > 1:
                cursor.execute("""
                    UPDATE cart
                    SET quantity = quantity - 1
                    WHERE id = ? AND user = ?
                """, (cart_id, session["user"]))
            else:
                cursor.execute("""
                    DELETE FROM cart
                    WHERE id = ? AND user = ?
                """, (cart_id, session["user"]))

    conn.commit()
    conn.close()
    return redirect("/cart")


# ----------------------------
# REMOVE ITEM FROM CART
# ----------------------------
@app.route("/remove-from-cart/<int:cart_id>")
def remove_from_cart(cart_id):
    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart WHERE id = ? AND user = ?", (cart_id, session["user"]))
    conn.commit()
    conn.close()

    flash("Item removed from cart.", "success")
    return redirect("/cart")


# ----------------------------
# CHECKOUT PAGE
# ----------------------------
@app.route("/checkout")
def checkout():
    if "user" not in session:
        flash("Please login first to continue checkout.", "error")
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cart.id, products.name, products.price, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user = ?
    """, (session["user"],))
    cart_items = cursor.fetchall()
    conn.close()

    if not cart_items:
        flash("Your cart is empty.", "error")
        return redirect("/cart")

    return render_template("checkout.html")


# ----------------------------
# PLACE ORDER
# ----------------------------
@app.route("/place-order", methods=["POST"])
def place_order():
    if "user" not in session:
        flash("Please login first.", "error")
        return redirect("/login")

    fullname = request.form["fullname"]
    phone = request.form["phone"]
    address = request.form["address"]
    city = request.form["city"]
    pincode = request.form["pincode"]
    payment = request.form["payment"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cart.product_id, products.name, products.price, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user = ?
    """, (session["user"],))
    cart_items = cursor.fetchall()

    if not cart_items:
        conn.close()
        flash("Your cart is empty.", "error")
        return redirect("/cart")

    total = 0
    order_details = []

    for item in cart_items:
        product_id, name, price, quantity = item
        price_number = int(price.replace("₹", ""))
        subtotal = price_number * quantity
        total += subtotal
        order_details.append(f"{name} x {quantity} = ₹{subtotal}")

    items_text = " | ".join(order_details)
    full_address = f"{fullname}, {phone}, {address}, {city} - {pincode}"

    cursor.execute("""
        INSERT INTO orders (user, items, total, address, payment, status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session["user"], items_text, f"₹{total}", full_address, payment, "Order Placed"))

    cursor.execute("DELETE FROM cart WHERE user = ?", (session["user"],))

    conn.commit()
    conn.close()

    flash("Order placed successfully!", "success")
    return redirect("/orders")


# ----------------------------
# MY ORDERS
# ----------------------------
@app.route("/orders")
def orders():
    if "user" not in session:
        flash("Please login first to view orders.", "error")
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user=? ORDER BY id DESC", (session["user"],))
    user_orders = cursor.fetchall()
    conn.close()

    return render_template("orders.html", orders=user_orders)


# ----------------------------
# UPDATE ORDER STATUS
# ----------------------------
@app.route("/update-order-status/<int:order_id>")
def update_order_status(order_id):
    if "user" not in session:
        flash("Please login first.", "error")
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Get current status
    cursor.execute("SELECT status FROM orders WHERE id=? AND user=?", (order_id, session["user"]))
    order = cursor.fetchone()

    if order:
        current_status = order[0]

        if current_status == "Order Placed":
            new_status = "Packed"
        elif current_status == "Packed":
            new_status = "Out for Delivery"
        elif current_status == "Out for Delivery":
            new_status = "Delivered"
        else:
            new_status = "Delivered"

        cursor.execute("""
            UPDATE orders
            SET status=?
            WHERE id=? AND user=?
        """, (new_status, order_id, session["user"]))

        conn.commit()
        flash(f"Order #{order_id} updated to {new_status}", "success")

    conn.close()
    return redirect("/orders")


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)