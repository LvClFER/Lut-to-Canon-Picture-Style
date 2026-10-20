"""Bounded remote/event lifecycle over injected adapters; no device opening.

This is an experimental integration policy, not a full registration session.
Completed startup events can be retained by a camera and do not prove fresh115.
Caller owns the already-open device, apartment and operation authorization.
"""
from .event_mode_plan_reference import EventModePlan
from .canon_event_receive_reference import CompletedEvents, drain
from .session_inputs_reference import collect_inputs, SlotObservation
from .compiler_input_events_reference import descriptor_from_d17f
from .d170_decode_reference import decode_701d0


class RemoteEventSession:
    def __init__(self, commands, reader, plan):
        if (not isinstance(plan, EventModePlan)
                or type(plan.remote_mode) is not int or plan.remote_mode not in (1, 5, 17, 21, 65)
                or type(plan.event_mode) is not int or plan.event_mode not in (1, 2)
                or plan.commands != ((0x9114, (plan.remote_mode,)),
                                     (0x9115, (plan.event_mode,)))):
            raise ValueError('Require exact supported remote/event mode plan')
        self._commands, self._reader, self._plan = commands, reader, plan
        self._used = False
        self._attempted = []
        self.startup_events = None
        self.observed_inputs = None
        self._slot_transition = None
        self._updated_slot_seen = False

    def _shutdown(self):
        errors = []
        while self._attempted:
            opcode = self._attempted.pop()
            try:
                self._commands.execute(opcode, (0,))
            except Exception as error:
                errors.append(error)
        return errors

    def __enter__(self):
        if self._used:
            raise RuntimeError('Remote/event session is single-use')
        self._used = True
        try:
            for opcode, parameters in self._plan.commands:
                # A failed response may follow an applied command. Attempt
                # cleanup even when success could not be established.
                self._attempted.append(opcode)
                self._commands.execute(opcode, parameters)
            self.startup_events = drain(self._reader)
            self.observed_inputs = collect_inputs(self.startup_events)
            self._input_events = self.startup_events
            return self
        except BaseException as original:
            errors = self._shutdown()
            original.temporary_modes_cleanup_completed=not errors
            if errors:
                original.add_note(f'Remote/event cleanup also failed: {len(errors)} stage(s)')
            raise

    def __exit__(self, kind, error, traceback):
        errors = self._shutdown()
        if error is not None:error.temporary_modes_cleanup_completed=not errors
        if errors:
            if error is not None:
                error.add_note(f'Remote/event cleanup also failed: {len(errors)} stage(s)')
            else:
                raise RuntimeError('Remote/event cleanup incomplete') from errors[0]
        return False

    def request_descriptor(self):
        """Request D17F and await at most six completed drains, without a cache.

        Receipt after the request does not establish registration-state freshness.
        Caller must establish advertised9127 support and authorize this query.
        """
        return descriptor_from_d17f(self._request_property(0xd17f))

    def request_slot_style(self, handler_selector):
        """Observed D170..172 event conversion, not a9189/freshness substitute."""
        if type(handler_selector) is not int or handler_selector not in (0x21, 0x22, 0x23):
            raise ValueError('Require explicit user-slot handler21..23')
        return decode_701d0(self._request_property(handler_selector + 0xd14f))

    def request_registered_slot_style(self, before, after):
        """After acknowledged writes, require the intended state event and style.

        Caller owns the write/permission barrier. No directed D160..165 query,
        cached-state confirmation, implicit selector change or retry is used.
        """
        if (not isinstance(before,SlotObservation) or not isinstance(after,SlotObservation)
                or self.observed_inputs is None or before not in self.observed_inputs.slots
                or before==after or before.handler_selector!=after.handler_selector
                or before.marker!=after.marker or before.selector!=after.selector
                or type(after.control) is not bytes or len(before.control)!=len(after.control)
                or len(self._attempted)!=2 or self._slot_transition is not None):
            raise ValueError('Require one explicit live selected-slot control transition')
        codes={before.handler_selector+0xd13f,before.handler_selector+0xd142}
        self._slot_transition=(before,after);self._updated_slot_seen=False
        try:
            self._input_events=CompletedEvents(tuple(e for e in self._input_events.properties
                if e.property_code not in codes),self._input_events.batch_count,self._input_events.received_bytes)
            self.observed_inputs=collect_inputs(self._input_events)
            style=self.request_slot_style(before.handler_selector)
            for _ in range(6):
                if self._updated_slot_seen:return style
                observed=drain(self._reader)
                for event in observed.properties:
                    if (event.property_code==before.handler_selector+0xd14f
                            and decode_701d0(event.value)!=style):
                        raise ValueError('Registered style changed while confirming Basic controls')
                self._observe(observed)
            if self._updated_slot_seen:return style
            raise RuntimeError('Expected slot Basic controls were not observed after writing')
        finally:
            self._slot_transition=None;self._updated_slot_seen=False

    def _observe(self, observed):
        properties=observed.properties
        if self._slot_transition is not None:
            before,after=self._slot_transition;retained=[]
            codes={before.handler_selector+0xd13f,before.handler_selector+0xd142}
            for event in properties:
                if event.property_code not in codes:
                    retained.append(event);continue
                state=collect_inputs(CompletedEvents((event,),1,len(event.value)+20)).slots[0]
                if state==before and not self._updated_slot_seen:continue
                if state!=after:
                    raise ValueError('Unexpected selected-slot state after registration')
                self._updated_slot_seen=True;retained.append(event)
            properties=tuple(retained)
        combined=CompletedEvents(self._input_events.properties+properties,
            self._input_events.batch_count+observed.batch_count,
            self._input_events.received_bytes+observed.received_bytes)
        inputs=collect_inputs(combined)
        self._input_events,self.observed_inputs=combined,inputs

    def _request_property(self, code):
        if len(self._attempted) != 2 or self.startup_events is None:
            raise RuntimeError('Property request requires an active remote/event session')
        self._commands.execute(0x9127, (code,))
        for _ in range(6):
            observed = drain(self._reader)
            values = {event.value for event in observed.properties if event.property_code == code}
            if len(values) > 1:
                raise ValueError('Contradictory requested property observations')
            # Never silently keep startup state when later completed reads disagree.
            self._observe(observed)
            if values:
                return values.pop()
        raise RuntimeError('Requested property was absent from six completed event drains')
