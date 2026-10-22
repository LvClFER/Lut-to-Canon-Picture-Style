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
            main.callAttr("open",photo.toString());main.callAttr("checkpoint");
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
