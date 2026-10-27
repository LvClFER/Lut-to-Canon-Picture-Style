#pragma once
#include <cstddef>
#include <cstdint>

namespace canon {
struct BaselineExposure { bool valid; int tenThousandths; };

constexpr std::uint32_t little32(const unsigned char* p) {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1])<<8)
        | (std::uint32_t(p[2])<<16) | (std::uint32_t(p[3])<<24);
}

constexpr BaselineExposure flavorBaseline(const unsigned char* data,std::size_t size) {
    // shortcut: only the Flavor version verified against user RAW files is decoded.
    if(!data || size<0x43f6 || size>1024*1024 || little32(data)!=size
            || little32(data+4)!=0x2000000b)return {false,0};
    const int word=int(data[0x43f4]) | (int(data[0x43f5])<<8);
    return {true,word>=0x8000 ? word-0x10000 : word};
}
}
