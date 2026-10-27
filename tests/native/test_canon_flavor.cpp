#include "../../android/app/src/main/cpp/canon_flavor.h"
#include <array>

constexpr auto fixture(int word) {
    std::array<unsigned char,32476> bytes{};
    bytes[0]=0xdc;bytes[1]=0x7e;
    bytes[4]=0x0b;bytes[7]=0x20;
    bytes[0x43f4]=word&255;bytes[0x43f5]=(word&65535)>>8;
    return bytes;
}
constexpr bool check(int word) {
    const auto bytes=fixture(word);
    const auto result=canon::flavorBaseline(bytes.data(),bytes.size());
    return result.valid && result.tenThousandths==word;
}
static_assert(check(3326) && check(3240) && check(2613) && check(0));
static_assert(check(-32768) && check(32767) && check(-10000));
constexpr bool malformed() {
    auto bytes=fixture(3326);
    if(canon::flavorBaseline(bytes.data(),100).valid)return false;
    if(canon::flavorBaseline(bytes.data(),bytes.size()-1).valid)return false;
    bytes[4]=0x0c;
    return !canon::flavorBaseline(bytes.data(),bytes.size()).valid
        && !canon::flavorBaseline(nullptr,32476).valid;
}
static_assert(malformed());
