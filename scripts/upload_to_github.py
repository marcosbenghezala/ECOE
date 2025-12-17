"""
Script para subir casos procesados a GitHub automáticamente
Realiza git add, commit y push de los casos nuevos
"""
import os
import sys
import subprocess
from datetime import datetime
from typing import List, Optional

# Añadir el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import settings
    BASE_DIR = settings.BASE_DIR
except:
    from dotenv import load_dotenv
    script_dir = os.path.dirname(os.path.abspath(__file__))
    BASE_DIR = os.path.dirname(script_dir)
    env_path = os.path.join(os.path.dirname(BASE_DIR), '.env')
    load_dotenv(env_path)

# Configuración
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'marcosbenghezala')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'ECOE')
GITHUB_BRANCH = os.getenv('GITHUB_BRANCH', 'main')

CASOS_DIR = os.path.join(BASE_DIR, 'casos')


def run_command(command: List[str], cwd: str = None) -> tuple[bool, str]:
    """
    Ejecuta un comando de shell y retorna el resultado.

    Args:
        command: Lista con el comando y argumentos
        cwd: Directorio de trabajo

    Returns:
        (success, output)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd or BASE_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def check_git_status() -> bool:
    """Verifica si hay cambios pendientes en git"""
    success, output = run_command(['git', 'status', '--porcelain'])
    if success:
        return len(output.strip()) > 0
    return False


def get_new_json_files() -> List[str]:
    """Obtiene lista de archivos .json en casos/ que no están en git"""
    success, output = run_command(['git', 'ls-files', '--others', '--exclude-standard', 'casos/'])
    if success:
        files = [f.strip() for f in output.split('\n') if f.strip().endswith('.json')]
        return files
    return []


def upload_cases_to_github(commit_message: Optional[str] = None) -> bool:
    """
    Sube casos nuevos a GitHub.

    Args:
        commit_message: Mensaje personalizado del commit

    Returns:
        True si la subida fue exitosa
    """
    print("🚀 SUBIDA DE CASOS A GITHUB")
    print("="*70)

    # 1. Verificar que estamos en un repo git
    if not os.path.exists(os.path.join(BASE_DIR, '.git')):
        print("❌ Este directorio no es un repositorio git")
        print("Ejecuta primero:")
        print("  git init")
        print("  git remote add origin https://github.com/{}/{}.git".format(
            GITHUB_USERNAME, GITHUB_REPO
        ))
        return False

    # 2. Obtener archivos nuevos
    new_files = get_new_json_files()

    if not new_files:
        print("✅ No hay casos nuevos para subir")
        return True

    print(f"\n📁 Archivos nuevos encontrados ({len(new_files)}):")
    for file in new_files:
        print(f"   - {file}")

    # 3. Git add de los archivos nuevos
    print("\n📝 Añadiendo archivos a git...")
    for file in new_files:
        success, output = run_command(['git', 'add', file])
        if not success:
            print(f"❌ Error añadiendo {file}: {output}")
            return False

    # 4. Crear commit
    if not commit_message:
        commit_message = f"""Nuevos casos ECOE procesados ({len(new_files)})

- {len(new_files)} casos añadidos
- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}

🤖 Generated with Claude Code
"""

    print(f"\n💬 Creando commit...")
    success, output = run_command(['git', 'commit', '-m', commit_message])
    if not success:
        print(f"❌ Error en commit: {output}")
        return False

    print(f"✅ Commit creado")

    # 5. Push a GitHub
    print(f"\n⬆️  Subiendo a GitHub ({GITHUB_USERNAME}/{GITHUB_REPO})...")
    success, output = run_command(['git', 'push', 'origin', GITHUB_BRANCH])

    if not success:
        print(f"❌ Error en push: {output}")
        print("\nPosibles soluciones:")
        print("1. Verifica que el remote esté configurado:")
        print("   git remote -v")
        print("2. Configura el remote si es necesario:")
        print(f"   git remote add origin https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git")
        print("3. Verifica tus credenciales de GitHub")
        return False

    print(f"✅ Casos subidos exitosamente a GitHub!")
    print(f"\n🔗 Ver en: https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}/tree/{GITHUB_BRANCH}/casos")

    return True


def setup_git_repo():
    """
    Configura el repositorio git inicial (solo primera vez).
    """
    print("🔧 CONFIGURACIÓN INICIAL DE GIT")
    print("="*70)

    # Verificar si ya existe .git
    if os.path.exists(os.path.join(BASE_DIR, '.git')):
        print("✅ Repositorio git ya existe")
        return True

    # Git init
    print("\n📝 Inicializando repositorio git...")
    success, output = run_command(['git', 'init'])
    if not success:
        print(f"❌ Error: {output}")
        return False

    # Crear .gitignore si no existe
    gitignore_path = os.path.join(BASE_DIR, '.gitignore')
    if not os.path.exists(gitignore_path):
        print("📝 Creando .gitignore...")
        gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/

# Credentials
.env
config/google_credentials.json
*.bin

# Temporales
*.log
*.tmp
temp/
data/casos_nuevos_temp.json
"""
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)

    # Git add inicial
    print("📝 Añadiendo archivos iniciales...")
    run_command(['git', 'add', '.'])

    # Commit inicial
    print("💬 Creando commit inicial...")
    success, output = run_command(['git', 'commit', '-m', 'Initial commit: Sistema ECOE'])
    if not success:
        print(f"⚠️  Advertencia: {output}")

    # Configurar branch main
    print("🌿 Configurando branch main...")
    run_command(['git', 'branch', '-M', 'main'])

    # Añadir remote
    remote_url = f"https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
    print(f"🔗 Añadiendo remote: {remote_url}")
    success, output = run_command(['git', 'remote', 'add', 'origin', remote_url])
    if not success and 'already exists' not in output:
        print(f"⚠️  Advertencia: {output}")

    print("\n" + "="*70)
    print("✅ CONFIGURACIÓN COMPLETADA")
    print("="*70)
    print("\nPróximos pasos:")
    print("1. Asegúrate de que el repositorio existe en GitHub")
    print(f"   https://github.com/{GITHUB_USERNAME}/{GITHUB_REPO}")
    print("2. Ejecuta: python scripts/upload_to_github.py")

    return True


def main():
    """Función principal"""
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        setup_git_repo()
    else:
        upload_cases_to_github()


if __name__ == "__main__":
    main()
