"""Research-only compact16752 pixel-route replay from source records.

Validated against one archived normal RP control. This is not a route selector,
camera transport, arbitrary-LUT acceptance implementation or support declaration.
The caller supplies normalized modern descriptor bytes and cipher keys; this
module neither loads Canon DLLs nor reads captured output pixels.
"""
from .cipher_stream_reference import decode
from .control_section_reference import build_control_plain
from .compact_header_reference import build_compact16752_prefix,build_older_compact_prefix
from .descriptor_import_reference import modern_grid_arguments, parameterless_matrix_reference
from .legacy_grid_reference import prepare, flagged_point
from .compact_pixel_reference import prepare as prepare_pixel, point as pixel
from .tail_settings_reference import settings_from_records
from .packed10_reference import pack10_for_style
from .compact_cache_reference import build_compact_cache
from .compact_branch_reference import derived_compact_grid_flag,coefficient_policy,compact_pixel_scale
from .compact_branch_reference import convert_alternate_grid
from .compact_legacy_grid_reference import compact_legacy_grid
from .packed10_reference import unpack10_integer,pack10_integer
from .accepted_modern_reference import dense_source
from .compact_grid_reference import compact_flag1


def build_observed_compact16752_integer(fields,normalized_compact,keys,*,
                                       block_paths,internal_selector):
    return build_observed_compact_integer(fields,normalized_compact,keys,
        block_paths=block_paths,internal_selector=internal_selector,total_size=16752)


def build_observed_compact_integer(fields,normalized_compact,keys,*,
                                  block_paths,internal_selector,total_size):
    """Research-only class3..6 header + explicit compact integer/cache paths.

    This is NOT dispatch by descriptor length or a camera support declaration.
    Caller establishes serializer class, compact reader and callback provenance
    (class5/6 require independently established base callback no-op).
    Alternate 00FF0001 headers are deliberately not supported here.
    """
    if type(total_size) is not int or total_size not in (8528,16720,16744,16752):
        raise ValueError('Require explicitly established normal compact geometry')
    if type(normalized_compact) is not bytes or len(normalized_compact)!=7492:
        raise ValueError('Require explicit normalized compact7492-byte store')
    if not coefficient_policy(internal_selector):
        raise ValueError('Require independently established compact reader policy')
    if total_size==8528:
        valid_paths=type(block_paths) is tuple and block_paths==('cache','cache')
    else:
        valid_paths=(type(block_paths) is tuple and len(block_paths)==4
            and all(p in ('integer','cache') for p in block_paths[:2])
            and block_paths[2:]==('cache','cache'))
    if not valid_paths:
        raise ValueError('Require explicit integer/cache first pair and cached second pair')
    data={identifier:value for identifier,(_,value) in fields.items()}
    style=int.from_bytes(data[0x1009],'little')
    # Fine Detail's compact reader was not validated, even on cache-only input.
    if style not in range(0x81,0x86):
        raise ValueError('Unvalidated compact legacy style')
    flag=derived_compact_grid_flag(internal_selector)
    caches=[build_compact_cache(data[0x1070+i],grid_flag=flag,
                               coefficient_mode=True) for i in range(2)]
    blocks=[]
    for index,path in enumerate(block_paths):
        packed=caches[index%2]
        if path=='integer':
            grid=compact_legacy_grid(normalized_compact,style,index+1)
            packed=pack10_integer(convert_alternate_grid(
                grid,unpack10_integer(packed),True))
        blocks.append(decode(packed,keys,0xb8ed if index%2==0 else 0x33137))
    control=build_control_plain({i:fields[i] for i in (0x100a,0x100d) if i in fields})
    encoded=control[:8]+decode(control[8:],keys,0x22e1)
    prefix=(build_compact16752_prefix(fields,encoded) if total_size==16752
            else build_older_compact_prefix(fields,encoded,total_size))
    return prefix+b''.join(blocks)


