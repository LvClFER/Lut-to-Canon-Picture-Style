
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess, threading, queue, time, json, hashlib, os, sys, unicodedata

try:
    import frida
except Exception:
    frida=None

HERE=Path(__file__).resolve().parent
if getattr(sys,"frozen",False):
    RESOURCE_ROOT=Path(getattr(sys,"_MEIPASS",Path(sys.executable).resolve().parent))
    APP_ROOT=Path(sys.executable).resolve().parent
    TOOL_ROOT=RESOURCE_ROOT/"TOOLS"
else:
    RESOURCE_ROOT=HERE.parent
    APP_ROOT=RESOURCE_ROOT
    TOOL_ROOT=HERE

# Direct import: compiled builds no longer try to launch the EXE as a Python interpreter.
from build_lut_pf3 import build_pf3_from_source
from recipe_lut import (
    DEFAULT_RECIPE, normalize_recipe_settings,
    recipe_is_neutral, recipe_summary,
)

AGENT=(TOOL_ROOT/"rp_loader_agent.js").read_text(encoding="utf-8")
CAMID=(RESOURCE_ROOT/"REFERENCE"/"1300D_CAMERA_ID.bin").read_bytes()
DESC=(RESOURCE_ROOT/"REFERENCE"/"1300D_DESCRIPTOR_7772.bin").read_bytes()
SELFTEST_PF3=RESOURCE_ROOT/"SELFTEST"/"SUPERIA_SELFTEST.pf3"
SELFTEST_BLOCK=(RESOURCE_ROOT/"SELFTEST"/"SUPERIA_EXPECTED_BLOCK_8192.bin").read_bytes()
RP_TEMPLATE=(RESOURCE_ROOT/"REFERENCE"/"RP_SUPERIA_TEMPLATE_16752.bin").read_bytes()
OUT=APP_ROOT/"OUTPUT"
WORK=APP_ROOT/"WORK"

def sha(b):return hashlib.sha256(b).hexdigest()

def _fixed_ascii32(value):
    out=bytearray(32)
    raw=canon_style_name(value).encode("ascii","replace")[:31]
    out[:len(raw)]=raw
    return bytes(out)

def build_rp_payload(block1, style_name):
    if len(RP_TEMPLATE)!=16752:
        raise RuntimeError(f"RP carrier interno inválido: {len(RP_TEMPLATE)} bytes")
    if len(block1)!=8192:
        raise RuntimeError(f"Block1 inválido: {len(block1)} bytes")
    out=bytearray(RP_TEMPLATE)
    out[368:368+8192]=block1
    name=_fixed_ascii32(style_name)
    out[8:40]=name
    out[44:76]=name
    if b"TWILIGHT" in out:
        raise RuntimeError("Falha ao corrigir o nome: TWILIGHT ainda existe no payload final.")
    return bytes(out)

def canon_style_name(value, fallback="Picture Style"):
    s=(value or fallback or "Picture Style").strip()
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode("ascii")
    return (s.strip() or fallback or "Picture Style")[:31]

