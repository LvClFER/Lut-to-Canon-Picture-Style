"""ImageCaptureCore transaction boundary; caller owns the authorized open session.

No discovery, session opening, packet interpretation or retries happen here.
After timeout the caller must terminate its isolated worker: the OS request
cannot be assumed cancelled merely because the local wait ended.
"""
from dataclasses import dataclass,field
from contextlib import contextmanager
import sys
import struct
import threading
import time
from .ptp_wire import Container,Decoder
from .wpd_data_phase_reference import Completion,PtpCommandError


@dataclass(frozen=True)
class NativeReply:
    response:bytes=field(repr=False)
    data:bytes=field(repr=False)


def encode_command(opcode,parameters,transaction):
    if type(opcode) is not int or not 0<=opcode<=0xffff:
        raise ValueError('Invalid PTP opcode')
    if type(transaction) is not int or not 0<=transaction<=0xffffffff:
        raise ValueError('Invalid PTP transaction identifier')
    if type(parameters) is not tuple or len(parameters)>5 or any(
            type(value) is not int or not 0<=value<=0xffffffff for value in parameters):
        raise ValueError('Invalid PTP parameters')
    return Container(1,opcode,transaction,struct.pack('<'+'I'*len(parameters),*parameters)).encode()


def decode_response(response,transaction):
    if not isinstance(response,bytes) or not 12<=len(response)<=32:
        raise ValueError('Invalid PTP response size')
    if type(transaction) is not int or not 0<=transaction<=0xffffffff:
        raise ValueError('Invalid expected PTP transaction')
    decoder=Decoder();items=decoder.feed(response);decoder.finish()
    if len(items)!=1 or items[0].kind!=3 or items[0].transaction!=transaction:
        raise ValueError('PTP response type or transaction does not match')
    item=items[0]
    return Completion(item.code,tuple(value[0] for value in struct.iter_unpack('<I',item.payload)))


def exchange(camera,opcode,parameters,transaction,*,out_data=None,timeout=5.0):
    """Separate command/response containers from unframed native data.

    The encoding follows the PTPPT ImageCaptureCore implementation; a native
    round trip is still required before this path is enabled in the editor.
    """
    command=encode_command(opcode,parameters,transaction)
    reply=send(camera,command,out_data=out_data,timeout=timeout)
    completion=decode_response(reply.response,transaction)
    if completion.response_code!=0x2001:raise PtpCommandError(opcode,completion.response_code)
    return completion,reply.data


class Transactions:
    """One transaction sequence for one owned session, with no native I/O on init."""
    def __init__(self,camera,*,allow_control=False,allow_write=False):
        if type(allow_control) is not bool or type(allow_write) is not bool or (allow_write and not allow_control):
            raise ValueError('Require explicit native control/write policy')
        self.camera=camera;self.next_transaction=1;self.thread=threading.get_ident()
        self.active=False;self.unusable=False
        self.allow_control=allow_control;self.allow_write=allow_write

    def _exchange(self,opcode,parameters,*,out_data=None):
        if self.thread!=threading.get_ident() or self.active or self.unusable:
            raise RuntimeError('PTP transaction owner is unavailable')
        transaction=self.next_transaction
        encode_command(opcode,parameters,transaction)
        self.next_transaction+=1;self.active=True
        try:return exchange(self.camera,opcode,parameters,transaction,out_data=out_data)
        except PtpCommandError:raise
        except BaseException:
            self.unusable=True
            raise
        finally:self.active=False

    def execute(self,opcode,parameters=()):
        if not self.allow_control:raise PermissionError('Native command control is not authorized')
        completion,data=self._exchange(opcode,parameters)
        if data:
            self.unusable=True
            raise ValueError('Unexpected data for a command-only transaction')
        return completion

    def receive_atomic(self,opcode,parameters,*,max_bytes):
        _completion,data=self._exchange(opcode,parameters)
        if len(data)>max_bytes:raise ValueError('Native receive exceeds the controller limit')
        return data

    def transfer_atomic(self,opcode,parameters,payload):
        if not self.allow_write:raise PermissionError('Native data-phase writing is not authorized')
        completion,data=self._exchange(opcode,parameters,out_data=payload)
        if data:
            self.unusable=True
            raise ValueError('Unexpected incoming data for an outgoing transaction')
        return completion.response_code

    def native_profile(self):
        from .connection_profile import Profile
        from .mtp_read_reference import receive
        from .ptp_device_info_reference import decode
        info=decode(receive(self,0x1001))
        return Profile(self,self,self,tuple(code for code in info.operations if code>=0x9000),info)