def compact_upstream_grid(normalized_descriptor, style, index):
    """48d10 first pair /49c90 parameterless pair, fixed 10-node flag1."""
    if not isinstance(normalized_descriptor, bytes) or len(normalized_descriptor)!=14796:
        raise ValueError('Require observed normalized modern descriptor')
    if type(index) is not int or index not in range(4):
        raise ValueError('Require compact block index 0..3')
    # Validate the style for both pairs, even the parameterless branch.
    arguments=modern_grid_arguments(normalized_descriptor,style,index%2+1,index%2+1)
    if index>=2:
        arguments=dict(oldParameterBlock=None,axisParameterBlock=None,
                       additionalParameterBlock=None,preCurvesHex=None,
                       postCurvesHex=None,thirdCurvesHex=None,
                       matrix240Hex=parameterless_matrix_reference().hex(),
                       numericArguments=[index%2+1,1])
    coefficients,mode,curves,groups=prepare(arguments,experimental_geometry=True)
    return [flagged_point((r,g,b),coefficients,mode,curves,groups,10,1)
            for r in range(10) for g in range(10) for b in range(10)]


def build_observed_compact16752_pixel(fields,normalized_descriptor,keys,*,pixel_scale=256):
    """Explicit pixel branch only: alternate integer-grid branch is separate."""
    return build_observed_compact16752(fields,normalized_descriptor,keys,
                                      block_paths=('pixel',)*4,pixel_scale=pixel_scale,
                                      internal_selector=0)


def build_accepted_compact16752(fields,normalized_descriptor,keys,*,internal_selector):
    """Explicit observed dense10 override followed by the normal pixel stage.

    Reproduces the archived RP twelve-vector override experiment, not automatic
    route negotiation, physical acceptance or a permission to register.
    """
    if coefficient_policy(internal_selector) or compact_pixel_scale(internal_selector)!=256:
        raise ValueError('Unvalidated dense10 pixel policy')
    return build_observed_compact16752(fields,normalized_descriptor,keys,
        block_paths=('dense-pixel','dense-pixel','pixel','pixel'),
        pixel_scale=256,internal_selector=internal_selector)


def pack_compact_pixel_grid(data,rgb,*,mode,style,pixel_scale):
    settings=prepare_pixel(settings_from_records(data,mode))
    processed=[pixel([v/pixel_scale for v in point],settings) for point in rgb]
    planar=[min(288,max(0,point[c]*pixel_scale)) for c in range(3) for point in processed]
    return pack10_for_style(planar,style,mode)


def build_observed_compact16752(fields,normalized_descriptor,keys,*,block_paths,
                                pixel_scale,internal_selector):
    """Explicit source-only pixel/dense-pixel/cache composition, no dispatch.

    Caller must establish the 10-node16752 route and each block path separately.
    No model names, recorded pixels or expected payload bytes are inputs.
    Cache and pixel packing deliberately use DIFFERENT coefficient policies.
    """
    if type(pixel_scale) is not int or pixel_scale not in (255,256):
        raise ValueError('Require explicit experimental pixel scale 255 or 256')
    if type(block_paths) is not tuple or len(block_paths)!=4 or any(p not in ('pixel','cache','dense-pixel') for p in block_paths) or 'dense-pixel' in block_paths[2:]:
        raise ValueError('Require four explicit pixel/cache paths; dense-pixel only in the first pair')
    grid_flag=derived_compact_grid_flag(internal_selector)
    cache_coefficient=coefficient_policy(internal_selector)
    data={identifier:value for identifier,(_,value) in fields.items()}
    style=int.from_bytes(data[0x1009],'little')
    control=build_control_plain({i:fields[i] for i in (0x100a,0x100d) if i in fields})
    encoded=control[:8]+decode(control[8:],keys,0x22e1)
    prefix=build_compact16752_prefix(fields,encoded)
    blocks=[]
    for index in range(4):
        mode=index%2+1
        if block_paths[index]=='cache':
            packed=build_compact_cache(data[0x1070+index%2],grid_flag=grid_flag,
                                       coefficient_mode=cache_coefficient)
        else:
            if block_paths[index]=='dense-pixel':
                # The fallback sets a 10-node flag1 intermediate before475c0.
                rgb=compact_flag1(dense_source(data[0x1070+index])).reshape(3,1000).T.tolist()
            else:
                rgb=compact_upstream_grid(normalized_descriptor,style,index)
            packed=pack_compact_pixel_grid(data,rgb,mode=mode,style=style,pixel_scale=pixel_scale)
        blocks.append(decode(packed,keys,0xb8ed if index%2==0 else 0x33137))
    return prefix+b''.join(blocks)
