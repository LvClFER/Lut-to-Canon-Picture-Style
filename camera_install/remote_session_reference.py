"""Bounded remote/event lifecycle over injected adapters; no device opening.

This is an experimental integration policy, not a full registration session.
Completed startup events can be retained by a camera and do not prove fresh115.
Caller owns the already-open device, apartment and operation authorization.
"""
from .event_mode_plan_reference import EventModePlan
from .canon_event_receive_reference import drain
from .session_inputs_reference import collect_inputs


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
            return self
        except BaseException as original:
            errors = self._shutdown()
            if errors:
                original.add_note(f'Remote/event cleanup also failed: {len(errors)} stage(s)')
            raise

    def __exit__(self, kind, error, traceback):
        errors = self._shutdown()
        if errors:
            if error is not None:
                error.add_note(f'Remote/event cleanup also failed: {len(errors)} stage(s)')
            else:
                raise RuntimeError('Remote/event cleanup incomplete') from errors[0]
        return False