@contextmanager
def open_selected(fingerprint,*,allow_session=False,allow_control=False,allow_write=False):
    """Resolve, open, own and invalidate one selected native connection."""
    if allow_session is not True:raise ValueError('Explicit session authorization is required')
    if type(allow_control) is not bool or type(allow_write) is not bool or (allow_write and not allow_control):
        raise ValueError('Require explicit native control/write policy')
    from .macos_discovery import selected_camera
    attempted=False
    try:
        with selected_camera(fingerprint) as camera:
            attempted=True
            with authorized_session(camera,allow_session=True):
                owner=Transactions(camera,allow_control=allow_control,allow_write=allow_write)
                try:yield owner
                finally:owner.unusable=True
    except BaseException as error:
        error.device_open_attempted=attempted
        raise


def _session_change(camera,opening,timeout):
    import Foundation as foundation
    outcome=[];active=True
    def completed(error):
        if active and not outcome:outcome.append((error,))
    deadline=time.monotonic()+timeout
    try:
        request=(camera.requestOpenSessionWithOptions_completion_ if opening
            else camera.requestCloseSessionWithOptions_completion_)
        request(None,completed)
        while not outcome:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Session request timed out; terminate the worker')
            foundation.NSRunLoop.currentRunLoop().runUntilDate_(
                foundation.NSDate.dateWithTimeIntervalSinceNow_(min(0.05,remaining)))
        if outcome[0][0] is not None:raise RuntimeError('ImageCaptureCore session request failed')
        if bool(camera.hasOpenSession())!=opening:raise RuntimeError('Session state did not match completion')
    finally:active=False


@contextmanager
def authorized_session(camera,*,allow_session=False,timeout=5.0):
    """Own one explicitly authorized session; never reuse an already-open one."""
    if allow_session is not True:raise ValueError('Explicit session authorization is required')
    if sys.platform!='darwin' or threading.current_thread() is not threading.main_thread():
        raise RuntimeError('Session requires the macOS worker main thread')
    if type(timeout) not in (int,float) or not 0<timeout<=10:raise ValueError('Invalid session deadline')
    if camera.hasOpenSession():raise RuntimeError('Refusing an already-open camera session')
    original=None;timed_out=False
    try:
        _session_change(camera,True,timeout)
        yield camera
    except BaseException as error:
        original=error
        pending=[error];seen=set()
        while pending:
            cause=pending.pop()
            if cause is None or id(cause) in seen:continue
            seen.add(id(cause))
            if isinstance(cause,TimeoutError):timed_out=True;break
            pending.extend((cause.__cause__,cause.__context__))
        raise
    finally:
        # A timed-out open or transaction requires worker termination, not more IPC.
        if not timed_out:
            try:_session_change(camera,False,timeout)
            except Exception:
                if original is None:raise
                original.add_note('ImageCaptureCore session cleanup also failed')
                original.connection_cleanup_completed=False


def send(camera,command,*,out_data=None,timeout=5.0):
    if sys.platform!='darwin':raise RuntimeError('ImageCaptureCore PTP requires macOS')
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('PTP requires the isolated worker main thread')
    if type(timeout) not in (int,float) or not 0<timeout<=10:
        raise ValueError('Invalid PTP deadline')
    if not isinstance(command,bytes) or not 12<=len(command)<=32:
        raise ValueError('Require a bounded encoded PTP command')
    if out_data is not None and (not isinstance(out_data,bytes) or not 0<len(out_data)<=1048576):
        raise ValueError('Invalid outgoing PTP data')
    import Foundation as foundation
    import ImageCaptureCore as capture
    if not camera.hasOpenSession():raise RuntimeError('An authorized open session is required')
    if capture.ICCameraDeviceCanAcceptPTPCommands not in (camera.capabilities() or ()):
        raise RuntimeError('Camera does not advertise PTP commands')
    outcome=[];active=True
    def completed(response,data,error):
        if not active or outcome:return
        if error is not None:
            outcome.append(RuntimeError('ImageCaptureCore PTP transaction failed'));return
        if response is None or data is None:
            outcome.append(ValueError('ImageCaptureCore omitted response or data'));return
        try:
            response_view=memoryview(response);data_view=memoryview(data)
            if not 12<=response_view.nbytes<=32 or data_view.nbytes>16*1024*1024:
                raise ValueError('ImageCaptureCore reply exceeds PTP bounds')
            outcome.append(NativeReply(bytes(response_view),bytes(data_view)))
        except (TypeError,ValueError,BufferError):
            outcome.append(ValueError('ImageCaptureCore returned invalid PTP buffers'))
    deadline=time.monotonic()+timeout
    try:
        camera.requestSendPTPCommand_outData_completion_(command,out_data,completed)
        while not outcome:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('PTP request timed out; terminate the session worker')
            foundation.NSRunLoop.currentRunLoop().runUntilDate_(
                foundation.NSDate.dateWithTimeIntervalSinceNow_(min(0.05,remaining)))
        if isinstance(outcome[0],Exception):raise outcome[0]
        return outcome[0]
    finally:active=False
