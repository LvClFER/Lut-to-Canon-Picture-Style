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
    private LinearLayout page, controls, references, toolHost;
    private String selectedTool = "RAW";
    private ScrollView toolScroll;
    private final java.util.Map<String,Integer> toolPositions=new java.util.HashMap<>();
    private final java.util.Map<String,View> toolPanels = new java.util.LinkedHashMap<>();
    private final java.util.Map<String,Button> toolButtons = new java.util.LinkedHashMap<>();
    private TextView status;
    private ComparisonView comparison;
    private boolean busy = true;
    private final Handler editTimer=new Handler(Looper.getMainLooper());
    private Runnable pendingAdjustment;
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
            selectedTool=saved.getString("selectedTool","RAW");
            cameraRequest=saved.getString("cameraRequest");cameraSource=saved.getString("cameraSource");
            cameraSlot=saved.getInt("cameraSlot");cameraDevice=saved.getParcelable("cameraDevice");
            cameraRunning=saved.getBoolean("cameraRunning");
        }
        IntentFilter permissionFilter=new IntentFilter(getPackageName()+".USB_PERMISSION");
        if(Build.VERSION.SDK_INT>=33)registerReceiver(usbPermission,permissionFilter,Context.RECEIVER_NOT_EXPORTED);
        else registerReceiver(usbPermission,permissionFilter);
        getWindow().setStatusBarColor(Color.WHITE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        page = column(); page.setPadding(12, 0, 12, 0); page.setBackgroundColor(Color.WHITE);
        setContentView(page);
        page.setOnApplyWindowInsetsListener((view,insets)->{
            page.setPadding(12,insets.getSystemWindowInsetTop(),12,insets.getSystemWindowInsetBottom());return insets;
        });
        LinearLayout actions = row(); page.addView(actions);
        button(actions, "Open", () -> choose("auto"));
        button(actions, "Undo", () -> run("undo", false));
        button(actions, "Save", this::saveDialog);
        button(actions, "More", this::moreMenu);
        comparison = new ComparisonView();
        comparison.setTag("photo-preview");
        page.addView(comparison, new LinearLayout.LayoutParams(-1, 0, 1));
        status = text("Starting editor…", 11); status.setTag("editor-status");page.addView(status);
        toolHost = column();
        toolScroll = new ScrollView(this); toolScroll.addView(toolHost);
        page.addView(toolScroll, new LinearLayout.LayoutParams(-1, (int)(getResources().getDisplayMetrics().heightPixels * .28)));
        LinearLayout tools = row();page.addView(tools);
        for(String name:new String[]{"RAW","Styles","Color","LUTs","Generate"}) {
            Button tab=button(tools,name,()->selectTool(name));tab.setTag("tool-"+name);
            tab.setTextSize(12);tab.setMinWidth(0);tab.setMinimumWidth(0);tab.setPadding(0,4,0,4);
            tab.setLayoutParams(new LinearLayout.LayoutParams(0,-2,1));toolButtons.put(name,tab);
        }
        references = row();
        worker.execute(() -> {
            try {
                if (!Python.isStarted()) Python.start(new AndroidPlatform(getApplicationContext()));
                editor = Python.getInstance().getModule("mobile_editor").callAttr("Editor", getFilesDir().toString());
                JSONObject loaded = new JSONObject(editor.callAttr("render").toString());
                runOnUiThread(() -> {showState(loaded);if(cameraRunning)pollCameraResult(System.currentTimeMillis()+50000);});
            } catch (Exception e) { error(e); }
        });
    }

    private void selectTool(String name) {
        toolPositions.put(selectedTool,toolScroll.getScrollY());
        selectedTool=name;
        for(java.util.Map.Entry<String,View> entry:toolPanels.entrySet())
            entry.getValue().setVisibility(entry.getKey().equals(name)?View.VISIBLE:View.GONE);
        for(java.util.Map.Entry<String,Button> entry:toolButtons.entrySet())
            entry.getValue().setTextColor(entry.getKey().equals(name)?RED:Color.DKGRAY);
        int position=toolPositions.getOrDefault(name,0);
        toolScroll.post(()->toolScroll.scrollTo(0,position));
    }
    private void tool(String name) {
        controls=column();controls.setPadding(12,4,12,8);controls.setBackgroundColor(Color.rgb(244,242,238));
        toolHost.addView(controls);toolPanels.put(name,controls);
        controls.addView(text(name.equals("RAW")?"RAW development":name,18));
    }
    private void moreMenu() {
        new AlertDialog.Builder(this).setItems(new String[]{"Redo","References","Snapshot A","Snapshot B","Snapshot C","Send to camera"},(d,index)->{
            if(index==0)run("undo",true);
            else if(index==1){
                try {JSONArray images=state.getJSONArray("references");String[] names=new String[images.length()];
                    for(int i=0;i<names.length;i++)names[i]=new File(images.getString(i)).getName();
                    new AlertDialog.Builder(this).setTitle("Reference images").setItems(names,(dialog,i)->run("select_reference",i)).show();
                }catch(JSONException e){error(e);}
            } else if(index==5)showCameras();
            else {String slot=new String[]{"A","B","C"}[index-2];new AlertDialog.Builder(this).setTitle("Snapshot "+slot)
                .setItems(new String[]{"Store current edit","Restore"},(dialog,i)->run("snapshot",slot,i==1)).show();}
        }).show();
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
            toolHost.removeAllViews(); toolPanels.clear(); JSONObject edit = updated.getJSONObject("edit");
            tool("RAW");
            slider("Exposure", "raw_exposure", -5, 5, 10, edit);
            button(controls, "White balance: " + edit.optString("raw_wb_mode", "As Shot"), () ->
                new AlertDialog.Builder(this).setItems(new String[]{"As Shot", "Auto", "Kelvin"}, (d, i) ->
                    update("raw_wb_mode", new String[]{"As Shot", "Auto", "Kelvin"}[i])).show());
            slider("Kelvin", "raw_kelvin", 2000, 15000, .01, edit);
            slider("WB shift B ↔ A", "wb_ab_shift", -9, 9, 1, edit);
            slider("WB shift G ↔ M", "wb_gm_shift", -9, 9, 1, edit);
            tool("Styles");
            button(controls,"Import PF3",()->choose("auto"));
            button(controls,"Import NP3",()->choose("auto"));
            button(controls,"NP3 setup: select prm.bin",()->choose("nikon_profile"));
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
            tool("Color");
            JSONObject creative = edit.getJSONObject("creative");
            for (String key : new String[]{"recipe_highlight", "recipe_shadow", "recipe_color"})
                creativeSlider(key, creative);
            button(controls, "Tone curve, six color axes and chrome", () -> settingsPanel("creative", creative)).setTag("color-adjustments");
            button(controls, "Recipe white balance", () -> settingsPanel("recipe_wb", edit.optJSONObject("recipe_wb")));
            tool("LUTs");
            button(controls,"Import LUT (.cube / Hald)",()->choose("lut"));
            JSONArray luts = edit.getJSONArray("luts");
            for (int i=0;i<luts.length();i++) {
                final int index=i; JSONObject lut=luts.getJSONObject(i);
                Switch enabled=new Switch(this);enabled.setText(new File(lut.getString("path")).getName());
                enabled.setChecked(lut.optBoolean("enabled",true));controls.addView(enabled);
                enabled.setOnCheckedChangeListener((view,on)->run("lut",index,lut.optDouble("opacity",1),on,false));
                TextView opacity=text("Opacity: "+Math.round(lut.optDouble("opacity",1)*100)+"%",14);controls.addView(opacity);
                SeekBar amount=new SeekBar(this);amount.setTag("lut-opacity-"+index);amount.setMax(100);amount.setProgress((int)Math.round(lut.optDouble("opacity",1)*100));
                amount.setContentDescription("LUT opacity");amount.setThumbTintList(ColorStateList.valueOf(RED));amount.setProgressTintList(ColorStateList.valueOf(RED));controls.addView(amount);
                Runnable reset=()->run("lut",index,1.0,lut.optBoolean("enabled",true),false);
                doubleTapReset(opacity,reset);doubleTapReset(amount,reset);
                amount.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
                    public void onStartTrackingTouch(SeekBar view){}
                    public void onProgressChanged(SeekBar view,int value,boolean user){opacity.setText("Opacity: "+value+"%");}
                    public void onStopTrackingTouch(SeekBar view){double value=view.getProgress()/100.0;commitAdjustment(()->run("lut",index,value,lut.optBoolean("enabled",true),false));}
                });
                LinearLayout order=row();controls.addView(order);
                Button up=button(order,"Move up",()->run("move_lut",index,-1));up.setEnabled(index>0);
                Button down=button(order,"Move down",()->run("move_lut",index,1));down.setEnabled(index<luts.length()-1);
                button(order,"Remove",()->run("lut",index,1.0,true,true));
            }
            tool("Generate");
            controls.addView(text("Adjust grading, then export the combined colour LUT. RAW exposure and sharpening are excluded.",12));
            button(controls,"Export LUT (.cube)",this::exportCube);
            for(String key:new String[]{"brightness","contrast","saturation","hue","temperature","tint","red_gamma","green_gamma","blue_gamma","toe","mid_contrast","shoulder","lightness","density"})
                gradingSlider(creative,key);
            selectTool(selectedTool);
        } catch (Exception e) { error(e); }
    }
    private void doubleTapReset(View view,Runnable reset) {
        view.setClickable(true);
        GestureDetector detector=new GestureDetector(this,new GestureDetector.SimpleOnGestureListener(){
            @Override public boolean onDoubleTap(MotionEvent event){if(pendingAdjustment!=null)editTimer.removeCallbacks(pendingAdjustment);if(!busy)reset.run();return true;}
        });
        view.setOnTouchListener((target,event)->detector.onTouchEvent(event));
    }
    private void commitAdjustment(Runnable action) {
        if(pendingAdjustment!=null)editTimer.removeCallbacks(pendingAdjustment);
        pendingAdjustment=action;editTimer.postDelayed(action,ViewConfiguration.getDoubleTapTimeout());
    }
    private int defaultValue(String key) {
        if(key.equals("raw_kelvin"))return 5200;
        if(key.equals("fineness"))return 2;
        if(key.equals("threshold"))return 4;
        return 0;
    }
    private void slider(String name, String key, double min, double max, double scale, JSONObject edit) {
        double value=edit.optDouble(key, min); TextView label=text(name+": "+value, 14); label.setTag("reset-"+key);controls.addView(label);
        SeekBar bar=new SeekBar(this);bar.setTag("adjustment-"+key); bar.setMax((int)Math.round((max-min)*scale)); bar.setProgress((int)Math.round((value-min)*scale));
        bar.setContentDescription(name);bar.setThumbTintList(ColorStateList.valueOf(RED)); bar.setProgressTintList(ColorStateList.valueOf(RED)); controls.addView(bar);
        Runnable reset=()->{bar.setProgress((int)Math.round((defaultValue(key)-min)*scale));update(key,defaultValue(key));};
        doubleTapReset(bar,reset);doubleTapReset(label,reset);
        bar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onStartTrackingTouch(SeekBar b) {}
            public void onProgressChanged(SeekBar b,int p,boolean user) { label.setText(name+": "+(min+p/scale)); }
            public void onStopTrackingTouch(SeekBar b) { double v=min+b.getProgress()/scale; commitAdjustment(()->update(key,key.equals("raw_exposure")?v:Math.round(v))); }
        });
    }
    private void creativeSlider(String key, JSONObject creative) {
        button(controls, key.replace('_',' ')+": "+creative.optInt(key), () -> settingsPanel("creative", creative));
    }
    private void setNumber(JSONObject object,String key,double value) {
        try { object.put(key,value); } catch(JSONException error) { throw new IllegalArgumentException(error); }
    }
    private void localSlider(LinearLayout box,String name,int min,int max,int value,java.util.function.IntConsumer apply) {
        TextView label=text(name+": "+value,14);box.addView(label);
        SeekBar slider=new SeekBar(this);slider.setMax(max-min);slider.setProgress(value-min);
        slider.setContentDescription(name);slider.setThumbTintList(ColorStateList.valueOf(RED));slider.setProgressTintList(ColorStateList.valueOf(RED));box.addView(slider);
        int neutral=name.startsWith("Input ")?Integer.parseInt(name.substring(6,name.indexOf('%'))):0;
        Runnable reset=()->{int target=Math.max(min,Math.min(max,neutral));slider.setProgress(target-min);label.setText(name+": "+target);apply.accept(target);};
        doubleTapReset(slider,reset);doubleTapReset(label,reset);
        slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onStartTrackingTouch(SeekBar view) {}
            public void onStopTrackingTouch(SeekBar view) {}
            public void onProgressChanged(SeekBar view,int progress,boolean user) {
                label.setText(name+": "+(min+progress));if(user)apply.accept(min+progress);
            }
        });
    }
    private void settingsPanel(String key,JSONObject object) {
        try {
            JSONObject settings=new JSONObject(object==null?"{}":object.toString());
            LinearLayout box=column();box.setPadding(8,4,8,8);
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
            LinearLayout panel=(LinearLayout)toolPanels.get("Color");panel.removeAllViews();
            LinearLayout actions=row();panel.addView(actions);
            button(actions,"Apply",()->update(key,settings));
            button(actions,"Cancel",()->showState(state)).setTag("cancel-color-adjustments");
            panel.addView(box);toolScroll.scrollTo(0,0);
        } catch(JSONException error){error(error);}
    }
    private void gradingSlider(JSONObject creative,String key) throws JSONException {
        JSONObject grading=creative.optJSONObject("grading");int limit=key.equals("hue")?180:100;
        int value=grading==null?0:grading.optInt(key);
        TextView label=text(key.replace('_',' ')+": "+value,14);controls.addView(label);
        SeekBar slider=new SeekBar(this);slider.setTag("grading-"+key);slider.setContentDescription(key.replace('_',' '));
        slider.setMax(limit*2);slider.setProgress(value+limit);
        slider.setThumbTintList(ColorStateList.valueOf(RED));slider.setProgressTintList(ColorStateList.valueOf(RED));controls.addView(slider);
        Runnable reset=()->{try {JSONObject copy=new JSONObject(creative.toString()),values=copy.optJSONObject("grading");
            if(values==null){values=new JSONObject();copy.put("grading",values);}values.put(key,0);update("creative",copy);
        }catch(JSONException e){error(e);}};
        doubleTapReset(slider,reset);doubleTapReset(label,reset);
        slider.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener(){
            public void onStartTrackingTouch(SeekBar view){}
            public void onProgressChanged(SeekBar view,int progress,boolean user){label.setText(key.replace('_',' ')+": "+(progress-limit));}
            public void onStopTrackingTouch(SeekBar view){
                try {JSONObject copy=new JSONObject(creative.toString()),values=copy.optJSONObject("grading");
                    if(values==null){values=new JSONObject();copy.put("grading",values);}
                    values.put(key,view.getProgress()-limit);commitAdjustment(()->update("creative",copy));
                }catch(JSONException e){error(e);}
            }
        });
    }
    private void exportCube() {
        busy=true;status.setText("Generating LUT…");
        worker.execute(()->{try {
            File output=new File(getCacheDir(),java.util.UUID.randomUUID()+".cube");
            pendingExport=editor.callAttr("export_cube",output.toString()).toString();
            runOnUiThread(()->{busy=false;Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);intent.setType("application/octet-stream");
                intent.putExtra(Intent.EXTRA_TITLE,"Custom look.cube");startActivityForResult(intent,2);});
        }catch(Exception e){error(e);}});
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
        out.putString("selectedTool",selectedTool);
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
