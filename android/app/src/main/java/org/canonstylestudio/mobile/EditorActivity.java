package org.canonstylestudio.mobile;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.res.ColorStateList;
import android.database.Cursor;
import android.graphics.*;
import android.hardware.usb.*;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.view.*;
import android.widget.*;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;
import org.json.*;
import java.io.*;
import java.util.concurrent.*;

/** Native touch UI. All engine work is serialized off the Android UI thread. */
public class EditorActivity extends Activity {
    private final ExecutorService worker = Executors.newSingleThreadExecutor();
    private PyObject editor;
    private JSONObject state;
    private LinearLayout page, controls, references;
    private TextView status;
    private ComparisonView comparison;
    private boolean busy = true;
    private String pendingKind = "auto", pendingExport;
    private String cameraRequest, cameraSource;
    private UsbDevice cameraDevice;
    private int cameraSlot;
    private boolean cameraRunning;
    private final Handler cameraTimer=new Handler(Looper.getMainLooper());
    private final BroadcastReceiver usbPermission=new BroadcastReceiver() {
        @Override public void onReceive(Context context,Intent intent) {
            if(!intent.getAction().equals(getPackageName()+".USB_PERMISSION"))return;
            if(intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED,false))startCameraWorker();
            else {busy=false;status.setText("USB permission was not granted; nothing was sent.");}
        }
    };
    private static final int RED = Color.rgb(220, 22, 49);

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        if(saved!=null) {
            cameraRequest=saved.getString("cameraRequest");cameraSource=saved.getString("cameraSource");
            cameraSlot=saved.getInt("cameraSlot");cameraDevice=saved.getParcelable("cameraDevice");
            cameraRunning=saved.getBoolean("cameraRunning");
        }
        IntentFilter permissionFilter=new IntentFilter(getPackageName()+".USB_PERMISSION");
        if(Build.VERSION.SDK_INT>=33)registerReceiver(usbPermission,permissionFilter,Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(usbPermission,permissionFilter);
        getWindow().setStatusBarColor(Color.WHITE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        ScrollView scroll = new ScrollView(this);
        page = column(); page.setPadding(20, 20, 20, 30); page.setBackgroundColor(Color.WHITE);
        scroll.addView(page); setContentView(scroll);
        if(Build.VERSION.SDK_INT>=35)scroll.setOnApplyWindowInsetsListener((view,insets)->{
            page.setPadding(20,20+insets.getSystemWindowInsetTop(),20,30+insets.getSystemWindowInsetBottom());return insets;
        });
        TextView title = text("Canon Style Studio", 26); title.setTextColor(RED); page.addView(title);
        LinearLayout actions = row(); page.addView(actions);
        button(actions, "Open", () -> choose("auto"));
        button(actions, "+ LUT", () -> choose("lut"));
        button(actions, "Save", this::saveDialog);
        LinearLayout history = row(); HorizontalScrollView historyScroll = new HorizontalScrollView(this); historyScroll.addView(history); page.addView(historyScroll);
        button(history, "Undo", () -> run("undo", false));
        button(history, "Redo", () -> run("undo", true));
        for (String slot : new String[]{"A", "B", "C"}) {
            Button snapshot = button(history, slot, () -> new AlertDialog.Builder(this)
                .setTitle("Snapshot " + slot).setItems(new String[]{"Store current edit", "Restore"},
                    (d, which) -> run("snapshot", slot, which == 1)).show());
        }
        comparison = new ComparisonView();
        page.addView(comparison, new LinearLayout.LayoutParams(-1, (int)(getResources().getDisplayMetrics().heightPixels * .48)));
        references = row(); HorizontalScrollView strip = new HorizontalScrollView(this);
        strip.addView(references); page.addView(strip);
        status = text("Starting editor…", 13); status.setTag("editor-status");page.addView(status);
        controls = column(); page.addView(controls);
        button(page, "Send to camera · experimental", this::showCameras);
        worker.execute(() -> {
            try {
                if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
                editor = Python.getInstance().getModule("mobile_editor").callAttr("Editor", getFilesDir().toString());
                JSONObject loaded = new JSONObject(editor.callAttr("render").toString());
                runOnUiThread(() -> {showState(loaded);if(cameraRunning)pollCameraResult(System.currentTimeMillis()+50000);});
            } catch (Exception e) { error(e); }
        });
    }

    private LinearLayout column() { LinearLayout v = new LinearLayout(this); v.setOrientation(LinearLayout.VERTICAL); return v; }
    private LinearLayout row() { LinearLayout v = new LinearLayout(this); v.setOrientation(LinearLayout.HORIZONTAL); return v; }
    private TextView text(String value, int size) { TextView v = new TextView(this); v.setText(value); v.setTextSize(size); v.setTextColor(Color.rgb(28,28,28)); v.setPadding(4,8,4,8); return v; }
    private Button button(LinearLayout parent, String name, Runnable action) {
        Button b = new Button(this); b.setText(name); b.setAllCaps(false); b.setTextColor(Color.rgb(28,28,28));
        b.setOnClickListener(v -> { if (!busy) action.run(); }); parent.addView(b); return b;
    }
    private void error(Exception error) {
        runOnUiThread(() -> { busy = false; status.setText("Operation failed");
            new AlertDialog.Builder(this).setTitle("Canon Style Studio").setMessage(error.getMessage()).setPositiveButton("Close", null).show(); });
    }
    private void run(String method, Object... arguments) {
        if (busy || editor == null) return;
        busy = true; status.setText("Working…");
        worker.execute(() -> {
            try {
                editor.callAttr(method, arguments);
                editor.callAttr("checkpoint");
                JSONObject updated = new JSONObject(editor.callAttr("render").toString());
                runOnUiThread(() -> showState(updated));
            } catch (Exception e) { error(e); }
        });
    }
    private void update(String key, Object value) {
        try { run("update", new JSONObject().put(key, value).toString()); }
        catch (JSONException e) { error(e); }
    }
    private void showState(JSONObject updated) {
        busy = cameraRunning; state = updated;
        try {
            comparison.setImages(updated.optString("before"), updated.optString("after"));
            status.setText(updated.optString("name") + " · " + updated.optString("decoder"));
            references.removeAllViews(); JSONArray images = updated.getJSONArray("references");
            for (int i = 0; i < images.length(); i++) {
                final int index = i;
                button(references, new File(images.getString(i)).getName(), () -> run("select_reference", index));
            }
            controls.removeAllViews(); JSONObject edit = updated.getJSONObject("edit");
            TextView heading = text("Picture Style", 22); controls.addView(heading);
            Spinner base = new Spinner(this);
            String current = edit.optString("basePictureStyle", "Neutral");
            java.util.List<String> bases = new java.util.ArrayList<>(java.util.Arrays.asList("Standard", "Portrait", "Landscape", "Neutral", "Faithful", "Fine Detail"));
            if(!bases.contains(current)) bases.add(current);
            base.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, bases));
            base.setSelection(bases.indexOf(current));
            controls.addView(base);
            base.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
                public void onNothingSelected(AdapterView<?> p) {}
                public void onItemSelected(AdapterView<?> p, View v, int i, long id) { if (!bases.get(i).equals(current) && !busy) update("basePictureStyle", bases.get(i)); }
            });
            slider("Contrast", "contrast", -4, 4, 1, edit);
            slider("Saturation", "saturation", -4, 4, 1, edit);
            slider("Color tone", "color_tone", -4, 4, 1, edit);
            Switch sharpness = new Switch(this); sharpness.setText("Set sharpness");
            sharpness.setChecked(edit.optBoolean("sharpness_override")); controls.addView(sharpness);
            sharpness.setOnCheckedChangeListener((b, checked) -> update("sharpness_override", checked));
            slider("Sharpness strength", "sharp_strength", 0, 7, 1, edit);
            slider("Fineness", "fineness", 1, 5, 1, edit);
            slider("Threshold", "threshold", 1, 5, 1, edit);
            controls.addView(text("Preview development", 22));
            slider("Exposure", "raw_exposure", -5, 5, 10, edit);
            button(controls, "White balance: " + edit.optString("raw_wb_mode", "As Shot"), () ->
                new AlertDialog.Builder(this).setItems(new String[]{"As Shot", "Auto", "Kelvin"}, (d, i) ->
                    update("raw_wb_mode", new String[]{"As Shot", "Auto", "Kelvin"}[i])).show());
            slider("Kelvin", "raw_kelvin", 2000, 15000, .01, edit);
            slider("WB shift B ↔ A", "wb_ab_shift", -9, 9, 1, edit);
            slider("WB shift G ↔ M", "wb_gm_shift", -9, 9, 1, edit);
            controls.addView(text("Creative color", 22));
            JSONObject creative = edit.getJSONObject("creative");
            for (String key : new String[]{"recipe_highlight", "recipe_shadow", "recipe_color"})
                creativeSlider(key, creative);
            button(controls, "Tone curve, six color axes and chrome", () -> settingsDialog("creative", creative));
            button(controls, "Recipe white balance", () -> settingsDialog("recipe_wb", edit.optJSONObject("recipe_wb")));
            controls.addView(text("LUT stack", 22)); JSONArray luts = edit.getJSONArray("luts");
            for (int i=0;i<luts.length();i++) {
                final int index=i; JSONObject lut=luts.getJSONObject(i);
                button(controls, new File(lut.getString("path")).getName() + " · " + Math.round(lut.optDouble("opacity", 1)*100) + "%", () ->
                    new AlertDialog.Builder(this).setItems(new String[]{"Enable", "Disable", "Opacity 25%", "Opacity 50%", "Opacity 100%", "Remove"},
                        (d, item) -> run("lut", index, item==2?.25:item==3?.5:1.0, item!=1, item==5)).show());
            }
        } catch (Exception e) { error(e); }
    }
    private void slider(String name, String key, double min, double max, double scale, JSONObject edit) {
        double value=edit.optDouble(key, min); TextView label=text(name+": "+value, 14); controls.addView(label);
        SeekBar bar=new SeekBar(this); bar.setMax((int)Math.round((max-min)*scale)); bar.setProgress((int)Math.round((value-min)*scale));
        bar.setContentDescription(name);bar.setThumbTintList(ColorStateList.valueOf(RED)); bar.setProgressTintList(ColorStateList.valueOf(RED)); controls.addView(bar);
        bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onStartTrackingTouch(SeekBar b) {}
            public void onProgressChanged(SeekBar b,int p,boolean user) { label.setText(name+": "+(min+p/scale)); }
            public void onStopTrackingTouch(SeekBar b) { double v=min+b.getProgress()/scale; update(key,key.equals("raw_exposure")?v:Math.round(v)); }
        });
    }
    private void creativeSlider(String key, JSONObject creative) {
        button(controls, key.replace('_',' ')+": "+creative.optInt(key), () -> settingsDialog("creative", creative));
    }
    private void setNumber(JSONObject object,String key,double value) {
        try { object.put(key,value); } catch(JSONException error) { throw new IllegalArgumentException(error); }
    }
    private void localSlider(LinearLayout box,String name,int min,int max,int value,java.util.function.IntConsumer apply) {
        TextView label=text(name+": "+value,14);box.addView(label);
        SeekBar slider=new SeekBar(this);slider.setMax(max-min);slider.setProgress(value-min);
        slider.setContentDescription(name);slider.setThumbTintList(ColorStateList.valueOf(RED));slider.setProgressTintList(ColorStateList.valueOf(RED));box.addView(slider);
        slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onStartTrackingTouch(SeekBar view) {}
            public void onStopTrackingTouch(SeekBar view) {}
            public void onProgressChanged(SeekBar view,int progress,boolean user) {
                label.setText(name+": "+(min+progress));if(user)apply.accept(min+progress);
            }
        });
    }
    private void settingsDialog(String key,JSONObject object) {
        try {
            JSONObject settings=new JSONObject(object==null?"{}":object.toString());
            LinearLayout box=column();box.setPadding(20,10,20,10);ScrollView scroll=new ScrollView(this);scroll.addView(box);
            if(key.equals("recipe_wb")) {
                for(String axis:new String[]{"red","blue"})
                    localSlider(box,axis,-9,9,settings.optInt(axis),v->setNumber(settings,axis,v));
            } else {
                for(String control:new String[]{"recipe_highlight","recipe_shadow","recipe_color"}) {
                    int min=control.equals("recipe_color")?-4:-2;
                    localSlider(box,control.replace('_',' '),min,4,settings.optInt(control),v->setNumber(settings,control,v));
                }
                box.addView(text("Tone curve",20));JSONArray curve=settings.getJSONArray("tone_curve");
                for(int i=0;i<5;i++) {
                    final int index=i;
                    localSlider(box,"Input "+(i*25)+"% → output %",0,100,(int)Math.round(curve.getDouble(i)*100),v->{
                        try { curve.put(index,v/100.0); }catch(JSONException error){throw new IllegalArgumentException(error);}
                    });
                }
                JSONObject axes=settings.getJSONObject("color_axes");
                for(String axis:new String[]{"Red","Yellow","Green","Cyan","Blue","Magenta"}) {
                    box.addView(text(axis,20));JSONObject values=axes.getJSONObject(axis);
                    for(String component:new String[]{"hue","saturation","luminance"}) {
                        int limit=component.equals("hue")?30:50;
                        localSlider(box,component,-limit,limit,values.optInt(component),v->setNumber(values,component,v));
                    }
                }
                for(String chrome:new String[]{"color_chrome","color_chrome_fx_blue"}) {
                    box.addView(text(chrome.replace('_',' '),16));Spinner level=new Spinner(this);
                    String[] levels={"Off","Weak","Strong"};level.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,levels));
                    for(int i=0;i<levels.length;i++)if(levels[i].equals(settings.optString(chrome)))level.setSelection(i);
                    level.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
                        public void onNothingSelected(AdapterView<?> p){}
                        public void onItemSelected(AdapterView<?> p,View view,int index,long id){try{settings.put(chrome,levels[index]);}catch(JSONException error){throw new IllegalArgumentException(error);}}
                    });box.addView(level);
                }
            }
            new AlertDialog.Builder(this).setTitle(key.replace('_',' ')).setView(scroll).setNegativeButton("Cancel",null)
                .setPositiveButton("Apply",(dialog,which)->update(key,settings)).show();
        } catch(JSONException error){error(error);}
    }
    private void choose(String kind) {
        pendingKind=kind; Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT); intent.setType("*/*");
        intent.addCategory(Intent.CATEGORY_OPENABLE); startActivityForResult(intent,1);
    }
    private void saveDialog() {
        EditText name=new EditText(this); name.setText(state.optString("name","Untitled"));
        new AlertDialog.Builder(this).setTitle("Save style").setView(name).setNegativeButton("Cancel",null)
            .setPositiveButton("Project",(d,w)->prepareExport(name.getText().toString(),true))
            .setNeutralButton("PF3",(d,w)->prepareExport(name.getText().toString(),false)).show();
    }
    private void prepareExport(String name, boolean project) {
        busy=true; status.setText("Compiling style…");
        worker.execute(()->{
            try {
                editor.callAttr("update", new JSONObject().put("name",name).toString());
                editor.callAttr("checkpoint");
                File directory=new File(getCacheDir(),"exports"); directory.mkdirs();
                File output=new File(directory, java.util.UUID.randomUUID()+(project?".canonstyleproject":".pf3"));
                pendingExport=editor.callAttr("export",output.toString(),project).toString();
                runOnUiThread(()->{ busy=false;
                    Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT); intent.addCategory(Intent.CATEGORY_OPENABLE); intent.setType("application/octet-stream");
                    intent.putExtra(Intent.EXTRA_TITLE,name.replaceAll("[\\\\/:*?\"<>|]","_")+(project?".canonstyleproject":".pf3")); startActivityForResult(intent,2);
                });
            } catch(Exception e) { error(e); }
        });
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(result!=RESULT_OK || data==null || data.getData()==null) return;
        Uri uri=data.getData(); busy=true; status.setText("Reading document…");
        worker.execute(()->{
            try {
                if(request==1) {
                    String name="image";
                    try(Cursor cursor=getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)) { if(cursor!=null && cursor.moveToFirst()) name=cursor.getString(0); }
                    File folder=new File(getFilesDir(),"imports/"+java.util.UUID.randomUUID()); folder.mkdirs();
                    File file=new File(folder,new File(name).getName());
                    try(InputStream input=getContentResolver().openInputStream(uri); OutputStream output=new FileOutputStream(file)) { copy(input,output,512L*1024*1024); }
                    editor.callAttr("open",file.toString(),pendingKind);
                    editor.callAttr("checkpoint");
                    JSONObject updated=new JSONObject(editor.callAttr("render").toString()); runOnUiThread(()->showState(updated));
                } else if(request==2) {
                    try(InputStream input=new FileInputStream(pendingExport); OutputStream output=getContentResolver().openOutputStream(uri,"wt")) { copy(input,output,512L*1024*1024); }
                    new File(pendingExport).delete(); pendingExport=null;
                    runOnUiThread(()->{busy=false;status.setText("Style saved successfully");});
                }
            } catch(Exception e) { error(e); }
        });
    }
    private static void copy(InputStream input,OutputStream output,long limit) throws IOException {
        if(input==null || output==null) throw new IOException("Document provider unavailable");
        byte[] buffer=new byte[65536]; long total=0; int count;
        while((count=input.read(buffer))!=-1) { total+=count; if(total>limit) throw new IOException("Document exceeds 512 MiB"); output.write(buffer,0,count); }
    }
    private void showCameras() {
        UsbManager manager=(UsbManager)getSystemService(USB_SERVICE);java.util.List<UsbDevice> found=new java.util.ArrayList<>();
        for(UsbDevice device:manager.getDeviceList().values()) if(device.getVendorId()==0x04a9)
            found.add(device);
        if(found.isEmpty()) {
            new AlertDialog.Builder(this).setTitle("USB cameras").setMessage("No Canon camera found. Connect using a USB host/OTG cable.").setPositiveButton("Close",null).show();return;
        }
        String[] names=new String[found.size()];for(int i=0;i<names.length;i++)names[i]=String.valueOf(found.get(i).getProductName());
        new AlertDialog.Builder(this).setTitle("Select camera").setItems(names,(dialog,index)-> {
            cameraDevice=found.get(index);
            new AlertDialog.Builder(this).setTitle("Destination slot").setItems(new String[]{"User Def. 1","User Def. 2","User Def. 3"},
                (slots,selected)->prepareCamera(selected+1)).show();
        }).show();
    }
    private void prepareCamera(int slot) {
        busy=true;status.setText("Preparing Picture Style…");cameraSlot=slot;cameraRequest=java.util.UUID.randomUUID().toString();
        worker.execute(()->{
            try {
                File directory=new File(getFilesDir(),"camera-jobs/"+cameraRequest);directory.mkdirs();
                cameraSource=editor.callAttr("export",new File(directory,"style.pf3").toString(),false).toString();
                runOnUiThread(()->{
                    busy=false;
                    new AlertDialog.Builder(this).setTitle("Install in User Def. "+cameraSlot+"?")
                        .setMessage("The current slot will be backed up privately before writing. The app will compare the final style and Basic controls, then close the session.\n\nThe Android USB route is experimental and has not been physically validated. A failure may require turning the camera off and disconnecting USB. There is one attempt with a 45-second deadline.")
                        .setNegativeButton("Cancel",(dialog,which)->{cameraRequest=null;status.setText("Camera installation cancelled");})
                        .setPositiveButton("Install",(dialog,which)->{
                            UsbManager manager=(UsbManager)getSystemService(USB_SERVICE);
                            if(manager.hasPermission(cameraDevice))startCameraWorker();
                            else {
                                Intent permission=new Intent(getPackageName()+".USB_PERMISSION").setPackage(getPackageName());
                                manager.requestPermission(cameraDevice,PendingIntent.getBroadcast(this,0,permission,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT));
                            }
                        }).show();
                });
            }catch(Exception error){cameraRequest=null;error(error);}
        });
    }
    private void startCameraWorker() {
        busy=true;cameraRunning=true;status.setText("Installing in User Def. "+cameraSlot+". Keep USB connected…");
        Intent intent=new Intent(this,CameraWorker.class).putExtra("device",cameraDevice).putExtra("source",cameraSource)
            .putExtra("slot",cameraSlot).putExtra("request",cameraRequest);
        try {startForegroundService(intent);pollCameraResult(System.currentTimeMillis()+50000);}
        catch(Exception error){busy=false;cameraRunning=false;error(error);}
    }
    private void pollCameraResult(long deadline) {
        cameraTimer.postDelayed(()->{
            if(isDestroyed()||cameraRequest==null)return;
            try {
                File resultFile=new File(getFilesDir(),"camera-result.json");
                if(resultFile.isFile()) {
                    JSONObject result=new JSONObject(new String(java.nio.file.Files.readAllBytes(resultFile.toPath()),java.nio.charset.StandardCharsets.UTF_8));
                    if(cameraRequest.equals(result.optString("request"))) {
                        busy=false;cameraRunning=false;cameraRequest=null;
                        boolean success=result.getBoolean("success");
                        status.setText(success?"Installed and verified in User Def. "+cameraSlot:"Camera installation failed; no automatic retry");
                        new AlertDialog.Builder(this).setTitle(success?"Installation confirmed":"Installation failed")
                            .setMessage(success?"The style and Basic controls matched the final camera readback. The session was closed. Check the result on the camera.":result.optString("detail"))
                            .setPositiveButton("Close",null).show();return;
                    }
                }
                if(System.currentTimeMillis()>=deadline) {
                    busy=false;cameraRunning=false;cameraRequest=null;throw new IOException("The camera worker did not return a result. The transfer will not be repeated; disconnect USB and check the camera.");
                }
                pollCameraResult(deadline);
            }catch(Exception error){busy=false;error(error);}
        },500);
    }
    @Override public void onBackPressed() {
        if(busy) return;
        new AlertDialog.Builder(this).setTitle("Close editor?").setMessage("Save your project before closing to keep your edits.")
            .setPositiveButton("Save",(d,w)->saveDialog()).setNegativeButton("Keep editing",null)
            .setNeutralButton("Close",(d,w)->finish()).show();
    }
    @Override protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);out.putString("cameraRequest",cameraRequest);out.putString("cameraSource",cameraSource);
        out.putInt("cameraSlot",cameraSlot);out.putParcelable("cameraDevice",cameraDevice);
        out.putBoolean("cameraRunning",cameraRunning);
    }
    @Override protected void onDestroy() { unregisterReceiver(usbPermission);cameraTimer.removeCallbacksAndMessages(null);worker.shutdown();super.onDestroy(); }

    private class ComparisonView extends View {
        private Bitmap before,after; private float split=.5f; private final Paint paint=new Paint(3);private final RectF box=new RectF();
        ComparisonView() { super(EditorActivity.this); setContentDescription("Before and after image. Drag horizontally to compare."); setFocusable(true); }
        void setImages(String a,String b) {
            if(a.isEmpty()||b.isEmpty()) { before=null;after=null;invalidate();return; }
            before=BitmapFactory.decodeFile(a); after=BitmapFactory.decodeFile(b); invalidate();
        }
        @Override protected void onDraw(Canvas canvas) {
            super.onDraw(canvas); canvas.drawColor(Color.rgb(245,243,239));
            if(after==null||before==null) return;
            float scale=Math.min((float)getWidth()/after.getWidth(),(float)getHeight()/after.getHeight());
            float w=after.getWidth()*scale,h=after.getHeight()*scale,x=(getWidth()-w)/2,y=(getHeight()-h)/2;
            box.set(x,y,x+w,y+h);canvas.drawBitmap(after,null,box,paint);
            float divider=x+w*split;canvas.save();canvas.clipRect(x,y,divider,y+h);canvas.drawBitmap(before,null,box,paint);canvas.restore();
            paint.setColor(RED);paint.setStrokeWidth(3);canvas.drawLine(divider,y,divider,y+h,paint);canvas.drawCircle(divider,y+h/2,12,paint);
        }
        @Override public boolean onTouchEvent(android.view.MotionEvent event) {
            if(after==null)return false;
            float scale=Math.min((float)getWidth()/after.getWidth(),(float)getHeight()/after.getHeight());float width=after.getWidth()*scale;
            split=Math.max(0,Math.min(1,(event.getX()-(getWidth()-width)/2)/width));
            getParent().requestDisallowInterceptTouchEvent(event.getAction()!=android.view.MotionEvent.ACTION_UP);
            invalidate(); if(event.getAction()==android.view.MotionEvent.ACTION_UP)performClick();return true;
        }
        @Override public boolean performClick() { super.performClick();return true; }
        @Override public void onInitializeAccessibilityNodeInfo(android.view.accessibility.AccessibilityNodeInfo info) {
            super.onInitializeAccessibilityNodeInfo(info);info.setClassName("android.widget.SeekBar");
            info.setRangeInfo(android.view.accessibility.AccessibilityNodeInfo.RangeInfo.obtain(1,0,1,split));
            info.addAction(android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction.ACTION_SET_PROGRESS);
        }
        @Override public boolean performAccessibilityAction(int action,Bundle arguments) {
            if(action==android.view.accessibility.AccessibilityNodeInfo.AccessibilityAction.ACTION_SET_PROGRESS.getId() && arguments!=null) {
                float value=arguments.getFloat(android.view.accessibility.AccessibilityNodeInfo.ACTION_ARGUMENT_PROGRESS_VALUE);
                if(Float.isNaN(value)||Float.isInfinite(value))return false;
                split=Math.max(0,Math.min(1,value));invalidate();return true;
            }
            return super.performAccessibilityAction(action,arguments);
        }
        @Override public boolean onKeyDown(int key,KeyEvent event) {
            if(key==KeyEvent.KEYCODE_DPAD_LEFT || key==KeyEvent.KEYCODE_DPAD_RIGHT) {
                split=Math.max(0,Math.min(1,split+(key==KeyEvent.KEYCODE_DPAD_LEFT?-.05f:.05f)));invalidate();return true;
            }
            return super.onKeyDown(key,event);
        }
    }
}
