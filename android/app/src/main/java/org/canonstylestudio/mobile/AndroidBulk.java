package org.canonstylestudio.mobile;

import android.hardware.usb.*;
import java.io.IOException;

/** Owned Canon still-image bulk interface, after the user grants USB permission. */
public final class AndroidBulk implements AutoCloseable {
    private final UsbDeviceConnection connection;
    private final UsbInterface camera;
    private final UsbEndpoint input, output;
    private boolean closed;

    public AndroidBulk(UsbManager manager, UsbDevice device) throws IOException {
        if (device.getVendorId() != 0x04a9 || !manager.hasPermission(device))
            throw new IOException("Explicit permission for the selected Canon camera is required");
        UsbInterface selected=null; UsbEndpoint in=null, out=null;
        for(int i=0;i<device.getInterfaceCount();i++) {
            UsbInterface candidate=device.getInterface(i);
            if(candidate.getInterfaceClass()!=UsbConstants.USB_CLASS_STILL_IMAGE) continue;
            UsbEndpoint a=null,b=null;
            for(int j=0;j<candidate.getEndpointCount();j++) {
                UsbEndpoint endpoint=candidate.getEndpoint(j);
                if(endpoint.getType()!=UsbConstants.USB_ENDPOINT_XFER_BULK) continue;
                if(endpoint.getDirection()==UsbConstants.USB_DIR_IN) a=endpoint;
                else b=endpoint;
            }
            if(a!=null && b!=null) {
                if(selected!=null) throw new IOException("Ambiguous camera USB interfaces");
                selected=candidate;in=a;out=b;
            }
        }
        if(selected==null) throw new IOException("Camera has no still-image bulk interface");
        UsbDeviceConnection opened=manager.openDevice(device);
        if(opened==null) throw new IOException("Could not open the selected camera");
        if(!opened.claimInterface(selected,false)) { opened.close();throw new IOException("Camera interface is already in use"); }
        connection=opened;camera=selected;input=in;output=out;
    }

    public synchronized String readHex(int size,int timeout) throws IOException {
        check(size,timeout);byte[] bytes=new byte[size];
        int actual=connection.bulkTransfer(input,bytes,size,timeout);
        if(actual<=0) throw new IOException("USB read failed or timed out");
        char[] encoded=new char[actual*2];String hex="0123456789abcdef";
        for(int i=0;i<actual;i++) { int value=bytes[i]&255;encoded[i*2]=hex.charAt(value>>>4);encoded[i*2+1]=hex.charAt(value&15); }
        return new String(encoded);
    }

    public synchronized int writeHex(String encoded,int timeout) throws IOException {
        if(encoded==null || (encoded.length()&1)!=0) throw new IOException("Invalid USB byte buffer");
        int size=encoded.length()/2;check(size,timeout);byte[] bytes=new byte[size];
        for(int i=0;i<size;i++) {
            int high=Character.digit(encoded.charAt(i*2),16),low=Character.digit(encoded.charAt(i*2+1),16);
            if(high<0||low<0)throw new IOException("Invalid USB byte buffer");
            bytes[i]=(byte)((high<<4)|low);
        }
        return connection.bulkTransfer(output,bytes,size,timeout);
    }

    private void check(int size,int timeout) throws IOException {
        if(closed || size<=0 || size>16384 || timeout<=0 || timeout>45000)
            throw new IOException("USB connection unavailable or invalid bounds");
    }

    @Override public synchronized void close() {
        if(!closed) { closed=true;try { connection.releaseInterface(camera); } finally { connection.close(); } }
    }
}
