import sqlite3
import pandas as pd
import streamlit as st

# Configuración de la app
st.set_page_config(page_title="Vexora Food POS", layout="wide", page_icon="🍔")


# --- BASE DE DATOS LOCAL ---
def init_db():
  conn = sqlite3.connect("restaurante.db")
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            precio REAL NOT NULL
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS ordenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_o_cliente TEXT NOT NULL,
            detalles TEXT NOT NULL,
            total REAL NOT NULL,
            metodo_pago TEXT DEFAULT 'PENDIENTE',
            monto_recibido REAL DEFAULT 0.0,
            cambio_entregado REAL DEFAULT 0.0,
            estado_cocina TEXT DEFAULT 'PENDIENTE',
            estado_pago TEXT DEFAULT 'PENDIENTE',
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_dia DATE DEFAULT (CURRENT_DATE)
        )
    """)

  cursor.execute("SELECT COUNT(*) FROM menu")
  if cursor.fetchone()[0] == 0:
    platillos_base = [
        ("Tacos al Pastor (Orden de 5)", "Comida", 75.0),
        ("Hamburguesa Doble Especial", "Comida", 120.0),
        ("Papas a la Francesa", "Complementos", 45.0),
        ("Refresco 600ml", "Bebidas", 30.0),
        ("Agua de Sabor 1L", "Bebidas", 35.0),
    ]
    cursor.executemany(
        "INSERT INTO menu (nombre, categoria, precio) VALUES (?, ?, ?)",
        platillos_base,
    )

  conn.commit()
  conn.close()


init_db()


# --- FUNCIONES DB ---
def obtener_menu():
  conn = sqlite3.connect("restaurante.db")
  df = pd.read_sql_query("SELECT * FROM menu", conn)
  conn.close()
  return df


def crear_orden(cliente, detalles, total):
  conn = sqlite3.connect("restaurante.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO ordenes (mesa_o_cliente, detalles, total, fecha_dia)
        VALUES (?, ?, ?, CURRENT_DATE)
    """,
      (cliente, detalles, total),
  )
  conn.commit()
  conn.close()


def registrar_pago(orden_id, metodo_pago, recibido, cambio):
  conn = sqlite3.connect("restaurante.db")
  cursor = conn.cursor()
  cursor.execute(
      """
        UPDATE ordenes 
        SET metodo_pago = ?, monto_recibido = ?, cambio_entregado = ?, estado_pago = 'PAGADO'
        WHERE id = ?
    """,
      (metodo_pago, recibido, cambio, orden_id),
  )
  conn.commit()
  conn.close()


def cambiar_estado_cocina(orden_id, nuevo_estado):
  conn = sqlite3.connect("restaurante.db")
  cursor = conn.cursor()
  cursor.execute(
      "UPDATE ordenes SET estado_cocina = ? WHERE id = ?",
      (nuevo_estado, orden_id),
  )
  conn.commit()
  conn.close()


def agregar_platillo(nombre, categoria, precio):
  conn = sqlite3.connect("restaurante.db")
  cursor = conn.cursor()
  cursor.execute(
      "INSERT INTO menu (nombre, categoria, precio) VALUES (?, ?, ?)",
      (nombre, categoria, precio),
  )
  conn.commit()
  conn.close()


def eliminar_platillo(platillo_id):
  conn = sqlite3.connect("restaurante.db")
  cursor = conn.cursor()
  cursor.execute("DELETE FROM menu WHERE id = ?", (platillo_id,))
  conn.commit()
  conn.close()


# --- INTERFAZ STREAMLIT ---
st.title("🍔 Vexora Food POS")

tab_caja, tab_cobrar, tab_cocina, tab_ventas, tab_menu = st.tabs([
    "📝 Tomar Pedido",
    "💳 Cobrar Cuentas",
    "👨‍🍳 Monitor Cocina",
    "📊 Cierre de Caja",
    "⚙️ Menú",
])

