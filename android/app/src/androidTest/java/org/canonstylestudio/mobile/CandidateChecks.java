package org.canonstylestudio.mobile;

import android.app.*;
import android.content.*;
import android.os.Bundle;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.io.File;

/** Executes the packaged native Python libraries; never requests USB access. */
public final class CandidateChecks extends Instrumentation {
    private Bundle inputs;
    @Override public void onCreate(Bundle arguments) { super.onCreate(arguments);inputs=arguments==null?new Bundle():arguments;start(); }
    @Override public void onStart() {
        Bundle result=new Bundle();
        try {
            Context context=getTargetContext();
            if(!Python.isStarted())Python.start(new AndroidPlatform(context));
            Python python=Python.getInstance();
            python.getBuiltins().callAttr("exec",
                "import numpy as np\nfrom creative_controls import apply_creative_rgb,linear_to_srgb\n"
                +"join=float(linear_to_srgb(np.asarray(.5**3)))\nx=join+np.array([-.001,-.0005,0,.0005,.001])\n"
                +"for key in ('recipe_highlight','recipe_shadow'):\n for level in (-2,4):\n"
                +"  y=apply_creative_rgb(np.repeat(x[:,None],3,axis=1),{key:level})[:,0]\n"
                +"  assert np.all(np.abs(np.diff(y)/np.diff(x)-1)<.03), 'Recipe tone cusp remains'\n",
                python.getBuiltins().callAttr("dict"));
            result.putBoolean("smoothRecipeTone",true);
            String conversion=python.getModule("nikon_conversion").get("CONVERSION_VERSION").toString();
            if(!conversion.equals("relative-flexible-v5"))throw new AssertionError("Stale NP3 conversion engine");
            python.getModule("nikon_import");python.getModule("nikon_profile_data");
            result.putString("np3ConversionVersion",conversion);
            if(inputs.containsKey("toneCases")) {
                PyObject scope=python.getBuiltins().callAttr("dict");
                scope.callAttr("__setitem__","tone_case_path",inputs.getString("toneCases"));
                python.getBuiltins().callAttr("exec",
                    "import json,hashlib,struct\nfrom pathlib import Path\n"
                    +"from camera_install.raw_recipe_reference import generate_model_tone_lookup\n"
                    +"case_file=Path(tone_case_path)\nassert case_file.stat().st_size<1024*1024\n"
                    +"tone_cases=json.loads(case_file.read_text())\nassert 0<len(tone_cases)<=32\n"
                    +"for case in tone_cases:\n"
                    +" table=generate_model_tone_lookup(**case['arguments'])\n"
                    +" assert len(table)==2048\n"
                    +" assert hashlib.sha256(struct.pack('<2048I',*table)).hexdigest()==case['sha256'],case['name']\n",
                    scope);
                result.putInt("exactModelToneCases",scope.callAttr("__getitem__","tone_cases").asList().size());
            }
            for(int i=0;i<6;i++)if(inputs.containsKey("baselineRaw"+i)) {
                java.util.List<PyObject> developed=python.getModule("android_raw").callAttr("decode",
                    inputs.getString("baselineRaw"+i),context.getCacheDir().toString()).asList();
                PyObject metadata=developed.get(1);
                double baseline=metadata.callAttr("__getitem__","canon_baseline_exposure_ev").toDouble();
                double expected=Double.parseDouble(inputs.getString("baselineExpected"+i));
                if(Math.abs(baseline-expected)>0.0000001
                        || metadata.callAttr("__getitem__","canon_baseline_exposure_applied").toBoolean())
                    throw new AssertionError("Canon Flavor baseline mismatch for fixture "+i);
                result.putString("canonBaselineEv"+i,String.valueOf(baseline));
                result.putString("canonBaselinePixelHash"+i,python.getModule("hashlib").callAttr("sha256",
                    developed.get(0).callAttr("tobytes")).callAttr("hexdigest").toString());
                developed.get(0).callAttr("close");
            }
            for(int i=0;i<5;i++)if(inputs.containsKey("brightnessRaw"+i)) {
                java.util.List<PyObject> developed=python.getModule("android_raw").callAttr("decode",
                    inputs.getString("brightnessRaw"+i),context.getCacheDir().toString()).asList();
                PyObject pixels=developed.get(0),metadata=developed.get(1);double mean=0;
                for(PyObject channel:python.getModule("PIL.ImageStat").callAttr("Stat",pixels).get("mean").asList())mean+=channel.toDouble()/3;
                double oldMean=Double.parseDouble(inputs.getString("brightnessOldMean"+i));
                if(!(mean>oldMean*1.3 && mean<250)
                        || !metadata.callAttr("__getitem__","output_transfer").toString().equals("sRGB")
                        || metadata.callAttr("__getitem__","embedded_preview_used").toBoolean())
                    throw new AssertionError("RAW brightness regression for fixture "+i+": "+mean);
                result.putString("brightnessMean"+i,String.valueOf(mean));pixels.callAttr("close");
            }
            File directory=new File(context.getCacheDir(),"candidate-check-"+java.util.UUID.randomUUID());directory.mkdirs();
            File invalidRaw=new File(directory,"invalid.cr3"),invalidOutput=new File(directory,"invalid.ppm");
            try(java.io.FileOutputStream output=new java.io.FileOutputStream(invalidRaw)){output.write(new byte[]{1,2,3,4});}
            boolean rejected=false;
            try { NativeRaw.develop(invalidRaw.toString(),invalidOutput.toString(),0); }
            catch(java.io.IOException expected){rejected=true;}
            if(!rejected || invalidOutput.exists())throw new AssertionError("Invalid RAW did not fail closed");
            if(inputs.containsKey("rawOriginal")) {
                PyObject rawModule=python.getModule("android_raw"),hashlib=python.getModule("hashlib");
                String first=null;String[] rotatedHashes=new String[2];double baselineMean=0;
                for(String key:new String[]{"rawOriginal","rawChanged"}) {
                    java.util.List<PyObject> decoded=rawModule.callAttr("decode",inputs.getString(key),directory.toString()).asList();
                    PyObject pixels=decoded.get(0),metadata=decoded.get(1);
                    if(metadata.callAttr("__getitem__","embedded_preview_used").toBoolean())throw new AssertionError("A JPEG preview was used");
                    if(inputs.containsKey("rawWidth") && inputs.containsKey("rawHeight")) {
                        if(metadata.callAttr("__getitem__","width").toInt()!=Integer.parseInt(inputs.getString("rawWidth"))
                                || metadata.callAttr("__getitem__","height").toInt()!=Integer.parseInt(inputs.getString("rawHeight"))
                                || !metadata.callAttr("__getitem__","camera_crop_applied").toBoolean())
                            throw new AssertionError("Camera active-area crop did not match the fixture");
                        result.putBoolean("rawCameraCrop",true);
                    }
                    String digest=hashlib.callAttr("sha256",pixels.callAttr("tobytes")).callAttr("hexdigest").toString();
                    if(first==null){
                        first=digest;
                        for(PyObject channel:python.getModule("PIL.ImageStat").callAttr("Stat",pixels).get("mean").asList())baselineMean+=channel.toDouble();
                        String[] turns={"ROTATE_270","ROTATE_90"};
                        for(int i=0;i<turns.length;i++) {
                            PyObject rotated=pixels.callAttr("transpose",python.getModule("PIL.Image").get("Transpose").get(turns[i]));
                            rotatedHashes[i]=hashlib.callAttr("sha256",rotated.callAttr("tobytes")).callAttr("hexdigest").toString();
                            rotated.callAttr("close");
                        }
                    }
                    else if(!first.equals(digest))throw new AssertionError("Changing the embedded JPEG changed sensor development");
                    result.putString("rawCamera",metadata.callAttr("__getitem__","camera_model").toString());
                    result.putString("rawDecoder",metadata.callAttr("__getitem__","decoder").toString());
                    result.putString("rawDimensions",pixels.get("size").toString());
                    pixels.callAttr("close");
                }
                result.putString("rawSensorSha256",first);
                result.putBoolean("rawIndependentOfEmbeddedJpeg",true);
                java.util.List<PyObject> darker=rawModule.callAttr("decode",inputs.getString("rawOriginal"),directory.toString(),new Kwarg("exposure",-2.0)).asList();
                PyObject darkPixels=darker.get(0);double darkMean=0;
                for(PyObject channel:python.getModule("PIL.ImageStat").callAttr("Stat",darkPixels).get("mean").asList())darkMean+=channel.toDouble();
                if(!darker.get(1).callAttr("__getitem__","sensor_exposure_applied").toBoolean() || !(darkMean>0 && darkMean<baselineMean))
                    throw new AssertionError("Sensor exposure was not applied");
                darkPixels.callAttr("close");result.putBoolean("rawSensorExposure",true);
                String[] portraitKeys={"rawPortraitCW","rawPortraitCCW"};
                for(int i=0;i<portraitKeys.length;i++)if(inputs.containsKey(portraitKeys[i])) {
                    java.util.List<PyObject> portrait=rawModule.callAttr("decode",inputs.getString(portraitKeys[i]),directory.toString()).asList();
                    PyObject portraitPixels=portrait.get(0);
                    String digest=hashlib.callAttr("sha256",portraitPixels.callAttr("tobytes")).callAttr("hexdigest").toString();
                    if(!rotatedHashes[i].equals(digest))throw new AssertionError("Portrait RAW was not an exact rotation of the active sensor crop");
                    portraitPixels.callAttr("close");result.putBoolean(portraitKeys[i],true);
                }
            }
            File photo=new File(directory,"portrait.png");
            PyObject size=python.getBuiltins().callAttr("tuple",new int[]{40,80});
            PyObject color=python.getBuiltins().callAttr("tuple",new int[]{100,80,60});
            PyObject image=python.getModule("PIL.Image").callAttr("new","RGB",size,color);
            image.callAttr("save",photo.toString());
            PyObject editor=python.getModule("mobile_editor").callAttr("Editor",new File(directory,"editor").toString());
            editor.callAttr("open",photo.toString());
            if(inputs.containsKey("np3Source")) {
                editor.callAttr("open",inputs.getString("np3Profile"),"nikon_profile");
                JSONObject imported=new JSONObject(editor.callAttr("open",inputs.getString("np3Source")).toString());
                if(imported.getJSONArray("references").length()!=1
                        || !imported.getJSONObject("edit").getJSONArray("luts").getJSONObject(0)
                        .getJSONObject("metadata").getString("conversionVersion").equals(conversion))
                    throw new AssertionError("NP3 import lost photo or used stale conversion");
                result.putBoolean("np3Converted",true);
            }
            editor.callAttr("update","{\"contrast\":2}");
            JSONObject rendered=new JSONObject(editor.callAttr("render").toString());
            android.graphics.Bitmap preview=android.graphics.BitmapFactory.decodeFile(rendered.getString("after"));
            if(preview==null || preview.getWidth()!=40 || preview.getHeight()!=80)throw new AssertionError("Portrait dimensions changed");
            File pf3=new File(directory,"test.pf3");editor.callAttr("export",pf3.toString(),false);
            if(pf3.length()!=434511)throw new AssertionError("PF3 size mismatch");
            File project=new File(directory,"test.canonstyleproject");editor.callAttr("export",project.toString(),true);
            editor.callAttr("update","{\"contrast\":-1}");
            JSONObject loaded=new JSONObject(editor.callAttr("open",project.toString()).toString());
            if(loaded.getJSONObject("edit").getInt("contrast")!=2 || loaded.getJSONArray("references").length()!=1)
                throw new AssertionError("Portable project round trip lost edits or photos");
            editor.callAttr("checkpoint");
            PyObject restored=python.getModule("mobile_editor").callAttr("Editor",new File(directory,"editor").toString());
            JSONObject recovered=new JSONObject(restored.callAttr("state").toString());
            if(recovered.getJSONObject("edit").getInt("contrast")!=2)throw new AssertionError("Session recovery failed");
            PyObject main=python.getModule("mobile_editor").callAttr("Editor",context.getFilesDir().toString());
            main.callAttr("open",photo.toString());
            File uiLut=new File(directory,"ui-look.cube");
            try(java.io.FileOutputStream output=new java.io.FileOutputStream(uiLut)) {
                output.write("LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n".getBytes(java.nio.charset.StandardCharsets.UTF_8));
            }
            main.callAttr("open",uiLut.toString(),"lut");main.callAttr("checkpoint");
            Intent intent=new Intent(context,EditorActivity.class);intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            Activity activity=startActivitySync(intent);waitForIdleSync();
            if(activity==null)throw new AssertionError("Activity failed to start");
            java.util.concurrent.atomic.AtomicBoolean ready=new java.util.concurrent.atomic.AtomicBoolean();
            long deadline=android.os.SystemClock.elapsedRealtime()+30000;
            while(!ready.get() && android.os.SystemClock.elapsedRealtime()<deadline) {
                runOnMainSync(()->{
                    android.widget.TextView status=activity.getWindow().getDecorView().findViewWithTag("editor-status");
                    ready.set(status!=null && status.getText().toString().contains("Image"));
                });
                if(!ready.get())android.os.SystemClock.sleep(100);
            }
            if(!ready.get())throw new AssertionError("Activity did not finish rendering");
            for(String tool:new String[]{"RAW","Styles","Color","LUTs","Generate","RAW"}) {
                runOnMainSync(()->{
                    android.view.View photoView=activity.getWindow().getDecorView().findViewWithTag("photo-preview");
                    android.view.View tab=activity.getWindow().getDecorView().findViewWithTag("tool-"+tool);
                    if(tab==null || photoView==null || photoView.getHeight()<100)throw new AssertionError("Missing fixed preview or tool "+tool);
                    int height=photoView.getHeight();tab.performClick();
                    if(tool.equals("LUTs") && activity.getWindow().getDecorView().findViewWithTag("lut-opacity-0")==null)
                        throw new AssertionError("LUT opacity is missing from the panel");
                    if(photoView.getHeight()!=height || !photoView.isShown())throw new AssertionError("Tool hid the photo");
                });waitForIdleSync();
            }
            runOnMainSync(()->{
                android.view.View root=activity.getWindow().getDecorView();
                root.findViewWithTag("tool-Color").performClick();
                root.findViewWithTag("color-adjustments").performClick();
                if(!root.findViewWithTag("photo-preview").isShown()
                        || root.findViewWithTag("cancel-color-adjustments")==null)
                    throw new AssertionError("Colour adjustments must stay inside the panel");
                root.findViewWithTag("cancel-color-adjustments").performClick();
                root.findViewWithTag("tool-RAW").performClick();
            });waitForIdleSync();
            result.putBoolean("inlineColorPanel",true);
            runOnMainSync(()->{
                android.view.View label=activity.getWindow().getDecorView().findViewWithTag("reset-raw_exposure");
                android.widget.SeekBar slider=activity.getWindow().getDecorView().findViewWithTag("adjustment-raw_exposure");
                slider.setProgress(70);long start=android.os.SystemClock.uptimeMillis();
                for(int tap=0;tap<2;tap++)for(int action:new int[]{android.view.MotionEvent.ACTION_DOWN,android.view.MotionEvent.ACTION_UP}) {
                    long time=start+tap*100+(action==android.view.MotionEvent.ACTION_UP?30:0);
                    android.view.MotionEvent event=android.view.MotionEvent.obtain(start+tap*100,time,action,10,10,0);
                    label.dispatchTouchEvent(event);event.recycle();
                }
                if(slider.getProgress()!=50)throw new AssertionError("Double tap did not reset exposure");
            });
            result.putBoolean("doubleTapReset",true);
            File generated=new File(directory,"generated.cube");editor.callAttr("export_cube",generated.toString());
            if(generated.length()<1000)throw new AssertionError("LUT export missing");
            result.putBoolean("bottomToolsAndLutExport",true);
            waitForIdleSync();android.os.SystemClock.sleep(500);
            android.graphics.Bitmap screenshot=getUiAutomation().takeScreenshot();
            if(screenshot==null)throw new AssertionError("Could not capture candidate UI");
            try(java.io.FileOutputStream output=new java.io.FileOutputStream(new File(context.getFilesDir(),"candidate-ui.png"))) {
                screenshot.compress(android.graphics.Bitmap.CompressFormat.PNG,100,output);
            }
            result.putString("result","PASS: native Python/Pillow/NumPy, portrait, PF3, portable project, photo preservation, session recovery, activity launch");
            finish(Activity.RESULT_OK,result);
        } catch(Throwable error) {
            result.putString("result","FAIL: "+android.util.Log.getStackTraceString(error));finish(Activity.RESULT_CANCELED,result);
        }
    }
}
