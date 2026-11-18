# 🛍️ LocalBizMart — Online Marketplace for Local, WhatsApp & Home-Based Businesses

*A web platform connecting local sellers, Instagram/WhatsApp creators, and home businesses directly with customers.*

---

## 🌟 About the Project
Many local businesses, homemade gifting brands, clothing boutiques, and tailoring artists sell primarily through WhatsApp or Instagram without a proper catalog or structured ordering system. **LocalBizMart** provides them with a free, clean digital storefront:
- Customers can discover local sellers, browse products with availability indicators, add items to cart, and place orders.
- Direct **WhatsApp click-to-chat** buttons allow buyers to enquire or send pre-filled order confirmations instantly.
- Sellers can manage their catalogue, adjust availability toggles, review orders, and record payments (UPI & Cash on Delivery).
- An Administrator dashboard provides user management, business verification, and product moderation.

---

## 📋 Technology Stack
- **Frontend**: HTML5, Vanilla CSS3 (Custom Responsive Layout), Vanilla JavaScript.
- **Backend**: Python Flask 3.x (Blueprints & Jinja2 Templates).
- **Database**: MySQL (via XAMPP) using Flask-SQLAlchemy + PyMySQL.
- **WhatsApp Integration**: Direct `wa.me` links with URL-encoded pre-filled messages (zero API cost, no third-party automation needed).
- **Security**: Werkzeug salted password hashing, Flask session management, CSRF protection, SQLAlchemy ORM queries.
- **Uploads**: Product photos and UPI payment screenshots saved in `/static/uploads`.

---

## 🚀 Setup & Run Instructions (Windows 10 / 11)

### 1. Start MySQL in XAMPP
- Open **XAMPP Control Panel**.
- Click **Start** next to **MySQL** (default port `3306`).
*(The app will automatically create the `localbizmart` database if it does not already exist).*

### 2. Open Project Folder in VS Code / PowerShell
```powershell
cd c:\Users\Faiza\Desktop\LocalBizMart
```

### 3. Check `.env` Configuration
Ensure `.env` matches your XAMPP setup:
```ini
SECRET_KEY=localbizmart_super_secure_secret_key_2026_project
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=localbizmart
PAYMENT_TRACKING_ENABLED=True
REQUIRE_ADMIN_APPROVAL=False
FLASK_ENV=development
FLASK_DEBUG=1
```

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5. Seed the Database
Populates categories, demo businesses, products, users, and sample orders:
```powershell
python seed.py
```

### 6. Run the Application
```powershell
python run.py
```
Open your browser at:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Demo Login Credentials

| Role | Name | Email | Password | Business / Access |
| :--- | :--- | :--- | :--- | :--- |
| **Admin** | Administrator | `admin@localbizmart.com` | `Admin@123` | Master control dashboard (`/admin/login`) |
| **Owner** | Priya Sen | `priya@sharmasweets.com` | `Owner@123` | *CraftyGifts & Customized Hampers* (**UPI Only**) |
| **Owner** | Anita Desai | `anita@craftcorner.com` | `Owner@123` | *Aura Ethnic Wear & Boutique* (**Both UPI & COD**) |
| **Owner** | Rajesh Kumar | `rajesh@bakersdelight.com` | `Owner@123` | *Creative Corner Crafts & Tailoring* (**COD Only**) |
| **Customer** | Rohan Gupta | `rohan@customer.com` | `Customer@123` | Customer with Delivered & Shipped orders |
| **Customer** | Sneha Patel | `sneha@customer.com` | `Customer@123` | Customer with Processing & Pending orders |

---

## 🎬 5-Minute Presentation Demo Script

### Minute 1: Public Marketplace & Diverse Business Discovery
1. Open `http://127.0.0.1:5000`. Show the homepage, category pills (Gifting, Boutique, Tailoring, Crafts, etc.), and featured shops.
2. Click **Browse Businesses** &rarr; Open **"CraftyGifts & Customized Hampers"** (or *Aura Ethnic Wear*).
3. Point out the **"Chat with Shop on WhatsApp"** button (generates a `wa.me` pre-filled enquiry).
4. Point out product cards (e.g. Resin Frames, Gift Hampers, Cotton Kurtis) with **Available** and **Unavailable** badges.

### Minute 2: Customer Ordering & Multi-Business Cart Protection
1. Log in as **Rohan Gupta** (`rohan@customer.com` / `Customer@123`).
2. Add **"Personalized Resin Photo Frame"** to the cart.
3. Open the **Shopping Cart** (`/cart`). Show quantity updates and subtotals.
4. Try adding a product from *Aura Boutique*: demonstrate the system warning enforcing **one business per order**.
5. Proceed to **Checkout** (`/checkout`). Enter delivery address. Note that because CraftyGifts only accepts UPI, COD is hidden automatically.
6. Click **Confirm & Place Order**.

### Minute 3: WhatsApp Click-to-Chat & UPI Receipt Upload
1. On the **Confirmation Page**, click **"💬 Send Order Details via WhatsApp to Seller"**: observe the generated `wa.me` URL with pre-filled Order ID, items, amounts, address, and notes.
2. Highlight the **Backup Copyable Box** with the **"Copy Message Text"** button (for browsers blocking popups).
3. Under the UPI Payment section, display the seller's UPI ID (`craftygifts@okhdfcbank`) and upload a sample payment receipt screenshot.
4. Submit the screenshot: payment status immediately transitions to **"Under Verification"** (does **not** auto-mark Paid).

### Minute 4: Business Owner Dashboard & Order State Transitions
1. Log out and log in as the owner: **Priya Sen** (`priya@sharmasweets.com` / `Owner@123`).
2. Walk through the **Owner Dashboard** (products count, pending orders, revenue from delivered orders, pending UPI receipts).
3. Go to **Incoming Orders** &rarr; open the new order.
4. In the **Payment Verification** section, view the uploaded receipt and click **"✓ Verify & Mark Paid"**.
5. In the **Order Status** section, transition the order step-by-step:
   - Click **"Advance to: Confirmed"**
   - Click **"Advance to: Processing"**
   - Click **"Advance to: Shipped"**
   - Click **"Advance to: Delivered"**
6. Explain that invalid transitions are blocked server-side and recorded in the audit history.

### Minute 5: Customer Timeline & Admin Management
1. Log back in as **Rohan Gupta** and visit **My Orders** &rarr; open the order to show the **Visual Status Timeline** with timestamps.
2. Log out and navigate to **`/admin/login`**.
3. Log in as **`admin@localbizmart.com`** / **`Admin@123`**.
4. Demonstrate the Admin Portal:
   - **Dashboard**: System-wide statistics.
   - **Categories**: Create and edit categories.
   - **Businesses**: Toggle shop visibility and manage approvals.
   - **Product Moderation**: Disable inappropriate listings (`is_disabled_by_admin`).
   - **All Orders**: Read-only platform log.
