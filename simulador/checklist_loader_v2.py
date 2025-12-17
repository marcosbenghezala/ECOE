"""
Loader canónico para master-checklist-v2.json
Provee índices optimizados y helpers para evaluación.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Pattern


class ChecklistLoaderV2:
    """
    Cargador de checklist v2 con índices optimizados.

    Estructura interna:
    - metadata: Dict con version, total_blocks, total_items, max_points, etc.
    - blocks: List[Dict] de bloques (B0-B9)
    - items: List[Dict] de ítems (180 total)

    Índices (acceso O(1) o O(k)):
    - blocks_by_id: Dict[block_id, block_dict]
    - items_by_id: Dict[item_id, item_dict]
    - items_by_block: Dict[block_id, List[item_dict]]
    - items_by_subsection: Dict[subsection, List[item_dict]]
    - compiled_regex: Dict[item_id, List[Pattern]] (pre-compilados)
    """

    def __init__(self, checklist_path: Path):
        """
        Carga y valida checklist v2.

        Args:
            checklist_path: Ruta a master-checklist-v2.json

        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si el JSON es inválido o falta estructura
        """
        if not checklist_path.exists():
            raise FileNotFoundError(f"Checklist no encontrado: {checklist_path}")

        # Cargar JSON
        with open(checklist_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validaciones mínimas
        self._validate_structure(data)

        # Datos principales
        self.metadata: Dict = data["metadata"]
        self.blocks: List[Dict] = data["blocks"]
        self.items: List[Dict] = data["items"]

        # Construir índices
        self.blocks_by_id: Dict[str, Dict] = {b["block_id"]: b for b in self.blocks}
        self.items_by_id: Dict[str, Dict] = {it["id"]: it for it in self.items}
        self.items_by_block: Dict[str, List[Dict]] = self._build_items_by_block()
        self.items_by_subsection: Dict[str, List[Dict]] = self._build_items_by_subsection()

        # Pre-compilar regex para performance
        self.compiled_regex: Dict[str, List[Pattern]] = self._precompile_regex()

    def _validate_structure(self, data: Dict) -> None:
        """Validaciones mínimas al cargar."""
        # Verificar keys principales
        if "metadata" not in data:
            raise ValueError("JSON falta key 'metadata'")
        if "blocks" not in data:
            raise ValueError("JSON falta key 'blocks'")
        if "items" not in data:
            raise ValueError("JSON falta key 'items'")

        # Verificar IDs únicos en blocks
        block_ids = [b.get("block_id") for b in data["blocks"]]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("block_id duplicados detectados")

        # Verificar IDs únicos en items
        item_ids = [it.get("id") for it in data["items"]]
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("item.id duplicados detectados")

        # Verificar que cada item.block_id existe en blocks
        block_ids_set = set(block_ids)
        for item in data["items"]:
            item_block_id = item.get("block_id")
            if not item_block_id:
                raise ValueError(f"Item {item.get('id')} sin block_id")
            if item_block_id not in block_ids_set:
                raise ValueError(
                    f"Item {item['id']} referencia bloque inexistente: {item_block_id}"
                )

    def _build_items_by_block(self) -> Dict[str, List[Dict]]:
        """Construye índice items agrupados por block_id."""
        index = {}
        for item in self.items:
            block_id = item["block_id"]
            if block_id not in index:
                index[block_id] = []
            index[block_id].append(item)
        return index

    def _build_items_by_subsection(self) -> Dict[str, List[Dict]]:
        """Construye índice items agrupados por subsection (solo items con subsection)."""
        index = {}
        for item in self.items:
            if "subsection" in item and item["subsection"]:
                subsection = item["subsection"]
                if subsection not in index:
                    index[subsection] = []
                index[subsection].append(item)
        return index

    def _precompile_regex(self) -> Dict[str, List[Pattern]]:
        """Pre-compila todos los regex de items para performance."""
        compiled = {}
        for item in self.items:
            item_id = item["id"]
            patterns = []
            for pattern_str in item.get("regex", []):
                try:
                    patterns.append(re.compile(pattern_str, re.IGNORECASE))
                except re.error:
                    # Ignorar regex inválidos (ya validados en smoke test)
                    pass
            compiled[item_id] = patterns
        return compiled

    # ========== HELPERS ==========

    def get_block(self, block_id: str) -> Optional[Dict]:
        """
        Obtiene un bloque por ID.

        Args:
            block_id: ID del bloque (ej: "B0_INTRODUCCION")

        Returns:
            Dict con bloque o None si no existe
        """
        return self.blocks_by_id.get(block_id)

    def get_items_for_block(self, block_id: str) -> List[Dict]:
        """
        Obtiene todos los items de un bloque.

        Args:
            block_id: ID del bloque

        Returns:
            Lista de items (vacía si bloque no existe o sin items)
        """
        return self.items_by_block.get(block_id, [])

    def get_items_for_subsection(self, subsection: str) -> List[Dict]:
        """
        Obtiene todos los items de una subsección.

        Args:
            subsection: Nombre de subsección (ej: "CARDIOVASCULAR")

        Returns:
            Lista de items (vacía si subsección no existe)
        """
        return self.items_by_subsection.get(subsection, [])

    def get_subsections_for_block(self, block_id: str) -> List[str]:
        """
        Obtiene subsecciones de un bloque específico.

        Args:
            block_id: ID del bloque

        Returns:
            Lista de subsecciones únicas (vacía si bloque sin subsecciones)

        Example:
            >>> loader.get_subsections_for_block("B7_ANAMNESIS_APARATOS")
            ['CARDIOVASCULAR', 'DIGESTIVO', 'ENDOCRINO', ...]
        """
        items = self.get_items_for_block(block_id)
        subsections = {it["subsection"] for it in items if "subsection" in it}
        return sorted(subsections)

    def list_subsections(self) -> List[str]:
        """
        Obtiene todas las subsecciones del checklist.

        Returns:
            Lista de subsecciones únicas ordenadas

        Example:
            >>> loader.list_subsections()
            ['CARDIOVASCULAR', 'DIGESTIVO', ...]
        """
        return sorted(self.items_by_subsection.keys())

    def get_applicable_items(self) -> List[Dict]:
        """
        Obtiene solo items aplicables (no_applicable=false).

        Returns:
            Lista de items aplicables (filtrados)

        Example:
            >>> len(loader.get_applicable_items())
            180  # Todos son aplicables en v2
        """
        return [it for it in self.items if not it.get("no_applicable", False)]

    def get_compiled_regex(self, item_id: str) -> List[Pattern]:
        """
        Obtiene regex pre-compilados de un item.

        Args:
            item_id: ID del item

        Returns:
            Lista de Pattern pre-compilados (vacía si item sin regex)
        """
        return self.compiled_regex.get(item_id, [])


# ========== FACTORY CON CACHE ==========

@lru_cache(maxsize=1)
def load_checklist_v2(path: Optional[str] = None) -> ChecklistLoaderV2:
    """
    Carga checklist v2 (singleton cached).

    Args:
        path: Ruta custom al JSON (opcional, usa default si None)

    Returns:
        ChecklistLoaderV2 instance (cached)

    Example:
        >>> loader = load_checklist_v2()
        >>> loader.metadata["total_items"]
        180
        >>> # Segunda llamada usa cache (no recarga archivo)
        >>> loader2 = load_checklist_v2()
        >>> loader is loader2  # True
    """
    if path is None:
        # Default: data/master-checklist-v2.json relativo al módulo
        default_path = Path(__file__).parent.parent / "data" / "master-checklist-v2.json"
        checklist_path = default_path
    else:
        checklist_path = Path(path)

    return ChecklistLoaderV2(checklist_path)
