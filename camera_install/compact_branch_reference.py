"""Offline provenance checks for observed compact integer builder branches."""
import math
from .integer_tetrahedral_reference import interpolate
from .descriptor_capability_reference import capability_word
from .descriptor_import_reference import validated_style_ordinal


def convert_alternate_grid(values, table, coefficient_mode):
    """Replay4a3b0 with its validated upper clamp, not an output serializer."""
    if len(values) != 3000 or len(table) != 3000 or type(coefficient_mode) is not bool:
        raise ValueError('Require planar 10-node input/table and observed policy')
    if not all(type(v) is int and -(2**31) <= v < 2**31 for v in table):
        raise ValueError('Require signed 32-bit interpolation table')
    result=[0]*3000
    for index in range(1000):
        coordinates=[]
        for channel in range(3):
            value=values[channel*1000+index]
            if not math.isfinite(value) or value < 0:
                raise ValueError('Unvalidated negative/nonfinite coordinate')
            quantized=int(min(value,288)+(0 if coefficient_mode else .5))
            coordinates.append(quantized*32)
        converted=interpolate(table,coordinates)
        #47af0 output pointers swap the two chroma planes in this wrapper.
        for channel, output in enumerate((converted[0],converted[2],converted[1])):
            result[channel*1000+index]=output>>6
    return result

# Known-revision 4b290 policy, not a camera support/installation registry.
COEFFICIENT_POLICY_IDS = frozenset((
    0x03740000, 0x03840000, 0x80000169, 0x80000176, 0x80000190,
    0x80000213, 0x80000215, 0x80000218, 0x80000232, 0x80000234,
    0x80000236, 0x80000250, 0x80000252, 0x80000254, 0x80000261,
    0x80000269, 0x80000270, 0x80000281, 0x80000285, 0x80000286,
    0x80000287, 0x80000288, 0x80000289, 0x80000292, 0x80000301,
    0x80000302, 0x80000324, 0x80000325, 0x80000326, 0x80000327,
    0x80000329, 0x80000331, 0x80000346, 0x80000347, 0x80000355,
    0x80000384, 0x80000393, 0x80000404, 0x80000422, 0x80000432,
    0xC0000250,
))


def coefficient_policy(camera_id):
    if type(camera_id) is not int or not 0 <= camera_id <= 0xFFFFFFFF:
        raise ValueError('Require unsigned camera ID')
    return camera_id in COEFFICIENT_POLICY_IDS


def compact_pixel_scale(internal_selector):
    """Known4b250 scale policy; not a camera-family/support classifier."""
    if type(internal_selector) is not int or not 0<=internal_selector<=0xffffffff:
        raise ValueError('Require unsigned internal compiler selector')
    return 255 if internal_selector in (0x80000382,0x80000401) else 256


def rejects_fine_detail_branch(camera_id, style_selector):
    """Known-revision 573dc..574c4 rejection only, not general style acceptance."""
    if type(style_selector) is not int or not 0 <= style_selector <= 0xffff:
        raise ValueError('Require unsigned 16-bit style selector')
    # Independently extracted 574e8/57510/57550 tables have the same 41 IDs.
    policy=coefficient_policy(camera_id)
    return style_selector == 0x88 and policy


def uses_pixel_builder(coefficient_mode, object_flag):
    if type(coefficient_mode) is not bool or type(object_flag) is not int or not 0 <= object_flag <= 255:
        raise ValueError('Require observed boolean policy and object byte')
    return not coefficient_mode and object_flag == 0


def compact_builder_path(capability_enabled,coefficient_mode,object_flag):
    """Static4c770/4d660 dispatch only, not a camera-family predictor.

    A disabled descriptor gate selects internal-table retrieval/copy before
    either pixel processing or integer interpolation can be reached.
    """
    if type(capability_enabled) is not bool:
        raise ValueError('Require explicit observed descriptor gate')
    pixel=uses_pixel_builder(coefficient_mode,object_flag)
    if not capability_enabled:return 'internal-table-copy'
    return 'pixel' if pixel else 'integer-interpolation'