class App:
    def __init__(self,root):
        self.root=root
        root.title("Canon EOS RP — Manual LUT Loader v2.3")
        root.geometry("940x700")
        root.minsize(860,650)

        self.q=queue.Queue()
        self.device=frida.get_local_device() if frida else None
        self.sessions={}
        self.scripts={}
        self.ready_evt=threading.Event()
        self.running=True
        self.selected=None
        self.current_pf3=None
        self.current_block=None
        self.slot=tk.IntVar(value=1)
        self.style_name=tk.StringVar(value="")
        self.install_done=False
        self.current_payload=None
        self.install_report=None
        self.pending_recipe=None
        self.pending_style_name=None

        # Only controls that are really encoded in the LUT/Picture Style.
        self.recipe_highlight=tk.IntVar(value=0)
        self.recipe_shadow=tk.IntVar(value=0)
        self.recipe_color=tk.IntVar(value=0)
        self.recipe_chrome=tk.StringVar(value="Off")
        self.recipe_blue=tk.StringVar(value="Off")

        f=tk.Frame(root,padx=24,pady=20);f.pack(fill="both",expand=True)
        tk.Label(f,text="Canon EOS RP — Manual LUT Loader",font=("Segoe UI",19,"bold")).pack(anchor="w")
        tk.Label(f,text="Gera/compila o Picture Style; o último registo no EOS Utility é manual e previsível.",
                 font=("Segoe UI",10)).pack(anchor="w",pady=(3,18))

        choose=tk.Frame(f);choose.pack(fill="x")
        self.file_lbl=tk.Label(choose,text="Nenhum ficheiro selecionado",anchor="w",relief="sunken",padx=8,pady=8)
        self.file_lbl.pack(side="left",fill="x",expand=True)
        tk.Button(choose,text="Escolher .cube / .tiff / .pf3",command=self.choose_file,padx=12,pady=7).pack(side="left",padx=(8,0))

        namef=tk.LabelFrame(f,text="Nome do Picture Style",padx=10,pady=7)
        namef.pack(fill="x",pady=(16,0))
        tk.Entry(namef,textvariable=self.style_name,font=("Segoe UI",10)).pack(fill="x")
        tk.Label(
            namef,
            text="Preenchido automaticamente a partir do nome do .cube/.pf3. Podes editar antes de gerar.",
            font=("Segoe UI",9)
        ).pack(anchor="w",pady=(4,0))

        slotf=tk.LabelFrame(f,text="User Def. na EOS RP",padx=10,pady=7)
        slotf.pack(fill="x",pady=(18,0))
        for i in (1,2,3):
            tk.Radiobutton(slotf,text=f"User Def. {i}",variable=self.slot,value=i).pack(side="left",padx=(2,20))

        recipef=tk.LabelFrame(f,text="LUT adjustments — optional",padx=10,pady=8)
        recipef.pack(fill="x",pady=(12,0))

        top=tk.Frame(recipef);top.pack(fill="x")
        tk.Button(top,text="Carregar ajustes…",command=self.load_adjustment_preset,padx=9).pack(side="left")
        tk.Button(top,text="Guardar ajustes…",command=self.save_adjustment_preset,padx=9).pack(side="left",padx=(6,0))
        tk.Button(top,text="Repor",command=self.reset_recipe,padx=9).pack(side="left",padx=(6,0))
        tk.Label(
            top,
            text="Aplicados a qualquer LUT antes da conversão para Canon 33³.",
            font=("Segoe UI",9)
        ).pack(side="right")

        grid=tk.Frame(recipef);grid.pack(fill="x",pady=(8,0))

        def add_opt(col,label,var,values,width=9):
            tk.Label(grid,text=label,font=("Segoe UI",9)).grid(row=0,column=col,sticky="w",padx=(0,7))
            om=tk.OptionMenu(grid,var,*values);om.config(width=width)
            om.grid(row=1,column=col,sticky="w",padx=(0,14))

        def add_spin(col,label,var,frm,to,width=5):
            tk.Label(grid,text=label,font=("Segoe UI",9)).grid(row=0,column=col,sticky="w",padx=(0,7))
            tk.Spinbox(grid,from_=frm,to=to,textvariable=var,width=width).grid(row=1,column=col,sticky="w",padx=(0,14))

        add_spin(0,"Highlight",self.recipe_highlight,-2,4)
        add_spin(1,"Shadow",self.recipe_shadow,-2,4)
        add_spin(2,"Color",self.recipe_color,-4,4)
        add_opt(3,"Color Chrome-style",self.recipe_chrome,("Off","Weak","Strong"),11)
        add_opt(4,"Blue Chrome-style",self.recipe_blue,("Off","Weak","Strong"),11)

        tk.Label(
            recipef,
            text="Estes controlos são independentes do LUT de origem. "
                 "Ajustes que não podem ser codificados num RGB→RGB 3D LUT não aparecem aqui.",
            font=("Segoe UI",9),anchor="w",justify="left",wraplength=850
        ).pack(fill="x",pady=(7,0))

        self.big=tk.Label(f,text="1. Escolhe .cube, Hald .tiff ou .pf3",font=("Segoe UI",15,"bold"),
                          anchor="w",justify="left",wraplength=880)
        self.big.pack(fill="x",pady=(22,8))
        self.sub=tk.Label(f,text="",font=("Segoe UI",10),anchor="w",justify="left",wraplength=880)
        self.sub.pack(fill="x")

        row=tk.Frame(f);row.pack(fill="x",pady=(18,6))
        self.main=tk.Button(row,text="Gerar PF3",state="disabled",command=self.main_action,
                            font=("Segoe UI",11,"bold"),padx=18,pady=9)
        self.main.pack(side="left")
        self.open=tk.Button(row,text="Abrir pasta",state="disabled",command=self.open_current,padx=12,pady=9)
        self.open.pack(side="left",padx=(8,0))

        self.state=tk.Label(f,text="",font=("Segoe UI",10),anchor="w")
        self.state.pack(fill="x",pady=(15,5))

        self.details=tk.Text(f,height=8,state="disabled",font=("Consolas",9))
        self.details.pack(fill="both",expand=True)
        self.log("Detalhes técnicos (não precisas de os interpretar).")

        self.root.protocol("WM_DELETE_WINDOW",self.close)
        self.root.after(100,self.poll)

        if len(sys.argv)>1 and Path(sys.argv[1]).exists():
            self.set_selected(Path(sys.argv[1]))

    def log(self,s):
        self.details.config(state="normal")
        self.details.insert("end",str(s).rstrip()+"\n")
        self.details.see("end")
        self.details.config(state="disabled")

    def get_recipe_settings(self):
        return normalize_recipe_settings({
            "highlight":self.recipe_highlight.get(),
            "shadow":self.recipe_shadow.get(),
            "color":self.recipe_color.get(),
            "color_chrome":self.recipe_chrome.get(),
            "color_chrome_fx_blue":self.recipe_blue.get(),
        })

    def set_recipe_settings(self,settings):
        s=normalize_recipe_settings(settings)
        self.recipe_highlight.set(s["highlight"])
        self.recipe_shadow.set(s["shadow"])
        self.recipe_color.set(s["color"])
        self.recipe_chrome.set(s["color_chrome"])
        self.recipe_blue.set(s["color_chrome_fx_blue"])

    def reset_recipe(self):
        self.set_recipe_settings(DEFAULT_RECIPE)
        self.log("LUT adjustments: reset / neutral.")

    def save_adjustment_preset(self):
        p=filedialog.asksaveasfilename(
            title="Guardar ajustes LUT",
            defaultextension=".json",
            filetypes=[("LUT adjustment preset","*.json"),("Todos","*.*")]
        )
        if not p:
            return
        data={
            "format":"canon-rp-lut-adjustments",
            "version":1,
            "adjustments":self.get_recipe_settings()
        }
        Path(p).write_text(json.dumps(data,indent=2),encoding="utf-8")
        self.log(f"Ajustes guardados: {Path(p).name}")

    def load_adjustment_preset(self):
        p=filedialog.askopenfilename(
            title="Carregar ajustes LUT",
            filetypes=[("LUT adjustment preset","*.json"),("Todos","*.*")]
        )
        if not p:
            return
        try:
            data=json.loads(Path(p).read_text(encoding="utf-8"))
            settings=data.get("adjustments",data)
            self.set_recipe_settings(settings)
            self.log(f"Ajustes carregados: {Path(p).name} · {recipe_summary(self.get_recipe_settings())}")
        except Exception as e:
            messagebox.showerror("Ajustes inválidos",str(e))

    def choose_file(self):
        p=filedialog.askopenfilename(
            title="Escolher LUT ou PF3",
            filetypes=[
                ("LUT / Hald / Picture Style","*.cube *.tif *.tiff *.pf3"),
                ("3D LUT","*.cube"),
                ("Hald CLUT TIFF","*.tif *.tiff"),
                ("Canon PF3","*.pf3"),
                ("Todos","*.*")
            ]
        )
        if p:self.set_selected(Path(p))

    def set_selected(self,p):
        self.selected=Path(p).resolve()
        self.file_lbl.config(text=str(self.selected))
        self.style_name.set(self.selected.stem[:31])

        # IMPORTANT: after an install the button becomes "Escolher outra LUT".
        # A newly selected file must restore the normal Generate/Install action.
        self.main.config(command=self.main_action)
        self.open.config(state="disabled")
        self.install_done=False

        ext=self.selected.suffix.lower()
        if ext in (".cube",".tif",".tiff"):
            self.current_pf3=None
        if ext==".cube":
            self.big.config(text="Pronto para gerar o PF3")
            self.sub.config(text="O .cube será convertido para Canon 33×33×33. Os ajustes opcionais acima são compostos numa única LUT antes do PF3.")
            self.main.config(text="Gerar PF3",state="normal")
        elif ext in (".tif",".tiff"):
            self.big.config(text="Hald CLUT TIFF selecionado")
            self.sub.config(
                text="O TIFF é lido diretamente como Hald CLUT e convertido para o PF3. "
                     "Não é criado nenhum .cube intermédio. "
                     "Ex.: Hald level 8 = 512×512 = LUT 64³."
            )
            self.main.config(text="Gerar PF3",state="normal")
        elif ext==".pf3":
            self.current_pf3=self.selected
            self.big.config(text="PF3 selecionado")
            self.sub.config(text="Posso compilar este PF3, montar o payload RP e preparar o registo manual no EOS Utility. Nota: estes ajustes são aplicados durante a geração a partir de .cube/.tiff; não alteram um PF3 já existente.")
            self.main.config(text="Preparar instalação manual",state="normal")
            self.open.config(state="normal")
        else:
            messagebox.showerror("Ficheiro inválido","Escolhe um .cube, um Hald .tif/.tiff ou um .pf3.")

    def main_action(self):
        self.main.config(state="disabled")
        if self.selected.suffix.lower() in (".cube",".tif",".tiff"):
            # Snapshot Tk values on the UI thread before the worker starts.
            self.pending_recipe=self.get_recipe_settings()
            self.pending_style_name=canon_style_name(self.style_name.get(),self.selected.stem)
            threading.Thread(target=self.build_pf3,daemon=True).start()
        else:
            threading.Thread(target=self.prepare_install,daemon=True).start()

    def build_pf3(self):
        try:
            self.q.put(("ui",("status","A gerar PF3 com a LUT completa… (sem ficheiro .cube intermédio para TIFF)")))
            requested_name=self.pending_style_name or canon_style_name(self.style_name.get(),self.selected.stem)
            logs=[]
            recipe=self.pending_recipe or self.get_recipe_settings()
            OUT.mkdir(parents=True,exist_ok=True)
            baked_cube_path=OUT/(self.selected.stem+"_ADJUSTED.cube") if not recipe_is_neutral(recipe) else None
            built, build_meta, actual_name = build_pf3_from_source(
                self.selected, requested_name, work_dir=WORK, log=lambda s: logs.append(str(s)),
                recipe_settings=recipe, baked_cube_output=baked_cube_path
            )
            self.style_name.set(actual_name)
            if logs:
                self.q.put(("log","\n".join(logs)))
            OUT.mkdir(parents=True,exist_ok=True)
            # Keep the generated filename aligned with the source LUT name.
            # The RP-specific behavior is handled by the loader, so "_RP" is unnecessary noise.
            dest=OUT/(self.selected.stem+".pf3")
            data=built.read_bytes();dest.write_bytes(data)
            self.current_pf3=dest
            meta={
                "source":str(self.selected),
                "sourceType":"hald_tiff" if self.selected.suffix.lower() in (".tif",".tiff") else "cube",
                "sourceSha256":sha(self.selected.read_bytes()),
                "pf3":dest.name,
                "pf3Sha256":sha(data),
                "pictureStyleName":requested_name,
                "recipe":recipe,
                "recipeSummary":recipe_summary(recipe),
                "bakedCube":str(baked_cube_path) if baked_cube_path else None,
                "note":"Contains full dense LUT in 0x40001070/71. Install with this package's RP loader."
            }
            (OUT/(self.selected.stem+"_RP.json")).write_text(json.dumps(meta,indent=2),encoding="utf-8")
            self.q.put(("ui",("built",str(dest))))
        except Exception as e:
            self.q.put(("error",repr(e)))

    def find_eos_exe(self):
        candidates=[
            Path(os.environ.get("ProgramFiles(x86)",""))/"Canon/EOS Utility/EU3/EOS Utility 3.exe",
            Path(os.environ.get("ProgramFiles",""))/"Canon/EOS Utility/EU3/EOS Utility 3.exe",
        ]
        for p in candidates:
            if str(p) and p.exists():return p
        return None

    def start_eos_if_needed(self):
        # We only launch it if the standard path exists and no suitable process is present.
        try:
            procs=self.device.enumerate_processes()
            if any("eos utility 3" in p.name.lower() for p in procs):
                return
        except Exception:
            pass
        exe=self.find_eos_exe()
        if exe:
            try:
                subprocess.Popen([str(exe)])
                self.q.put(("log","EOS Utility iniciado automaticamente."))
            except Exception:
                pass

    def candidate(self,p):
        n=(p.name or "").lower()
        return "eos utility 3" in n or n=="eos utility 3.exe"

    def onmsg(self,pid,name,message,data):
        if message.get("type")!="send":
            if message.get("type")=="error":
                self.q.put(("log","FRIDA ERROR: "+str(message)))
            return

        e=dict(message.get("payload") or {})
        raw=bytes(data) if data else b""
        typ=e.get("type")

        if self.install_report is not None:
            ev=dict(e)
            if raw:
                ev["binarySize"]=len(raw)
                ev["binarySha256"]=sha(raw)
            self.install_report.setdefault("events",[]).append(ev)

        if typ=="ready":
            self.q.put(("log",f"EOS Utility monitorizado (PID {pid})."))
            self.ready_evt.set()
        elif typ=="armed":
            self.q.put(("log",f"Instalação armada para User Def. {e.get('slot')} · nome: {e.get('styleName')}."))
        elif typ=="registration_seen":
            self.q.put(("log",f"Registo detetado: User Def. {e.get('slot')} ({e.get('size')} bytes)."))
        elif typ=="payload_patched":
            self.q.put(("log",f"Payload RP 16752 substituído · nome interno: {e.get('styleName')}."))
            if raw and self.install_report is not None:
                self.install_report["actualOutgoingPayloadSha256"]=sha(raw)
        elif typ=="registration_return":
            self.q.put(("log",f"EOS Utility escreveu 0x01000203: rc={e.get('rc')} patched={e.get('patched')}."))
        elif typ=="control115_seen":
            self.q.put(("log",f"0x00000115 observado ({e.get('size')} bytes) e deixado INTACTO."))
        elif typ=="install_success":
            self.install_done=True
            if self.install_report is not None:
                self.install_report["status"]="SUCCESS"
                self.install_report["completedAt"]=datetime.now().isoformat()
                try:
                    report_path=Path(self.install_report["reportPath"])
                    report_path.write_text(json.dumps(self.install_report,indent=2,ensure_ascii=False),encoding="utf-8")
                except Exception:
                    pass
            self.q.put(("ui",("installed",e.get("slot"))))
        elif typ=="install_error":
            self.q.put(("error","Erro durante a instalação: "+str(e.get("reason"))))
        elif typ=="hook_error":
            self.q.put(("error","Erro no hook EOS Utility: "+str(e.get("error"))))

    def attach(self,p):
        if p.pid in self.sessions:return
        try:
            s=self.device.attach(p.pid)
            sc=s.create_script(AGENT)
            sc.on("message",lambda m,d,pid=p.pid,name=p.name:self.onmsg(pid,name,m,d))
            sc.load()
            self.sessions[p.pid]=s;self.scripts[p.pid]=sc
        except Exception:
            pass

    def scanner(self):
        while self.running and not self.ready_evt.is_set():
            try:
                for p in self.device.enumerate_processes():
                    if self.candidate(p):self.attach(p)
            except Exception:pass
            time.sleep(.15)

    def rpc_compile(self,sc,path):
        r=sc.exports_sync.compile(str(path),CAMID.hex(),DESC.hex())
        if not isinstance(r,(list,tuple)) or len(r)!=2:
            raise RuntimeError("Resposta binária inesperada do Frida.")
        meta,data=r
        return dict(meta or {}),bytes(data or b"")

    def get_live_script(self):
        # A live session can still be reused, but v2.2 recommends closing/reopening EOS Utility between presets because repeated registration state is less reliable.
        for pid,sc in list(self.scripts.items()):
            try:
                st=sc.exports_sync.status()
                if st and st.get("ready"):
                    return sc
            except Exception:
                try:self.scripts.pop(pid,None)
                except Exception:pass
                sess=self.sessions.pop(pid,None)
                if sess:
                    try:sess.detach()
                    except Exception:pass
        return None

    def prepare_install(self):
        try:
            if frida is None:
                self.q.put(("error","Frida não está instalado. Executa START_HERE.bat para instalar dependências."))
                return
            if not self.current_pf3 or not Path(self.current_pf3).exists():
                self.q.put(("error","Não existe PF3 preparado para instalar."))
                return

            self.install_done=False
            self.current_payload=None
            sc=self.get_live_script()

            if sc is None:
                self.ready_evt.clear()
                self.start_eos_if_needed()
                threading.Thread(target=self.scanner,daemon=True).start()
                self.q.put(("ui",("status","Liga a EOS RP e deixa o EOS Utility aberto. A detetar o compiler Canon…")))

                if not self.ready_evt.wait(35):
                    self.q.put(("error","Não encontrei o EOS Utility 3 com EdsCFParse/EDSDK carregados. Liga a RP e abre o EOS Utility."))
                    return
                sc=self.get_live_script()
            else:
                self.ready_evt.set()
                self.q.put(("log","A reutilizar a sessão EOS Utility já ativa. Nota: entre presets, fechar/reabrir EOS Utility continua a ser o workflow mais fiável."))

            if not sc:
                self.q.put(("error","Não consegui comunicar com o EOS Utility."))
                return

            # Exact compiler oracle self-test.
            self.q.put(("ui",("status","A validar o compiler Canon automaticamente…")))
            mtest,dtest=self.rpc_compile(sc,SELFTEST_PF3)
            if not mtest.get("ok") or len(dtest)!=16744:
                self.q.put(("error","O compiler Canon não devolveu um payload legacy válido."))
                return
            testblock=dtest[360:8552]
            testblock2=dtest[8552:16744]
            if testblock!=SELFTEST_BLOCK or testblock2!=SELFTEST_BLOCK:
                self.q.put(("error",
                    "O self-test do compiler não deu match byte-for-byte com a Superia validada. "
                    "Instalação cancelada."))
                return
            self.q.put(("log","Self-test compiler: Superia 8192 = MATCH EXATO."))

            # Compile user's PF3 -> exact legacy Block1.
            self.q.put(("ui",("status","A compilar a LUT para o Block1 8192…")))
            meta,data=self.rpc_compile(sc,self.current_pf3)
            if not meta.get("ok") or len(data)!=16744:
                self.q.put(("error","Não consegui compilar este PF3 para o formato legacy 16744."))
                return

            b1=data[360:8552]
            b2=data[8552:16744]
            if len(b1)!=8192 or b1!=b2:
                self.q.put(("error","O compiler devolveu um layout inesperado; instalação cancelada."))
                return

            chosen=int(self.slot.get())
            style_name=canon_style_name(self.style_name.get(),self.current_pf3.stem)
            self.style_name.set(style_name)

            # Build the FULL RP payload here. This includes the validated V37 Block1
            # recipe and fixes both carrier name fields before the EOS hook even sees it.
            payload=build_rp_payload(b1,style_name)
            self.current_block=b1
            self.current_payload=payload

            OUT.mkdir(parents=True,exist_ok=True)
            block_path=OUT/(self.current_pf3.stem+".RP_BLOCK1_8192.bin")
            payload_path=OUT/(self.current_pf3.stem+".RP_PAYLOAD_16752.bin")
            block_path.write_bytes(b1)
            payload_path.write_bytes(payload)

            stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path=OUT/f"MANUAL_REPORT_{stamp}.json"
            self.install_report={
                "status":"ARMED",
                "createdAt":datetime.now().isoformat(),
                "reportPath":str(report_path),
                "sourcePf3":str(self.current_pf3),
                "sourcePf3Sha256":sha(Path(self.current_pf3).read_bytes()),
                "slot":chosen,
                "pictureStyleName":style_name,
                "compilerSelfTest":{
                    "exact":True,
                    "blockSha256":sha(testblock),
                    "meta":mtest,
                },
                "targetCompiler":{
                    "blockSha256":sha(b1),
                    "duplicateBlocks":True,
                    "meta":meta,
                },
                "rpPayload":{
                    "size":len(payload),
                    "sha256":sha(payload),
                    "containsTwilight":b"TWILIGHT" in payload,
                    "nameOffset8":payload[8:40].split(b"\x00",1)[0].decode("ascii","replace"),
                    "nameOffset44":payload[44:76].split(b"\x00",1)[0].decode("ascii","replace"),
                },
                "cameraWritePolicy":{
                    "patch203Payload":True,
                    "patch115":False,
                    "reason":"0x00000115 is binary state/control data, not a text/name field."
                },
                "events":[],
            }
            report_path.write_text(json.dumps(self.install_report,indent=2,ensure_ascii=False),encoding="utf-8")

            self.q.put(("log",f"Block1: {sha(b1)}"))
            self.q.put(("log",f"Payload RP 16752: {sha(payload)}"))
            self.q.put(("log",f"Nome final: {style_name} · TWILIGHT ausente = {b'TWILIGHT' not in payload}"))
            self.q.put(("log",f"Relatório: {report_path.name}"))

            # Arm with the full final payload. 0x00000115 is observed only and remains untouched.
            sc.exports_sync.arm(chosen,payload.hex(),style_name)

            self.q.put(("ui",("armed",chosen,str(self.current_pf3),style_name)))
        except Exception as e:
            self.q.put(("error",repr(e)))

    def open_current(self):
        p=self.current_pf3 or self.selected
        if not p:return
        try:subprocess.Popen(["explorer","/select,",str(p)])
        except Exception:os.startfile(str(p.parent))

    def poll(self):
        try:
            while True:
                typ,val=self.q.get_nowait()
                if typ=="log":
                    self.log(val)
                elif typ=="error":
                    messagebox.showerror("Erro",val)
                    self.main.config(state="normal")
                elif typ=="ui":
                    kind=val[0]
                    if kind=="status":
                        self.state.config(text="Estado: "+val[1])
                    elif kind=="built":
                        self.big.config(text="✓ PF3 gerado")
                        self.sub.config(text=
                            f"{val[1]}\n\n"
                            f"Nome interno do Picture Style: {self.style_name.get().strip() or self.selected.stem}\n\n"
                            f"Recipe: {recipe_summary(self.get_recipe_settings())}\n\n"
                            "Agora clica em Preparar instalação manual. "
                            "A app compila o Block1, monta o payload RP completo e arma o hook."
                        )
                        self.main.config(text="Preparar instalação manual",state="normal",
                                         command=lambda:threading.Thread(target=self.prepare_install,daemon=True).start())
                        self.open.config(state="normal")
                        self.state.config(text="Estado: PF3 pronto")
                    elif kind=="armed":
                        slot,path,style_name=val[1],val[2],val[3]
                        self.big.config(text=f"ÚLTIMO PASSO — User Def. {slot}")
                        self.sub.config(text=
                            f"No EOS Utility faz o registo NORMAL deste ficheiro em User Def. {slot}:\n\n{path}\n\n"
                            f"Nome esperado na câmara: {style_name}\n\n"
                            "Camera settings → Register Picture Style File → User Def. "
                            f"{slot} → Open → escolhe o PF3 acima → OK.\n\n"
                            "A app substitui apenas o payload 0x01000203. O blob binário 0x00000115 fica intacto."
                        )
                        self.main.config(text="À espera do registo…",state="disabled")
                        self.open.config(state="normal")
                        self.state.config(text=f"Estado: armado para User Def. {slot}")
                        self.open_current()
                    elif kind=="installed":
                        slot=val[1]
                        self.big.config(text=f"✓ Instalado na EOS RP — User Def. {slot}")
                        self.sub.config(text=
                            "Payload foi aceite pela câmara; o blob binário 0x00000115 ficou intacto. "
                            "Para o próximo preset: FECHA completamente o EOS Utility, volta a abri-lo, e só depois prepara/regista a próxima LUT. "
                            "A app pode continuar aberta."
                        )
                        self.main.config(text="Escolher outra LUT",state="normal",command=self.choose_file)
                        self.state.config(text="Estado: instalação concluída")
        except queue.Empty:
            pass
        if self.running:self.root.after(100,self.poll)

    def close(self):
        self.running=False
        for sc in list(self.scripts.values()):
            try:sc.exports_sync.disarm()
            except Exception:pass
            try:sc.unload()
            except Exception:pass
        for s in list(self.sessions.values()):
            try:s.detach()
            except Exception:pass
        self.root.destroy()

if __name__=="__main__":
    r=tk.Tk();App(r);r.mainloop()
