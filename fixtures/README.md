# Runtime / validation fixtures

The ready-to-run experimental bundle contains compact binary fixtures used by the current compiler self-test and EOS RP carrier construction. They are intentionally not committed to the public source tree.

Expected files in the packaged build:

| Path | SHA-256 |
|---|---|
| `REFERENCE/1300D_CAMERA_ID.bin` | `898b7b827df342c282579b0cc635d75601af4fa5d6a78f7309b8e40a4051730c` |
| `REFERENCE/1300D_DESCRIPTOR_7772.bin` | `649693d61f816ddeda7b1b2ee2ba1421a92d593efe96ed2f9ba218f162b6b3f0` |
| `REFERENCE/RP_SUPERIA_TEMPLATE_16752.bin` | `68c971e8fd62b626eb3d97df889060018e546c282e20a53e6dfb028bbe51edc6` |
| `SELFTEST/SUPERIA_EXPECTED_BLOCK_8192.bin` | `803efd8609e43d7c1fd612513539ce26c5d2e00304a1a6429bf1003f01b9de1c` |
| `SELFTEST/SUPERIA_SELFTEST.pf3` | `c1167362652535e9d591689fa82c53a6bf03e2fecad4dedb6c1dcf22fd26f860` |
| `SOURCE/BASE_NEUTRAL_RP.pf3` | `51959f04d1eeac4ec41f4158c9ec2dfabea79c4380473edf8eaccce6274e481c` |

The repository does not distribute Canon DLLs. The program locates the required Canon compiler/runtime from the user's own Canon installation.
