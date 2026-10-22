package org.canonstylestudio.mobile;

import android.app.*;
import android.content.*;
import android.hardware.usb.*;
import android.os.*;
import com.chaquo.python.*;
import com.chaquo.python.android.AndroidPlatform;
import org.json.JSONObject;
import java.io.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** A dedicated app process with a hard deadline; never restarts a transfer. */
public final class CameraWorker extends Service {
    private final AtomicBoolean completed=new AtomicBoolean();
    private final AtomicBoolean started=new AtomicBoolean();
    private final Handler timer=new Handler(Looper.getMainLooper());
    @Override public IBinder onBind(Intent intent) { return null; }
    @Override public int onStartCommand(Intent intent,int flags,int id) {
        if(intent==null || !started.compareAndSet(false,true))return START_NOT_STICKY;
        NotificationManager manager=getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel("camera","Camera transfer",NotificationManager.IMPORTANCE_LOW));
        Notification.Builder notification=new Notification.Builder(this,"camera");
        startForeground(1,notification.setContentTitle("Canon Style Studio").setContentText("Installing Picture Style. Keep USB connected.")
            .setSmallIcon(android.R.drawable.stat_sys_upload).build());
        final String request=intent.getStringExtra("request");
        timer.postDelayed(()->finish(request,false,"The 45-second camera deadline expired. The transfer was not repeated; camera recovery may be required."),45000);
        new Thread(()->{
            try {
                UsbDevice device=intent.getParcelableExtra("device");
                int slot=intent.getIntExtra("slot",0);
                if(device==null || slot<1 || slot>3 || request==null || !request.matches("[0-9a-f-]{36}"))
                    throw new IOException("Invalid explicit camera request");
                File source=new File(intent.getStringExtra("source")).getCanonicalFile();
                File allowed=new File(getFilesDir(),"camera-jobs/"+request).getCanonicalFile();
                if(!source.getParentFile().equals(allowed))throw new IOException("Camera source is outside its private job");
                String result;
                try(AndroidBulk bulk=new AndroidBulk((UsbManager)getSystemService(USB_SERVICE),device)) {
                    if(!Python.isStarted())Python.start(new AndroidPlatform(getApplicationContext()));
                    PyObject os=Python.getInstance().getModule("os");
                    os.get("environ").callAttr("__setitem__","CANON_STYLE_STUDIO_PORTABLE_ROOT",getFilesDir().toString());
                    result=Python.getInstance().getModule("mobile_camera").callAttr("install",bulk,source.toString(),slot,
                        new File(allowed,"slot-backup.bin").toString()).toString();
                }
                finish(request,true,result);
            } catch(Throwable error) { finish(request,false,error.toString()); }
        },"camera-transfer").start();
        return START_NOT_STICKY;
    }
    private void finish(String request,boolean success,String detail) {
        if(!completed.compareAndSet(false,true))return;
        timer.removeCallbacksAndMessages(null);
        try {
            JSONObject result=new JSONObject().put("request",request).put("success",success).put("detail",detail);
            File target=new File(getFilesDir(),"camera-result.json"),temporary=new File(getFilesDir(),"camera-result.json.tmp");
            try(FileOutputStream stream=new FileOutputStream(temporary)) {
                stream.write(result.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));stream.getFD().sync();
            }
            if(!temporary.renameTo(target))throw new IOException("Could not publish the camera result");
        } catch(Exception error) { android.util.Log.e("CanonCamera","Could not save result",error); }
        stopForeground(true);stopSelf();
        // This Service owns only the :camera process, never the editor process.
        android.os.Process.killProcess(android.os.Process.myPid());
    }
}
