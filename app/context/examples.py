"""Ejemplos estáticos que se inyectarán en el prompt (CAG)."""

ESTIMATION_EXAMPLES: list[dict[str, str]] = [
    {
        "meeting_summary": (
            "El cliente necesita una plataforma web de gestión de inventario para "
            "una cadena de 12 tiendas físicas. Requiere catálogo de productos con "
            "SKU, control de stock en tiempo real por sucursal, alertas de stock "
            "mínimo, roles de administrador/operador/consulta, y un dashboard con "
            "métricas de rotación. Integración con su ERP actual vía API REST. "
            "Quiere lanzar un MVP en menos de 2 meses."
        ),
        "estimation": """
        ## Estimación: Plataforma de Gestión de Inventario

        ### Desglose de tareas:
        1. Diseño UI/UX: 40 horas
        2. Backend API (CRUD inventario): 60 horas
        3. Autenticación y roles: 20 horas
        4. Dashboard con métricas: 30 horas
        5. Integración ERP (API REST): 25 horas
        6. Testing y QA: 25 horas

        **Total estimado: 200 horas**
        **Equipo recomendado: 2 desarrolladores full-stack + 1 diseñador UX (part-time)**
        **Duración estimada: 6-8 semanas**
        """,
    },
    {
        "meeting_summary": (
            "El cliente quiere una app móvil (iOS y Android) para que sus clientes "
            "reserven citas en una red de clínicas dentales. Debe mostrar agenda "
            "disponible por sucursal y profesional, confirmar/cancelar citas, "
            "enviar recordatorios por push y email, y un panel web para que la "
            "recepción gestione la agenda. Login con email y Google. El histórico "
            "de pacientes vive en un sistema legacy al que hay que conectarse. "
            "Prioridad: experiencia simple para pacientes mayores de 50 años."
        ),
        "estimation": """
        ## Estimación: App de Reserva de Citas para Clínicas

        ### Desglose de tareas:
        1. Diseño UI/UX (app + panel recepción): 45 horas
        2. App móvil (React Native, iOS/Android): 80 horas
        3. Backend de citas, disponibilidad y notificaciones: 55 horas
        4. Autenticación (email + Google): 16 horas
        5. Panel web de recepción: 40 horas
        6. Integración con sistema legacy de pacientes: 30 horas
        7. Testing y QA: 28 horas

        **Total estimado: 294 horas**
        **Equipo recomendado: 1 desarrollador móvil + 1 backend + 1 frontend (panel) + 1 diseñador UX (part-time)**
        **Duración estimada: 8-10 semanas**
        """,
    },
]
