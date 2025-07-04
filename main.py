import flet as ft
from State import State
from NFA import NFA
import re
import asyncio

# --- Asignación de IDs únicos a cada State para trazabilidad ---
State._id_counter = 0
_original_init = State.__init__

def _state_init(self, is_final=False):
    # Llamamos al constructor original
    _original_init(self, is_final)
    # Incrementamos contador y asignamos ID al estado
    State._id_counter += 1
    self.id = State._id_counter
State.__init__ = _state_init

# --- Funciones Auxiliares ---
def close_dialog(dialog: ft.AlertDialog, page: ft.Page):
    """Cierra el diálogo pasado como argumento."""
    dialog.open = False
    page.update()

def show_result_alert(title: str, text: str, page: ft.Page, on_dismiss_callback=None):
    """Muestra un modal de resultado y, al cerrar, ejecuta callback o vuelve al menú."""
    result_modal = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(text),
        actions=[
            ft.TextButton("Cerrar", on_click=lambda e: close_dialog(result_modal, page)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=on_dismiss_callback or (lambda e: show_main_menu(page))
    )
    page.open(result_modal)


# --- Vistas ---

# def show_main_menu(page: ft.Page):
#     """Muestra el menú principal."""
    page.clean()
    page.title = "Máquinas de Estados y Validadores"

    title = ft.Text("Bienvenido, ¿Qué desea hacer el día de Hoy?", size=24, weight=ft.FontWeight.BOLD)

    btn_validator = ft.ElevatedButton(
        "Validador de Formato Simple",
        on_click=lambda e: show_validator(page)
    )
    btn_simulator = ft.ElevatedButton(
        "Simulador de Máquina de Estados Finitos",
        on_click=lambda e: show_simulator(page)
    )

    page.add(
        ft.Column(
            [
                title,
                ft.Container(height=20),
                btn_validator,
                btn_simulator
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True
        )
    )
    page.update()


def show_validator(page: ft.Page):
    """Muestra la interfaz para el validador de formato."""
    page.clean()
    page.title = "Validador de Formato"

    # -------------------------------------------------------
    # Referencia para el diálogo de entrada
    dialog_ref = {"input": None}
    # Variables de estado para validación
    validation_result_title = None
    validation_result_text = None
    validation_done = False
    # -------------------------------------------------------

    # --- Controles de configuración ---
    switch_numbers = ft.Switch(label="Permite números del 0-9", value=True)
    switch_letters = ft.Switch(label="Permite letras A-Z (mayús/minús)", value=True)
    switch_special = ft.Switch(label="Permite Caracteres Especiales", value=False)

    special_chars = r"!@#$%^&*()_+-=[]{}|;:',.<>/?\\"
    special_chars_display = r"""`!@#$%^&*()_+-=[]{}|;':",.<>/?"""

    def update_switch_label(e):
        switch = e.control
        if switch == switch_numbers:
            switch.label = "Permite números del 0-9" if switch.value else "NO Permite números del 0-9"
        elif switch == switch_letters:
            switch.label = "Permite letras A-Z (mayús/minús)" if switch.value else "NO Permite letras A-Z"
        else:
            switch.label = (
                f"Permite Caracteres Especiales ({special_chars_display})"
                if switch.value else
                "NO Permite Caracteres Especiales"
            )
        page.update()

    for sw in (switch_numbers, switch_letters, switch_special):
        sw.on_change = update_switch_label

    # --- Regex personalizado ---
    checkbox_custom_regex = ft.Checkbox(label="Utilizar un Regex personalizado", value=False)
    textfield_custom_regex = ft.TextField(label="Introduce tu regex aquí", visible=False, width=400)

    def toggle_custom_regex(e):
        is_checked = checkbox_custom_regex.value
        textfield_custom_regex.visible = is_checked
        switch_numbers.disabled = is_checked
        switch_letters.disabled = is_checked
        switch_special.disabled = is_checked
        page.update()

    checkbox_custom_regex.on_change = toggle_custom_regex

    # Campo de entrada de la cadena a validar
    txt_input_string = ft.TextField(label="Ingresa la cadena a validar", width=300)

    # --- Función de cierre y validación ---
    def close_dlg_and_validate(e):
        nonlocal validation_done, validation_result_title, validation_result_text
        s = txt_input_string.value or ""
        txt_input_string.value = ""

        if checkbox_custom_regex.value:
            pattern = textfield_custom_regex.value
            if not pattern:
                validation_result_title = "Error"
                validation_result_text = "Debes introducir un regex personalizado."
            else:
                try:
                    nfa = regex_to_nfa(pattern)
                    valid, trace = simulate_nfa_trace(nfa, s)
                    # Construir texto con pasos intermedios
                    details = []
                    for sym, states in trace:
                        if sym is None:
                            details.append(f"Inicio ε-cierre: estados {sorted(st.id for st in states)}")
                        else:
                            details.append(f"Después de '{sym}': estados {sorted(st.id for st in states)}")
                    trace_text = "\n".join(details)
                    title = "Cadena Válida" if valid else "Cadena Inválida"
                    validation_result_title = title
                    validation_result_text = trace_text
                except re.error as ex:
                    validation_result_title = "Error de Regex"
                    validation_result_text = f"Regex inválido: {ex}"
        else:
            # ... lógica original para DFA conceptual ...
            valid = re.fullmatch(pattern, s) is not None
            valid, trace = False, []  # Omitir traza para modo simple
            validation_result_title = "Validación Exitosa" if valid else "Validación Fallida"
            validation_result_text = ("✅ La cadena tiene el formato válido." if valid else "❌ La cadena NO cumple con el formato.")

        validation_done = True
        dialog_ref["input"].open = False
        page.update()

    # --- Al cerrarse el diálogo de entrada ---
    async def on_input_modal_dismiss(e):
        nonlocal validation_result_title, validation_result_text, validation_done
        if validation_done:
            await asyncio.sleep(0.05)
            show_result_alert(validation_result_title, validation_result_text, page)
        # Resetear banderas
        validation_done = False
        validation_result_title = None
        validation_result_text = None

    # --- Mostrar el diálogo de entrada ---
    def show_validation_input_modal(e):
        # Creamos el AlertDialog y guardamos su instancia
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Validar Cadena"),
            content=ft.Column([txt_input_string], tight=True),
            actions=[
                ft.TextButton("Validar", on_click=close_dlg_and_validate),
                ft.TextButton("Cancelar", on_click=lambda e: close_dialog(dlg, page)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=on_input_modal_dismiss
        )
        dialog_ref["input"] = dlg
        page.open(dlg)

    # Botón para lanzar el diálogo
    btn_validate_text = ft.ElevatedButton("Validar Texto", on_click=show_validation_input_modal)

    # Layout completo
    settings_column = ft.Column(
        [
            ft.Text("Configura el formato permitido:", size=18, weight=ft.FontWeight.BOLD),
            switch_numbers,
            switch_letters,
            switch_special,
            ft.Container(height=20),
            checkbox_custom_regex,
            textfield_custom_regex,
            ft.Container(expand=True),
        ],
        expand=True
    )

    page.add(
        ft.Column(
            [
                ft.Text("Validador de Formato Simple (DFA conceptual)", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                settings_column,
                ft.Row([btn_validate_text], alignment=ft.MainAxisAlignment.END),
            ],
            expand=True
        )
    )

    # Inicializar etiquetas
    # update_switch_label(ft.ControlEvent(control=switch_numbers))
    # update_switch_label(ft.ControlEvent(control=switch_letters))
    # update_switch_label(ft.ControlEvent(control=switch_special))
    class _DummyEvent:
        def __init__(self, control):
            self.control = control
    
    for sw in (switch_numbers, switch_letters, switch_special):
        update_switch_label(_DummyEvent(sw))

    page.update()

def simulate_nfa_trace(nfa: NFA, s: str):
    trace = []
    # Paso 0: ε-cierre del estado inicial
    curr = epsilon_closure([nfa.start])
    trace.append((None, curr))  # None representa paso inicial
    # Por cada símbolo, movemos y luego cerramos con ε
    for c in s:
        moved = move(curr, c)
        curr = epsilon_closure(list(moved))
        trace.append((c, curr))
    valid = any(st.is_final for st in curr)
    return valid, trace

def regex_to_nfa(pattern):
    """
    Convierte una expresión regular simple en un NFA.
    Devuelve un objeto NFA con:
      - start: estado inicial
      - end: estado final marcado con is_final=True
    """
    def build_nfa(c: str) -> NFA:
        # Creamos dos estados: s1 (no final) y s2 (final)
        s1 = State(is_final=False)
        s2 = State(is_final=True)
        # Saltos: transición con símbolo c de s1 a s2
        s1.add_transition(c, s2)
        return NFA(s1, s2)

    def concat(nfa1: NFA, nfa2: NFA) -> NFA:
        # Marcamos que el estado intermedio deja de ser final
        nfa1.end.is_final = False
        # Añadimos un salto epsilon del antiguo end de nfa1 al start de nfa2
        nfa1.end.add_epsilon(nfa2.start)
        # Nuevo NFA: start de nfa1, end de nfa2
        return NFA(nfa1.start, nfa2.end)

    # --- Alternativa (|): crea un nuevo start y end, con saltos epsilon a cada rama ---
    def alternate(nfa1: NFA, nfa2: NFA) -> NFA:
        start = State(is_final=False)
        end = State(is_final=True)
        # Saltos epsilon desde nuevo start a cada sub-NFA
        start.add_epsilon(nfa1.start)
        start.add_epsilon(nfa2.start)
        # Desmarcamos estados finales intermedios
        nfa1.end.is_final = False
        nfa2.end.is_final = False
        # Saltos epsilon desde cada end antiguo al nuevo end
        nfa1.end.add_epsilon(end)
        nfa2.end.add_epsilon(end)
        return NFA(start, end)

    # --- Cierre de Kleene (*): bucle y aceptación vacía ---
    def kleene(nfa: NFA) -> NFA:
        start = State(is_final=False)
        end = State(is_final=True)
        # Saltos epsilon para permitir cero o más repeticiones
        start.add_epsilon(nfa.start)
        start.add_epsilon(end)
        nfa.end.is_final = False
        nfa.end.add_epsilon(nfa.start)
        nfa.end.add_epsilon(end)
        return NFA(start, end)
    

    # --- Parser (Shunting-yard) adaptado para regex ---
    def parse(regex: str) -> NFA:
        output: list[NFA] = []
        ops: list[str] = []
        # Precedencia de operadores
        prec = {'*': 3, '.': 2, '|': 1}

        def apply_op():
            op = ops.pop()
            if op == '.':
                # Concatenación
                b = output.pop()
                a = output.pop()
                output.append(concat(a, b))
            elif op == '|':
                # Alternativa
                b = output.pop()
                a = output.pop()
                output.append(alternate(a, b))
            elif op == '*':
                # Cierre de Kleene
                a = output.pop()
                output.append(kleene(a))

        i = 0
        while i < len(regex):
            c = regex[i]
            if c.isalnum():
                # Literal: construye mini-NFA y lo apila
                output.append(build_nfa(c))
                # Si sigue literal o '(', implicamos concatenación
                if i+1 < len(regex) and (regex[i+1].isalnum() or regex[i+1] == '('):
                    ops.append('.')
            elif c == '(':
                ops.append(c)
            elif c == ')':
                while ops and ops[-1] != '(': apply_op()
                ops.pop()  # quitamos '('
            elif c in ('*', '|'):
                # Aplicamos ops de mayor o igual precedencia
                while ops and ops[-1] != '(' and prec[ops[-1]] >= prec[c]:
                    apply_op()
                ops.append(c)
            i += 1
        # Aplicamos operadores restantes
        while ops: apply_op()
        return output[-1]
    
    return parse(pattern)

# --- Funciones de simulación y trazas ---
def epsilon_closure(states: list[State]) -> set[State]:
    stack = states.copy()
    closure = set(states)
    while stack:
        st = stack.pop()
        for nxt in st.epsilon:
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)
    return closure

def move(states: set[State], symbol: str) -> set[State]:
    result = set()
    for st in states:
        # Saltos etiquetados con symbol
        for tgt in st.transitions.get(symbol, []):
            result.add(tgt)
    return result

def simulate_nfa(nfa, s):
    current_states = epsilon_closure([nfa.start])
    for c in s:
        current_states = epsilon_closure(move(current_states, c))
    return any(state.is_final for state in current_states)

def show_simulator(page: ft.Page):
    """Simulador de máquina expendedora (FSM)."""
    page.clean()
    page.title = "Simulador Máquina Expendedora"

    STATES = {
        "WAITING_FOR_COIN": "Esperando Moneda",
        "COIN_INSERTED": "Moneda Insertada",
        "PRODUCT_SELECTED": "Producto Seleccionado",
        "PRODUCT_DELIVERED": "Producto Entregado",
        "RETURNING_CHANGE": "Devolviendo Cambio"
    }
    current_state = STATES["WAITING_FOR_COIN"]

    txt_current_state = ft.Text(f"Estado Actual: {current_state}", size=18, weight=ft.FontWeight.BOLD)
    txt_message = ft.Text("", size=14)

    btn_insert = ft.ElevatedButton("Insertar Moneda")
    btn_A = ft.ElevatedButton("Seleccionar Producto A")
    btn_B = ft.ElevatedButton("Seleccionar Producto B")
    btn_return = ft.ElevatedButton("Devolver Cambio")
    btn_take = ft.ElevatedButton("Recoger Producto")

    def update_gui():
        txt_current_state.value = f"Estado Actual: {current_state}"
        txt_message.value = ""
        btn_insert.disabled = current_state != STATES["WAITING_FOR_COIN"]
        btn_A.disabled = btn_B.disabled = btn_return.disabled = current_state != STATES["COIN_INSERTED"]
        btn_take.disabled = current_state != STATES["PRODUCT_DELIVERED"]
        page.update()

    def set_state(new_state, msg=""):
        nonlocal current_state
        current_state = new_state
        txt_message.value = msg
        update_gui()
        if new_state == STATES["RETURNING_CHANGE"]:
            async def task():
                await asyncio.sleep(1)
                set_state(STATES["WAITING_FOR_COIN"], "Cambio devuelto. Gracias.")
            page.run_task(task)
        elif new_state == STATES["PRODUCT_SELECTED"]:
            async def task():
                await asyncio.sleep(2)
                set_state(STATES["PRODUCT_DELIVERED"], msg.replace("Procesando", "dispensado"))
            page.run_task(task)

    def handle_insert(e):
        if current_state == STATES["WAITING_FOR_COIN"]:
            set_state(STATES["COIN_INSERTED"], "Moneda insertada.")
        else:
            txt_message.value = f"Acción no válida desde {current_state}"
            page.update()

    def handle_select(e):
        if current_state == STATES["COIN_INSERTED"]:
            prod = e.control.text.split()[-1]
            set_state(STATES["PRODUCT_SELECTED"], f"Procesando Producto {prod}...")
        else:
            txt_message.value = "Inserta moneda primero."
            page.update()

    def handle_return(e):
        if current_state == STATES["COIN_INSERTED"]:
            set_state(STATES["RETURNING_CHANGE"], "Devolviendo cambio...")
        else:
            txt_message.value = "No hay moneda para devolver."
            page.update()

    def handle_take(e):
        if current_state == STATES["PRODUCT_DELIVERED"]:
            show_result_alert(
                "Simulación Finalizada",
                "Producto recogido. Gracias por tu compra.",
                page,
                on_dismiss_callback=lambda e: show_main_menu(page)
            )
        else:
            txt_message.value = "No hay producto para recoger."
            page.update()

    btn_insert.on_click = handle_insert
    btn_A.on_click = handle_select
    btn_B.on_click = handle_select
    btn_return.on_click = handle_return
    btn_take.on_click = handle_take

    page.add(
        ft.Column(
            [
                ft.Text("Simulador de Máquina Expendedora (FSM)", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                txt_current_state,
                txt_message,
                ft.Container(height=20),
                ft.Row([btn_insert, btn_return]),
                ft.Row([btn_A, btn_B]),
                ft.Row([btn_take]),
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True
        )
    )

    update_gui()


def main(page: ft.Page):
    page.window_width = 600
    page.window_height = 700
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    show_main_menu(page)


if __name__ == "__main__":
    ft.app(target=main)
