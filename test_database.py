import unittest
import os
import database as db_helper

class TestDatabaseFunctions(unittest.TestCase):

    def setUp(self):
        self.db_path = 'hb.db'
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        db_helper.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

#crear tablas
    def test_01(self):
        conn = db_helper.get_db_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        self.assertIsNotNone(cursor.fetchone(), "La tabla 'users' deberia haber sido creada.")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        self.assertIsNotNone(cursor.fetchone(), "La tabla 'products' deberia haber sido creada.")
        conn.close()
#insertar datos
    def test_02(self):
        username = "testuser"
        password_hash = "hashed_password_example"
        nombre = "Xavi"
        apellido = "Valls"

        user_id = db_helper.execute_db(
            self.db_path,
            'INSERT INTO users (username, password_hash, nombre, apellido) VALUES (?, ?, ?, ?)',
            (username, password_hash, nombre, apellido)
        )
        
        self.assertIsNotNone(user_id, "Se deberia haber retornado un ID para el usuario insertado.")
        self.assertGreater(user_id, 0, "El ID del usuario deberia ser un numero positivo.")

        retrieved_user = db_helper.query_db(
            self.db_path,
            'SELECT * FROM users WHERE username = ?',
            (username,),
            one=True
        )

        self.assertIsNotNone(retrieved_user, "El usuario deberia haber sido recuperado de la base de datos.")
        self.assertEqual(retrieved_user['id'], user_id)
        self.assertEqual(retrieved_user['username'], username)
        self.assertEqual(retrieved_user['password_hash'], password_hash)
        self.assertEqual(retrieved_user['nombre'], nombre)
        self.assertEqual(retrieved_user['apellido'], apellido)
#no existente
    def test_03(self):
        non_existent_user = db_helper.query_db(
            self.db_path,
            'SELECT * FROM users WHERE username = ?',
            ('usuario_inexistente',),
            one=True
        )
        self.assertIsNone(non_existent_user, "Consultar un usuario no existente deberia devolver None.")

if __name__ == '__main__':
    unittest.main()