import os
import logging
from dotenv import load_dotenv
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    filters,
    ContextTypes,
    ConversationHandler
)
import sqlite3
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database instance
from database import db

# States for conversations
(
    # Admin product states
    PRODUCT_NAME, PRODUCT_PRICE, PRODUCT_DESCRIPTION, PRODUCT_QUANTITY,
    PRODUCT_IMAGE1, PRODUCT_IMAGE2_OPTION, PRODUCT_IMAGE2, PRODUCT_COORDINATES,
    
    # Admin payment states
    PAYMENT_CURRENCY, PAYMENT_ADDRESS, PAYMENT_BLOCKCHAIN,
    
    # Admin discount states
    DISCOUNT_CLIENT_TYPE, DISCOUNT_CLIENT_ID, DISCOUNT_CODE, 
    DISCOUNT_PERCENTAGE, DISCOUNT_EXPIRY, DISCOUNT_MAX_USES,
    
    # Admin content states
    CONTENT_EDIT,
    
    # Client payment states
    PAYMENT_SOURCE_ADDRESS,
    
    # Discount code input
    DISCOUNT_CODE_INPUT
) = range(23)

class StoreBot:
    def __init__(self):
        self.token = os.getenv('BOT_TOKEN')
        self.admin_id = int(os.getenv('ADMIN_ID'))
        self.exchange_rate = float(os.getenv('EXCHANGE_RATE', 1.16))
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        # Check if user is admin
        if user.id == self.admin_id:
            await self.show_admin_panel(update, context)
            return
            
        welcome_message = self.get_content('welcome_message')
        
        keyboard = [
            [
                InlineKeyboardButton("🛍️ Browse Products", callback_data="browse_products"),
                InlineKeyboardButton("🛒 My Cart", callback_data="view_cart")
            ],
            [
                InlineKeyboardButton("ℹ️ About Us", callback_data="about"),
                InlineKeyboardButton("📞 Contact", callback_data="contact")
            ],
            [
                InlineKeyboardButton("🌐 Website", callback_data="website"),
                InlineKeyboardButton("📝 Rules", callback_data="rules")
            ],
            [
                InlineKeyboardButton("🔍 FAQ", callback_data="faq")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(welcome_message, reply_markup=reply_markup)
        else:
            await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Client handlers
        if data == "browse_products":
            await self.show_products(update, context)
        elif data == "view_cart":
            await self.show_cart(update, context)
        elif data == "about":
            await self.show_about(update, context)
        elif data == "contact":
            await self.show_contact(update, context)
        elif data == "website":
            await self.show_website(update, context)
        elif data == "rules":
            await self.show_rules(update, context)
        elif data == "faq":
            await self.show_faq(update, context)
        elif data == "main_menu":
            await self.start(update, context)
        elif data.startswith("product_"):
            product_id = int(data.split("_")[1])
            await self.show_product_detail(update, context, product_id)
        elif data.startswith("add_to_cart_"):
            product_id = int(data.split("_")[3])
            await self.add_to_cart(update, context, product_id)
        elif data == "back_to_products":
            await self.show_products(update, context)
        elif data == "continue_shopping":
            await self.show_products(update, context)
        elif data == "clear_cart":
            await self.clear_cart(update, context)
        elif data == "checkout_all":
            await self.start_checkout(update, context)
        elif data.startswith("buy_now_"):
            product_id = int(data.split("_")[2])
            await self.buy_now(update, context, product_id)
        elif data == "no_discount":
            await self.show_payment_methods(update, context)
        elif data == "continue_to_payment":
            await self.ask_discount_code(update, context)
        elif data.startswith("payment_"):
            currency = data.split("_")[1]
            await self.show_payment_details(update, context, currency)
        elif data == "payment_made":
            await self.ask_payment_source_address(update, context)
        elif data == "back_to_payment_methods":
            await self.show_payment_methods(update, context)
        
        # Admin handlers
        elif data == "admin_panel":
            await self.show_admin_panel(update, context)
        elif data == "product_management":
            await self.show_product_management(update, context)
        elif data == "content_management":
            await self.show_content_management(update, context)
        elif data == "payment_settings":
            await self.show_payment_settings(update, context)
        elif data == "discount_codes":
            await self.show_discount_management(update, context)
        elif data == "statistics":
            await self.show_statistics(update, context)
        elif data == "add_new_product":
            await self.start_add_product(update, context)
        elif data.startswith("edit_product_"):
            product_id = int(data.split("_")[2])
            await self.show_product_edit(update, context, product_id)
        elif data.startswith("delete_product_"):
            product_id = int(data.split("_")[2])
            await self.confirm_delete_product(update, context, product_id)
        elif data.startswith("confirm_delete_"):
            product_id = int(data.split("_")[2])
            await self.delete_product(update, context, product_id)
        elif data.startswith("cancel_delete_"):
            product_id = int(data.split("_")[2])
            await self.show_product_edit(update, context, product_id)
        elif data.startswith("edit_content_"):
            content_key = data.split("_")[2]
            await self.start_edit_content(update, context, content_key)
        elif data.startswith("edit_payment_"):
            currency = data.split("_")[2]
            await self.start_edit_payment(update, context, currency)
        elif data.startswith("remove_payment_"):
            currency = data.split("_")[2]
            await self.remove_payment_method(update, context, currency)
        elif data == "add_new_crypto":
            await self.start_add_payment_method(update, context)
        elif data == "add_client_specific_code":
            await self.start_add_client_specific_code(update, context)
        elif data == "add_general_discount":
            await self.start_add_general_discount(update, context)
        elif data == "view_all_codes":
            await self.show_all_discount_codes(update, context)
        
        # Admin payment confirmation handlers
        elif data.startswith("admin_confirm_"):
            order_id = data.split("_")[2]
            await self.ask_admin_confirmation(update, context, order_id)
        elif data.startswith("admin_confirm_yes_"):
            order_id = data.split("_")[3]
            await self.confirm_payment(update, context, order_id)
        elif data.startswith("admin_confirm_no_"):
            order_id = data.split("_")[3]
            await self.cancel_confirmation(update, context, order_id)
        elif data.startswith("admin_reject_"):
            order_id = data.split("_")[2]
            await self.reject_payment(update, context, order_id)
    
    # CLIENT FUNCTIONS
    async def show_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, price, quantity FROM products 
            WHERE active = TRUE AND quantity > 0
            ORDER BY name
        ''')
        products = cursor.fetchall()
        conn.close()
        
        if not products:
            text = "🛍️ Our Products:\n\nNo products available at the moment."
        else:
            text = "🛍️ Our Products:"
        
        keyboard = []
        for product in products:
            product_id, name, price, quantity = product
            button_text = f"{name} - {price}€" if quantity == 1 else f"{name} - {price}€ ({quantity} pcs)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"product_{product_id}")])
        
        keyboard.append([
            InlineKeyboardButton("🛒 View Cart", callback_data="view_cart"),
            InlineKeyboardButton("🔙 Back", callback_data="main_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_product_detail(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, description, price, quantity FROM products 
            WHERE id = ? AND active = TRUE
        ''', (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            await update.callback_query.edit_message_text("Product not found!")
            return
        
        name, description, price, quantity = product
        
        text = f"""🛍️ {name}

📝 {description}
💰 Price: {price}€
📦 Available: {quantity} pcs"""
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Buy Now", callback_data=f"buy_now_{product_id}"),
                InlineKeyboardButton("🛒 Add to Cart", callback_data=f"add_to_cart_{product_id}")
            ],
            [
                InlineKeyboardButton("🔙 Back to Products", callback_data="browse_products"),
                InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def add_to_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
        user_id = update.callback_query.from_user.id
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if product exists and has quantity
        cursor.execute('SELECT name, price, quantity FROM products WHERE id = ? AND active = TRUE', (product_id,))
        product = cursor.fetchone()
        
        if not product:
            await update.callback_query.answer("Product not available!", show_alert=True)
            return
        
        name, price, available_quantity = product
        
        # Check if item already in cart
        cursor.execute('SELECT quantity FROM cart WHERE user_id = ? AND product_id = ?', (user_id, product_id))
        existing_item = cursor.fetchone()
        
        if existing_item:
            current_quantity = existing_item[0]
            if current_quantity + 1 > available_quantity:
                await update.callback_query.answer("Not enough quantity available!", show_alert=True)
                return
            cursor.execute(
                'UPDATE cart SET quantity = quantity + 1 WHERE user_id = ? AND product_id = ?',
                (user_id, product_id)
            )
        else:
            cursor.execute(
                'INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, 1)',
                (user_id, product_id)
            )
        
        conn.commit()
        conn.close()
        
        await update.callback_query.answer(f"Added {name} to cart!")
    
    async def show_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.product_id, c.quantity, p.name, p.price 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = ? AND p.active = TRUE
        ''', (user_id,))
        cart_items = cursor.fetchall()
        conn.close()
        
        if not cart_items:
            text = "🛒 Your cart is empty!"
            keyboard = [
                [
                    InlineKeyboardButton("🛍️ Continue Shopping", callback_data="browse_products"),
                    InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
                ]
            ]
        else:
            text = "🛒 Your Cart:\n\n"
            total = 0
            total_items = 0
            
            for item in cart_items:
                product_id, quantity, name, price = item
                item_total = price * quantity
                text += f"🛍️ {name}\n 💰 {price}€ × {quantity} = {item_total:.2f}€\n\n"
                total += item_total
                total_items += quantity
            
            usd_total = total * self.exchange_rate
            text += f"💵 Total: {total:.2f}€ (${usd_total:.2f})"
            
            keyboard = [
                [
                    InlineKeyboardButton("💰 Checkout All", callback_data="checkout_all"),
                    InlineKeyboardButton("🗑️ Clear Cart", callback_data="clear_cart")
                ],
                [
                    InlineKeyboardButton("🛍️ Continue Shopping", callback_data="continue_shopping"),
                    InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
                ]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def clear_cart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        await update.callback_query.answer("Cart cleared!")
        await self.show_cart(update, context)
    
    async def buy_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
        context.user_data['current_order'] = {
            'type': 'single',
            'product_id': product_id,
            'quantity': 1
        }
        await self.start_checkout(update, context)
    
    async def start_checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.callback_query.from_user.id
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if 'current_order' in context.user_data and context.user_data['current_order']['type'] == 'single':
            # Single product purchase
            product_id = context.user_data['current_order']['product_id']
            cursor.execute('SELECT name, price FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            
            if product:
                name, price = product
                total = price
                context.user_data['checkout_total'] = total
                context.user_data['checkout_items'] = [{'product_id': product_id, 'name': name, 'price': price, 'quantity': 1}]
        else:
            # Cart checkout
            cursor.execute('''
                SELECT c.product_id, c.quantity, p.name, p.price 
                FROM cart c 
                JOIN products p ON c.product_id = p.id 
                WHERE c.user_id = ?
            ''', (user_id,))
            cart_items = cursor.fetchall()
            
            total = 0
            checkout_items = []
            for item in cart_items:
                product_id, quantity, name, price = item
                item_total = price * quantity
                total += item_total
                checkout_items.append({
                    'product_id': product_id,
                    'name': name,
                    'price': price,
                    'quantity': quantity
                })
            
            context.user_data['checkout_total'] = total
            context.user_data['checkout_items'] = checkout_items
        
        conn.close()
        
        await self.ask_discount_code(update, context)
    
    async def ask_discount_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        total = context.user_data.get('checkout_total', 0)
        usd_total = total * self.exchange_rate
        
        text = f"""💰 {total:.2f}€ (${usd_total:.2f})

Do you have a discount code? Enter it below or press 'No Code' to continue:"""
        
        keyboard = [
            [
                InlineKeyboardButton("🚫 No Code", callback_data="no_discount"),
                InlineKeyboardButton("✅ Continue to Payment", callback_data="continue_to_payment")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
        
        return DISCOUNT_CODE_INPUT
    
    async def receive_discount_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        discount_code = update.message.text.upper()
        user_id = update.effective_user.id
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if discount code is valid
        cursor.execute('''
            SELECT discount_percentage, expiry_date, max_uses, used_count, is_general, client_id, client_username, active
            FROM discount_codes 
            WHERE code = ? AND active = TRUE
        ''', (discount_code,))
        code_data = cursor.fetchone()
        
        if not code_data:
            await update.message.reply_text("❌ Invalid discount code. Please try again or press 'No Code':")
            return DISCOUNT_CODE_INPUT
        
        discount_percentage, expiry_date, max_uses, used_count, is_general, client_id, client_username, active = code_data
        
        # Check expiry
        if expiry_date and datetime.now().date() > datetime.strptime(expiry_date, '%Y-%m-%d').date():
            await update.message.reply_text("❌ Discount code has expired. Please try another code or press 'No Code':")
            return DISCOUNT_CODE_INPUT
        
        # Check max uses
        if max_uses != -1 and used_count >= max_uses:
            await update.message.reply_text("❌ Discount code has reached maximum uses. Please try another code or press 'No Code':")
            return DISCOUNT_CODE_INPUT
        
        # Check if client-specific code matches
        if not is_general:
            if client_id and client_id != user_id:
                await update.message.reply_text("❌ This discount code is not for you. Please try another code or press 'No Code':")
                return DISCOUNT_CODE_INPUT
            if client_username and client_username != update.effective_user.username:
                await update.message.reply_text("❌ This discount code is not for you. Please try another code or press 'No Code':")
                return DISCOUNT_CODE_INPUT
        
        # Apply discount
        original_total = context.user_data.get('checkout_total', 0)
        discount_amount = original_total * (discount_percentage / 100)
        new_total = original_total - discount_amount
        
        context.user_data['discount_code'] = discount_code
        context.user_data['checkout_total'] = new_total
        
        usd_new_total = new_total * self.exchange_rate
        
        text = f"""🎫 Discount Applied!
💰 Original: {original_total:.2f}€
📊 Discount: {discount_percentage}%
💵 New Total: {new_total:.2f}€ (${usd_new_total:.2f})"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Continue to Payment", callback_data="continue_to_payment")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return ConversationHandler.END
    
    async def show_payment_methods(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT currency_code, address, blockchain FROM payment_settings')
        payment_methods = cursor.fetchall()
        conn.close()
        
        total = context.user_data.get('checkout_total', 0)
        usd_total = total * self.exchange_rate
        
        if 'current_order' in context.user_data and context.user_data['current_order']['type'] == 'single':
            product_id = context.user_data['current_order']['product_id']
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT name, price FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            conn.close()
            product_text = f"🛍️ {product[0]}\n💰 Price: {product[1]}€"
        else:
            product_text = "🛍️ Multiple products from cart"
        
        text = f"""💳 Choose payment method:

{product_text}
💰 Total: {total:.2f}€ (${usd_total:.2f})"""
        
        keyboard = []
        for method in payment_methods:
            currency_code, address, blockchain = method
            currency_name = {
                'btc': '₿ Bitcoin',
                'eth': 'Ξ Ethereum', 
                'sol': '◎ Solana',
                'ltc': '💎 Litecoin',
                'usdt': '💵 USDT'
            }.get(currency_code, currency_code.upper())
            
            keyboard.append([InlineKeyboardButton(currency_name, callback_data=f"payment_{currency_code}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="view_cart")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_payment_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT address, blockchain FROM payment_settings WHERE currency_code = ?', (currency,))
        payment_method = cursor.fetchone()
        conn.close()
        
        if not payment_method:
            await update.callback_query.edit_message_text("Payment method not found!")
            return
        
        address, blockchain = payment_method
        total = context.user_data.get('checkout_total', 0)
        usd_total = total * self.exchange_rate
        
        currency_name = {
            'btc': 'Bitcoin',
            'eth': 'Ethereum',
            'sol': 'Solana', 
            'ltc': 'Litecoin',
            'usdt': 'USDT'
        }.get(currency, currency.upper())
        
        text = f"""💳 **PAYMENT DETAILS**

🛍️ {'Single product' if 'current_order' in context.user_data else 'Cart items'}
💰 Total: {total:.2f}€ (${usd_total:.2f})
⛓️ Blockchain: {blockchain}

📧 **SEND PAYMENT TO ADDRESS:**
`{address}`

⚠️ **IMPORTANT:**
• Send exactly {total:.2f}€ worth of {currency_name}
• Copy address exactly

After payment, click the button below:"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ PAYMENT MADE", callback_data="payment_made"),
                InlineKeyboardButton("🔙 Back to Payment Methods", callback_data="back_to_payment_methods")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data['payment_currency'] = currency
        context.user_data['payment_address'] = address
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def ask_payment_source_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """🔍 **PAYMENT CONFIRMATION**

Please enter the payment source address (where you sent from):

⚠️ **IMPORTANT:** This helps us identify your payment and link it to your order!

Example: `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`"""
        
        await update.callback_query.edit_message_text(text, parse_mode='Markdown')
        return PAYMENT_SOURCE_ADDRESS
    
    async def receive_payment_source_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        payment_source = update.message.text
        user = update.effective_user
        order_id = str(uuid.uuid4())[:8].upper()
        
        # Create order record
        conn = db.get_connection()
        cursor = conn.cursor()
        
        checkout_items = context.user_data.get('checkout_items', [])
        total = context.user_data.get('checkout_total', 0)
        currency = context.user_data.get('payment_currency')
        discount_code = context.user_data.get('discount_code')
        
        for item in checkout_items:
            cursor.execute('''
                INSERT INTO orders 
                (user_id, user_name, product_id, product_name, quantity, total_price, order_id, payment_currency, payment_source_address, discount_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.id,
                user.username or user.first_name,
                item['product_id'],
                item['name'],
                item['quantity'],
                total,
                order_id,
                currency,
                payment_source,
                discount_code
            ))
            
            # Update product quantity
            cursor.execute('''
                UPDATE products SET quantity = quantity - ? WHERE id = ?
            ''', (item['quantity'], item['product_id']))
        
        # Clear cart if this was a cart checkout
        if 'current_order' not in context.user_data:
            cursor.execute('DELETE FROM cart WHERE user_id = ?', (user.id,))
        
        # Update discount code usage
        if discount_code:
            cursor.execute('''
                UPDATE discount_codes SET used_count = used_count + 1 
                WHERE code = ? AND (max_uses = -1 OR used_count < max_uses)
            ''', (discount_code,))
        
        conn.commit()
        conn.close()
        
        # Clear temporary data
        context.user_data.pop('checkout_total', None)
        context.user_data.pop('checkout_items', None)
        context.user_data.pop('payment_currency', None)
        context.user_data.pop('current_order', None)
        context.user_data.pop('discount_code', None)
        
        # Notify admin
        await self.notify_admin_of_payment(context, user, order_id, total, currency, payment_source, discount_code)
        
        text = f"""✅ Notified admin of your payment!
🆔 Order ID: {order_id}
💰 Total: {total:.2f}€
📧 Payment source address: {payment_source}

Admin will check your transaction and send products after confirmation."""
        
        await update.message.reply_text(text)
        
        # Show main menu
        await self.start(update, context)
        return ConversationHandler.END
    
    async def notify_admin_of_payment(self, context: ContextTypes.DEFAULT_TYPE, user, order_id: str, total: float, currency: str, payment_source: str, discount_code: str = None):
        user_info = f"@{user.username}" if user.username else user.first_name
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT product_name FROM orders WHERE order_id = ? LIMIT 1', (order_id,))
        order = cursor.fetchone()
        conn.close()
        
        product_name = order[0] if order else "Cart checkout"
        
        text = f"""🔄 PAYMENT AWAITING CONFIRMATION!

👤 Client: {user_info}
🆔 User ID: {user.id}
🛍️ Product: {product_name}
💰 Price: {total:.2f}€
🆔 Order ID: {order_id}
⛓️ Crypto: {currency.upper()}
📧 Payment source address: {payment_source}
🎫 Discount Code: {discount_code if discount_code else 'None'}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Is payment visible in your wallet?"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Payment", callback_data=f"admin_confirm_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{order_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=self.admin_id,
            text=text,
            reply_markup=reply_markup
        )
    
    # PAYMENT CONFIRMATION SYSTEM - PILDID SAADETAKSE KLIENTIDELE ALLA
    async def ask_admin_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Küsib adminilt makse kinnitust"""
        text = f"""🔍 **CONFIRMATION**

Are you sure you want to approve this payment?

🆔 Order ID: {order_id}"""

        keyboard = [
            [
                InlineKeyboardButton("✅ YES, confirm payment", callback_data=f"admin_confirm_yes_{order_id}"),
                InlineKeyboardButton("❌ NO, cancel", callback_data=f"admin_confirm_no_{order_id}")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def confirm_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Kinnitab makse ja saadab kliendile pildid/koordinaadid"""
        conn = db.get_connection()
        cursor = conn.cursor()

        # Võtame kõik selle tellimuse tooted
        cursor.execute('SELECT user_id, product_id, product_name, quantity FROM orders WHERE order_id = ?', (order_id,))
        orders = cursor.fetchall()

        # Muudame tellimuse staatuse "completed"
        cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', ('completed', order_id))
        conn.commit()

        # Saadame kliendile toote pildid ja koordinaadid
        for order in orders:
            user_id, product_id, product_name, quantity = order

            # Võtame toote pildid ja koordinaadid andmebaasist
            cursor.execute('SELECT image1, image2, coordinates FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()

            if product:
                image1, image2, coordinates = product

                # Saadame kliendile kinnitusteate
                text = f"✅ Your payment has been confirmed!\n\n🛍️ Product: {product_name}\n📦 Quantity: {quantity}"

                if coordinates:
                    text += f"\n📍 Location: {coordinates}"

                # Saadame teksti
                await context.bot.send_message(chat_id=user_id, text=text)

                # SAADAME PILDID kliendile (need ei olnud enne maksmist nähtavad)
                if image1:
                    await context.bot.send_photo(chat_id=user_id, photo=image1, caption="Product image 1")
                if image2:
                    await context.bot.send_photo(chat_id=user_id, photo=image2, caption="Product image 2")

        conn.close()

        # Uuendame admini teadet
        query = update.callback_query
        await query.edit_message_text(f"✅ Payment for order {order_id} confirmed and client notified!")

    async def cancel_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Tühistab admini kinnituse"""
        # Läheme tagasi algse makse teate juurde
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, user_name, product_name, total_price, payment_currency, payment_source_address, discount_code FROM orders WHERE order_id = ? LIMIT 1', (order_id,))
        order = cursor.fetchone()
        conn.close()

        if order:
            user_id, user_name, product_name, total_price, payment_currency, payment_source_address, discount_code = order

            text = f"""🔄 PAYMENT AWAITING CONFIRMATION!

👤 Client: {user_name}
🆔 User ID: {user_id}
🛍️ Product: {product_name}
💰 Price: {total_price:.2f}€
🆔 Order ID: {order_id}
⛓️ Crypto: {payment_currency}
📧 Payment source address: {payment_source_address}
🎫 Discount Code: {discount_code if discount_code else 'None'}
⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Is payment visible in your wallet?"""

            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm Payment", callback_data=f"admin_confirm_{order_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{order_id}")
                ]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            query = update.callback_query
            await query.edit_message_text(text, reply_markup=reply_markup)

    async def reject_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
        """Lükkab makse tagasi"""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', ('rejected', order_id))
        conn.commit()

        # Teavitame klienti
        cursor.execute('SELECT user_id FROM orders WHERE order_id = ? LIMIT 1', (order_id,))
        order = cursor.fetchone()
        if order:
            user_id = order[0]
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"❌ Your payment for order {order_id} has been rejected. Please contact admin."
            )

        conn.close()

        query = update.callback_query
        await query.edit_message_text(f"❌ Payment for order {order_id} rejected!")
    
    # STATIC CONTENT METHODS
    def get_content(self, key: str) -> str:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM content WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "Content not found"
    
    async def show_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = self.get_content('about_us')
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = self.get_content('contact')
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_website(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        website_url = self.get_content('website')
        text = f"🌐 Visit our website: {website_url}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_rules(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = self.get_content('rules')
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_faq(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = self.get_content('faq')
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    # ADMIN METHODS
    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            if update.callback_query:
                await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        text = "🛠️ Admin Panel:"
        
        keyboard = [
            [InlineKeyboardButton("📦 Product Management", callback_data="product_management")],
            [InlineKeyboardButton("📝 Content Management", callback_data="content_management")],
            [InlineKeyboardButton("💳 Payment Settings", callback_data="payment_settings")],
            [InlineKeyboardButton("🎫 Discount Codes", callback_data="discount_codes")],
            [InlineKeyboardButton("📊 Statistics", callback_data="statistics")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_product_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, price, active FROM products ORDER BY name')
        products = cursor.fetchall()
        conn.close()
        
        text = "📦 Product Management:"
        
        keyboard = []
        for product in products:
            product_id, name, price, active = product
            status = "✅" if active else "❌"
            keyboard.append([InlineKeyboardButton(
                f"{status} {name} - {price}€", 
                callback_data=f"edit_product_{product_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Add New Product", callback_data="add_new_product")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def start_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        context.user_data['new_product'] = {}
        await update.callback_query.edit_message_text("Enter product name:")
        return PRODUCT_NAME
    
    async def receive_product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['new_product']['name'] = update.message.text
        await update.message.reply_text("Enter product price (example: 25.00):")
        return PRODUCT_PRICE
    
    async def receive_product_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            price = float(update.message.text)
            context.user_data['new_product']['price'] = price
            await update.message.reply_text("Enter product description:")
            return PRODUCT_DESCRIPTION
        except ValueError:
            await update.message.reply_text("Invalid price format. Please enter a number (example: 25.00):")
            return PRODUCT_PRICE
    
    async def receive_product_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['new_product']['description'] = update.message.text
        await update.message.reply_text("Enter product quantity (example: 5):")
        return PRODUCT_QUANTITY
    
    async def receive_product_quantity(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            quantity = int(update.message.text)
            context.user_data['new_product']['quantity'] = quantity
            await update.message.reply_text("Now send the first product image:")
            return PRODUCT_IMAGE1
        except ValueError:
            await update.message.reply_text("Invalid quantity. Please enter a whole number (example: 5):")
            return PRODUCT_QUANTITY
    
    async def receive_product_image1(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.photo:
            # Store the file_id of the largest photo
            photo = update.message.photo[-1]
            context.user_data['new_product']['image1'] = photo.file_id
            await update.message.reply_text("Would you like to add a second image? Send 'yes' to add second image or 'no' to skip:")
            return PRODUCT_IMAGE2_OPTION
        else:
            await update.message.reply_text("Please send an image file:")
            return PRODUCT_IMAGE1
    
    async def receive_product_image2_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = update.message.text.lower()
        if response == 'yes':
            await update.message.reply_text("Please send the second product image:")
            return PRODUCT_IMAGE2
        elif response == 'no':
            context.user_data['new_product']['image2'] = None
            await update.message.reply_text("Now you can add map coordinates (optional). Enter coordinates in format: 59.4370, 24.7536\nOr send 'skip' to skip.")
            return PRODUCT_COORDINATES
        else:
            await update.message.reply_text("Please send 'yes' or 'no':")
            return PRODUCT_IMAGE2_OPTION
    
    async def receive_product_image2(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.photo:
            photo = update.message.photo[-1]
            context.user_data['new_product']['image2'] = photo.file_id
            await update.message.reply_text("Now you can add map coordinates (optional). Enter coordinates in format: 59.4370, 24.7536\nOr send 'skip' to skip.")
            return PRODUCT_COORDINATES
        else:
            await update.message.reply_text("Please send an image file:")
            return PRODUCT_IMAGE2
    
    async def receive_product_coordinates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        coords_text = update.message.text.strip()
        if coords_text.lower() == 'skip':
            context.user_data['new_product']['coordinates'] = None
        else:
            # Basic coordinate validation
            try:
                lat, lon = map(float, coords_text.split(','))
                context.user_data['new_product']['coordinates'] = coords_text
            except ValueError:
                await update.message.reply_text("Invalid coordinates format. Please use format: 59.4370, 24.7536\nOr send 'skip' to skip.")
                return PRODUCT_COORDINATES
        
        # Save product to database
        product_data = context.user_data['new_product']
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (name, price, description, quantity, image1, image2, coordinates, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, TRUE)
        ''', (
            product_data['name'],
            product_data['price'],
            product_data['description'],
            product_data['quantity'],
            product_data.get('image1'),
            product_data.get('image2'),
            product_data.get('coordinates')
        ))
        
        conn.commit()
        conn.close()
        
        # Prepare completion message
        coord_message = f"📍 Coordinates: {product_data.get('coordinates') or 'Not set'}\n\n" if product_data.get('coordinates') else ""
        image_count = 1 + (1 if product_data.get('image2') else 0)
        
        text = f"""🎉 Product added completely!
{coord_message}
📦 {product_data['name']}
💰 {product_data['price']}€
🖼️ {image_count} image(s) attached

Product is now available to clients."""
        
        await update.message.reply_text(text)
        
        # Clear temporary data
        context.user_data.pop('new_product')
        
        # Show product management
        await self.show_product_management(update, context)
        return ConversationHandler.END

    async def show_product_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name, price, description, quantity, coordinates, active FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            await update.callback_query.edit_message_text("Product not found!")
            return
        
        name, price, description, quantity, coordinates, active = product
        status = "Active" if active else "Inactive"
        
        text = f"""📦 Product: {name}
💰 Price: {price}€
📝 Description: {description}
📦 Quantity: {quantity}
📍 Coordinates: {coordinates or 'Not set'}
🎯 Status: {status}"""
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Name", callback_data=f"edit_name_{product_id}")],
            [InlineKeyboardButton("💰 Edit Price", callback_data=f"edit_price_{product_id}")],
            [InlineKeyboardButton("📝 Edit Description", callback_data=f"edit_description_{product_id}")],
            [InlineKeyboardButton("📦 Edit Quantity", callback_data=f"edit_quantity_{product_id}")],
            [InlineKeyboardButton("📍 Edit Coordinates", callback_data=f"edit_coordinates_{product_id}")],
            [InlineKeyboardButton("🖼️ Add/Replace Image 1", callback_data=f"edit_image1_{product_id}")],
            [InlineKeyboardButton("🖼️ Add/Replace Image 2", callback_data=f"edit_image2_{product_id}")],
            [InlineKeyboardButton("🔄 Toggle Active", callback_data=f"toggle_active_{product_id}")],
            [InlineKeyboardButton("🗑️ Delete Product", callback_data=f"delete_product_{product_id}")],
            [InlineKeyboardButton("🔙 Back to Products", callback_data="product_management")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def confirm_delete_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name, price FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            await update.callback_query.edit_message_text("Product not found!")
            return
        
        name, price = product
        
        text = f"""🗑️ **DELETE CONFIRMATION**

Are you sure you want to delete this product?

📦 {name}
💰 {price}€

⚠️ **This action cannot be undone!**"""
        
        keyboard = [
            [
                InlineKeyboardButton("✅ YES, delete", callback_data=f"confirm_delete_{product_id}"),
                InlineKeyboardButton("❌ NO, cancel", callback_data=f"cancel_delete_{product_id}")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def delete_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        
        await update.callback_query.answer("Product deleted!")
        await self.show_product_management(update, context)
    
    # Additional admin functions would continue here...
    # For brevity, I'm showing the most critical functions
    
    async def show_content_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        text = "📝 Content Management:"
        
        keyboard = [
            [InlineKeyboardButton("👋 Welcome Message", callback_data="edit_content_welcome_message")],
            [InlineKeyboardButton("ℹ️ About Us", callback_data="edit_content_about_us")],
            [InlineKeyboardButton("📞 Contact", callback_data="edit_content_contact")],
            [InlineKeyboardButton("🌐 Website", callback_data="edit_content_website")],
            [InlineKeyboardButton("📝 Rules", callback_data="edit_content_rules")],
            [InlineKeyboardButton("🔍 FAQ", callback_data="edit_content_faq")],
            [InlineKeyboardButton("🎉 Success Message", callback_data="edit_content_success_message")],
            [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_payment_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT currency_code, address, blockchain FROM payment_settings')
        payment_methods = cursor.fetchall()
        conn.close()
        
        text = "💳 Payment Settings:\n\n"
        
        keyboard = []
        for method in payment_methods:
            currency_code, address, blockchain = method
            currency_name = {
                'btc': '₿ Bitcoin',
                'eth': 'Ξ Ethereum', 
                'sol': '◎ Solana',
                'ltc': '💎 Litecoin',
                'usdt': '💵 USDT'
            }.get(currency_code, currency_code.upper())
            
            text += f"{currency_name}:\n`{address}`\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✏️ Edit {currency_name}", callback_data=f"edit_payment_{currency_code}"),
                InlineKeyboardButton(f"🗑️ Remove {currency_name}", callback_data=f"remove_payment_{currency_code}")
            ])
        
        keyboard.append([InlineKeyboardButton("➕ Add New Crypto", callback_data="add_new_crypto")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_discount_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        text = "🎫 Discount Code Management:"
        
        keyboard = [
            [InlineKeyboardButton("👤 Add Client-Specific", callback_data="add_client_specific_code")],
            [InlineKeyboardButton("🌍 Add General Discount", callback_data="add_general_discount")],
            [InlineKeyboardButton("📋 View All Codes", callback_data="view_all_codes")],
            [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            await update.callback_query.answer("Access denied!", show_alert=True)
            return
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Product statistics
        cursor.execute('SELECT COUNT(*) FROM products')
        total_products = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM products WHERE active = TRUE')
        active_products = cursor.fetchone()[0]
        
        # Order statistics
        cursor.execute('SELECT COUNT(*) FROM orders')
        total_orders = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "completed"')
        completed_orders = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM orders WHERE status = "pending"')
        pending_orders = cursor.fetchone()[0]
        
        # Cart statistics
        cursor.execute('SELECT COUNT(*) FROM cart')
        products_in_carts = cursor.fetchone()[0]
        
        # Discount code statistics
        cursor.execute('SELECT COUNT(*) FROM discount_codes')
        total_codes = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM discount_codes WHERE active = TRUE')
        active_codes = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""📊 STORE STATISTICS

🛍️ PRODUCTS:
• All products: {total_products}
• Active products: {active_products}

📦 ORDERS:
• All orders: {total_orders}
• Completed: {completed_orders}
• Pending: {pending_orders}

🛒 CARTS:
• Products in carts: {products_in_carts}

🎫 DISCOUNT CODES:
• All codes: {total_codes}
• Active: {active_codes}"""
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=reply_markup)
    
    def setup_handlers(self, application):
        # Start command
        application.add_handler(CommandHandler("start", self.start))
        
        # Button handler
        application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Add product conversation
        add_product_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_add_product, pattern="^add_new_product$")],
            states={
                PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_product_name)],
                PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_product_price)],
                PRODUCT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_product_description)],
                PRODUCT_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_product_quantity)],
                PRODUCT_IMAGE1: [MessageHandler(filters.PHOTO, self.receive_product_image1)],
                PRODUCT_IMAGE2_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_product_image2_option)],
                PRODUCT_IMAGE2: [MessageHandler(filters.PHOTO, self.receive_product_image2)],
                PRODUCT_COORDINATES: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_product_coordinates)],
            },
            fallbacks=[],
        )
        
        application.add_handler(add_product_conv)
        
        # Payment source address handler
        payment_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.ask_payment_source_address, pattern="^payment_made$")],
            states={
                PAYMENT_SOURCE_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_payment_source_address)],
            },
            fallbacks=[],
        )
        
        application.add_handler(payment_conv)
        
        # Discount code input handler
        discount_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.ask_discount_code, pattern="^continue_to_payment$")],
            states={
                DISCOUNT_CODE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.receive_discount_code)],
            },
            fallbacks=[],
        )
        
        application.add_handler(discount_conv)

    def run(self):
        application = Application.builder().token(self.token).build()
        self.setup_handlers(application)
        
        logger.info("Bot is running...")
        application.run_polling()

if __name__ == '__main__':
    bot = StoreBot()
    bot.run()
