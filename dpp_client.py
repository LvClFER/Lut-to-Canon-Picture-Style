from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path

from PIL import Image


class DppBackendError(RuntimeError):
    pass


class DppBackendClient:
    """Serialized client for the isolated persistent Canon DPP4Lib worker."""

    def __init__(self, worker_path: Path, cache_dir: Path, env_overrides=None):
        self.worker_path = Path(worker_path).resolve()
        self.cache_dir = Path(cache_dir).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.proc = None
        self.log_handle = None
        self.lock = threading.RLock()
        self.seq = 0
        self.ready_info = None
        self.memory_cache = OrderedDict()
        self._inflight_cmd = None
        self._inflight_proc = None
        self._cancelled_proc = None
        self.env_overrides = dict(env_overrides or {})

    def _log_path(self):
        return self.cache_dir / "dpp_worker_stderr.log"

    def _start(self):
        if self.proc is not None and self.proc.poll() is None:
            return
        self.close(force=True)
        self.log_handle = self._log_path().open("a", encoding="utf-8", errors="replace")
        frozen_worker=self.worker_path.suffix.lower()==".exe"
        command=[str(self.worker_path)] if frozen_worker else [sys.executable,"-u",str(self.worker_path)]
        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.log_handle,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=str(self.worker_path.parent),
            env={**os.environ, **self.env_overrides},
            creationflags=creationflags,
        )
        line = self.proc.stdout.readline()
        if not line:
            rc = self.proc.poll()
            self.close(force=True)
            raise DppBackendError(f"Canon worker did not start (exit {rc}). See {self._log_path()}")
        try:
            msg = json.loads(line)
        except Exception as e:
            self.close(force=True)
            raise DppBackendError(f"Invalid Canon worker startup response: {line[:300]!r}") from e
        if not msg.get("ok"):
            self.ready_info = msg
            err = msg.get("error") or "Canon DPP4Lib worker failed to initialize."
            self.close(force=True)
            raise DppBackendError(err)
        self.ready_info = msg

    def _request_once(self, payload):
        self._start()
        self.seq += 1
        rid = self.seq
        req = dict(payload)
        req["id"] = rid
        request_proc=self.proc
        self._inflight_cmd = req.get("cmd")
        self._inflight_proc = self.proc
        try:
            self.proc.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
            line = self.proc.stdout.readline()
        except Exception as e:
            raise DppBackendError(f"Canon worker IPC failed: {e}") from e
        finally:
            self._inflight_cmd = None
            self._inflight_proc = None
        if not line:
            rc = self.proc.poll()
            if self._cancelled_proc is request_proc:
                self._cancelled_proc=None
                raise DppBackendError("Canon render cancelled")
            raise DppBackendError(f"Canon worker exited unexpectedly (exit {rc}). See {self._log_path()}")
        if self._cancelled_proc is request_proc:self._cancelled_proc=None
        try:
            resp = json.loads(line)
        except Exception as e:
            raise DppBackendError(f"Invalid Canon worker response: {line[:300]!r}") from e
        if resp.get("id") != rid:
            raise DppBackendError("Canon worker response ID mismatch.")
        if not resp.get("ok"):
            raise DppBackendError(resp.get("error") or "Canon DPP4Lib render failed.")
        return resp

    def request(self, payload, retry=True):
        with self.lock:
            try:
                return self._request_once(payload)
            except Exception:
                if not retry:
                    raise
                self.close(force=True)
                return self._request_once(payload)

    def probe(self):
        return self.request({"cmd": "ping"})

    def render(self, raw_path, settings, width=1620, height=1080):
        raw_path = Path(raw_path).resolve()
        stat = raw_path.stat()
        cache_payload = {
            "path": str(raw_path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            # v8 also invalidates previews created before the validated
            # Saturation/Color Tone DPP property mapping correction.
            "settings": settings, "width": int(width), "height": int(height),
            "runtime": self.env_overrides, "cache_version": 8,
        }
        key = hashlib.sha256(json.dumps(cache_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        out = self.cache_dir / f"render_{key}.rgb"
        if key in self.memory_cache:
            cached=self.memory_cache.pop(key);self.memory_cache[key]=cached
            return cached.copy(), {
                "ok":True,"cached":True,"memory_cached":True,
                "dpp4lib":(self.ready_info or {}).get("dpp4lib","Canon DPP4Lib"),
            }
        if out.exists():
            try:
                data=out.read_bytes();expected=int(width)*int(height)*3
                if len(data)!=expected:raise ValueError(f"RGB cache size {len(data)} != {expected}")
                result=Image.frombytes("RGB",(int(width),int(height)),data)
                self._remember(key,result)
                return result.copy(), {
                    "ok": True, "cached": True,
                    "dpp4lib": (self.ready_info or {}).get("dpp4lib", "Canon DPP4Lib"),
                }
            except Exception:
                out.unlink(missing_ok=True)
        # A render error returned by DppCore (for example 0x60 for an unsupported
        # stream geometry) is deterministic. Retrying the same request only doubles
        # latency and cannot recover it; process startup/probe still retain retry.
        resp = self.request({
            "cmd": "render",
            "path": str(raw_path),
            "settings": settings,
            "width": int(width),
            "height": int(height),
            "output": str(out),
        }, retry=False)
        data=out.read_bytes();expected=int(width)*int(height)*3
        if len(data)!=expected:
            out.unlink(missing_ok=True)
            raise DppBackendError(f"Canon RGB output size {len(data)} != {expected}")
        result=Image.frombytes("RGB",(int(width),int(height)),data)
        self._remember(key,result)
        # Keep a rolling disk cache for crash diagnostics and repeated settings,
        # bounded by both item count and total bytes now that zoom can request full
        # 20–30 MP Canon frames.
        try:
            files = sorted(self.cache_dir.glob("render_*.rgb"), key=lambda p: p.stat().st_mtime, reverse=True)
            total=0
            for index,old in enumerate(files):
                total+=old.stat().st_size
                if index>=24 or total>1_000_000_000:
                    old.unlink(missing_ok=True)
        except Exception:
            pass
        return result, resp

    def _remember(self,key,image):
        self.memory_cache[key]=image.copy()
        self.memory_cache.move_to_end(key)
        # Six working previews are cheap, but six native EOS frames are not. Keep
        # roughly one native frame plus several working frames (about 108 MB RGB).
        while len(self.memory_cache)>1 and (
            len(self.memory_cache)>6 or
            sum(im.width*im.height for im in self.memory_cache.values())>36_000_000
        ):
            self.memory_cache.popitem(last=False)

    def cancel_active_render(self):
        """Terminate an obsolete isolated DPP render without touching an idle worker."""
        if self._inflight_cmd!="render":return False
        proc=self._inflight_proc
        if proc is None or proc.poll() is not None:return False
        try:
            self._cancelled_proc=proc
            proc.terminate()
            try:
                proc.wait(timeout=0.25)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait(timeout=0.25)
            return True
        except Exception:
            return False

    def close_raw(self):
        with self.lock:
            if self.proc is not None and self.proc.poll() is None:
                try:
                    self._request_once({"cmd": "close_raw"})
                except Exception:
                    pass

    def close(self, force=False):
        with self.lock:
            p = self.proc
            self.proc = None
            if p is not None:
                if not force and p.poll() is None:
                    try:
                        self.seq += 1
                        rid = self.seq
                        p.stdin.write(json.dumps({"id": rid, "cmd": "shutdown"}) + "\n")
                        p.stdin.flush()
                        p.stdout.readline()
                        p.wait(timeout=2)
                    except Exception:
                        force = True
                if force and p.poll() is None:
                    try:
                        p.terminate()
                        p.wait(timeout=1)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
                for stream in (p.stdin, p.stdout):
                    try:
                        if stream is not None: stream.close()
                    except Exception:
                        pass
            if self.log_handle is not None:
                try:
                    self.log_handle.close()
                except Exception:
                    pass
                self.log_handle = None

    def __del__(self):
        try:
            self.close(force=True)
        except Exception:
            pass