def derived_compact_grid_flag(internal_selector):
    """4ce77..4ceb3 dispatch AFTER selecting the derived 10-node branch.

    Input is the compiler's internal1001 value, not an assumed public camera
    ID. This function does not select 9/10/17-node initialization branches.
    """
    if type(internal_selector) is not int or not 0<=internal_selector<=0xffffffff:
        raise ValueError('Require unsigned internal compiler selector')
    # x86 add ebx,0x7ffffe97 subtracts0x80000169 with uint32 wrap.
    # The unsigned ja at4ce9a selects flag1 for indices above205.
    index=(internal_selector-0x80000169)&0xffffffff
    return 0 if index in (0,39,170,172,201,203,205) else 1


def compact_first_pair_plan(normalized_modern_store,style_selector,internal_selector,object_flag):
    """Known4c3b0/4b4f0/4c770 first-pair policy, not serializer dispatch.

    Input is the full normalized internal modern store. Legacy readers copy
    its7492-byte prefix; do NOT renormalize that prefix as a raw descriptor.
    Caller provides the actual builder's flag, not another object's byte+8.
    """
    if type(normalized_modern_store) is not bytes or len(normalized_modern_store)!=14796:
        raise ValueError('Require full normalized modern internal store')
    ordinal=validated_style_ordinal(style_selector)
    coefficient=coefficient_policy(internal_selector)
    # Independently extracted4c3b0 compact-prefix set equals4b290's set.
    modern=not coefficient
    descriptor=normalized_modern_store if modern else normalized_modern_store[:7492]
    gates=[capability_word(descriptor,modern,ordinal,index) for index in (1,2)]
    paths=tuple(compact_builder_path(gate['enabled'],coefficient,object_flag) for gate in gates)
    return dict(descriptorPrefixBytes=len(descriptor),gateWords=tuple(g['word'] for g in gates),
                paths=tuple('cache' if p=='internal-table-copy' else p for p in paths))


def compact_store_plan(normalized_compact,style_selector,internal_selector,
                       object_flag,serializer_class,*,base_callback_noop=False):
    """Explicit compact7492 reader, classes3..6; never camera authorization.

    Unlike compact_first_pair_plan this accepts an actual compact store, not
    a prefix copied from a modern internal store. Do not pad or renormalize it.
    """
    if type(normalized_compact) is not bytes or len(normalized_compact)!=7492:
        raise ValueError('Require explicit normalized compact7492 store')
    if type(serializer_class) is not int or serializer_class not in (3,4,5,6):
        raise ValueError('Unvalidated compact-store serializer class')
    if type(base_callback_noop) is not bool:
        raise ValueError('Require explicit callback evidence')
    if serializer_class in (5,6) and not base_callback_noop:
        raise ValueError('Class5/6 requires independently verified callback')
    if not coefficient_policy(internal_selector):
        raise ValueError('Selector does not establish compact-reader policy')
    ordinal=validated_style_ordinal(style_selector)
    if ordinal>=5:raise ValueError('Unvalidated compact legacy style')
    gates=[capability_word(normalized_compact,False,ordinal,index) for index in (1,2)]
    first=tuple(compact_builder_path(g['enabled'],True,object_flag) for g in gates)
    first=tuple('cache' if p=='internal-table-copy' else 'integer' for p in first)
    paths=('cache','cache') if serializer_class==3 else first+('cache','cache')
    return dict(descriptorPrefixBytes=7492,gateWords=tuple(g['word'] for g in gates),
        blockPaths=paths,serializerClass=serializer_class,
        totalSize={3:8528,4:16720,5:16744,6:16752}[serializer_class])


