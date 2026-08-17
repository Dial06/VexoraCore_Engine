import sqlite3
import flet as ft

def main(page: ft.Page):
    page.title = "Vexora POS Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    # Base de Datos Local
    conn = sqlite3.connect("restaurante_local.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

    # Componentes de la Interfaz
    txt_platillo = ft.TextField(label="Nombre del Platillo", expand=True)
    txt_precio = ft.TextField(label="Precio ($)", keyboard_type=ft.KeyboardType.NUMBER, width=120)
    lista_menu = ft.ListView(expand=True, spacing=10)

    def cargar_menu():
        lista_menu.controls.clear()
        conn = sqlite3.connect("restaurante_local.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM menu")
        filas = cursor.fetchall()
        conn.close()

        for f in filas:
            lista_menu.controls.append(
                ft.ListTile(
                    leading=ft.Icon("fastfood"),
                    title=ft.Text(f[1]),
                    subtitle=ft.Text(f"${f[2]:.2f} MXN"),
                    trailing=ft.IconButton(
                        icon="delete",
                        icon_color="red",
                        on_click=lambda e, id_p=f[0]: eliminar_item(id_p)
                    )
                )
            )
        page.update()

    def agregar_item(e):
        if txt_platillo.value and txt_precio.value:
            conn = sqlite3.connect("restaurante_local.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO menu (nombre, precio) VALUES (?, ?)", (txt_platillo.value, float(txt_precio.value)))
            conn.commit()
            conn.close()

            txt_platillo.value = ""
            txt_precio.value = ""
            cargar_menu()

    def eliminar_item(id_p):
        conn = sqlite3.connect("restaurante_local.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM menu WHERE id = ?", (id_p,))
        conn.commit()
        conn.close()
        cargar_menu()

    btn_agregar = ft.ElevatedButton("Guardar", icon="add", on_click=agregar_item)

    # Construcción de la vista
    page.add(
        ft.Text("🍔 Vexora POS Native", size=24, weight=ft.FontWeight.BOLD),
        ft.Row([txt_platillo, txt_precio, btn_agregar]),
        ft.Divider(),
        ft.Text("Menú Registrado:", size=16, weight=ft.FontWeight.W_500),
        lista_menu
    )

    cargar_menu()
    page.update()

ft.app(target=main)