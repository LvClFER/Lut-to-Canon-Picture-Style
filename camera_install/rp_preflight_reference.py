"""Pure bounded RP compiler-profile preflight; never opens or writes a device."""
import hashlib
from .compact_header_reference import inspect_compact16752_style
from .compact_branch_reference import compact16752_plan
from .descriptor_import_reference import normalize_observed_raw
from .pf3_source_reference import read_source_fields
from .offline_registration_reference import prepare


# This observed profile is narrower than a model-name or format-size rule.
RP_DESCRIPTOR_SHA256 = '2bff34bc3d7cae7d6c65c5e930befe2e0d0920d725ca9fdb18acbb9c8a7aec60'


class SlotControlMismatch(ValueError):
    """Known Basic words only; never exposes or modifies the opaque state blob."""
    def __init__(self,differences):
        super().__init__('Observed slot controls differ from the compiled candidate')
        self.differences=differences


def prepare_rp_sequence(job, observations):
    """Build a coherent plan from caller-owned observations, not write permission."""
    from .session_inputs_reference import SlotObservation
    from .registration_sequence_reference import plan_registration, validate_sequence
    if getattr(job,'route',None)!='compact16752-dense-pixel':
        raise ValueError('Registration state is not validated for this compiler route')
    selected = [value for value in observations
                if isinstance(value, SlotObservation)
                and value.handler_selector == 0x20 + job.send.slot]
    if len(selected) != 1:
        raise ValueError('Require one unambiguous selected-slot state observation')
    state = selected[0]
    if state.marker != 1 or state.selector != 0x40 + job.send.slot:
        raise ValueError('Selected-slot state differs from the observed RP profile')
    sequence = plan_registration(job.carrier, state.control, state.handler_selector,
        (0x9110,), observed_marker=state.marker, selected_cache_value=state.selector)
    validate_sequence(sequence)
    if sequence.style != job.send:
        raise ValueError('Sequence style differs from compiled transport plan')
    # All five archived native RP transactions match these six header/control words.
    # Do not manufacture the remaining state or silently reuse conflicting controls.
    differences=[]
    for name,control,header,signed in (('Contrast',0,76,True),('Strength',4,80,False),
            ('Saturation',8,84,True),('Color Tone',12,88,True),
            ('Fineness',24,100,False),('Threshold',28,104,False)):
        observed=state.control[control:control+4]
        candidate=job.carrier[header:header+4]
        if observed!=candidate:
            differences.append(dict(control=name,slotValue=int.from_bytes(observed,'little',signed=signed),
                candidateValue=int.from_bytes(candidate,'little',signed=signed)))
    if differences:
        raise SlotControlMismatch(tuple(differences))
    return sequence


def preflight_registration_sequence(job, observations):
    """Check a complete plan locally; never retain control or authorize replay."""
    sequence = prepare_rp_sequence(job, observations)
    return dict(sequencePlanValidated=True, statePacketBytes=len(sequence.state.data),
        stateProperty=hex(sequence.state.property_code), stateFreshnessEstablished=False,
        physicalAcceptanceEstablished=False, writeAuthorized=False)


def prepare_rp_preflight(raw, keys, *, camera_id, descriptor, slot_style, slot,
                         vendor_operations, device_operations):
    """Select only the archived RP profile plus matching live capabilities.

    The returned packet is an offline candidate, not registration permission,
    fresh115 state, post-write confirmation or physical LUT acceptance.
    """
    if type(camera_id) is not int or camera_id != 0x80000433:
        raise ValueError('Unverified camera event identifier')
    if type(slot) is not int or slot not in (1,2,3):
        raise ValueError('Require selected user slot1..3')
    required = {0x9110,0x9114,0x9115,0x9116,0x911b,0x911c,0x9127}
    for operations in (vendor_operations,device_operations):
        if (type(operations) is not tuple or len(operations)>65535
                or any(type(code) is not int or not 0<=code<=0xffff for code in operations)
                or not required.issubset(operations)):
            raise ValueError('Required profile operations were not advertised')
    if (type(descriptor) is not bytes or len(descriptor)!=15076
            or hashlib.sha256(descriptor).hexdigest()!=RP_DESCRIPTOR_SHA256):
        raise ValueError('Descriptor differs from the verified RP compiler profile')
    normalized,_ = normalize_observed_raw(descriptor,keys)
    inspect_compact16752_style(slot_style,keys)
    fields = read_source_fields(raw,keys)
    if 0x1009 not in fields or fields[0x1009][0]!=3 or len(fields[0x1009][1])!=2:
        raise ValueError('Missing exact source base-style record')
    style = int.from_bytes(fields[0x1009][1],'little')
    plan = compact16752_plan(normalized,style,camera_id,0,7)
    if plan['blockPaths']!=('pixel',)*4 or plan['pixelScale']!=256:
        raise ValueError('Descriptor gates differ from the verified pixel profile')
    # Use the property route proven by this RP's archived and live capabilities.
    job = prepare(raw,keys,route='compact16752-dense-pixel',
        internal_selector=camera_id,normalized_descriptor=normalized,
        handler_selector=0x20+slot,supported_operations=(0x9110,))
    return job, dict(compilerProfileMatched=True,route=job.route,
        sourceSha256=job.source_sha256,carrierSha256=hashlib.sha256(job.carrier).hexdigest(),
        packetSha256=hashlib.sha256(job.send.data).hexdigest(),packetBytes=len(job.send.data),
        opcode=hex(job.send.opcode),slot=slot,descriptorGateWords=list(plan['gateWords']),
        physicalAcceptanceEstablished=False,stateFreshnessEstablished=False)


def load_preflight_source(path, extraction_root):
    """Read an owned PF3 or project before opening a device; recover keys locally."""
    from pathlib import Path
    import canon_engine as engine
    from project_state import load_project
    path = Path(path)
    if path.suffix.lower()=='.canonstyleproject':
        document = load_project(path,extraction_root=extraction_root)
        if not document.renderedPf3:
            raise ValueError('Project has no compiled PF3; save it in the editor first')
        path = Path(document.renderedPf3)
    elif path.suffix.lower()!='.pf3':
        raise ValueError('Require an owned PF3 or single-file style project')
    keys,_ = engine._independent_pf3_input(path)
    raw = path.read_bytes()
    read_source_fields(raw,keys)
    return raw,keys