def compact16752_plan(normalized_modern_store,style_selector,internal_selector,
                      object_flag,serializer_class,*,base_callback_noop=False):
    """Offline known-revision dispatch, never installation authorization.

    Class6 requires independently verified base-reference callback evidence.
    Class7 invokes the parameterless second builder with the same gates.
    Other classes/reference subclasses remain deliberately unclassified.
    """
    if type(serializer_class) is not int or serializer_class not in (6,7):
        raise ValueError('Unvalidated compact serializer class')
    if type(base_callback_noop) is not bool:
        raise ValueError('Require explicit callback evidence')
    if serializer_class==6 and not base_callback_noop:
        raise ValueError('Class6 requires verified no-op base callback')
    first=compact_first_pair_plan(normalized_modern_store,style_selector,internal_selector,object_flag)
    second=('cache','cache') if serializer_class==6 else first['paths']
    return dict(first,blockPaths=first['paths']+second,
                pixelScale=compact_pixel_scale(internal_selector),
                serializerClass=serializer_class)


def older_compact_plan(normalized_modern_store,style_selector,internal_selector,
                       object_flag,serializer_class,*,base_callback_noop=False):
    """Known class3/4/5 serializer topology, offline only.

    Class3 directly copies its cache pair; class4 computes only the first
    pair. Class5's second pair needs independently verified callback evidence.
    This does not prove the cache initializer for every internal selector.
    """
    if type(serializer_class) is not int or serializer_class not in (3,4,5):
        raise ValueError('Unvalidated older compact serializer class')
    if type(base_callback_noop) is not bool:
        raise ValueError('Require explicit callback evidence')
    if serializer_class==5 and not base_callback_noop:
        raise ValueError('Class5 requires verified no-op base callbacks')
    # Validate shared inputs even when descriptor gates are bypassed.
    first=compact_first_pair_plan(normalized_modern_store,style_selector,internal_selector,object_flag)
    paths=('cache','cache') if serializer_class==3 else first['paths']+('cache','cache')
    return dict(first,blockPaths=paths,serializerClass=serializer_class,
                totalSize={3:8528,4:16720,5:16744}[serializer_class],
                pixelScale=compact_pixel_scale(internal_selector))


def verify_builder_links(captures):
    origins = {'0x4c900': '0x4c92d', '0x4d7f0': '0x4d81d'}
    packers = [c for c in captures if c.get('functionRva') == '0x49e00']
    rows = []
    for item in captures:
        if item.get('functionRva') != '0x475c0':
            continue
        caller = item.get('callerRva')
        if caller not in origins:
            raise ValueError('Unmapped builder caller')
        value = item.get('outputPlanarInt32Hex')
        if not isinstance(value, str) or len(bytes.fromhex(value)) != 12000:
            raise ValueError('Missing or invalid integer grid')
        matches = [p for p in packers if p.get('callerRva') == origins[caller]
                   and p.get('inputPlanarInt32Hex') == value]
        if not matches:
            raise ValueError('Builder output has no exact downstream packer input')
        rows.append({'builderCaller': caller, 'packerCaller': origins[caller],
                     'byteExact': True})
    if not rows:
        raise ValueError('No observed builder links')
    return rows


def verify_float_builder_links(captures):
    """Match initialized MLib output, never entry-time/uninitialized memory."""
    rows = []
    for index, item in enumerate(captures):
        if item.get('functionRva') != '0x475c0':
            continue
        value = item.get('inputPlanarFloat64Hex')
        if not isinstance(value, str) or len(bytes.fromhex(value)) != 24000:
            raise ValueError('Missing bounded 10-node floating input')
        candidates = []
        for source_index, source in enumerate(captures):
            if source.get('functionRva') != '0x14bd0' or source.get('result') != 1:
                continue
            for grid in source.get('gridArguments', []):
                if (grid.get('argument') == 'stack7' and grid.get('nodes') == 10
                        and grid.get('bytes') == 24000
                        and grid.get('initializedOutputFloat64Hex') == value):
                    candidates.append(source_index)
        if not candidates:
            raise ValueError('No byte-exact initialized floating builder output')
        rows.append({'pixelBuilderCapture': index, 'sourceCandidates': candidates,
                     'byteExact': True})
    if not rows:
        raise ValueError('No floating builder links')
    return rows
