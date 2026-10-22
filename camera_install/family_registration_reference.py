"""Source-only compiler/session integration for reconstructed serializer families.

Live inputs establish geometry and advertised operations. The model catalog is
compiler evidence, not a claim that each body's USB installation was tested.
"""
import hashlib
import struct
from .camera_families_reference import camera_family, FAMILY_SIZES
from .cipher_stream_reference import decode
from .descriptor_import_reference import normalize_observed_raw
from .pf3_source_reference import read_source_fields
from .offline_registration_reference import OfflineRegistration
from .style_send_plan_reference import plan_style_send
from .registration_sequence_reference import plan_registration, validate_sequence
from .session_inputs_reference import SlotObservation
from .rp_preflight_reference import SlotControlMismatch
from .compact_branch_reference import rejects_fine_detail_branch


CONTROLS=(('Contrast',0,0x1031,True),('Strength',4,0x1030,False),
    ('Saturation',8,0x1032,True),('Color Tone',12,0x1033,True),
    ('Fineness',24,0x1034,False),('Threshold',28,0x1035,False))
REQUIRED_OPERATIONS=frozenset((0x9110,0x9114,0x9115,0x9116,0x911b,0x911c,0x9127))
CONTROL_LIMITS={'Contrast':(-4,4),'Strength':(0,7),'Saturation':(-4,4),
    'Color Tone':(-4,4),'Fineness':(1,5),'Threshold':(1,5)}


class FamilyCompatibilityError(ValueError):
    """Safe compiler/session-plan reason; contains no device identifier or state."""


def inspect_family_style(style,keys,family):
    """Check complete normalized readback, including encrypted table geometry."""
    size=FAMILY_SIZES[family]
    if type(style) is not bytes or len(style)!=size-32:
        raise ValueError('Slot style geometry differs from the identified serializer family')
    if struct.unpack_from('<II',style)!=(1,size-40):
        raise ValueError('Slot style envelope is disabled or inconsistent')
    compact=family<=7
    if compact:
        length,selector=struct.unpack_from('<HH',style,8)
    else:
        length,selector=struct.unpack_from('<IH',style,8)
    if length!=size-40 or selector not in (0x81,0x82,0x83,0x84,0x85,0x88):
        raise ValueError('Slot style size/base selector differs from the reconstructed format')
    if family in (1,2):
        offset=44 if family==1 else 300
        metadata=style[offset:offset+1460]
        if len(metadata)!=1460 or struct.unpack_from('<I',metadata)[0]!=1460:
            raise ValueError('Legacy slot lacks complete live 1007 metadata')
        control=2044 if family==1 else 48
        table_start=2300 if family==1 else 2304
        block_size,blocks=2916,2
    else:
        marker,tag={3:(44,0x28),4:(44,0x28),5:(68,0x40),6:(76,0x48),
                    7:(76,0x48),8:(80,0x4c),9:(80,0x4c),10:(80,0x4c)}[family]
        if struct.unpack_from('<HH',style,marker)!=(tag,252):
            raise ValueError('Slot control envelope marker differs from the reconstructed format')
        control=marker+4
        table_start={3:304,4:304,5:328,6:336,7:336,8:340,9:340,10:340}[family]
        block_size=4096 if family<=7 else 19652 if family<=9 else 215622
        blocks=2 if family in (3,10) else 4
    if struct.unpack_from('<HHI',style,control)!=(0x2fff,0xffff,0):
        raise ValueError('Slot control record marker differs')
    if family>=5 and struct.unpack_from('<II',style,60 if compact else 64)!=(0xdeadbeef,0xdeadbeef):
        raise ValueError('Slot Basic control sentinels differ')
    from .packed10_reference import packed_index
    used={packed_index(r,g,b) for r in range(10) for g in range(10) for b in range(10)}
    for index in range(blocks+(family==9)):
        auxiliary=index==4
        start=table_start+index*block_size
        count=4096 if auxiliary else block_size
        block=style[start:start+count]
        if len(block)!=count:raise ValueError('Truncated slot table')
        if family==10:
            if max(struct.unpack('<107811H',block))>32768:
                raise ValueError('Full33 slot sample exceeds the reconstructed range')
        else:
            words=struct.unpack('<'+str(count//4)+'I',decode(block,keys,
                0xb8ed if auxiliary or index%2==0 else 0x33137)) if family>2 else struct.unpack(
                '<729I',decode(block,keys,0x252e4 if index==0 else 0x2d456))
            if any(word&0xc0000000 for word in words):
                raise ValueError('Slot packed table has reserved high bits')
            if (family in (3,4,5,6,7) or auxiliary) and any(
                    word for position,word in enumerate(words) if position not in used):
                raise ValueError('Slot compact table has nonzero padding')
    return selector


