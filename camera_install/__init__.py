"""Camera-installation layer, deliberately isolated from preview and PF3 editing."""

from .rp_assets import (
    RpAssetSet, RpAssetError, discover_rp_assets, import_rp_support_folder,
    import_rp_support_zip, validate_rp_asset_folder,
)
from .rp_payload import (
    build_rp_payload, canon_style_name, extract_duplicate_block1,
    extract_legacy_block1, split_legacy_blocks, validate_compiler_selftest,
)

__all__ = [
    "RpAssetSet", "RpAssetError", "discover_rp_assets", "import_rp_support_folder",
    "import_rp_support_zip", "validate_rp_asset_folder",
    "build_rp_payload", "canon_style_name", "extract_duplicate_block1",
    "extract_legacy_block1", "split_legacy_blocks", "validate_compiler_selftest",
]
