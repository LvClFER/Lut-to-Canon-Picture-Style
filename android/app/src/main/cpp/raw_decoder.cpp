#include <jni.h>
#include <libraw/libraw.h>
#include <cstdio>
#include <cmath>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
std::string path(JNIEnv* env,jbyteArray encoded) {
    if(!encoded)throw std::runtime_error("Missing RAW path");
    const jsize length=env->GetArrayLength(encoded);
    if(length<=0 || length>=4096)throw std::runtime_error("Invalid RAW path length");
    std::string value(static_cast<size_t>(length),'\0');
    env->GetByteArrayRegion(encoded,0,length,reinterpret_cast<jbyte*>(value.data()));
    if(value.find('\0')!=std::string::npos)throw std::runtime_error("Invalid RAW path");
    return value;
}
void checked(int result,const char* phase) {
    if(result!=LIBRAW_SUCCESS)throw std::runtime_error(std::string(phase)+": "+libraw_strerror(result));
}
std::string quoted(const char* value) {
    std::string result="\"";
    for(const unsigned char* c=reinterpret_cast<const unsigned char*>(value);*c;c++) {
        if(*c=='"'||*c=='\\'){result+='\\';result+=static_cast<char>(*c);}
        else if(*c>=32 && *c<127)result+=static_cast<char>(*c);
        else result+='?';
    }
    return result+'"';
}
}

extern "C" JNIEXPORT jstring JNICALL
Java_org_canonstylestudio_mobile_NativeRaw_developNative(JNIEnv* env,jclass,jbyteArray source,jbyteArray destination,jint wbMode,jdouble exposure) {
    std::string output;
    bool created=false;
    try {
        if(wbMode<0 || wbMode>2)throw std::runtime_error("Invalid RAW white balance mode");
        if(!std::isfinite(exposure) || exposure < -5 || exposure > 5)throw std::runtime_error("Invalid RAW exposure");
        std::string input=path(env,source);output=path(env,destination);
        if(input==output)throw std::runtime_error("RAW input cannot be overwritten");
        LibRaw processor;
        auto& params=processor.imgdata.params;
        processor.imgdata.rawparams.max_raw_memory_mb=256;
        params.half_size=1;
        params.output_bps=8;
        params.output_color=1;
        params.use_camera_wb=wbMode==0;
        params.use_auto_wb=wbMode==1;
        params.use_camera_matrix=1;
        params.no_auto_bright=0;
        params.bright=static_cast<float>(std::exp2(exposure));
        params.gamm[0]=1.0/2.4;
        params.gamm[1]=12.92;
        checked(processor.open_file(input.c_str()),"Open RAW");
        checked(processor.unpack(),"Unpack sensor RAW");
        const auto& sizes=processor.imgdata.sizes;
        const auto& crop=sizes.raw_inset_crops[0];
        const bool cameraCrop=crop.cleft<0xffff && crop.ctop<0xffff && crop.cwidth>0 && crop.cheight>0
            && crop.cleft>=sizes.left_margin && crop.ctop>=sizes.top_margin
            && static_cast<unsigned>(crop.cleft-sizes.left_margin)+crop.cwidth<=sizes.width
            && static_cast<unsigned>(crop.ctop-sizes.top_margin)+crop.cheight<=sizes.height;
        if(cameraCrop) {
            // Vendor coordinates include sensor margins; LibRaw's crop box does not.
            params.cropbox[0]=crop.cleft-sizes.left_margin;
            params.cropbox[1]=crop.ctop-sizes.top_margin;
            params.cropbox[2]=crop.cwidth;
            params.cropbox[3]=crop.cheight;
        }
        checked(processor.dcraw_process(),"Develop sensor RAW");
        int error=0;
        std::unique_ptr<libraw_processed_image_t,decltype(&LibRaw::dcraw_clear_mem)> image(
            processor.dcraw_make_mem_image(&error),&LibRaw::dcraw_clear_mem);
        checked(error,"Read developed pixels");
        if(!image || image->type!=LIBRAW_IMAGE_BITMAP || image->colors!=3 || image->bits!=8
                || image->width==0 || image->height==0
                || static_cast<size_t>(image->width)*image->height>20000000
                || image->data_size!=static_cast<size_t>(image->width)*image->height*3)
            throw std::runtime_error("Unexpected or oversized developed RAW image");
        // Exclusive creation prevents accidental source/cache overwrite on failure.
        std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(output.c_str(),"wbx"),&std::fclose);
        if(!file)throw std::runtime_error("Cannot create the private RAW preview");
        created=true;
        if(std::fprintf(file.get(),"P6\n%u %u\n255\n",image->width,image->height)<0
                || std::fwrite(image->data,1,image->data_size,file.get())!=image->data_size
                || std::fflush(file.get())!=0)throw std::runtime_error("Writing RAW preview failed");
        std::string metadata="{\"decoder\":\"LibRaw "+std::string(LibRaw::version())+" · sensor RAW\",\"camera_make\":"
            +quoted(processor.imgdata.idata.make)+",\"camera_model\":"+quoted(processor.imgdata.idata.model)
            +",\"width\":"+std::to_string(image->width)+",\"height\":"+std::to_string(image->height)
            +",\"camera_crop_applied\":"+(cameraCrop?"true":"false")
            +",\"embedded_preview_used\":false,\"sensor_exposure_applied\":true,\"brightness_normalization\":\"LibRaw histogram\",\"output_transfer\":\"sRGB\",\"canon_base_render_verified\":false}";
        return env->NewStringUTF(metadata.c_str());
    } catch(const std::exception& error) {
        if(created)std::remove(output.c_str());
        env->ThrowNew(env->FindClass("java/io/IOException"),error.what());
    } catch(...) {
        if(created)std::remove(output.c_str());
        env->ThrowNew(env->FindClass("java/io/IOException"),"Native RAW development failed");
    }
    return nullptr;
}