def prepare_family_registration(raw,keys,**options):
    try:return _prepare_family_registration(raw,keys,**options)
    except ValueError as error:raise FamilyCompatibilityError(str(error)) from error


def _prepare_family_registration(raw,keys,*,camera_id,descriptor,slot_style,slot,
                                vendor_operations,device_operations):
    family,model=camera_family(camera_id,slot_style)
    if type(slot) is not int or slot not in (1,2,3):
        raise ValueError('Require selected User Def. 1..3')
    for operations in (vendor_operations,device_operations):
        if (type(operations) is not tuple or len(operations)>4096
                or any(type(code) is not int or not 0<=code<=0xffff for code in operations)
                or not REQUIRED_OPERATIONS.issubset(operations)):
            raise ValueError('Camera did not advertise the reconstructed registration operations')
    baseline_selector=inspect_family_style(slot_style,keys,family)
    fields=read_source_fields(raw,keys)
    selector=fields.get(0x1009)
    if selector is None or selector[0]!=3 or len(selector[1])!=2:
        raise ValueError('Missing exact source Picture Style selector')
    style=int.from_bytes(selector[1],'little')
    if (style not in (0x81,0x82,0x83,0x84,0x85,0x88)
            or (family<=5 and style==0x88) or rejects_fine_detail_branch(camera_id,style)):
        raise ValueError('Selected base is not reconstructed for this serializer family')
    control_words=[]
    for name,offset,identifier,signed in CONTROLS:
        if family<=5 and offset>=24:continue
        record=fields.get(identifier)
        if record is None or record[0]!=4 or len(record[1])!=4:
            raise ValueError('Missing exact source Basic control '+name)
        control_words.append((name,offset,record[1],signed))
    if family in (1,2):
        if baseline_selector!=style:
            raise ValueError('Select the same base in camera first; legacy metadata is base-specific')
        from .legacy_dense9_carrier_reference import build_legacy_dense9_carrier
        start=44 if family==1 else 300
        carrier=build_legacy_dense9_carrier(dict(fields),keys,slot_style[start:start+1460],
            total_size=FAMILY_SIZES[family])
        route='legacy-dense9'
    else:
        if type(descriptor) is not bytes:raise ValueError('Missing live compiler descriptor')
        normalized,_=normalize_observed_raw(descriptor,keys)
        if family in (3,4,5,6,7):
            from .compact_branch_reference import (coefficient_policy,compact_store_plan,
                compact16752_plan)
            from .compact_carrier_reference import (build_observed_compact_integer,
                build_observed_compact16752)
            # In strict PF3 3000, class5/6 reference callbacks are no-ops;
            # compile active records while retaining the untouched reference bank.
            if coefficient_policy(camera_id):
                compact=normalized if len(normalized)==7492 else normalized[:7492]
                plan=compact_store_plan(compact,style,camera_id,0,family,base_callback_noop=True)
                carrier=build_observed_compact_integer(dict(fields),compact,keys,
                    block_paths=plan['blockPaths'],internal_selector=camera_id,
                    total_size=FAMILY_SIZES[family])
                route='compact-integer'
            else:
                if family not in (6,7):raise ValueError('Unreconstructed compact reader policy')
                plan=compact16752_plan(normalized,style,camera_id,0,family,base_callback_noop=True)
                paths=tuple('dense-pixel' if index<2 and path=='pixel' else path
                    for index,path in enumerate(plan['blockPaths']))
                carrier=build_observed_compact16752(dict(fields),normalized,keys,
                    block_paths=paths,pixel_scale=plan['pixelScale'],internal_selector=camera_id)
                route='compact16752-dense-pixel' if paths==('dense-pixel','dense-pixel','pixel','pixel') else 'compact-mixed'
        elif family in (8,9):
            if len(normalized)!=14796:raise ValueError('Modern17 requires a modern live descriptor')
            from .accepted_modern_reference import build_accepted_modern17
            carrier=build_accepted_modern17(fields,normalized,keys,extended=family==9)
            route='modern83076-dense' if family==9 else 'modern78980-dense'
        else:
            if len(normalized)!=14796:raise ValueError('Full33 requires a modern live descriptor')
            from .full33_packing_reference import encode_app_dense_full33
            from .modern_header_reference import build_full33_prefix
            from .control_section_reference import build_control_plain
            control=build_control_plain({i:fields[i] for i in (0x100a,0x100d) if i in fields})
            encoded=control[:8]+decode(control[8:],keys,0x22e1)
            carrier=build_full33_prefix(fields,encoded)+b''.join(
                encode_app_dense_full33(fields[i][1]) for i in (0x1070,0x1071))
            route='full33-dense'
    if len(carrier)!=FAMILY_SIZES[family]:raise ValueError('Compiled carrier size differs from negotiated family')
    inspect_family_style(carrier[:8]+carrier[40:],keys,family)
    # Compare serialized/clamped values, rather than pre-serialization PF3 sentinels.
    if family>=5:
        header=76 if family<=7 else 80
        control_words=[(name,offset,carrier[header+offset:header+offset+4],signed)
            for name,offset,value,signed in control_words]
    operations=tuple(code for code in device_operations if code in vendor_operations)
    send=plan_style_send(carrier,0x20+slot,operations)
    job=OfflineRegistration(hashlib.sha256(raw).hexdigest(),route,carrier,send,tuple(control_words))
    return job,dict(compilerProfileMatched=True,model=model,serializerFamily=family,route=route,
        sourceSha256=job.source_sha256,carrierSha256=hashlib.sha256(carrier).hexdigest(),
        packetSha256=hashlib.sha256(send.data).hexdigest(),packetBytes=len(send.data),
        opcode=hex(send.opcode),slot=slot,liveRegistrationEnabled=True,
        cameraId=hex(camera_id),descriptorBytes=None if descriptor is None else len(descriptor),
        descriptorSha256=None if descriptor is None else hashlib.sha256(descriptor).hexdigest(),
        physicalAcceptanceEstablished=False,stateFreshnessEstablished=False,
        physicalValidationScope='RP only; other bodies require physical confirmation')


