#!/usr/bin/env python3
"""
GESTIONAR DJGEEORGE — añadir o quitar canciones sin tocar JSON a mano.

Este script SOLO edita tools/mapeo_djgeeorge.json (añade o borra una
entrada) y, si tú quieres, lanza ACTUALIZAR_TODO.py al final para que
playlist_djgeeorge/library.json quede regenerado al momento.

NO sube ni baja archivos de Supabase. El MP3 tienes que subirlo tú antes,
a mano, al bucket público "musicaa" — este script solo apunta la web
hacia el nombre exacto que le hayas puesto ahí.
"""
from pathlib import Path
import json
import subprocess
import sys

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
MAPEO_PATH = TOOLS_DIR / "mapeo_djgeeorge.json"
ACTUALIZAR_PATH = TOOLS_DIR / "actualizar_todo.py"


def cargar_mapeo():
    if not MAPEO_PATH.exists():
        print(f"No encuentro {MAPEO_PATH}. No puedo continuar.")
        sys.exit(1)
    try:
        return json.loads(MAPEO_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"El archivo {MAPEO_PATH.name} tiene un error y no se puede leer: {e}")
        sys.exit(1)


def guardar_mapeo(mapeo):
    MAPEO_PATH.write_text(
        json.dumps(mapeo, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def preguntar(texto):
    try:
        return input(texto).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado.")
        sys.exit(0)


def preguntar_si_no(texto, por_defecto=True):
    sufijo = " [S/n]: " if por_defecto else " [s/N]: "
    r = preguntar(texto + sufijo).lower()
    if not r:
        return por_defecto
    return r.startswith("s")


def regenerar_biblioteca():
    print("\nRegenerando library.json...\n")
    subprocess.run([sys.executable, str(ACTUALIZAR_PATH)])


def anadir_cancion(mapeo):
    print("\n--- Añadir canción a DJGEEORGE ---")
    titulo = preguntar("Título de la canción (tal y como debe verse en la web): ")
    if not titulo:
        print("Título vacío, cancelado.")
        return

    nuevo = preguntar("Nombre EXACTO del archivo tal y como lo subiste a Supabase\n"
                       "(con extensión, ej: Nombre-De-La-Cancion-(@DJgeeorge-Mashup).mp3): ")
    if not nuevo:
        print("Nombre de archivo vacío, cancelado.")
        return

    if " " in nuevo:
        print("\n[!] Ese nombre de archivo lleva espacios. Si en Supabase lo subiste")
        print("    exactamente así, puede funcionar, pero es más seguro usar guiones")
        print("    en vez de espacios (como el resto de canciones ya migradas).")
        if not preguntar_si_no("¿Seguro que quieres seguir con ese nombre tal cual?", por_defecto=False):
            print("Cancelado. Vuelve a subir el archivo sin espacios, o inténtalo de nuevo.")
            return

    if any(e.get("nuevo") == nuevo for e in mapeo):
        print(f"\n[!] Ya existe una canción con el nombre de archivo '{nuevo}'.")
        if not preguntar_si_no("¿Quieres añadirla igualmente (quedará duplicada)?", por_defecto=False):
            print("Cancelado.")
            return

    ext = Path(nuevo).suffix
    entrada = {
        "original": titulo + ext,
        "nuevo": nuevo,
        "titulo": titulo,
    }
    mapeo.append(entrada)
    guardar_mapeo(mapeo)
    print(f"\n✓ Añadida: \"{titulo}\"")


def quitar_cancion(mapeo):
    print("\n--- Quitar canción de DJGEEORGE ---")
    busqueda = preguntar("Escribe parte del título para buscarla: ").lower()
    if not busqueda:
        print("Búsqueda vacía, cancelado.")
        return

    coincidencias = [
        (i, e) for i, e in enumerate(mapeo)
        if busqueda in (e.get("titulo") or "").lower()
        or busqueda in (e.get("original") or "").lower()
    ]
    if not coincidencias:
        print("No he encontrado ninguna canción con ese texto.")
        return

    print(f"\nEncontradas {len(coincidencias)}:")
    for n, (i, e) in enumerate(coincidencias, start=1):
        print(f"  {n}) {e.get('titulo') or e.get('original')}")

    eleccion = preguntar("\nNúmero(s) a borrar, separados por comas si son varios "
                          "(ej: 1,3,5) — ENTER para cancelar: ")
    if not eleccion:
        print("Cancelado.")
        return

    seleccionados = []
    for trozo in eleccion.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        try:
            idx_local = int(trozo) - 1
            if idx_local < 0 or idx_local >= len(coincidencias):
                raise ValueError
        except ValueError:
            print(f"'{trozo}' no es un número válido de la lista, cancelado.")
            return
        if idx_local not in seleccionados:
            seleccionados.append(idx_local)

    if not seleccionados:
        print("No has indicado ningún número válido, cancelado.")
        return

    elegidas = [coincidencias[idx_local] for idx_local in seleccionados]

    print(f"\nVas a borrar {len(elegidas)} canción(es):")
    for _, e in elegidas:
        print(f"  - {e.get('titulo') or e.get('original')}")

    if not preguntar_si_no("\n¿Confirmas el borrado?", por_defecto=False):
        print("Cancelado.")
        return

    # Se borra de mayor a menor indice para que borrar una entrada no
    # desplace las posiciones de las que quedan por borrar despues.
    for i, _ in sorted(elegidas, key=lambda par: par[0], reverse=True):
        del mapeo[i]

    guardar_mapeo(mapeo)
    print(f"\n✓ Borrada(s) {len(elegidas)} canción(es) de mapeo_djgeeorge.json.")
    print("  (Los archivos siguen en el bucket de Supabase; bórralos ahí también")
    print("   si quieres liberar espacio, esto no lo hace automáticamente.)")


def menu():
    while True:
        print("\n=======================================")
        print(" GESTIONAR CANCIONES — DJGEEORGE")
        print("=======================================")
        print("1) Añadir canción")
        print("2) Quitar canción")
        print("3) Salir")
        opcion = preguntar("\nElige una opción: ")

        if opcion == "1":
            mapeo = cargar_mapeo()
            anadir_cancion(mapeo)
        elif opcion == "2":
            mapeo = cargar_mapeo()
            quitar_cancion(mapeo)
        elif opcion == "3":
            print("Hasta luego.")
            return
        else:
            print("Opción no válida.")
            continue

        if preguntar_si_no("\n¿Actualizar la web ahora (regenerar library.json)?", por_defecto=True):
            regenerar_biblioteca()

        if not preguntar_si_no("\n¿Quieres hacer algo más?", por_defecto=True):
            print("Hasta luego.")
            return


if __name__ == "__main__":
    menu()
