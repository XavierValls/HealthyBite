import sqlite3
import os

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db(db_path):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS users;
                         
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            telefono TEXT,
            direccion TEXT,
            rol INTEGER DEFAULT 0
        );


        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            descripcion TEXT,
            precio REAL NOT NULL,
            informacion_nutricional TEXT,
            es_vegetariano INTEGER DEFAULT 0 NOT NULL,
            es_vegano INTEGER DEFAULT 0 NOT NULL,
            es_sin_tacc INTEGER DEFAULT 0 NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            fecha_pedido TEXT NOT NULL DEFAULT (DATETIME('now')),
            total_precio REAL NOT NULL,
            fecha_entrega TEXT,
            forma_pago TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE TABLE order_items (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
        );

        INSERT INTO products (nombre, descripcion, precio, informacion_nutricional, es_vegetariano, es_vegano, es_sin_tacc) VALUES
            ('Ensalada de Quinoa Fresca', 'Una mezcla vibrante de quinoa, vegetales frescos y aderezo ligero.', 4500, 'Rica en proteínas y fibra.', 1, 1, 1),
            ('Sándwich de Pollo a la Parrilla', 'Pechuga de pollo jugosa, lechuga, tomate y aguacate en pan integral.', 9000, 'Fuente de proteínas.', 0, 0, 0),
            ('Wrap de Garbanzos y Vegetales', 'Garbanzos especiados con vegetales asados en tortilla integral.', 6500, 'Opción saludable y llena de sabor.', 1, 1, 0),
            ('Lasaña Vegetal Casera', 'Capas de pasta, verduras frescas y salsa de tomate, gratinada.', 11000, 'Un clásico reconfortante, lleno de vitaminas.', 1, 0, 0),
            ('Bowl de Acaí con Frutas', 'Acaí bowl cremoso con bayas frescas, granola y coco rallado.', 5000, 'Ideal para el desayuno o un snack energético.', 1, 1, 0),
            ('Pasta Integral con Pesto', 'Pasta integral al dente con pesto casero de albahaca y piñones.', 7000, 'Energía de larga duración.', 1, 0, 0),
            ('Sopa de Lentejas y Verduras', 'Sopa nutritiva y reconfortante con lentejas y una variedad de vegetales.', 4000, 'Excelente fuente de fibra y hierro.', 1, 1, 1),
            ('Burger de Portobello', 'Champiñón Portobello marinado a la parrilla, con lechuga y tomate en pan brioche.', 10000, 'Alternativa sabrosa a la carne.', 1, 0, 0);
                         
        INSERT INTO users (username, password_hash, nombre, apellido, telefono, direccion, rol) VALUES
        ('admin', 'scrypt:32768:8:1$akKHFur35lNjXsdL$fde3de40e5a6b2c119b497fbb0cbe2c665dfc79b9a149f01d3a7bf53d3d4b55484606b176e3604d5e49e2f5535b392fe94a889065ed8dfdda57e7edadfbb6867', 'Admin', 'User', NULL, NULL, 1);
    """)
    conn.commit()
    conn.close()
    print('Base de datos inicializada.')

def query_db(db_path, query, args=(), one=False):
    conn = get_db_connection(db_path)
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(db_path, query, args=()):
    conn = get_db_connection(db_path)
    cursor = conn.execute(query, args)
    conn.commit()
    lastrowid = cursor.lastrowid
    conn.close()
    return lastrowid

def get_all_products(db_path):
    return query_db(db_path, 'SELECT * FROM Products ORDER BY nombre')

def get_product_by_id(db_path, product_id):
    return query_db(db_path, 'SELECT * FROM Products WHERE ID = ?', (product_id,), one=True)

def add_product(db_path, nombre, descripcion, informacion_nutricional, precio, es_vegetariano, es_vegano, es_sin_tacc):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO products (nombre, descripcion, informacion_nutricional, precio, es_vegetariano, es_vegano, es_sin_tacc) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (nombre, descripcion, informacion_nutricional, precio, es_vegetariano, es_vegano, es_sin_tacc)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error adding product: {e}")
        return False
    finally:
        conn.close()

def update_product(db_path, product_id, nombre, descripcion, informacion_nutricional, precio, es_vegetariano, es_vegano, es_sin_tacc):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(
            'UPDATE products SET nombre = ?, descripcion = ?, informacion_nutricional = ?, precio = ?, es_vegetariano = ?, es_vegano = ?, es_sin_tacc = ? WHERE id = ?',
            (nombre, descripcion, informacion_nutricional, precio, es_vegetariano, es_vegano, es_sin_tacc, product_id)
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error updating product: {e}")
        return False
    finally:
        conn.close()

def delete_product(db_path, product_id):
    return execute_db(db_path, 'DELETE FROM Products WHERE ID = ?', (product_id,))