# =========================================================
# PESTAÑA 1: TOMAR PEDIDO (MANDA A COCINA SIN OBLIGAR A PAGAR)
# =========================================================
with tab_caja:
  col_menu, col_ticket = st.columns([2, 1])
  df_menu = obtener_menu()

  if "carrito" not in st.session_state:
    st.session_state.carrito = []

  with col_menu:
    st.subheader("📋 Menú Digital")
    if not df_menu.empty:
      categorias = ["Todas"] + list(df_menu["categoria"].unique())
      cat_sel = st.selectbox("Categoría", categorias)
      items = (
          df_menu
          if cat_sel == "Todas"
          else df_menu[df_menu["categoria"] == cat_sel]
      )

      for _, row in items.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{row['nombre']}**")
        c2.write(f"${row['precio']:.2f}")
        if c3.button("➕", key=f"add_{row['id']}"):
          st.session_state.carrito.append(
              {"id": row["id"], "nombre": row["nombre"], "precio": row["precio"]}
          )
          st.toast(f"Agregado: {row['nombre']}")

  with col_ticket:
    st.subheader("🧾 Comanda de Mesa")
    cliente = st.text_input("Mesa / Cliente", "Mesa 1")

    if st.session_state.carrito:
      df_cart = pd.DataFrame(st.session_state.carrito)
      st.dataframe(df_cart[["nombre", "precio"]], use_container_width=True)

      total_pedido = float(df_cart["precio"].sum())
      st.markdown(f"## **Total: ${total_pedido:,.2f} MXN**")

      notas = st.text_input("Especificaciones (ej. Sin cebolla)")

      col_btn1, col_btn2 = st.columns(2)
      with col_btn1:
        if st.button(
            "🚀 Enviar a Cocina", type="primary", use_container_width=True
        ):
          resumen_items = ", ".join(df_cart["nombre"].tolist())
          if notas:
            resumen_items += f" [{notas}]"

          crear_orden(cliente, resumen_items, total_pedido)
          st.session_state.carrito = []
          st.success("¡Comanda enviada a cocina correctamente!")
          st.rerun()

      with col_btn2:
        if st.button("🗑️ Vaciar", use_container_width=True):
          st.session_state.carrito = []
          st.rerun()
    else:
      st.info("Agrega platillos para armar la comanda.")

# =========================================================
# PESTAÑA 2: COBRAR CUENTAS (CALCULADORA DE CAMBIO)
# =========================================================
with tab_cobrar:
  st.subheader("💳 Cuentas Activas por Cobrar")

  conn = sqlite3.connect("restaurante.db")
  df_pendientes = pd.read_sql_query(
      "SELECT * FROM ordenes WHERE estado_pago = 'PENDIENTE' ORDER BY id DESC",
      conn,
  )
  conn.close()

  if not df_pendientes.empty:
    col_lista, col_cobro = st.columns([1, 1])

    with col_lista:
      st.write("### Selecciona la Cuenta")
      opciones = [
          f"Orden #{r['id']} - {r['mesa_o_cliente']} (${r['total']:.2f})"
          for _, r in df_pendientes.iterrows()
      ]
      orden_sel_text = st.radio("Cuentas Abiertas:", opciones)

      # Obtener ID de la orden seleccionada
      orden_id_sel = int(orden_sel_text.split("#")[1].split(" ")[0])
      orden_data = df_pendientes[df_pendientes["id"] == orden_id_sel].iloc[0]

      st.info(f"**Detalle del Pedido:** {orden_data['detalles']}")

    with col_cobro:
      st.write("### 💵 Cobrar y Calcular Cambio")
      total_a_cobrar = float(orden_data["total"])
      st.markdown(f"## **Total a Cobrar: ${total_a_cobrar:,.2f} MXN**")

      metodo_pago = st.radio(
          "Forma de Pago",
          ["Efectivo", "Tarjeta", "Transferencia"],
          horizontal=True,
      )

      recibido = total_a_cobrar
      cambio = 0.0

      if metodo_pago == "Efectivo":
        st.caption("Elegir Billetes:")
        b1, b2, b3 = st.columns(3)
        if b1.button("$100"):
          st.session_state.paga_val = 100.0
        if b2.button("$200"):
          st.session_state.paga_val = 200.0
        if b3.button("$500"):
          st.session_state.paga_val = 500.0

        if "paga_val" not in st.session_state:
          st.session_state.paga_val = total_a_cobrar

        recibido = st.number_input(
            "Recibido ($)",
            min_value=0.0,
            value=float(st.session_state.paga_val),
            step=10.0,
        )
        cambio = recibido - total_a_cobrar

        if cambio >= 0:
          st.success(f"💰 **CAMBIO A ENTREGAR: ${cambio:,.2f} MXN**")
        else:
          st.error(f"⚠️ Faltan: ${abs(cambio):,.2f} MXN")

      puedes_cobrar = (metodo_pago != "Efectivo") or (cambio >= 0)
      if st.button(
          f"✅ Confirmar Pago de Orden #{orden_id_sel}",
          type="primary",
          use_container_width=True,
          disabled=not puedes_cobrar,
      ):
        registrar_pago(orden_id_sel, metodo_pago, recibido, cambio)
        if "paga_val" in st.session_state:
          del st.session_state.paga_val
        st.success(f"¡Orden #{orden_id_sel} cobrada exitosamente!")
        st.rerun()
  else:
    st.info("🎉 ¡No hay cuentas pendientes por cobrar!")

