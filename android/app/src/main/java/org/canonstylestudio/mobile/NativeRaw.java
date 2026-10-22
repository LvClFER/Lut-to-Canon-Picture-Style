package org.canonstylestudio.mobile;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

/** LibRaw decodes the sensor plane. Embedded thumbnails are never requested. */
public final class NativeRaw {
    static { System.loadLibrary("canonraw"); }
    private NativeRaw() {}
    private static native String developNative(byte[] input,byte[] output,int wbMode,double exposure) throws IOException;
    public static String develop(String input,String output,int wbMode) throws IOException {
        return develop(input,output,wbMode,0);
    }
    public static String develop(String input,String output,int wbMode,double exposure) throws IOException {
        return developNative(input.getBytes(StandardCharsets.UTF_8),output.getBytes(StandardCharsets.UTF_8),wbMode,exposure);
    }
}
