import datetime
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import database as db_helper
from functools import wraps

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='TEST',
        DATABASE=os.path.join(app.instance_path, 'hb.db'),
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    db_path = app.config['DATABASE']
    if not os.path.exists(db_path):
        db_helper.init_db(db_path)

    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped_view
    
    
    def admin_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            user_data = db_helper.query_db(db_path, 'SELECT rol FROM users WHERE id = ?', (session['user_id'],), one=True)
            if not user_data or user_data['rol'] != 1:
                print('Acceso denegado. No tienes permisos de administrador.') 
                return redirect(url_for('index'))
            return view(*args, **kwargs)
        return wrapped_view

    @app.route('/')
    def index():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            user_data = db_helper.query_db(db_path, 'SELECT rol FROM users WHERE id = ?', (session['user_id'],), one=True)
            if user_data and user_data['rol'] == 1:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))

        error_message = None 

        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = db_helper.query_db(db_path, 'SELECT * FROM users WHERE username = ?', (username,), one=True)

            if user and check_password_hash(user['password_hash'], password):
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                if user['rol'] == 1:
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('dashboard'))
            else:
                error_message = 'Usuario o contraseña incorrectos.'
        
        return render_template('login.html', error_message=error_message)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        error_message = None
        success_message = None

        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            nombre = request.form.get('nombre', '')
            apellido = request.form.get('apellido', '')
            telefono = request.form.get('telefono', '')
            direccion = request.form.get('direccion', '')

            if not username or not password or not nombre or not apellido:
                error_message = 'Usuario, contraseña, nombre y apellido son requeridos.'
            else:
                existing_user = db_helper.query_db(db_path, 'SELECT * FROM users WHERE username = ?', (username,), one=True)
                if existing_user:
                    error_message = f"El usuario '{username}' ya esta registrado."
                else:
                    hashed_password = generate_password_hash(password)
                    try:
                        db_helper.execute_db(
                            db_path,
                            'INSERT INTO users (username, password_hash, nombre, apellido, telefono, direccion) VALUES (?, ?, ?, ?, ?, ?)',
                            (username, hashed_password, nombre, apellido, telefono, direccion)
                        )
                        success_message = 'Registro exitoso! Ahora podes iniciar sesion.'
                        return render_template('login.html', success_message=success_message)
                    except Exception as e:
                        error_message = f'Error al registrar el usuario: {str(e)}'
        
        return render_template('register.html', error_message=error_message, success_message=success_message)

    @app.route('/dashboard')
    @login_required
    def dashboard():
        username = session.get('username')
        return render_template('dashboard.html', username=username)

    @app.route('/products')
    @login_required
    def products():
        filter_vegetariano = request.args.get('vegetariano', '0') == '1' 
        filter_vegano = request.args.get('vegano', '0') == '1'
        filter_gluten_free = request.args.get('sin_tacc', '0') == '1'

        # Asegúrate de seleccionar informacion_nutricional
        query = 'SELECT id, nombre, descripcion, precio, informacion_nutricional, es_vegetariano, es_vegano, es_sin_tacc FROM products WHERE 1=1'
        params = []

        if filter_vegetariano:
            query += ' AND es_vegetariano = 1'
        if filter_vegano:
            query += ' AND es_vegano = 1'
        if filter_gluten_free:
            query += ' AND es_sin_tacc = 1'

        query += ' ORDER BY nombre ASC'
        products_raw = db_helper.query_db(db_path, query, params)
        products_for_template = [dict(p) for p in products_raw] if products_raw else []
        current_filters = {
            'vegetariano': filter_vegetariano,
            'vegano': filter_vegano,
            'sin_tacc': filter_gluten_free
        }

        success_message = request.args.get('success')
        error_message = request.args.get('error')

        return render_template(
            'products.html', 
            products=products_for_template, 
            filters=current_filters,
            success=success_message,
            error=error_message      
        )

    @app.route('/add_to_cart', methods=['POST'])
    @login_required
    def add_to_cart():
        product_id = request.form.get('product_id', type=int)
        quantity = request.form.get('quantity', type=int, default=1)

        if not product_id or quantity <= 0:
            return redirect(url_for('products', error='Error: No se pudo añadir el producto al carrito. Cantidad inválida.'))

        product = db_helper.query_db(db_path, 'SELECT id, nombre, precio FROM products WHERE id = ?', (product_id,), one=True)
        if not product:
            return redirect(url_for('products', error='Error: El producto seleccionado no existe.'))

        if 'cart' not in session:
            session['cart'] = []

        found_in_cart = False
        for item in session['cart']:
            if item['product_id'] == product_id:
                item['quantity'] += quantity
                found_in_cart = True
                break
        
        if not found_in_cart:
            session['cart'].append({
                'product_id': product_id,
                'name': product['nombre'],
                'price': float(product['precio']),
                'quantity': quantity
            })
        
        session.modified = True
        
        return redirect(url_for('products', success=f'"{product["nombre"]}" agregado al carrito.'))


    @app.route('/cart')
    @login_required
    def view_cart():
        cart_data = session.get('cart', [])
        cart_items = []
        total_price = 0

        for item in cart_data:
            product = db_helper.query_db(db_path, 'SELECT id, nombre, precio FROM products WHERE id = ?', (item['product_id'],), one=True)
            if product:
                subtotal = product['precio'] * item['quantity']
                total_price += subtotal
                cart_items.append({
                    'product_id': item['product_id'],
                    'name': product['nombre'],
                    'quantity': item['quantity'],
                    'price': product['precio'],
                    'subtotal': subtotal
                })
                
        session['cart'] = [item for item in cart_data if db_helper.query_db(db_path, 'SELECT id FROM products WHERE id = ?', (item['product_id'],), one=True)]
        session.modified = True

        return render_template('cart.html', cart_items=cart_items, total_price=total_price)


    @app.route('/remove_from_cart/<int:product_id>')
    @login_required
    def remove_from_cart(product_id):
        if 'cart' in session:
            session['cart'] = [item for item in session['cart'] if item['product_id'] != product_id]
            session.modified = True
        return redirect(url_for('view_cart'))


    @app.route('/checkout', methods=['GET', 'POST'])
    @login_required
    def checkout():
        cart_data = session.get('cart', [])
        cart_items_for_checkout = []
        total_price_for_checkout = 0
        
        error_message = None
        success_message = None

        if cart_data:
            for item in cart_data:
                product = db_helper.query_db(db_path, 'SELECT id, nombre, precio, descripcion FROM products WHERE id = ?', (item['product_id'],), one=True)
                if product:
                    subtotal = product['precio'] * item['quantity']
                    total_price_for_checkout += subtotal
                    cart_items_for_checkout.append({
                        'product_id': item['product_id'],
                        'name': product['nombre'],
                        'quantity': item['quantity'],
                        'price': product['precio'],
                        'subtotal': subtotal,
                        'description': product['descripcion']
                    })
            
        if not cart_items_for_checkout and request.method == 'GET':
            error_message = 'Tu carrito esta vacio. Añade algunos productos para finalizar el pedido.'
            return render_template('checkout.html', 
                                    cart_items=[], 
                                    total_price=0, 
                                    error_message=error_message)
                
        if request.method == 'POST':
            user_id = session.get('user_id')
            if not user_id:
                error_message = 'Debes iniciar sesion para completar tu pedido.'
                return render_template('checkout.html', 
                                        cart_items=cart_items_for_checkout, 
                                        total_price=total_price_for_checkout, 
                                        error_message=error_message)
            
            if not cart_items_for_checkout:
                error_message = 'Tu carrito esta vacio. No se puede procesar el pedido.'
                return render_template('checkout.html', 
                                        cart_items=[], 
                                        total_price=0, 
                                        error_message=error_message)

            forma_pago = request.form.get('forma_pago', 'Efectivo')
            fecha_entrega_str = request.form.get('fecha_entrega')

            if not fecha_entrega_str:
                error_message = 'La fecha de entrega es obligatoria.'
                return render_template('checkout.html', 
                                        cart_items=cart_items_for_checkout, 
                                        total_price=total_price_for_checkout, 
                                        error_message=error_message)
            try:
                fecha_entrega = datetime.datetime.strptime(fecha_entrega_str, '%Y-%m-%d').date()
            except ValueError:
                error_message = 'Formato de fecha de entrega invalido.'
                return render_template('checkout.html', 
                                        cart_items=cart_items_for_checkout, 
                                        total_price=total_price_for_checkout, 
                                        error_message=error_message)

            today = datetime.date.today()
            if fecha_entrega < today:
                error_message = 'La fecha de entrega no puede ser anterior al dia de hoy.'
                return render_template('checkout.html', 
                                        cart_items=cart_items_for_checkout, 
                                        total_price=total_price_for_checkout, 
                                        error_message=error_message)

            conn = None 
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO orders (user_id, fecha_pedido, total_precio, forma_pago, fecha_entrega) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?)',
                    (user_id, total_price_for_checkout, forma_pago, fecha_entrega.isoformat())
                )
                order_id = cursor.lastrowid

                if not order_id: 
                    raise Exception("No se pudo obtener el ID de la orden insertada.")
                for item in cart_items_for_checkout:
                    cursor.execute(
                        'INSERT INTO order_items (order_id, product_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
                        (order_id, item['product_id'], item['quantity'], item['price'])
                    )
                
                conn.commit()

                session.pop('cart', None) 
                session.modified = True
                
                success_message = 'Tu pedido ha sido realizado exitosamente!'
                return render_template('checkout.html', 
                                        cart_items=[], 
                                        total_price=0, 
                                        success_message=success_message)
                
            except sqlite3.Error as e:
                if conn: conn.rollback()
                error_message = f'Error al procesar el pedido: {e}'
                print(f"Database error during checkout: {e}")
                return render_template('checkout.html', 
                                        cart_items=cart_items_for_checkout, 
                                        total_price=total_price_for_checkout, 
                                        error_message=error_message)
            except Exception as e:
                if conn: conn.rollback()
                error_message = f'Ocurrio un error inesperado: {e}'
                print(f"Unexpected error during checkout: {e}")
                return render_template('checkout.html', 
                                        cart_items=cart_items_for_checkout, 
                                        total_price=total_price_for_checkout, 
                                        error_message=error_message)
            finally:
                if conn: conn.close()
    
        return render_template('checkout.html', 
                                cart_items=cart_items_for_checkout, 
                                total_price=total_price_for_checkout,
                                error_message=error_message, 
                                success_message=success_message)


    @app.route('/orders')
    @login_required
    def orders():
        user_id = session['user_id']
        orders_list = db_helper.query_db(
            db_path, 
            'SELECT id, fecha_pedido, total_precio, forma_pago, fecha_entrega FROM orders WHERE user_id = ? ORDER BY fecha_pedido DESC', 
            (user_id,)
        )

        detailed_orders = []
        for order_row in orders_list: 
            order_id = order_row['id']
            order_items_raw = db_helper.query_db(
                db_path,
                'SELECT oi.cantidad, oi.precio_unitario, p.nombre, p.descripcion FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?',
                (order_id,)
            )
            processed_items_for_template = []
            if order_items_raw:
                for item_row in order_items_raw:
                    subtotal = item_row['cantidad'] * item_row['precio_unitario']
                    
                    item_dict = dict(item_row)
                    item_dict['subtotal'] = subtotal
                    processed_items_for_template.append(item_dict)
                
            current_order_dict = {
                'id': order_row['id'],
                'fecha_pedido': order_row['fecha_pedido'],
                'total_precio': order_row['total_precio'],
                'forma_pago': order_row['forma_pago'],
                'fecha_entrega': order_row['fecha_entrega'],
                'productos_del_pedido': processed_items_for_template 
            }
            
            detailed_orders.append(current_order_dict)
        
        return render_template('orders.html', orders=detailed_orders)

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        user_id = session['user_id']
        user_data = db_helper.query_db(
            db_path,
            'SELECT username, nombre, apellido, telefono, direccion FROM users WHERE id = ?',
            (user_id,), one=True
        )

        error_message = None
        success_message = None

        if request.method == 'POST':
            nombre = request.form.get('nombre', '')
            apellido = request.form.get('apellido', '')
            telefono = request.form.get('telefono', '')
            direccion = request.form.get('direccion', '')
            
            try:
                db_helper.execute_db(
                    db_path,
                    'UPDATE users SET nombre = ?, apellido = ?, telefono = ?, direccion = ? WHERE id = ?',
                    (nombre, apellido, telefono, direccion, user_id)
                )
                success_message = 'Perfil actualizado exitosamente!'
                user_data = db_helper.query_db(
                    db_path,
                    'SELECT username, nombre, apellido, telefono, direccion FROM users WHERE id = ?',
                    (user_id,), one=True
                )
            except Exception as e:
                error_message = f'Error al actualizar el perfil: {str(e)}'

        return render_template('profile.html', user=user_data, error_message=error_message, success_message=success_message)
    
    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        return render_template('admin_dashboard.html')

    @app.route('/admin/products')
    @admin_required
    def admin_products():
        products = db_helper.get_all_products(db_path)
        return render_template('admin_products.html', products=products)

    @app.route('/admin/products/add', methods=['GET', 'POST'])
    @admin_required
    def admin_add_product():
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            informacion_nutricional = request.form.get('informacion_nutricional')
            precio_str = request.form.get('precio')
            es_vegetariano = 1 if request.form.get('es_vegetariano') == 'on' else 0
            es_vegano = 1 if request.form.get('es_vegano') == 'on' else 0
            es_sin_tacc = 1 if request.form.get('es_sin_tacc') == 'on' else 0

            if not nombre or not descripcion or not precio_str:
                return render_template('admin_product_add.html', product={}, error_message="Faltan campos obligatorios (Nombre, Descripción, Precio).")
            
            try:
                precio = float(precio_str)
                if precio <= 0:
                    return render_template('admin_product_add.html', product={}, error_message="El precio debe ser un numero positivo.")
            except ValueError:
                return render_template('admin_product_add.html', product={}, error_message="El precio debe ser un numero valido.")
                
            db_helper.add_product(db_path, nombre, descripcion, informacion_nutricional, precio, es_vegetariano, es_vegano, es_sin_tacc)
            return redirect(url_for('admin_products'))
        
        return render_template('admin_product_add.html', product={})

    @app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_product(product_id):
        product = db_helper.get_product_by_id(db_path, product_id)
        if not product:
            return redirect(url_for('admin_products'))

        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            informacion_nutricional = request.form.get('informacion_nutricional')
            precio_str = request.form.get('precio')
            es_vegetariano = 1 if request.form.get('es_vegetariano') == 'on' else 0
            es_vegano = 1 if request.form.get('es_vegano') == 'on' else 0
            es_sin_tacc = 1 if request.form.get('es_sin_tacc') == 'on' else 0
            # ---------------------------------------------------------------------------------

            if not nombre or not descripcion or not precio_str:
                return render_template('admin_product_add.html', product=product, error_message="Faltan campos obligatorios (Nombre, Descripcion, Precio).")
            
            try:
                precio = float(precio_str)
                if precio <= 0:
                    return render_template('admin_product_add.html', product=product, error_message="El precio debe ser un numero positivo.")
            except ValueError:
                return render_template('admin_product_add.html', product=product, error_message="El precio debe ser un numero valido.")
                
            db_helper.update_product(db_path, product_id, nombre, descripcion, informacion_nutricional, precio, es_vegetariano, es_vegano, es_sin_tacc)
            return redirect(url_for('admin_products'))
        
        return render_template('admin_product_add.html', product=product)

    @app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
    @admin_required
    def admin_delete_product(product_id):
        db_helper.delete_product(db_path, product_id)
        return redirect(url_for('admin_products'))

    @app.route('/logout')
    @login_required
    def logout():
        session.clear()
        return redirect(url_for('login'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)