# =========================================================
# PESTAÑA 3: MONITOR DE COCINA (KDS)
# =========================================================
with tab_cocina:
  st.subheader("👨‍🍳 Comandas Pendientes en Cocina")
  conn = sqlite3.connect("restaurante.db")
  df_cocina = pd.read_sql_query(
      "SELECT * FROM ordenes WHERE estado_cocina = 'PENDIENTE' ORDER BY id ASC",
      conn,
  )
  conn.close()

  if not df_cocina.empty:
    cols = st.columns(3)
    for idx, row in df_cocina.iterrows():
      col_idx = idx % 3
      with cols[col_idx]:
        st.warning(f"**Orden #{row['id']} - {row['mesa_o_cliente']}**")
        st.caption(
            f"⏱️ {row['fecha_hora']} | Pago: **{row['estado_pago']}**"
        )
        st.write(f"📝 {row['detalles']}")
        if st.button(
            f"✅ Platillos Listos #{row['id']}",
            key=f"listo_{row['id']}",
            type="primary",
        ):
          cambiar_estado_cocina(row['id'], "LISTO")
          st.rerun()
  else:
    st.info("🎉 ¡Sin comandas pendientes en cocina!")

# =========================================================
# PESTAÑA 4: CIERRE DE CAJA & FILTRO DE DÍAS
# =========================================================
with tab_ventas:
  st.subheader("📊 Cierre de Caja & Filro de Días")

  conn = sqlite3.connect("restaurante.db")
  fechas_df = pd.read_sql_query(
      "SELECT DISTINCT fecha_dia FROM ordenes WHERE fecha_dia IS NOT NULL ORDER"
      " BY fecha_dia DESC",
      conn,
  )

  col_filtro, _ = st.columns([1, 2])
  with col_filtro:
    opcion_dia = st.selectbox(
        "Seleccionar Día",
        ["Hoy (Día Actual)", "Ver Todos los Días"]
        + list(fechas_df["fecha_dia"]),
    )

  if opcion_dia == "Hoy (Día Actual)":
    query = (
        "SELECT * FROM ordenes WHERE fecha_dia = CURRENT_DATE AND estado_pago ="
        " 'PAGADO'"
    )
  elif opcion_dia == "Ver Todos los Días":
    query = "SELECT * FROM ordenes WHERE estado_pago = 'PAGADO'"
  else:
    query = (
        f"SELECT * FROM ordenes WHERE fecha_dia = '{opcion_dia}' AND"
        " estado_pago = 'PAGADO'"
    )

  df_totales = pd.read_sql_query(query, conn)
  conn.close()

  if not df_totales.empty:
    total_acumulado = df_totales["total"].sum()
    pago_efectivo = df_totales[df_totales["metodo_pago"] == "Efectivo"][
        "total"
    ].sum()
    pago_tarjeta = df_totales[df_totales["metodo_pago"] == "Tarjeta"][
        "total"
    ].sum()
    pago_transf = df_totales[df_totales["metodo_pago"] == "Transferencia"][
        "total"
    ].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 Pedidos Cobrados", len(df_totales))
    m2.metric("💵 Total Caja", f"${total_acumulado:,.2f} MXN")
    m3.metric("💵 En Efectivo", f"${pago_efectivo:,.2f} MXN")
    m4.metric("💳 Tarjeta / Transf.", f"${(pago_tarjeta + pago_transf):,.2f} MXN")

    st.markdown("---")
    st.write("### 📋 Desglose de Ventas Cobradas")
    st.dataframe(
        df_totales[[
            "id",
            "fecha_hora",
            "mesa_o_cliente",
            "detalles",
            "total",
            "metodo_pago",
            "monto_recibido",
            "cambio_entregado",
        ]],
        use_container_width=True,
    )
  else:
    st.info("No hay ventas cobradas registradas para la fecha seleccionada.")

# =========================================================
# PESTAÑA 5: MENÚ
# =========================================================
with tab_menu:
  st.subheader("⚙️ Menú de Platillos")
  col_a, col_b = st.columns(2)
  with col_a:
    with st.form("add_p"):
      n = st.text_input("Platillo")
      c = st.selectbox(
          "Categoría", ["Comida", "Bebidas", "Postres", "Complementos"]
      )
      p = st.number_input("Precio ($)", min_value=1.0, value=50.0)
      if st.form_submit_button("Guardar"):
        if n:
          agregar_platillo(n, c, p)
          st.rerun()
  with col_b:
    df_act = obtener_menu()
    if not df_act.empty:
      for _, r in df_act.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{r['nombre']}** ({r['categoria']})")
        c2.write(f"${r['precio']:.2f}")
        if c3.button("🗑️", key=f"d_{r['id']}"):
          eliminar_platillo(r['id'])
          st.rerun()