def prepare_family_sequence(job,observations,*,update_known_basic_controls=False):
    try:return _prepare_family_sequence(job,observations,update_known_basic_controls=update_known_basic_controls)
    except SlotControlMismatch:raise
    except ValueError as error:raise FamilyCompatibilityError(str(error)) from error


def _prepare_family_sequence(job,observations,*,update_known_basic_controls=False):
    if type(update_known_basic_controls) is not bool:
        raise ValueError('Require explicit boolean known-control update policy')
    selected=[s for s in observations if isinstance(s,SlotObservation)
        and s.handler_selector==0x20+job.send.slot]
    if len(selected)!=1:raise ValueError('Require one unambiguous selected-slot state observation')
    state=selected[0]
    if state.marker not in (0,1) or state.selector!=0x40+job.send.slot:
        raise ValueError('Selected-slot marker/selector differs from the reconstructed protocol')
    if not job.control_words:raise ValueError('Missing candidate Basic controls')
    differences=[];control=bytearray(state.control);seen=set()
    specifications={name:(offset,signed) for name,offset,_identifier,signed in CONTROLS}
    for name,offset,value,signed in job.control_words:
        if update_known_basic_controls:
            if (type(name) is not str or name not in specifications or name in seen
                    or type(offset) is not int or type(signed) is not bool
                    or specifications[name]!=(offset,signed) or type(value) is not bytes or len(value)!=4):
                raise ValueError('Unknown or duplicate Basic control word')
            seen.add(name)
            number=int.from_bytes(value,'little',signed=signed)
            minimum,maximum=CONTROL_LIMITS[name]
            if not minimum<=number<=maximum:
                raise ValueError('Candidate Basic control outside the supported range: '+name)
        if offset+4>len(state.control):continue
        actual=state.control[offset:offset+4]
        if actual!=value:
            differences.append(dict(control=name,slotValue=int.from_bytes(actual,'little',signed=signed),
                candidateValue=int.from_bytes(value,'little',signed=signed)))
            if update_known_basic_controls:
                if len(state.control)!=(32 if state.marker else 24):
                    raise ValueError('Known control update requires an observed control matching the wire layout')
                if state.marker==0 and offset+4>24:
                    raise ValueError('Basic control cannot be updated by the legacy state layout: '+name)
                control[offset:offset+4]=value
    if differences and not update_known_basic_controls:raise SlotControlMismatch(tuple(differences))
    sequence=plan_registration(job.carrier,bytes(control),state.handler_selector,(job.send.opcode,),
        observed_marker=state.marker,selected_cache_value=state.selector)
    if sequence.style!=job.send:raise ValueError('Negotiated style differs from session plan')
    validate_sequence(sequence)
    return sequence
