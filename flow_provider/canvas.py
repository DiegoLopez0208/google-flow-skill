"""
Selección de items del canvas y upload de frames para modo Fotogramas/Ingredientes.
"""
from .browser import get_page
from .registry import capture_name
import re


SEL_ADD_INGREDIENT = 'button[aria-haspopup="dialog"]:has-text("Crear")'
async def select_ingredients_by_name(uuids: list[str]) -> None:
    """Marca items del canvas como ingredientes a través del Dialog Modal de Flow, buscando por UUID."""
    page = await get_page()
    PANEL_RECURSOS = 'div[role="dialog"]:has(input[placeholder*="Buscar"]), div[role="dialog"]:has(input[placeholder*="Search"])'
    
    for uuid in uuids:
        encontrado = False
        # Intentar hasta 3 veces con recarga de página intermedia si no se encuentra (para curación por retraso del backend)
        for intento_busqueda in range(3):
            await page.locator(SEL_ADD_INGREDIENT).first.click()
            await page.wait_for_timeout(2500)
            
            # Intentar buscar el ingrediente directamente en la pestaña activa
            target_img = page.locator(PANEL_RECURSOS).locator(f'img[src*="{uuid}"]')
            
            if await target_img.count() == 0:
                # Probar diferentes textos posibles para las pestañas de recursos en toda la página
                for tab_text in ["Cargas", "Uploads", "Imágenes", "Images", "Todos", "All", "Lienzo", "Canvas"]:
                    tab = page.locator('div, span, p, button, [role="tab"]').get_by_text(tab_text, exact=False).first
                    if await tab.count() > 0:
                        print(f"    [Robusto] Haciendo clic en pestaña: {tab_text}")
                        await tab.click()
                        await page.wait_for_timeout(2000)
                        # Volver a verificar
                        if await target_img.count() > 0:
                            break
            
            # Si aún no se encuentra, realizar scroll vertical robusto para cargar elementos del virtual scroll
            if await target_img.count() == 0:
                print(f"    [Robusto] Iniciando scroll vertical en la lista del modal de recursos para UUID: {uuid}...")
                for scroll_step in range(10):
                    await page.evaluate(f"""() => {{
                        const dialog = document.querySelector('{PANEL_RECURSOS}');
                        if (!dialog) return;
                        const divs = dialog.querySelectorAll('div');
                        for (const div of divs) {{
                            if (div.scrollHeight > div.clientHeight) {{
                                div.scrollTop += 250;
                            }}
                        }}
                    }}""")
                    await page.wait_for_timeout(1200)
                    if await target_img.count() > 0:
                        print(f"    [Robusto] ¡Ingrediente encontrado tras scroll en paso {scroll_step+1}!")
                        break
            
            if await target_img.count() > 0:
                encontrado = True
                break
                
            # Si no se encontró, cerramos el panel con Escape, esperamos y recargamos la página (auto-curación)
            if intento_busqueda < 2:
                print(f"    [Auto-Curación] Ingrediente {uuid} NO visible en intento {intento_busqueda+1}. Cerrando panel, esperando 5s y recargando página...")
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(5000)
                await page.reload()
                await page.wait_for_timeout(5000)
        
        # Verificación final
        if not encontrado:
            # Tomar una captura para depurar
            from pathlib import Path
            debug_dir = Path(__file__).parent.parent / "_debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            shot = str(debug_dir / "select_ingredient_error.png")
            await page.screenshot(path=shot)
            print(f"    [ERROR] Captura del diálogo de recursos guardada en {shot}")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
            raise ValueError(f"No se encontró el ingrediente con UUID {uuid} in el proyecto.")
            
        await target_img.first.click()
        await page.wait_for_timeout(1500)
        
        # Buscar el botón 'Agregar a la instrucción' o su equivalente en inglés dentro del panel flotante
        import re
        add_btn = page.locator(PANEL_RECURSOS).locator('button, [role="button"]').filter(
            has_text=re.compile(r"(Agregar a la instrucción|Add to instrucción|Add to instruction|Add to prompt)", re.IGNORECASE)
        ).first
        
        try:
            # Esperar a que el botón de agregar esté visible en la previsualización
            await add_btn.wait_for(state="visible", timeout=6000)
            await add_btn.click()
            await page.wait_for_timeout(1000)
        except Exception:
            # Si no se encuentra o ya se cerró el panel, usar Escape como fallback
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)


async def upload_standalone_image(image_path: str) -> None:
    """Sube una imagen al canvas directamente (modo imagen). Flujo 5."""
    page = await get_page()
    
    # 1. Contar elementos en canvas antes de subir para tener baseline
    pre_upload_cards = await page.locator('[aria-roledescription="draggable"]').count()
    
    # 2. Esperar al boton Crear y click
    await page.wait_for_selector(SEL_ADD_INGREDIENT, state="visible", timeout=8_000)
    await page.locator(SEL_ADD_INGREDIENT).first.click()
    await page.wait_for_timeout(2_000)
    
    # 3. Click en Cargar medios / Subir imagen
    import re
    upload_btn = page.locator('button, [role="button"]').filter(
        has_text=re.compile(r"(Cargar medios|Upload media|Subir imagen)", re.IGNORECASE)
    ).first
    
    if await upload_btn.count() == 0:
        raise Exception("Botón 'Cargar medios' o 'Upload' no encontrado.")
        
    async with page.expect_file_chooser(timeout=8_000) as fc_info:
        await upload_btn.click(force=True)
    
    file_chooser = await fc_info.value
    await file_chooser.set_files(str(image_path))
    
    # 4. Esperar de forma dinámica y rigurosa usando la cuenta previa (Igual que en test-flow 5)
    await page.wait_for_function(
        f"""() => {{
            const cards = document.querySelectorAll('[aria-roledescription="draggable"]');
            if (cards.length <= {pre_upload_cards}) return false;
            const img = cards[0].querySelector('img');
            return img && img.complete && img.naturalWidth > 0;
        }}""",
        timeout=60_000,
    )
    
    # 5. Cerrar el panel presionando Escape una vez confirmado el upload en el canvas
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(1000)



async def get_canvas_count() -> int:
    """Retorna cantidad actual de items en el canvas."""
    page = await get_page()
    return await page.locator('[aria-roledescription="draggable"]').count()


SEL_SLOTS_INICIAR = 'div:text-is("Iniciar")'
SEL_SLOTS_FIN = 'div:text-is("Fin")'
SEL_UPLOAD_BTN = ':text-is("Subir imagen")'
SEL_SLOT_LOADED = 'img[alt*="contenido multimedia"]'

async def upload_frame(file_path: str, slot: str = "initial") -> None:
    """Sube un frame para modo Fotogramas. slot: 'initial' o 'final'."""
    page = await get_page()
    
    await page.wait_for_selector(SEL_SLOTS_INICIAR, state="visible", timeout=10000)
    target_slot = page.locator(SEL_SLOTS_INICIAR) if slot == "initial" else page.locator(SEL_SLOTS_FIN)
    
    initial_count = await page.locator(SEL_SLOT_LOADED).count()
    await target_slot.click()
    await page.wait_for_timeout(2000)
    
    async with page.expect_file_chooser(timeout=5000) as fc_info:
        import re
        upload_btn = page.locator('button, [role="button"], div').filter(
            has_text=re.compile(r"(Cargar medios|Upload media|Subir imagen)", re.IGNORECASE)
        ).first
        if await upload_btn.count() == 0:
            raise Exception("Botón de subida ('Cargar medios' / 'Upload') no encontrado para el slot.")
        await upload_btn.click(force=True)
    file_chooser = await fc_info.value
    await file_chooser.set_files(file_path)
    
    await page.wait_for_function(
        f"""() => {{
            const imgs = document.querySelectorAll('{SEL_SLOT_LOADED}');
            if (imgs.length <= {initial_count}) return false;
            return [...imgs].some(img => img.complete && img.naturalWidth > 0);
        }}""",
        timeout=60000
    )


async def select_frame_from_project(uuid: str, slot: str = "initial") -> None:
    """Selecciona un frame existente del proyecto para modo Fotogramas."""
    page = await get_page()
    
    await page.wait_for_selector(SEL_SLOTS_INICIAR, state="visible", timeout=10000)
    target_slot = page.locator(SEL_SLOTS_INICIAR) if slot == "initial" else page.locator(SEL_SLOTS_FIN)
    
    initial_count = await page.locator(SEL_SLOT_LOADED).count()
    await target_slot.click()
    await page.wait_for_timeout(2000)
    
    # Buscar la imagen en el dropup por UUID dentro del diálogo modal
    target_img = page.locator(f'[role="dialog"] img[src*="{uuid}"]')
    if await target_img.count() == 0:
        await page.keyboard.press("Escape")
        raise ValueError(f"No se encontró la imagen con UUID {uuid} en el proyecto para usar como frame.")
        
    await target_img.first.click()
    await page.wait_for_timeout(1000)
    
    # Confirmar selección con el botón 'Agregar a la instrucción'
    import re
    add_btn = page.locator('button, [role="button"]').filter(
        has_text=re.compile(r"(Agregar a la instrucción|Add to instruction|Add to prompt)", re.IGNORECASE)
    ).first
    if await add_btn.count() > 0:
        await add_btn.click()
        await page.wait_for_timeout(1000)
    
    # Esperar que cargue en el slot
    await page.wait_for_function(
        f"""() => {{
            const imgs = document.querySelectorAll('{SEL_SLOT_LOADED}');
            if (imgs.length <= {initial_count}) return false;
            return [...imgs].some(img => img.complete && img.naturalWidth > 0);
        }}""",
        timeout=60000
    )


async def capture_newest_asset_name(label: str, is_video: bool = False) -> str:
    """Rastrea el card más nuevo en el canvas y guarda su UUID en el registry bajo label.
    
    Para imágenes extrae el src del <img alt="Imagen generada">.
    Para videos extrae el src del <video> (mismo patrón URL ?name=UUID).
    """
    page = await get_page()
    
    # Flow prepende, así que .first siempre es el asset recién generado.
    card = page.locator('[aria-roledescription="draggable"]').first
    
    if is_video:
        element = card.locator('video').first
    else:
        element = card.locator('img').first
    
    src = await element.get_attribute("src")
    if not src:
        raise ValueError("No se pudo obtener el atributo src del asset más reciente.")
        
    match = re.search(r'[?&]name=([a-f0-9-]{36})', src)
    if not match:
        raise ValueError(f"No se encontró UUID en el src: {src}")
        
    uuid = match.group(1)
    capture_name(label, uuid)
    print(f"  📌 Registry: Guardado '{label}' -> {uuid}")
    return uuid
